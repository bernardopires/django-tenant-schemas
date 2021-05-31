"""
Django settings for dts_test_project project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "cl1)b#c&xmm36z3e(quna-vb@ab#&gpjtdjtpyzh!qn%bc^xxn"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

DEFAULT_FILE_STORAGE = "tenant_schemas.storage.TenantFileSystemStorage"

# Application definition

SHARED_APPS = (
    "tenant_schemas",  # mandatory
    "customers",  # you must list the app where your tenant model resides in
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
)

TENANT_APPS = ("dpt_test_app",)

TENANT_MODEL = "customers.Client"  # app.Model

TEST_RUNNER = "django.test.runner.DiscoverRunner"

INSTALLED_APPS = (
    "tenant_schemas",
    "dpt_test_app",
    "customers",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
)

ROOT_URLCONF = "dpt_test_project.urls"

WSGI_APPLICATION = "dpt_test_project.wsgi.application"

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "tenant_schemas.postgresql_backend",
        "NAME": os.environ.get("PG_NAME", "dpt_test_project"),
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": os.environ.get("PG_HOST"),
        "PORT": int(os.environ.get("PG_PORT")) if os.environ.get("PG_PORT") else None,
    }
}

DATABASE_ROUTERS = ("tenant_schemas.routers.TenantSyncRouter",)

MIDDLEWARE = (
    "tenant_tutorial.middleware.TenantTutorialMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "OPTIONS": {
            "debug": True,
            "context_processors": (
                "django.core.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.core.context_processors.debug",
                "django.core.context_processors.media",
                "django.core.context_processors.static",
                "django.contrib.messages.context_processors.messages",
            ),
            "loaders": (
                "tenant_schemas.template_loaders.FilesystemLoader",
                "django.template.loaders.app_directories.Loader",
            ),
        },
    }
]

MULTITENANT_TEMPLATE_DIRS = []

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = "/static/"

STATICFILES_STORAGE = "tenant_schemas.storage.TenantStaticFilesStorage"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "tenant_context": {"()": "tenant_schemas.log.TenantContextFilter"},
    },
    "formatters": {
        "simple": {"format": "%(levelname)-7s %(asctime)s %(message)s"},
        "tenant_context": {
            "format": "[%(schema_name)s:%(domain_url)s] %(levelname)-7s %(asctime)s %(message)s",
        },
    },
    "handlers": {
        "null": {"class": "logging.NullHandler"},
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["tenant_context"],
            "formatter": "tenant_context",
        },
    },
    "loggers": {"": {"handlers": ["null"], "level": "DEBUG", "propagate": True}},
}
