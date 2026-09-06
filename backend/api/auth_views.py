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

from django.contrib.auth import authenticate, get_user_model
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    GET /api/auth/me/

    Returns the current user.  Used by the frontend to validate a stored
    token on page load and to learn the user's role (is_staff).
    """
    return Response({'user': _user_payload(request.user)})


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