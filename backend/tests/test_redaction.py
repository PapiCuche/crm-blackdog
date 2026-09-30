"""Redactor compartido: claves de proveedores, claves sensibles y contenido de mensajes.

Los secretos de prueba se construyen en tiempo de ejecución (sin literales que gitleaks
tenga que ignorar; no hay allowlist).
"""

import copy
import functools
from typing import Any

import pytest

from core.redaction import REDACTED, redact, redact_text

OPENAI_PROJECT = "sk-" + "proj-" + "Ab1" * 16
OPENAI_LEGACY = "sk-" + "Zx9Yw8" * 8
ANTHROPIC = "sk-" + "ant-api03-" + "Xy9" * 30 + "AA"
META = "EAA" + "Bw" + "Zq7" * 15
JWT = "eyJ" + "hbGciOi" + "." + "eyJzdWIi" + "OjEyMzQ" + "." + "SflKxwRJ" + "SMeKKF2Q"


@pytest.mark.parametrize(
    "secret", [OPENAI_PROJECT, OPENAI_LEGACY, ANTHROPIC, META, JWT], ids=["openai-proj",
    "openai", "anthropic", "meta", "jwt"]
)  # fmt: skip
def test_redacts_provider_key_patterns(secret: str) -> None:
    for text in (secret, f"error con la clave {secret}, reintentar", f"key={secret}&x=1"):
        out = redact_text(text)
        assert secret not in out and REDACTED in out
    assert redact({"detalle": [f"token: {secret}"]}) == {"detalle": [f"token: {REDACTED}"]}


def test_redacts_bearer_and_url_credentials() -> None:
    assert (
        redact_text("Authorization: Bearer abcdef123456789") == f"Authorization: Bearer {REDACTED}"
    )
    url = "postgres://crm_app:" + "s3cr3t" + "@db:5432/crm"
    assert redact_text(url) == f"postgres://{REDACTED}@db:5432/crm"
    assert redact_text("https://x.test/cb?access_token=abc123&ok=1").endswith(f"={REDACTED}&ok=1")
    for text in (
        "?client_id=1&client_secret=0123abcd",
        "hub.verify_token=v3r1fy",
        "DB_PASSWORD=pw",
    ):
        assert redact_text(text).endswith(f"={REDACTED}"), text
    assert redact_text("redis://:" + "pw9" + "@redis:6379/0") == f"redis://{REDACTED}@redis:6379/0"
    assert "hunter2" not in redact_text("{'password': 'hunter2', \"api_key\": \"k9\"}")
    for text in ("input_tokens=1200&x=1", "http://host:8080/p", "Polo basic Oversize negro"):
        assert redact_text(text) == text  # sin falsos positivos


def test_redacts_sensitive_keys_preserving_shape() -> None:
    secret_keys = ("apiKey", "x-api-key", "Authorization", "Set-Cookie", "client_secret",
                   "new_password2", "cookies", "secrets")  # fmt: skip
    nested = {"access_token": "t", "hub.verify_token": "v", "credentials": {"a": 1}}
    kept = {"input_tokens": 1200, "key_last_four": ["4242", "1111"], "daily_token_limit": [1, 2],
            "credential_id": "c1", "password_changed_at": "2026-09-30"}  # fmt: skip
    data = dict.fromkeys(secret_keys, "valor") | kept | {"password": ["a", None], "n": nested}
    out = redact(data)
    assert {k: out[k] for k in secret_keys} == dict.fromkeys(secret_keys, REDACTED)
    assert out["password"] == [REDACTED, None]  # conserva la forma [antes, después]
    assert out["n"] == dict.fromkeys(nested, REDACTED)
    assert {k: out[k] for k in kept} == kept


def test_redacts_message_content() -> None:
    data = {"body": "hola, mi tarjeta es…", "message_content": ["a", None], "draft_text": "x"}
    assert redact(data) == {
        "body": REDACTED,
        "message_content": [REDACTED, None],
        "draft_text": REDACTED,
    }


def test_redact_does_not_mutate_and_handles_edge_values() -> None:
    data = {"password": "x", "items": ({"token": "y"},), "blob": b"\x00", "n": 1}
    original = copy.deepcopy(data)
    assert redact(data) == {
        "password": REDACTED,
        "items": [{"token": REDACTED}],
        "blob": "[BINARY]",
        "n": 1,
    }
    assert data == original
    deep: dict[str, Any] = functools.reduce(lambda acc, _: {"k": acc}, range(12), {})
    assert "[TRUNCATED]" in repr(redact(deep))
