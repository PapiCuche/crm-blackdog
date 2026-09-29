# backend/

Django 5.2 LTS (ASGI) sobre Python 3.14 — versiones exactas en [ADR-012](../docs/adr/ADR-012-engineering-runtime-baseline.md).
**Fase 1:** esqueleto con health checks, tooling y CI (F1-02), roles y RLS (F1-03) y puntos de entrada con tenant (F1-04). Sin dominio de negocio.

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
DATABASE_URL=postgres://crm_app:…@localhost:5432/crm \
DATABASE_MIGRATOR_URL=postgres://crm_migrator:…@localhost:5432/crm uv run pytest
```

**Tests de BD (F1-03, ADR-002):** necesitan los roles de `infra/docker/postgres/init/01-roles.sh`.
- `tests/conftest.py` aplica las migraciones como `crm_migrator` y ejecuta los tests como `crm_app`.
- Si el rol de test es superusuario o tiene BYPASSRLS, la sesión se aborta.
- La app `tests.tenancy_app` (solo en `config.settings.test`) aporta modelos con RLS para probar el aislamiento.

## Settings

| Módulo | Uso | Notas |
|---|---|---|
| `config.settings.base` | Común | `DJANGO_SECRET_KEY` y `DATABASE_URL` obligatorias (el proceso no arranca sin ellas) |
| `config.settings.local` | Desarrollo | `DEBUG=True`, valores locales por defecto (nunca producción) |
| `config.settings.test` | pytest | BD desde `DATABASE_URL` |
| `config.settings.production` | Producción | `DEBUG=False` forzado; falla si `DJANGO_ALLOWED_HOSTS` está vacío, si la clave es insegura (< 50 caracteres o `django-insecure…`) o si el entorno contiene `DATABASE_MIGRATOR_URL`/`CRM_MIGRATOR_PASSWORD` (ADR-002 §1.1; el error nombra la variable, nunca su valor). Tras validar los hosts añade `127.0.0.1`, `localhost` y `[::1]` para las sondas locales. HSTS, cookies seguras, redirección SSL (excepto `/health/`) |

Variables de producción: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `DJANGO_CSRF_TRUSTED_ORIGINS` (opcional), `DJANGO_LOG_LEVEL` (opcional). En F1-03 `DATABASE_URL` pasa a ser exclusivamente el rol `crm_app` (ADR-002 §1.1).

## Roles de BD y tenancy (F1-03, ADR-002)

| Proceso | Settings | Rol |
|---|---|---|
| web / worker / ws / beat | `config.settings.production` | `DATABASE_URL` → `crm_app`. Rechaza las variables del migrador y, en cada conexión nueva (y al arrancar ASGI), un rol superusuario, con BYPASSRLS o propietario de tablas |
| Job de migraciones | `config.settings.migrate` | `DATABASE_MIGRATOR_URL` → `crm_migrator`. Rechaza `DATABASE_URL`; la `SECRET_KEY` es efímera |

**Kernel de tenancy:**
- `core.tenancy`: `TenantContext`, `tenant_scope()` / `user_scope()` (solo `set_config(…, true)`) y `assert_clean_connection()`.
- `core.db.models`: `TenantModel` / `TenantManager`, que fallan sin contexto.
- `core.db.operations`: `EnableRLS`, `CompositeTenantFK` y `SecurityDefinerFunction`.
- Funciones SQL `app_current_tenant()` y `app_current_user()`.

## Puntos de entrada con tenant (F1-04, tenancy-context §2–§4 y §7)

| Entrada | Pieza | Comportamiento |
|---|---|---|
| HTTP `/api/v1/o/{slug}/…` | `core.tenancy.middleware.TenantResolutionMiddleware` | Sin usuario → 401. Organización inexistente o sin membresía → **404 idéntico** (`{"code":"NOT_FOUND"}`). Miembro de una organización suspendida → 403 `ORG_SUSPENDED`. La vista completa corre dentro de `tenant_scope` (streaming prohibido) |
| Celery | `@tenant_task` / `@platform_task` (`core.tenancy.celery`), app en `config/celery.py` | `@tenant_task` exige el kwarg `organization_id` (UUID) **al encolar** y ejecuta en `tenant_scope`. El bootstep `TenancyCheck` impide arrancar el worker si hay tareas sin decorar |
| WebSockets | `TenantConsumerMixin` (`core.tenancy.channels`) | `connect_tenant()` resuelve igual que HTTP (cierra con 4404/4403). `in_tenant(fn)` ejecuta cada acceso a BD en su propio scope vía `database_sync_to_async`: sin transacciones entre `await` |
| Comandos | `TenantCommand` (`--org`, `--reason`) / `PlatformCommand` (`--reason`) | El motivo y el operador se registran en el log (auditoría persistente en F1-06) |

- `apps.organizations`: tabla `organizations` mínima (platform-owned, sin RLS) y el selector `organization_by_slug`.
- Resolución compartida (`core.tenancy.resolution`) inyectada por settings (`TENANCY_ORGANIZATION_SELECTOR`, `TENANCY_MEMBERSHIP_RESOLVER`): el kernel no importa `apps` (import-linter).
- **Sin membresías reales hasta la Fase 2:** el resolvedor por defecto niega todo (fail-closed). Los tests usan un doble (`tests/fakes.py`).
- Broker de Celery y `AuthMiddlewareStack` de Channels: F1-10 y Fase 2.

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
