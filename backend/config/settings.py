from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-change-me'
    else:
        raise RuntimeError('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=False')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'corsheaders', 'rest_framework', 'jobs',
]
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND':'django.template.backends.django.DjangoTemplates',
    'DIRS': [], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request','django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages']},
}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if os.getenv('DATABASE_URL'):
    try:
        import dj_database_url
        db_from_env = dj_database_url.config(conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '600')), ssl_require=not DEBUG)
        if db_from_env:
            DATABASES['default'].update(db_from_env)
    except ImportError:
        pass
LANGUAGE_CODE='en-us'; TIME_ZONE='Asia/Kolkata'; USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
STATICFILES_STORAGE='whitenoise.storage.CompressedManifestStaticFilesStorage'
FRONTEND_DIST_DIR=BASE_DIR/'frontend_dist'
MEDIA_URL=os.getenv('MEDIA_URL', '/media/'); MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'

# Local resumes stay on disk. Production can switch only user-uploaded files
# to durable S3-compatible object storage (AWS S3, Cloudflare R2, MinIO, etc.)
# by setting AWS_STORAGE_BUCKET_NAME.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
if os.getenv('AWS_STORAGE_BUCKET_NAME'):
    s3_options = {
        'bucket_name': os.getenv('AWS_STORAGE_BUCKET_NAME'),
        'region_name': os.getenv('AWS_S3_REGION_NAME') or None,
        'endpoint_url': os.getenv('AWS_S3_ENDPOINT_URL') or None,
        'access_key': os.getenv('AWS_ACCESS_KEY_ID') or None,
        'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY') or None,
        'file_overwrite': False,
        'default_acl': None,
        'querystring_auth': os.getenv('AWS_QUERYSTRING_AUTH', 'True').lower() == 'true',
    }
    STORAGES['default'] = {'BACKEND': 'storages.backends.s3.S3Storage', 'OPTIONS': s3_options}
CORS_ALLOWED_ORIGINS=[x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]
# Vite uses strictPort:false, so it can shift to another port if 5173 is busy.
# Accept any localhost port in development so that does not break API calls.
CORS_ALLOWED_ORIGIN_REGEXES=[r'^http://(localhost|127\.0\.0\.1)(:\d+)?$'] if DEBUG and not os.getenv('CORS_ALLOWED_ORIGIN_REGEXES') else [x.strip() for x in os.getenv('CORS_ALLOWED_ORIGIN_REGEXES','').split(',') if x.strip()]
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL'),
    }
} if os.getenv('REDIS_URL') else {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'ai-career-copilot-local'}
}

# Celery uses the same Redis instance for the broker and result backend. Keep
# this optional so the existing synchronous/local workflow still works when
# Redis is not configured.
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND') or os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT', '900'))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '840'))
CELERY_RESULT_EXPIRES = int(os.getenv('CELERY_RESULT_EXPIRES', str(60 * 60 * 24)))
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# Local fallback for machines without Redis. Tasks keep the same task IDs and
# status API, but execute during the request instead of on a worker.
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'False').lower() == 'true'
CELERY_TASK_EAGER_PROPAGATES = False
# Page size is 20 because JobsPage computes totalPages as ceil(count / 20).
REST_FRAMEWORK={'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.AllowAny'],'DEFAULT_AUTHENTICATION_CLASSES':['jobs.auth.ProfileTokenAuthentication'],
                'DEFAULT_PAGINATION_CLASS':'rest_framework.pagination.PageNumberPagination','PAGE_SIZE':20,
                'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.AnonRateThrottle','rest_framework.throttling.UserRateThrottle'],
                'DEFAULT_THROTTLE_RATES':{'anon':'30/min','user':'120/min','auth':'5/min'}}

DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', str(12 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', str(12 * 1024 * 1024)))
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', str(not DEBUG)).lower() == 'true'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000' if not DEBUG else '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'standard': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'django': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'jobs': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO'), 'propagate': False},
    },
}
