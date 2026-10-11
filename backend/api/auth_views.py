"""
api/auth_views.py — user registration, token login/logout, identity, and the
staff-only usage overview endpoint.

Authentication model
--------------------
The React frontend exchanges credentials for a DRF ``Token`` (stored in the
``authtoken_token`` table) and sends it on every request as
``Authorization: Token <key>``.  The admin panel works the same way — an admin
is just a user with ``is_staff=True`` (created via ``createsuperuser``).

All views here are light function-based API views that return only primitive
JSON (no large analysis matrices), so they are cheap for the frontend to poll.
"""

import os
import posixpath
import re
import secrets
from collections.abc import Mapping
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes
from django.utils.http import base36_to_int, urlsafe_base64_decode, urlsafe_base64_encode
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import AudioRecording, EmailVerification
from .emails import email_configured, send_email

User = get_user_model()


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Stateless, single-use token for the sign-up email-confirmation link.

    The hash includes ``is_active`` so that once the account is activated the
    token no longer validates.  Expiry uses ``EMAIL_VERIFICATION_TIMEOUT``
    (24 h) rather than the shorter password-reset window.
    """

    key_salt = 'api.tokens.EmailVerificationTokenGenerator'

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{timestamp}{user.email}{user.is_active}'

    def check_token(self, user, token):
        if not (user and token):
            return False
        try:
            ts_b36, _ = token.split('-')
            ts = base36_to_int(ts_b36)
        except (ValueError, AttributeError):
            return False
        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret), token
            ):
                break
        else:
            return False
        timeout = getattr(settings, 'EMAIL_VERIFICATION_TIMEOUT', 86400)
        if (self._num_seconds(self._now()) - ts) > timeout:
            return False
        return True


email_verification_generator = EmailVerificationTokenGenerator()


def _is_email_verified(user) -> bool:
    """Users without an EmailVerification row are considered verified."""
    record = getattr(user, 'email_verification', None)
    return record is None or record.verified


class RegisterAnonThrottle(AnonRateThrottle):
    """Strict per-IP rate limit on new user registrations to mitigate bot abuse."""
    scope = 'register_anon'


class LoginAnonThrottle(AnonRateThrottle):
    """Per-IP rate limit on login attempts to mitigate brute-force credential stuffing."""
    scope = 'login_anon'


class GoogleAnonThrottle(AnonRateThrottle):
    """Per-IP rate limit on Google OAuth token exchanges."""
    scope = 'google_anon'


class PasswordResetAnonThrottle(AnonRateThrottle):
    """Per-IP rate limit on password-reset requests to prevent email bombing."""
    scope = 'password_reset_anon'


class VerifyAnonThrottle(AnonRateThrottle):
    """Per-IP rate limit on email-verification resend requests."""
    scope = 'verify_anon'


def _user_payload(user) -> dict:
    """Compact, serialisable description of a user for the frontend."""
    return {
        'id':          user.id,
        'username':    user.username,
        'email':       user.email,
        'first_name':  user.first_name,
        'last_name':   user.last_name,
        'is_staff':    user.is_staff,
        'is_superuser': user.is_superuser,
        'is_active':   user.is_active,
        'date_joined': user.date_joined.isoformat(),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterAnonThrottle])
def register(request):
    """
    POST /api/auth/register/

    Body: { username, email, password, first_name?, last_name? }
    Returns: { user, verification_required: true } on success (201); the
    account is created locked (inactive) and a verification email is sent.
    { error } on failure (400); 503 when email is not configured.
    """
    username   = (request.data.get('username') or '').strip()
    email      = (request.data.get('email') or '').strip()
    password   = request.data.get('password') or ''
    first_name = (request.data.get('first_name') or '').strip()
    last_name  = (request.data.get('last_name') or '').strip()

    if not username or not password:
        return Response(
            {'error': 'username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(username) < 3 or len(username) > 150:
        return Response(
            {'error': 'Username must be between 3 and 150 characters.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not re.match(r'^[\w.@+-]+$', username):
        return Response(
            {'error': 'Username contains invalid characters.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    username_field = User._meta.get_field('username')
    if len(username) > username_field.max_length:
        return Response(
            {'error': f'Username must be {username_field.max_length} characters or fewer.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        username_field.run_validators(username)
    except ValidationError as exc:
        return Response(
            {'error': ' '.join(exc.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not email:
        return Response(
            {'error': 'Email is required to create an account.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {'error': 'Invalid email address format.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username__iexact=username).exists():
        return Response(
            {'error': 'A user with that username already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email__iexact=email).exists():
        return Response(
            {'error': 'An account with that email already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters long.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) > 128:
        return Response(
            {'error': 'Password must not exceed 128 characters.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Without a working mail provider the user could never verify, so refuse to
    # create an unusable account.
    if not email_configured():
        return Response(
            {'error': 'Account creation is temporarily unavailable because email '
                      'delivery is not configured. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )
        EmailVerification.objects.create(user=user, verified=False)

    sent = _send_verification_email(user)
    return Response(
        {
            'user': _user_payload(user),
            'verification_required': True,
            'message': 'Account created. Check your email to verify your address '
                       'before signing in.',
            'email_sent': sent,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginAnonThrottle])
def login(request):
    """
    POST /api/auth/login/

    Body: { username | email, password }
    Returns: { token, user } on success (200); { error } on failure.
    Unverified accounts are refused with 403 until they confirm their email.
    """
    identifier = request.data.get('username') or request.data.get('email') or ''
    password   = request.data.get('password') or ''
    identifier = str(identifier).strip()

    if not identifier or not password:
        return Response(
            {'error': 'username/email and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if '@' in identifier:
        candidate = User.objects.filter(email__iexact=identifier).first()
    else:
        candidate = User.objects.filter(username=identifier).first()

    if candidate is None or not candidate.check_password(password):
        return Response(
            {'error': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if _needs_verification(candidate):
        return Response(
            {'error': 'Please verify your email address before signing in.',
             'verification_required': True},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not candidate.is_active:
        return Response(
            {'error': 'This account has been disabled.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    user = candidate
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': _user_payload(user)})


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """
    POST /api/auth/logout/

    Revokes the caller's token server-side.  The frontend should also discard
    its locally stored token.
    """
    Token.objects.filter(user=request.user).delete()
    return Response({'message': 'Logged out.'})


def _send_password_reset_email(user, reset_link: str) -> bool:
    """Send the reset email; returns True when the provider accepted it."""
    name = (user.first_name or user.username or 'there').strip()
    subject = 'Reset your Vedic Acoustica password'
    text_body = (
        f'Hello {name},\n\n'
        'We received a request to reset the password for your Vedic Acoustica '
        'account. Open the link below to choose a new password:\n\n'
        f'{reset_link}\n\n'
        'This link expires in 1 hour. If you did not request a password reset, '
        'you can safely ignore this email — your password will not change.\n\n'
        '— Vedic Acoustica'
    )
    html_body = f"""\
