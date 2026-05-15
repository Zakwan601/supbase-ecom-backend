import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name):
    return [
        item.strip()
        for item in os.getenv(name, "").split(",")
        if item.strip()
    ]


def append_env_values(defaults, env_name):
    values = []
    for value in [*defaults, *env_list(env_name)]:
        if value not in values:
            values.append(value)
    return values


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ["SECRET_KEY"].strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DEBUG", default=False)


# IMPORTANT:
# ALLOWED_HOSTS must contain only hostnames.
# Do not use https:// or http:// here.
ALLOWED_HOSTS = append_env_values(
    [
        "supbase-ecom-backend-ggtu.onrender.com",
        "supbase-ecom-backend.onrender.com",
        "supbase-zuanshi-backend.onrender.com",

        "playmartbd.com",
        "www.playmartbd.com",

        "bebeee.store",
        "www.bebeee.store",

        "localhost",
        "127.0.0.1",
    ],
    "ALLOWED_HOSTS",
)


# Application definition
INSTALLED_APPS = [
    "corsheaders",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "imagekit",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Keep CorsMiddleware as high as possible
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "myproject.urls"


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


WSGI_APPLICATION = "myproject.wsgi.application"


# Database
# Currently using SQLite.
# Note: Render free services do not keep SQLite data permanently after redeploys.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files
STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# CORS:
# CORS_ALLOWED_ORIGINS must include full origins with https:// or http://
CORS_ALLOWED_ORIGINS = append_env_values(
    [
        "http://localhost:5173",
        "http://localhost:5174",

        "https://playmartbd.com",
        "https://www.playmartbd.com",

        "https://bebeee.store",
        "https://www.bebeee.store",

        "https://supabase-ecom-testing-ground.onrender.com",
        "https://supabase-zuanshi.onrender.com",

        "https://supbase-zuanshi-backend.onrender.com",
        "https://supbase-ecom-backend-ggtu.onrender.com",
    ],
    "CORS_ALLOWED_ORIGINS",
)


# CSRF trusted origins:
# Needed for POST requests, admin login, forms, and session/cookie-based requests.
CSRF_TRUSTED_ORIGINS = append_env_values(
    [
        "http://localhost:5173",
        "http://localhost:5174",

        "https://playmartbd.com",
        "https://www.playmartbd.com",

        "https://bebeee.store",
        "https://www.bebeee.store",

        "https://supabase-ecom-testing-ground.onrender.com",
        "https://supabase-zuanshi.onrender.com",

        "https://supbase-zuanshi-backend.onrender.com",
        "https://supbase-ecom-backend-ggtu.onrender.com",
    ],
    "CSRF_TRUSTED_ORIGINS",
)


# Optional but useful if your frontend sends cookies/session auth
CORS_ALLOW_CREDENTIALS = True


# Security settings for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_SSL_REDIRECT = False


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"