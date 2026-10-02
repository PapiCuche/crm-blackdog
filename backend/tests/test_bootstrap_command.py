"""F2-06B: el comando `bootstrap_organization`, punto de entrada del alta de una organización."""

import io
import json
import logging
from typing import Any

import psycopg
import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management.base import CommandError

from tests.factories import TEST_PASSWORD, make_user
from tests.test_bootstrap import EMAIL, TABLES, counts, platform_rows

pytestmark = pytest.mark.usefixtures("tenant_db")
ARGS = ["--slug", "acme", "--name", "Acme SAC", "--owner-email", EMAIL]


def stdin(text: str | bytes) -> io.TextIOWrapper:
    """La entrada estándar de un proceso: texto sobre bytes, con el locale que toque."""
    raw = text if isinstance(text, bytes) else text.encode()
    return io.TextIOWrapper(io.BytesIO(raw), encoding="latin-1")  # el comando no usa el locale


def test_command_reads_the_password_from_stdin_and_never_prints_it(
    migrator: psycopg.Connection[Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    secret = " ñandú " + TEST_PASSWORD + " "  # tal cual: con sus espacios y sin mojibake
    monkeypatch.setattr("sys.stdin", stdin("\ufeff" + secret + "\r\n"))  # BOM y CRLF fuera
    monkeypatch.setattr("getpass.getuser", lambda: "ops@gooddoggy.pe")
    out, reason = io.StringIO(), ["--reason", f"alta pedida por {EMAIL} y otro@acme.pe"]
    call_command("bootstrap_organization", *ARGS, "--password-stdin", *reason, stdout=out)
    assert authenticate(username=EMAIL, password=secret) is not None
    assert authenticate(username=EMAIL, password=secret.strip()) is None  # no se recorta
    captured = capsys.readouterr()
    printed = out.getvalue() + captured.out + captured.err + caplog.text
    assert "Organización acme" in printed
    assert "por [EMAIL]: alta pedida por [EMAIL] y [EMAIL]" in printed  # operador y motivo
    assert TEST_PASSWORD not in printed and "@" not in printed
    started = json.loads(platform_rows(migrator)[0][4])  # el motivo y el operador llegan al alta
    assert started["reason"] == "alta pedida por [EMAIL] y [EMAIL]" and started["operator"]
    with pytest.raises(CommandError, match="slug"):  # repetirlo no crea otra
        call_command("bootstrap_organization", *ARGS, "--existing-owner", "--reason", "otra vez")
    with pytest.raises(CommandError, match="reason"):
        call_command("bootstrap_organization", *ARGS)  # el motivo es obligatorio
    assert counts(migrator)["organizations"] == 1


def test_command_gives_owner_to_an_existing_account_only_when_told_to(
    migrator: psycopg.Connection[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(CommandError, match="no existe"):
        call_command("bootstrap_organization", *ARGS, "--existing-owner", "--reason", "alta")
    ana = make_user(email=EMAIL)
    new = "otra-clave-larga-y-nueva-42"
    monkeypatch.setattr("sys.stdin", stdin(new + "\n"))
    with pytest.raises(CommandError, match="ya existe") as refused:  # anuncia una cuenta nueva
        call_command("bootstrap_organization", *ARGS, "--password-stdin", "--reason", "alta")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": new)  # también por el terminal
    with pytest.raises(CommandError, match="ya existe"):
        call_command("bootstrap_organization", *ARGS, "--reason", "alta")
    assert new not in str(refused.value) and EMAIL not in str(refused.value)
    for both in (["--existing-owner", "--password-stdin"], []):  # por argv y por kwargs
        flags = {} if both else {"existing_owner": True, "password_stdin": True}
        with pytest.raises(CommandError, match="password-stdin"):
            call_command("bootstrap_organization", *ARGS, *both, "--reason", "alta", **flags)
    assert counts(migrator)["organizations"] == 0 and platform_rows(migrator)[-1][1] == "FAILED"
    call_command("bootstrap_organization", *ARGS, "--existing-owner", "--reason", "alta")
    assert authenticate(username=EMAIL, password=TEST_PASSWORD) == ana  # conserva la suya
    assert counts(migrator)["membership_roles"] == 1


@pytest.mark.parametrize(
    ("typed", "args"),
    [
        ("corta\n", ARGS),
        (TEST_PASSWORD + "\nsegunda línea\n", ARGS),
        (TEST_PASSWORD + "\n\n", ARGS),
        (TEST_PASSWORD.encode() + b"\xff\n", ARGS),  # no es UTF-8
        (None, ARGS),  # sin entrada estándar
        (TEST_PASSWORD, ["--slug", "Acme", *ARGS[2:]]),
        (TEST_PASSWORD, [*ARGS[:5], "no-es-un-email"]),
        (TEST_PASSWORD, [*ARGS[:5], "a" * 250 + "@acme.pe"]),  # no cabe en la columna
    ],
)
def test_command_reports_invalid_input_as_a_command_error(
    migrator: psycopg.Connection[Any],
    monkeypatch: pytest.MonkeyPatch,
    typed: str | bytes | None,
    args: list[str],
) -> None:
    monkeypatch.setattr("sys.stdin", None if typed is None else stdin(typed))
    with pytest.raises(CommandError) as error:
        call_command("bootstrap_organization", *args, "--password-stdin", "--reason", "alta")
    assert TEST_PASSWORD not in str(error.value)
    assert counts(migrator) == dict.fromkeys(TABLES, 0)


def test_command_prompts_twice_and_rejects_a_mismatch(
    migrator: psycopg.Connection[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = iter([TEST_PASSWORD, TEST_PASSWORD[::-1]])  # la segunda no coincide
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    with pytest.raises(CommandError, match="no coinciden"):
        call_command("bootstrap_organization", *ARGS, "--reason", "alta")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": (_ for _ in ()).throw(EOFError))
    with pytest.raises(CommandError, match="password-stdin"):  # sin terminal
        call_command("bootstrap_organization", *ARGS, "--reason", "alta")
    assert counts(migrator) == dict.fromkeys(TABLES, 0) and platform_rows(migrator) == []
    monkeypatch.setattr("getpass.getpass", lambda prompt="": TEST_PASSWORD)  # las dos coinciden
    call_command("bootstrap_organization", *ARGS, "--reason", "alta", stdout=io.StringIO())
    assert authenticate(username=EMAIL, password=TEST_PASSWORD) is not None