<div style="font-family:Segoe UI,Helvetica,Arial,sans-serif;max-width:520px;margin:0 auto;color:#231f1a">
  <h2 style="font-weight:600">Reset your password</h2>
  <p>Hello {name},</p>
  <p>We received a request to reset the password for your <strong>Vedic Acoustica</strong> account.</p>
  <p style="margin:28px 0">
    <a href="{reset_link}" style="background:#b8860b;color:#fff;padding:12px 22px;border-radius:6px;text-decoration:none;display:inline-block">Choose a new password</a>
  </p>
  <p style="font-size:13px;color:#6b6157">Or paste this link into your browser:<br>
    <a href="{reset_link}" style="color:#8a6d1f;word-break:break-all">{reset_link}</a>
  </p>
  <p style="font-size:13px;color:#6b6157">This link expires in 1 hour. If you did not request a reset, you can ignore this email.</p>
  <p style="font-size:13px;color:#6b6157">— Vedic Acoustica</p>
</div>"""
    return send_email(user.email, subject, text_body, html_body)


def _verification_link(user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_generator.make_token(user)
    base = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
    return f'{base}/?verify=1&uid={uid}&token={token}'


def _send_verification_email(user) -> bool:
    """Send the sign-up verification email; returns True when accepted."""
    link = _verification_link(user)
    name = (user.first_name or user.username or 'there').strip()
    subject = 'Verify your Vedic Acoustica email'
    text_body = (
        f'Hello {name},\n\n'
        'Welcome to Vedic Acoustica. Confirm your email address to activate '
        'your account by opening the link below:\n\n'
        f'{link}\n\n'
        'This link expires in 24 hours. If you did not create an account, you '
        'can ignore this email.\n\n'
        '— Vedic Acoustica'
    )
    html_body = f"""\
