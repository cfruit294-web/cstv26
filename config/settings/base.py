"""
Settings communs à tous les environnements (dev, prod, tests).
Les valeurs sensibles ou dépendantes de l'environnement viennent du fichier .env.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config as env

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-env')
DEBUG = env('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = env('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

DJANGO_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_celery_beat',
    'channels',
]

LOCAL_APPS = [
    'core',
    'accounts',
    'catalog',
    'videos',
    'live',
    'community',
    'messaging',
    'dashboard',
    'notifications',
    'search',
    'cms',
    'watchparty',
    'library',
    'ads',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env('DB_NAME', default='cstv'),
        'USER': env('DB_USER', default='cstv'),
        'PASSWORD': env('DB_PASSWORD', default='cstv'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
        # 'prefer' fonctionne aussi bien en local (pas de TLS) que sur des hébergeurs gérés qui
        # l'exigent (ex: Render Postgres) : pas besoin de le forcer sauf cas particulier.
        'OPTIONS': {'sslmode': env('DB_SSLMODE', default='prefer')},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Active X-Accel-Redirect pour les fichiers media protégés (core/media_access.py) uniquement
# derrière un nginx configuré pour ça (voir docker-compose.yml, docker/nginx/nginx.conf). Sur un
# hébergeur sans reverse-proxy dédié (ex: Render), Django sert directement le fichier.
USE_X_ACCEL_REDIRECT = env('USE_X_ACCEL_REDIRECT', default=False, cast=bool)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Django REST Framework ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '240/minute',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.exception_handler',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'CSTV API',
    'DESCRIPTION': 'API de la plateforme de streaming vidéo CSTV.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env('ACCESS_TOKEN_LIFETIME_MIN', default=15, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env('REFRESH_TOKEN_LIFETIME_DAYS', default=14, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS', default='http://localhost:3000', cast=Csv())

# --- Cache / Redis ---
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# --- Celery ---
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {}

# --- Email ---
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env('EMAIL_PORT', default=25, cast=int)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env('EMAIL_USE_TLS', default=False, cast=bool)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='no-reply@cstv.local')

FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

# --- Règles métier accounts ---
EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 48
PASSWORD_RESET_TOKEN_TTL_HOURS = 2
TWO_FACTOR_PREAUTH_TTL_SECONDS = 300

# --- Intégration OMDb (métadonnées films/séries pour le catalogue) ---
OMDB_API_KEY = env('OMDB_API_KEY', default='')
OMDB_BASE_URL = env('OMDB_BASE_URL', default='https://www.omdbapi.com/')

# --- Encodage vidéo (FFmpeg) ---
FFMPEG_BINARY = env('FFMPEG_BINARY', default='ffmpeg')
FFPROBE_BINARY = env('FFPROBE_BINARY', default='ffprobe')
MAX_VIDEO_UPLOAD_SIZE_MB = env('MAX_VIDEO_UPLOAD_SIZE_MB', default=2048, cast=int)


# --- Live streaming (ingestion RTMP via MediaMTX, cf docker-compose.yml) ---
RTMP_INGEST_BASE_URL = env('RTMP_INGEST_BASE_URL', default='rtmp://localhost')
RTMP_WEBHOOK_SECRET = env('RTMP_WEBHOOK_SECRET', default='change-me-rtmp-secret')
# Base interne (réseau Docker) utilisée par LiveHlsProxyView pour relayer le HLS depuis MediaMTX ;
# jamais exposée au client (voir live/views.py, live/serializers.py get_hls_playback_url).
MEDIAMTX_HLS_INTERNAL_URL = env('MEDIAMTX_HLS_INTERNAL_URL', default='http://mediamtx:8888')
# Dossier des enregistrements bruts produits par MediaMTX (volume Docker partagé, jamais servi
# publiquement) : source des rediffusions automatiques générées par live.tasks.
LIVE_RECORDINGS_ROOT = env('LIVE_RECORDINGS_ROOT', default=str(BASE_DIR / 'live_recordings'))

# --- Channels (WebSocket, chat live) ---
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [REDIS_URL]},
    },
}
