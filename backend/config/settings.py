import os
import re
import urllib.parse
from pathlib import Path

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "tracker",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def clean_database_url(url: str) -> str:
    url = url.strip().strip("'\"")
    prefix = "postgresql://"
    if url.startswith("postgres://"):
        prefix = "postgres://"

    if url.startswith(prefix):
        body = url[len(prefix):]
        if "@" in body and ":" in body.split("@", 1)[0]:
            cred_part, host_part = body.rsplit("@", 1)
            user, raw_pass = cred_part.split(":", 1)
            # Remove brackets if user typed [mypassword]
            if raw_pass.startswith("[") and raw_pass.endswith("]"):
                raw_pass = raw_pass[1:-1]
            unquoted = urllib.parse.unquote(raw_pass)
            encoded_pass = urllib.parse.quote(unquoted, safe="")
            return f"{prefix}{user}:{encoded_pass}@{host_part}"
    return url


raw_database_url = os.getenv("DATABASE_URL", "").strip()
if raw_database_url:
    cleaned_url = clean_database_url(raw_database_url)
    db_config = dj_database_url.parse(cleaned_url, conn_max_age=0)
    if "postgresql" in db_config.get("ENGINE", ""):
        db_config.setdefault("OPTIONS", {})["sslmode"] = "require"
    DATABASES = {"default": db_config}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Models match supabase/schema.sql. Disable management when those tables already exist.
DJANGO_MANAGE_TABLES = os.getenv("DJANGO_MANAGE_TABLES", "true").lower() == "true"

STORE_BASE_URL = os.getenv("STORE_BASE_URL", "https://demo.inelabteamdev.com").rstrip("/")
STORE_USER_AGENT = os.getenv(
    "STORE_USER_AGENT",
    "INEPriceTracker/1.0 (+https://github.com/your-name/ine-price-tracker)",
)
CRON_SECRET = os.getenv("CRON_SECRET", "").strip()
SCRAPER_MAX_ATTEMPTS = int(os.getenv("SCRAPER_MAX_ATTEMPTS", "3"))
SCRAPER_TIMEOUT_MS = int(os.getenv("SCRAPER_TIMEOUT_MS", "30000"))
SCRAPER_SLOW_MO_MS = int(os.getenv("SCRAPER_SLOW_MO_MS", "120"))

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}

cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
elif cors_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
else:
    CORS_ALLOW_ALL_ORIGINS = True
