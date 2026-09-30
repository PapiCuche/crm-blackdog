"""Settings comunes. Cada entorno (local, test, production) los importa y ajusta."""

from pathlib import Path

from config import env

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = env.required("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS: list[str] = env.csv_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "core",
    "apps.organizations",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.tenancy.middleware.TenantResolutionMiddleware",  # tras la autenticación (Fase 2)
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.database(env.required("DATABASE_URL"))}
# ADR-002: rol de runtime (sin BYPASSRLS, no propietario). Recibe los GRANT de las migraciones.
DB_APP_ROLE = env.optional("DB_APP_ROLE", "crm_app")
# Propietario explícito de tablas y funciones SECURITY DEFINER (ADR-002 §3.3).
DB_MIGRATOR_ROLE = env.optional("DB_MIGRATOR_ROLE", "crm_migrator")
# Verificación del rol conectado en cada conexión nueva (activa en production).
ENFORCE_RUNTIME_DB_ROLE = False
# Tenancy (F1-04): inyección para que core no importe módulos superiores.
TENANCY_ORGANIZATION_SELECTOR = "apps.organizations.selectors.organization_by_slug"
TENANCY_MEMBERSHIP_RESOLVER = "core.tenancy.resolution.no_memberships"  # Fase 2: memberships
# Outbox (F1-06): el publisher corre cada segundo en beat (beat y broker: F1-10).
CELERY_BEAT_SCHEDULE = {"core.publish_outbox": {"task": "core.publish_outbox", "schedule": 1.0}}
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
