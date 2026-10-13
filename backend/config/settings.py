import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-spotter-planner")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "planner",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
}

GRAPHHOPPER_API_KEY = os.environ.get("GRAPHHOPPER_API_KEY", "")
GRAPHHOPPER_ROUTE_URL = os.environ.get(
    "GRAPHHOPPER_ROUTE_URL", "https://graphhopper.com/api/1/route"
)
GRAPHHOPPER_PROFILE = os.environ.get("GRAPHHOPPER_PROFILE", "car")
OPEN_METEO_FORECAST_URL = os.environ.get(
    "OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast"
)
OPEN_METEO_GEOCODE_URL = os.environ.get(
    "OPEN_METEO_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search"
)
