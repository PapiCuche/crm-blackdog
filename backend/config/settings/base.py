"""Settings comunes. Cada entorno (local, test, production) los importa y ajusta."""

from pathlib import Path

from config import env

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = env.required("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS: list[str] = env.csv_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.database(env.required("DATABASE_URL"))}
# ADR-002: rol de runtime (sin BYPASSRLS, no propietario). Recibe los GRANT de las migraciones.
DB_APP_ROLE = env.optional("DB_APP_ROLE", "crm_app")
# Verificación del rol conectado en cada conexión nueva (activa en production).
ENFORCE_RUNTIME_DB_ROLE = False
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "es-pe"
LANGUAGES = [("es", "Español"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = "UTC"  # se guarda en UTC; la zona de cada organización se aplica al mostrar
USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env.optional("DJANGO_LOG_LEVEL", "INFO")},
}
