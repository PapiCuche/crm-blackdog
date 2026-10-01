"""Contrato OpenAPI (F1-08A): servido en /api/schema/ y versionado sin drift."""

from pathlib import Path

import yaml
from django.core.management import call_command
from django.test import Client

COMMITTED = Path(__file__).resolve().parents[1] / "openapi" / "schema.yaml"


def generate(path: Path) -> str:
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(path))
    return path.read_text()


def test_committed_schema_matches_the_generated_one_deterministically(tmp_path: Path) -> None:
    first, second = generate(tmp_path / "a.yaml"), generate(tmp_path / "b.yaml")
    assert first == second  # determinista
    assert first == COMMITTED.read_text(), "Regenerar: ver backend/README.md (Contrato OpenAPI)"


def test_schema_endpoint_serves_the_contract_without_internal_routes() -> None:
    response = Client().get("/api/schema/")
    assert response.status_code == 200
    schema = yaml.safe_load(response.content)
    assert schema["info"]["title"] == "Good Doggy CRM API"
    # Sin endpoints de negocio todavía: ni health, ni rutas de tenant, ni el propio schema.
    assert schema["paths"] == {} and schema["openapi"].startswith("3.")
