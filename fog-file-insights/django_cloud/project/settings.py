import os
from pathlib import Path

# base
BASE_DIR = Path(__file__).resolve().parent.parent

# secrets & env
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-for-local")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",

    "uploads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "project.urls"
WSGI_APPLICATION = "project.wsgi.application"

# DB (sqlite for demo)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# international
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# static & media (local by default)
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Simple file storage toggle: set USE_S3=1 to enable S3 storage (Day 2)
USE_S3 = os.environ.get("USE_S3", "0") in ("1", "true", "True")

if USE_S3:
    # S3 (django-storages) configuration placeholders
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
    AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "")
    AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", None)  # for localstack testing
else:
    # default local file system storage
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# rest framework (basic)
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.JSONParser",
    ],
}
