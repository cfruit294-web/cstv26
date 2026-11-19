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
# Hôte public transmis par le proxy (Caddy/nginx) ou par le serveur Next.js quand il appelle Django
# via le réseau Docker interne (http://web:8000, cf frontend/src/lib/config.ts). Reste validé
# contre ALLOWED_HOSTS par Django : une valeur forgée hors liste est refusée (400).
USE_X_FORWARDED_HOST = True
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
    # Tout fournisseur S3-compatible : AWS S3, Cloudflare R2, Backblaze B2, Scaleway, Wasabi...
    # Pour autre chose qu'AWS, renseigner AWS_S3_ENDPOINT_URL (ex: R2 :
    # https://<account_id>.r2.cloudflarestorage.com, avec AWS_S3_REGION_NAME=auto).
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default='') or None
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='eu-west-3')
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    # Bucket privé + URLs signées temporaires, NON désactivables : les vidéos et sous-titres ne sont
    # protégés que par ça (core/media_access.py). Pas d'AWS_S3_CUSTOM_DOMAIN volontairement :
    # django-storages renvoie alors des URLs NON signées, ce qui rendrait tout le média public.
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = env('AWS_QUERYSTRING_EXPIRE', default=3600, cast=int)
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
