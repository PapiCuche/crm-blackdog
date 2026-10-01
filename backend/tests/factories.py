"""Fábricas de datos de test (sin dependencias externas)."""

from itertools import count
from typing import Any

from apps.accounts.models import User

TEST_PASSWORD = "correct-horse-battery-staple"  # noqa: S105 — dato ficticio de test
_sequence = count(1)


def make_user(**overrides: Any) -> User:
    fields: dict[str, Any] = {
        "email": f"user{next(_sequence)}@example.com",
        "password": TEST_PASSWORD,
        **overrides,
    }
    return User.objects.create_user(**fields)
