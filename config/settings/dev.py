from decouple import config as env

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']

if env('USE_SQLITE', default=True, cast=bool):
    DATABASES['default'] = {  # noqa: F405
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }

if env('USE_LOCMEM_CACHE', default=True, cast=bool):
    CACHES['default'] = {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}  # noqa: F405
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}  # noqa: F405

CELERY_TASK_ALWAYS_EAGER = env('CELERY_TASK_ALWAYS_EAGER', default=True, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
