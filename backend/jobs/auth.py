"""JWT authentication for candidate profiles."""

from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import jwt
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import AuthenticationFailed

ACCESS_TTL = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30")))
REFRESH_TTL = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))
JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.getenv("JWT_ISSUER", "ai-career-copilot")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "ai-career-copilot-api")


def _secret():
    return os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")


def _sign(profile_id, token_type, lifetime):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(profile_id), "type": token_type, "jti": uuid4().hex,
         "iat": now, "exp": now + lifetime, "iss": JWT_ISSUER, "aud": JWT_AUDIENCE},
        _secret(), algorithm=JWT_ALGORITHM,
    )


def make_tokens(profile):
    return {"access": _sign(profile.id, "access", ACCESS_TTL),
            "refresh": _sign(profile.id, "refresh", REFRESH_TTL)}


def read_token(token, expected_type):
    """Decode a JWT and return its CandidateProfile, or None if invalid."""
    if not token:
        return None
    try:
        data = jwt.decode(
            token, _secret(), algorithms=[JWT_ALGORITHM], issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "type", "jti", "iat", "exp", "iss", "aud"]},
        )
    except (jwt.InvalidTokenError, TypeError, ValueError):
        return None
    if data.get("type") != expected_type:
        return None
    from .models import CandidateProfile
    return CandidateProfile.objects.filter(pk=data.get("sub")).first()


class AuthUser:
    is_authenticated = True
    is_anonymous = False
    is_staff = False
    is_superuser = False

    def __init__(self, profile):
        self.profile = profile
        self.id = profile.id
        self.pk = profile.id
        self.name = profile.name
        self.email = profile.email
        self.username = profile.email or f"profile-{profile.id}"

    def __str__(self):
        return self.username


class ProfileTokenAuthentication(BaseAuthentication):
    """Authenticate ``Authorization: Bearer <access JWT>`` headers."""
    keyword = b"bearer"

    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword:
            return None
        if len(header) != 2:
            raise AuthenticationFailed("Invalid bearer token header.")
        try:
            token = header[1].decode("ascii")
        except UnicodeError:
            raise AuthenticationFailed("Invalid bearer token header.")
        profile = read_token(token, "access")
        if profile is None:
            raise AuthenticationFailed("Token is invalid or expired.")
        return AuthUser(profile), None


class AuthRateThrottle(SimpleRateThrottle):
    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
