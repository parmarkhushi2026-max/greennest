import os
"""Settings for the GreenNest storefront project."""
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-greennest-local-development-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "https://*.onrender.com",
    "https://*.pythonanywhere.com",
    "https://*.trycloudflare.com",
    "https://*.ngrok-free.app",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "store",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "greennest.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "greennest" / "templates",
            BASE_DIR / "store" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "store.context_processors.shopping_bag",
            ],
        },
    },
]

WSGI_APPLICATION = "greennest.wsgi.application"
ASGI_APPLICATION = "greennest.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "greennest" / "static",
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage" 
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "store:login"
LOGIN_REDIRECT_URL = "store:home"
LOGOUT_REDIRECT_URL = "store:home"
# ==============================================================================
# EMAIL CONFIGURATION (Real Active Cloud SMTP Server - No Personal Password Needed!)
# ==============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.ethereal.email"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "ixaaijwbhtsrsi5m@ethereal.email"
EMAIL_HOST_PASSWORD = "3c4eQtB9FZS3w38G9p"
DEFAULT_FROM_EMAIL = "Green Nest Nursery <orders@greennest.local>"

# Razorpay Payment Gateway Settings
RAZORPAY_KEY_ID = "rzp_test_greenNestStore"
RAZORPAY_KEY_SECRET = "greenNestDemoSecret"
