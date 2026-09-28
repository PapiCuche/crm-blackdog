# backend/

Django 5.2 LTS (ASGI) sobre Python 3.14 — versiones exactas en [ADR-012](../docs/adr/ADR-012-engineering-runtime-baseline.md).
**F1-02:** esqueleto ejecutable con health checks, tooling y CI. Sin dominio de negocio, RLS ni tenancy (llegan en F1-03 y F1-04).

## Requisitos

- [uv](https://docs.astral.sh/uv/) **0.12.19** (lo exige `required-version`); uv usa Python 3.14.7 (`.python-version`).
- PostgreSQL para los tests y `/health/ready` (local: `infra/docker/compose.yaml`; CI: `postgres:18.6`).

## Uso

```bash
cd backend
uv sync --frozen                         # entorno reproducible desde uv.lock
uv run python manage.py check            # settings local por defecto
DJANGO_SETTINGS_MODULE=config.settings.local uv run uvicorn config.asgi:application --reload
```

`manage.py` usa `config.settings.local`. `config/asgi.py` usa `config.settings.production` si no se indica otra cosa.

## Validaciones (las mismas que CI)

```bash
uv run ruff format --check . && uv run ruff check .
uv run mypy .
uv run lint-imports
uv run python manage.py makemigrations --check --dry-run
DATABASE_URL=postgres://user:pass@localhost:5432/crm uv run pytest
```

## Settings

| Módulo | Uso | Notas |
|---|---|---|
| `config.settings.base` | Común | `DJANGO_SECRET_KEY` y `DATABASE_URL` obligatorias (el proceso no arranca sin ellas) |
| `config.settings.local` | Desarrollo | `DEBUG=True`, valores locales por defecto (nunca producción) |
| `config.settings.test` | pytest | BD desde `DATABASE_URL` |
| `config.settings.production` | Producción | `DEBUG=False` forzado; falla si `DJANGO_ALLOWED_HOSTS` está vacío, si la clave es insegura (< 50 caracteres o `django-insecure…`) o si el entorno contiene `DATABASE_MIGRATOR_URL`/`CRM_MIGRATOR_PASSWORD` (ADR-002 §1.1; el error nombra la variable, nunca su valor). Tras validar los hosts añade `127.0.0.1`, `localhost` y `[::1]` para las sondas locales. HSTS, cookies seguras, redirección SSL (excepto `/health/`) |

Variables de producción: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `DJANGO_CSRF_TRUSTED_ORIGINS` (opcional), `DJANGO_LOG_LEVEL` (opcional). En F1-03 `DATABASE_URL` pasa a ser exclusivamente el rol `crm_app` (ADR-002 §1.1).

## Health checks (ADR-011 §4)

| Endpoint | Comportamiento |
|---|---|
| `GET /health/live` | `200 {"status":"ok"}`; no toca dependencias |
| `GET /health/ready` | `200` si la BD responde a `SELECT 1`; si no, `503 {"status":"fail","checks":{"database":"fail"}}` sin detalles (el motivo solo va al log). Redis y storage se añadirán cuando existan |

Ambos: solo `GET`/`HEAD`, `Cache-Control: no-cache`.

## Docker

```bash
docker build -t crm-backend backend/
```

Imagen `python:3.14.7-slim` multi-stage, dependencias de `uv.lock` (`--frozen`, sin dev), usuario no root `10001`, `HEALTHCHECK` sobre `/health/live`, servidor `uvicorn` con `--proxy-headers` (IPs de confianza vía `FORWARDED_ALLOW_IPS`).
