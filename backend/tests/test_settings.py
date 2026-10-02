import importlib
import secrets
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

GOOD_KEY = "k" * 60
MIGRATOR_SECRET = secrets.token_hex(16)  # aleatorio por ejecución
BASE_ENV: dict[str, str | None] = {
    "DJANGO_SECRET_KEY": GOOD_KEY,
    "DJANGO_ALLOWED_HOSTS": "app.example.com",
    "DATABASE_URL": "postgres://crm_app:secret@db:5432/crm",
    "DATABASE_MIGRATOR_URL": None,
    "CRM_MIGRATOR_PASSWORD": None,
    "STORAGE_ENDPOINT_URL": None,
}


def load_production(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> object:
    for key, value in {**BASE_ENV, **overrides}.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    for name in ("config.settings.production", "config.settings.base"):
        sys.modules.pop(name, None)
    return importlib.import_module("config.settings.production")


def test_production_loads_with_valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_production(monkeypatch)
    assert settings.DEBUG is False  # type: ignore[attr-defined]
    assert settings.SECURE_SSL_REDIRECT is True  # type: ignore[attr-defined]
    assert settings.DATABASES["default"]["HOST"] == "db"  # type: ignore[attr-defined]
    # ADR-014 §2: la cookie de sesión de producción no se relaja.
    assert settings.SESSION_COOKIE_NAME == "__Host-crm_session"  # type: ignore[attr-defined]
    for flag in ("SESSION_COOKIE_SECURE", "SESSION_COOKIE_HTTPONLY", "CSRF_COOKIE_SECURE"):
        assert getattr(settings, flag) is True
    assert settings.SESSION_COOKIE_SAMESITE == settings.CSRF_COOKIE_SAMESITE == "Lax"  # type: ignore[attr-defined]
    # `__Host-` exige Path=/ y ningún Domain; el cliente tiene que poder leer `csrftoken`.
    assert getattr(settings, "SESSION_COOKIE_PATH", "/") == "/"
    assert getattr(settings, "SESSION_COOKIE_DOMAIN", None) is None
    assert settings.CSRF_COOKIE_HTTPONLY is False  # type: ignore[attr-defined]
    assert getattr(settings, "CSRF_COOKIE_DOMAIN", None) is None
    # D-F2-2: sesiones en base de datos (revocar es borrar una fila) y 12 horas.
    assert settings.SESSION_ENGINE.endswith(".db")  # type: ignore[attr-defined]
    assert settings.SESSION_COOKIE_AGE == 12 * 60 * 60  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "overrides",
    [
        {"DJANGO_SECRET_KEY": None},
        {"DJANGO_SECRET_KEY": "django-insecure-" + "x" * 60},
        {"DJANGO_SECRET_KEY": "too-short"},
        {"DJANGO_ALLOWED_HOSTS": None},
        {"DJANGO_ALLOWED_HOSTS": ""},
        {"DJANGO_ALLOWED_HOSTS": " , "},
        {"DATABASE_URL": None},
        {"DATABASE_URL": "mysql://u:p@h/db"},
        {"DJANGO_DEBUG": "true"},
        {"DJANGO_DEBUG": "maybe"},
    ],
)
def test_production_refuses_insecure_or_missing_config(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, str | None]
) -> None:
    with pytest.raises(ImproperlyConfigured):
        load_production(monkeypatch, **overrides)


def test_production_adds_loopback_after_validating_configured_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_production(monkeypatch, DJANGO_ALLOWED_HOSTS="app.example.com,localhost")
    hosts = settings.ALLOWED_HOSTS  # type: ignore[attr-defined]
    assert hosts[0] == "app.example.com"
    assert {"127.0.0.1", "localhost", "[::1]"} <= set(hosts)
    assert len(hosts) == len(set(hosts))  # sin duplicados


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("DATABASE_MIGRATOR_URL", f"postgres://crm_migrator:{MIGRATOR_SECRET}@db:5432/crm"),
        ("CRM_MIGRATOR_PASSWORD", MIGRATOR_SECRET),
    ],
)
def test_production_refuses_migrator_credentials(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    with pytest.raises(ImproperlyConfigured) as excinfo:
        load_production(monkeypatch, **{variable: value})
    message = str(excinfo.value)
    assert variable in message
    assert MIGRATOR_SECRET not in message


@pytest.mark.parametrize(
    "endpoint", ["http://s.example.com", "https://u:" + "p" + "@s.example.com"]
)
def test_production_storage_endpoint_requires_tls(
    monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    for valid in ("https://storage.example.com", ""):  # vacío = AWS por defecto
        load_production(monkeypatch, STORAGE_ENDPOINT_URL=valid)
    with pytest.raises(ImproperlyConfigured):
        load_production(monkeypatch, STORAGE_ENDPOINT_URL=endpoint)


def load_migrate(monkeypatch: pytest.MonkeyPatch, **env: str | None) -> object:
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    for name in ("config.settings.migrate", "config.settings.base"):
        sys.modules.pop(name, None)
    return importlib.import_module("config.settings.migrate")


def test_migrate_settings_use_migrator_url_without_runtime_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_migrate(
        monkeypatch,
        DATABASE_URL=None,
        DATABASE_MIGRATOR_URL="postgres://crm_migrator:x@db:5432/crm",
        DJANGO_SECRET_KEY=None,
    )
    assert settings.DATABASES["default"]["USER"] == "crm_migrator"  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "env",
    [
        {
            "DATABASE_URL": "postgres://crm_app:x@db:5432/crm",
            "DATABASE_MIGRATOR_URL": "postgres://m:x@db/crm",
        },
        {"DATABASE_URL": None, "DATABASE_MIGRATOR_URL": None},
    ],
)
def test_migrate_settings_refuse_runtime_url_or_missing_migrator(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str | None]
) -> None:
    with pytest.raises(ImproperlyConfigured):
        load_migrate(monkeypatch, **env)
