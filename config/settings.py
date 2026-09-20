"""Settings for the local TravelStan application."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-synthetic-demo-local-only-key"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "flights",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "autoescape": True,
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite is configured for local development only. The search slice stores
# nothing: no searches, results, query values, IP addresses, or provider data.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# No cache backend is used by the search slice; results are never cached.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CSRF_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Search request/response data is never logged.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}


def _csv_setting(name: str, default: str) -> tuple[str, ...]:
    return tuple(
        item.strip().lower()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    )


TRAVELSTAN_PROVIDERS = _csv_setting("TRAVELSTAN_PROVIDERS", "synthetic_demo")
TRAVELSTAN_COUNTRY = os.environ.get("TRAVELSTAN_COUNTRY", "EE")
TRAVELSTAN_LOCALE = os.environ.get("TRAVELSTAN_LOCALE", "en-EE")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
SERPAPI_CURRENCY = os.environ.get("SERPAPI_CURRENCY", "EUR")
SERPAPI_API_URL = os.environ.get("SERPAPI_API_URL", "https://serpapi.com/search.json")
