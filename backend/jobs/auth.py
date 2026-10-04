'''Dependency-free token authentication for the MVP.

Access/refresh tokens are signed with SECRET_KEY (django.core.signing) and are
stateless, so no extra package (e.g. simplejwt) is required.
'''
from datetime import timedelta

from django.core import signing
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

ACCESS_SALT='ai-career-copilot.access'
REFRESH_SALT='ai-career-copilot.refresh'
ACCESS_TTL=timedelta(minutes=60).total_seconds()
REFRESH_TTL=timedelta(days=7).total_seconds()

def _sign(profile_id, salt):
    return signing.dumps({'id':profile_id},salt=salt,compress=True)

def make_tokens(profile):
    return {'access':_sign(profile.id,ACCESS_SALT),'refresh':_sign(profile.id,REFRESH_SALT)}

def read_token(token,salt,max_age):
    '''Decode a token and return its CandidateProfile, or None if invalid/expired.'''
    if not token: return None
    try:
        data=signing.loads(token,salt=salt,max_age=max_age)
    except signing.BadSignature:
        return None
    from .models import CandidateProfile
    return CandidateProfile.objects.filter(pk=data.get('id')).first()

class AuthUser:
    '''Lightweight authenticated principal bound to a CandidateProfile.'''
    is_authenticated=True
    is_anonymous=False
    is_staff=False
    is_superuser=False
    def __init__(self,profile):
        self.profile=profile
        self.id=profile.id
        self.pk=profile.id
        self.name=profile.name
        self.email=profile.email
        self.username=profile.email or f'profile-{profile.id}'
    def __str__(self):
        return self.username

class ProfileTokenAuthentication(BaseAuthentication):
    '''Authenticates 'Authorization: Bearer <access-token>' headers.'''
    keyword=b'bearer'
    def authenticate(self,request):
        header=get_authorization_header(request).split()
        if not header or header[0].lower()!=self.keyword:
            return None
        if len(header)!=2:
            raise AuthenticationFailed('Invalid bearer token header.')
        try:
            token=header[1].decode()
        except UnicodeError:
            raise AuthenticationFailed('Invalid bearer token header.')
        profile=read_token(token,ACCESS_SALT,ACCESS_TTL)
        if profile is None:
            raise AuthenticationFailed('Token is invalid or expired.')
        return (AuthUser(profile),None)
