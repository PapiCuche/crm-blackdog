import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

GOOD_KEY = "k" * 60
BASE_ENV = {
    "DJANGO_SECRET_KEY": GOOD_KEY,
    "DJANGO_ALLOWED_HOSTS": "app.example.com",
    "DATABASE_URL": "postgres://crm_app:secret@db:5432/crm",
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


@pytest.mark.parametrize(
    "overrides",
    [
        {"DJANGO_SECRET_KEY": None},
        {"DJANGO_SECRET_KEY": "django-insecure-" + "x" * 60},
        {"DJANGO_SECRET_KEY": "too-short"},
        {"DJANGO_ALLOWED_HOSTS": None},
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
