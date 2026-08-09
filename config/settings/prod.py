from decouple import config as env

from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# --- Content-Security-Policy (django-csp) ---
MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'csp.middleware.CSPMiddleware',
)
INSTALLED_APPS = [*INSTALLED_APPS, 'csp']  # noqa: F405

CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:'],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
    },
}

# --- Stockage média : S3 si configuré, sinon disque local (fallback dev/petites installations) ---
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')

if AWS_STORAGE_BUCKET_NAME:
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='eu-west-3')
    AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN', default='')
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    # URLs signées temporaires : empêche le lien direct permanent vers un fichier média/vidéo source.
    AWS_QUERYSTRING_AUTH = env('AWS_QUERYSTRING_AUTH', default=True, cast=bool)
    AWS_QUERYSTRING_EXPIRE = env('AWS_QUERYSTRING_EXPIRE', default=3600, cast=int)
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
        },
    }