<div style="font-family:Segoe UI,Helvetica,Arial,sans-serif;max-width:520px;margin:0 auto;color:#231f1a">
  <h2 style="font-weight:600">Verify your email</h2>
  <p>Hello {name},</p>
  <p>Welcome to <strong>Vedic Acoustica</strong>. Confirm your email address to activate your account.</p>
  <p style="margin:28px 0">
    <a href="{link}" style="background:#b8860b;color:#fff;padding:12px 22px;border-radius:6px;text-decoration:none;display:inline-block">Verify email address</a>
  </p>
  <p style="font-size:13px;color:#6b6157">Or paste this link into your browser:<br>
    <a href="{link}" style="color:#8a6d1f;word-break:break-all">{link}</a>
  </p>
  <p style="font-size:13px;color:#6b6157">This link expires in 24 hours. If you did not create an account, you can ignore this email.</p>
  <p style="font-size:13px;color:#6b6157">— Vedic Acoustica</p>
</div>"""
    return send_email(user.email, subject, text_body, html_body)


def _user_from_uid(uid: str):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        return User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError,
            UnicodeDecodeError):
        return None


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([VerifyAnonThrottle])
def verify_email(request):
    """
    POST /api/auth/verify-email/

    Body: { uid, token }

    Activates a pending sign-up once the emailed link's token is verified.
    """
    uid = (request.data.get('uid') or '').strip()
    token = (request.data.get('token') or '').strip()
    if not uid or not token:
        return Response(
            {'error': 'This verification link is invalid or incomplete.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = _user_from_uid(uid)
    if user is None or not email_verification_generator.check_token(user, token):
        return Response(
            {'error': 'This verification link is invalid or has expired. '
                      'You can request a new one.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    record, _ = EmailVerification.objects.get_or_create(user=user)
    if not record.verified:
        record.verified = True
        record.verified_at = timezone.now()
        record.save(update_fields=['verified', 'verified_at'])
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])

    return Response({'message': 'Email verified. You can now sign in.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([VerifyAnonThrottle])
def resend_verification(request):
    """
    POST /api/auth/verify-email/resend/

    Body: { email }

    Re-sends the verification link.  Always answers 200 so it never reveals
    whether an account exists.
    """
    if not email_configured():
        return Response(
            {'error': 'Email delivery is not configured. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    email = (request.data.get('email') or '').strip()
    if not email:
        return Response(
            {'error': 'Please enter your email address.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generic = {
        'message': 'If your account still needs verification, a new link is on '
                   'its way. Check your inbox and spam folder.'
    }

    user = User.objects.filter(email__iexact=email).first()
    if user is not None and _needs_verification(user):
        _send_verification_email(user)

    return Response(generic)


def _needs_verification(user) -> bool:
    record = getattr(user, 'email_verification', None)
    return record is not None and not record.verified


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetAnonThrottle])
def password_reset(request):
    """
    POST /api/auth/password-reset/

    Body: { email }

    Always answers 200 with a generic message so the response never reveals
    whether an account exists.  When the email matches an active user, a
    one-time reset link is emailed.  Returns 503 when no email provider is
    configured on the server.
    """
    if not email_configured():
        return Response(
            {'error': 'Password reset is not available right now. '
                      'Please contact the administrator.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    email = (request.data.get('email') or '').strip()
    if not email:
        return Response(
            {'error': 'Please enter your email address.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generic = {
        'message': 'If an account exists for that email, a reset link is on '
                   'its way. Check your inbox and spam folder.'
    }

    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is not None:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        base = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
        reset_link = f'{base}/?reset=1&uid={uid}&token={token}'
        _send_password_reset_email(user, reset_link)

    return Response(generic)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetAnonThrottle])
def password_reset_confirm(request):
    """
    POST /api/auth/password-reset/confirm/

    Body: { uid, token, password }

    Validates the one-time token and sets the new password.  All existing
    DRF tokens for the user are revoked so old sessions must sign in again.
    """
    uid = (request.data.get('uid') or '').strip()
    token = (request.data.get('token') or '').strip()
    password = request.data.get('password') or ''

    if not uid or not token:
        return Response(
            {'error': 'This reset link is invalid or incomplete.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters long.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(password) > 128:
        return Response(
            {'error': 'Password must not exceed 128 characters.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError,
            UnicodeDecodeError):
        user = None

    if user is None or not user.is_active or not default_token_generator.check_token(user, token):
        return Response(
            {'error': 'This reset link is invalid or has expired. '
                      'Please request a new one.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(password)
    user.save(update_fields=['password'])
    Token.objects.filter(user=user).delete()
    return Response({'message': 'Password updated. Please sign in.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([GoogleAnonThrottle])
def google_login(request):
    """
    POST /api/auth/google/

    Body: { credential: "<Google ID token JWT>" }

    Verifies the ID token issued by Google Identity Services against the
    GOOGLE_CLIENT_ID audience, then finds-or-creates the user by the verified
    email address.  Returns the same { token, user } shape as username login so
    the frontend can reuse its existing DRF token handling.  No password is ever
    stored on Google-created accounts (login is exclusively via Google).
    """
    _google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    if not _google_client_id:
        return Response(
            {'error': 'Google OAuth is not configured on the server '
                      '(GOOGLE_CLIENT_ID is unset).'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    credential = (request.data.get('credential') or '').strip()
    if not credential:
        return Response(
            {'error': 'credential (Google ID token) is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        info = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            _google_client_id,
        )
    except (ValueError, GoogleAuthError):
        return Response(
            {'error': 'Invalid or expired Google credential.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not info.get('email_verified'):
        return Response(
            {'error': 'The Google account email is not verified.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = (info.get('email') or '').strip().lower()
    if not email:
        return Response(
            {'error': 'The Google account has no email address.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        base = re.sub(r'[^a-z0-9._-]+', '', email.split('@')[0].lower()) or 'google'
        username = base
        while User.objects.filter(username__iexact=username).exists():
            username = f'{base[:20]}_{secrets.token_hex(3)}'
        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
            first_name=(info.get('given_name') or '').strip()[:150],
            last_name=(info.get('family_name') or '').strip()[:150],
        )

    record = getattr(user, 'email_verification', None)
    if record is not None and not record.verified:
        # Google has already verified ownership of this email address, so a
        # pending sign-up can be activated without a separate confirmation.
        record.verified = True
        record.verified_at = timezone.now()
        record.save(update_fields=['verified', 'verified_at'])
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

    if not user.is_active:
        return Response(
            {'error': 'This account has been disabled.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': _user_payload(user)})


def _delete_owned_recording_files(recording):
    """Remove a recording's media (audio + playback mp3 + matrices + progress)."""
    if recording.audio_file:
        storage = recording.audio_file.storage
        audio_name = recording.audio_file.name
        storage.delete(audio_name)
        storage.delete(f'{posixpath.splitext(audio_name)[0]}.mp3')

    if recording.matrices_file:
        media_root = Path(settings.MEDIA_ROOT).resolve()
        matrices_root = (media_root / 'analysis_matrices').resolve()
        matrices_path = (media_root / recording.matrices_file).resolve()
        if matrices_path.is_relative_to(matrices_root) and matrices_path != matrices_root:
            if matrices_path.is_file():
                matrices_path.unlink()

    from .views import _delete_progress
    _delete_progress(recording.pk)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    GET /api/auth/me/

    Returns the current user.  Used by the frontend to validate a stored
    token on page load and to learn the user's role (is_staff).

    PATCH /api/auth/me/

    Body: { username?, first_name?, last_name? }
    Updates only the authenticated user's username and name fields.
    """
    if request.method == 'PATCH':
        if not isinstance(request.data, Mapping):
            return Response(
                {'error': 'Profile updates must be a JSON object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        allowed_fields = {'username', 'first_name', 'last_name'}
        unexpected_fields = set(request.data) - allowed_fields
        if unexpected_fields:
            return Response(
                {'error': 'Only username and name can be changed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.data:
            return Response(
                {'error': 'Provide a username or name to update.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updates = {}
        for field in allowed_fields.intersection(request.data):
            value = request.data[field]
            if not isinstance(value, str):
                return Response(
                    {'error': f'{field} must be text.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            updates[field] = value.strip()

        if 'username' in updates:
            username = updates['username']
            if not username:
                return Response(
                    {'error': 'Username cannot be empty.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            username_field = User._meta.get_field('username')
            if len(username) > username_field.max_length:
                return Response(
                    {'error': f'Username must be {username_field.max_length} characters or fewer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                username_field.run_validators(username)
            except ValidationError as exc:
                return Response(
                    {'error': ' '.join(exc.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if User.objects.filter(username__iexact=username).exclude(
                pk=request.user.pk
            ).exists():
                return Response(
                    {'error': 'A user with that username already exists.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        name_fields = {'first_name', 'last_name'}.intersection(updates)
        if name_fields:
            first_name = updates.get('first_name', request.user.first_name)
            last_name = updates.get('last_name', request.user.last_name)
            if not f'{first_name} {last_name}'.strip():
                return Response(
                    {'error': 'Name cannot be empty.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            for field_name, value in (
                ('first_name', first_name),
                ('last_name', last_name),
            ):
                max_length = User._meta.get_field(field_name).max_length
                if max_length and len(value) > max_length:
                    return Response(
                        {'error': f'{field_name.replace("_", " ").title()} must be {max_length} characters or fewer.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            updates.update(first_name=first_name, last_name=last_name)

        for field, value in updates.items():
            setattr(request.user, field, value)
        request.user.save(update_fields=list(updates))
        return Response({'user': _user_payload(request.user)})

    return Response({'user': _user_payload(request.user)})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    DELETE /api/auth/delete-account/

    Permanently deletes the authenticated user's account and explicitly owned
    recordings after an explicit confirmation. Historical recordings without
    an owner are left untouched.
    """
    if (
        not isinstance(request.data, Mapping)
        or request.data.get('confirmation') != 'DELETE'
    ):
        return Response(
            {'error': 'Type DELETE to confirm permanent account deletion.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        owned_recordings = list(
            AudioRecording.objects.select_for_update().filter(uploaded_by=request.user)
        )
        for recording in owned_recordings:
            _delete_owned_recording_files(recording)
            recording.delete()
        request.user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_overview(request):
    """
    GET /api/admin/overview/   (staff only)

    Usage overview for the admin dashboard: counts plus recent recordings and
    users.  Lightweight — no analysis matrices are returned.
    """
    recordings = AudioRecording.objects.order_by('-uploaded_at')[:100]
    users = User.objects.order_by('-date_joined')[:100]

    return Response({
        'counts': {
            'total_users':          User.objects.count(),
            'staff_users':          User.objects.filter(is_staff=True).count(),
            'total_recordings':     AudioRecording.objects.count(),
            'analyzed_recordings':  AudioRecording.objects.filter(is_analyzed=True).count(),
            'pending_recordings':   AudioRecording.objects.filter(is_analyzed=False).count(),
        },
        'recordings': [
            {
                'id':           r.id,
                'title':        r.title,
                'uploaded_at':  r.uploaded_at.isoformat(),
                'is_analyzed':  r.is_analyzed,
            }
            for r in recordings
        ],
        'users': [
            {
                'id':           u.id,
                'username':     u.username,
                'email':        u.email,
                'is_staff':     u.is_staff,
                'is_active':    u.is_active,
                'date_joined':  u.date_joined.isoformat(),
            }
            for u in users
        ],
    })