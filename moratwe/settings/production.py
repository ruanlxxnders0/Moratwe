import environ

from .base import *

env = environ.Env()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['0.0.0.0', '10.0.0.105', '13.247.223.33', 'app.moratwe.co.za', 'rsvps.moratwe.co.za', 'moratwe.co.za']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']

# Database
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': env.db('DATABASE_URL'),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    },
    'staticfiles': {
        # Non-manifest: django-ckeditor ships multiple plugins (codesnippet,
        # preview, etc.) whose bundled CSS references images missing from
        # the actual package. The Manifest variant hard-validates every CSS
        # url() reference and fails the whole build on each one; this
        # variant still compresses (gzip/brotli) but skips that validation.
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}
# django-cloudinary-storage's collectstatic override still reads the
# pre-Django-4.2 legacy setting name; keep it in sync with STORAGES above.
STATICFILES_STORAGE = STORAGES['staticfiles']['BACKEND']
DEFAULT_FILE_STORAGE = STORAGES['default']['BACKEND']

# django-ckeditor ships a CSS file (codesnippet plugin's "brown_paper" theme)
# that references a background image missing from the package itself. Don't
# hard-fail the whole build over that one broken third-party asset reference.
WHITENOISE_MANIFEST_STRICT = False

# Media files — stored on Cloudinary since Render's disk is ephemeral and
# wipes uploaded files on every redeploy/restart.
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}
MEDIA_URL = '/media/'

# Site URL for the deployed application
# RENDER_EXTERNAL_URL is set automatically by Render to the live https URL
SITE_URL = os.environ.get('SITE_URL', 'https://rsvps.moratwe.co.za')

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://app.moratwe.co.za",
    "https://rsvps.moratwe.co.za",
    "https://moratwe.co.za",
]
CORS_ALLOW_CREDENTIALS = True

# Session settings for production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'api': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'events': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# Celery Configuration
# No Redis broker or separate worker process is running on this deployment,
# so tasks run synchronously in-process instead of being queued.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE