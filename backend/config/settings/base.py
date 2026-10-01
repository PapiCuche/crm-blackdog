"""Settings comunes. Cada entorno (local, test, production) los importa y ajusta."""

from pathlib import Path

from config import env

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = env.required("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS: list[str] = env.csv_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "rest_framework",
    "drf_spectacular",
    "core",
    "apps.organizations",
    "apps.audit",
    "apps.files",
]

MIDDLEWARE = [
    "core.observability.middleware.RequestContextMiddleware",  # request/correlation id (F1-07)
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

# ADR-011: JSON en stdout, redactado (core.observability.logging). Celery no reemplaza el root.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "core.observability.logging.json_formatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"handlers": ["console"], "level": env.optional("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {  # uvicorn configura handlers de texto antes que Django: se reemplazan
        "uvicorn": {"handlers": ["console"], "propagate": False},
        "uvicorn.error": {"handlers": [], "propagate": True},
        "uvicorn.access": {"handlers": [], "propagate": True},
        "celery.app.trace": {"level": "WARNING"},  # "succeeded: <repr(resultado)>"
    },
}
# API (F1-08A): DRF solo JSON; sin autenticación todavía (Fase 2). Contrato OpenAPI con
# drf-spectacular, versionado en backend/openapi/schema.yaml (fuente de verdad para orval).
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,  # sin django.contrib.auth hasta la Fase 2
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Good Doggy CRM API",
    "DESCRIPTION": "Contrato de la API del backend. Fuente para el cliente TypeScript (orval).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,  # el propio /api/schema/ no forma parte del contrato
    "COMPONENT_SPLIT_REQUEST": True,  # tipos separados de petición/respuesta para orval
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
}
# Object storage S3-compatible (ADR-008): credenciales solo por entorno.
STORAGE_BACKEND = env.optional("STORAGE_BACKEND", "s3")  # s3 | memory (tests)
STORAGE_ENDPOINT_URL = env.optional("STORAGE_ENDPOINT_URL", "")  # vacío = AWS S3
STORAGE_REGION = env.optional("STORAGE_REGION", "us-east-1")
STORAGE_BUCKET = env.optional("STORAGE_BUCKET", "")
STORAGE_ACCESS_KEY_ID = env.optional("STORAGE_ACCESS_KEY_ID", "")
STORAGE_SECRET_ACCESS_KEY = env.optional("STORAGE_SECRET_ACCESS_KEY", "")
STORAGE_ADDRESSING_STYLE = env.optional("STORAGE_ADDRESSING_STYLE", "path")
# HTTP saliente (security-boundaries B9): allowlist exacta de hosts; vacía = nada permitido.
HTTP_ALLOWED_HOSTS: list[str] = env.csv_list("HTTP_ALLOWED_HOSTS")
# Reporte de errores (ADR-011 §3): sin SENTRY_DSN, NoopReporter (sin red).
SENTRY_DSN = env.optional("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = env.optional("SENTRY_ENVIRONMENT", "")
