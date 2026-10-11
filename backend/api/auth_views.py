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

from collections.abc import Mapping
import posixpath
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import AudioRecording

User = get_user_model()


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
def register(request):
    """
    POST /api/auth/register/

    Body: { username, email?, password, first_name?, last_name? }
    Returns: { token, user } on success (201); { error } on failure (400).
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

    if User.objects.filter(username__iexact=username).exists():
        return Response(
            {'error': 'A user with that username already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters long.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {'token': token.key, 'user': _user_payload(user)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    POST /api/auth/login/

    Body: { username | email, password }
    Returns: { token, user } on success (200); { error } on failure (401).
    """
    identifier = request.data.get('username') or request.data.get('email') or ''
    password   = request.data.get('password') or ''
    identifier = str(identifier).strip()

    user = None
    if not identifier or not password:
        return Response(
            {'error': 'username/email and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if '@' in identifier:
        try:
            candidate = User.objects.get(email__iexact=identifier)
            if candidate.check_password(password):
                user = candidate
        except User.DoesNotExist:
            user = None
    else:
        user = authenticate(request, username=identifier, password=password)

    if user is None:
        return Response(
            {'error': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': _user_payload(user)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    POST /api/auth/logout/

    Revokes the caller's token server-side.  The frontend should also discard
    its locally stored token.
    """
    Token.objects.filter(user=request.user).delete()
    return Response({'message': 'Logged out.'})


def _delete_owned_recording_files(recording):
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
            AudioRecording.objects.select_for_update().filter(owner=request.user)
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