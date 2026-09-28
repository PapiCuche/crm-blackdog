from unittest import mock

import pytest
from django.test import Client


def test_live_ok_without_touching_database(client: Client) -> None:
    with mock.patch(
        "core.health._database_ok", side_effect=AssertionError("no debe consultar la BD")
    ):
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "no-cache" in response["Cache-Control"]


@pytest.mark.django_db
def test_ready_ok_with_real_database(client: Client) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


def test_ready_fails_without_leaking_details(client: Client) -> None:
    with mock.patch("core.health.connection") as conn:
        conn.cursor.side_effect = RuntimeError("could not connect to host db.internal:5432")
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "fail", "checks": {"database": "fail"}}
    assert b"db.internal" not in response.content


@pytest.mark.parametrize("path", ["/health/live", "/health/ready"])
def test_health_rejects_unsafe_methods(client: Client, path: str) -> None:
    assert client.post(path).status_code == 405
