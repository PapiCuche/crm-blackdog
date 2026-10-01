# backend/

Django 5.2 LTS (ASGI) sobre Python 3.14 — versiones exactas en [ADR-012](../docs/adr/ADR-012-engineering-runtime-baseline.md).
**Fase 1:** esqueleto con health checks, tooling y CI (F1-02), roles y RLS (F1-03) y puntos de entrada con tenant (F1-04), UUIDv7 y numeración por organización (F1-05), outbox y auditoría (F1-06). Sin dominio de negocio.

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

## Usuarios (F2-01, ADR-001 §2, ADR-003 §2)

`apps.accounts.User` es la **identidad global** de una persona (`AUTH_USER_MODEL = "accounts.User"`, tabla `users`, platform-owned y sin RLS de tenant).

- **Sin organización ni rol.** No tiene `organization_id`, `role` ni grupos o permisos de Django. Un usuario se vincula a organizaciones mediante membresías, y los roles (Owner, Admin, Vendedor o personalizados) se asignan a la membresía (F2-02, F2-04, F2-05).
- **`is_platform_staff`** es administración técnica de la plataforma, no un rol de negocio. No da acceso a ningún tenant: un usuario autenticado sin membresía recibe el mismo 404 que cualquier otro. `createsuperuser` crea este tipo de usuario.
- **Email canónico** (`apps.accounts.emails.canonical_email`): se quita el espacio exterior; parte local en minúsculas y solo ASCII; dominio en minúsculas y en forma IDNA si es internacionalizado; formato validado. No hay reglas por proveedor: los puntos y los `+tag` distinguen direcciones.
- **Unicidad sin distinguir mayúsculas, garantizada en la BD:** `UNIQUE (email)` más `CHECK (email = lower(email))`. No se usa la extensión `citext` (decisión D-F2-3 en [phase-2.md](../docs/phases/phase-2.md)).
- **Contraseñas:** solo Argon2id (`argon2-cffi`, ADR-012). Validadores: mínimo 12 caracteres, contraseñas comunes, solo numéricas y parecido con los datos del usuario.
- **Sesiones:** `django.contrib.sessions` y `AuthenticationMiddleware` están activos para que exista `request.user`. Los endpoints de login, la cookie `__Host-crm_session` y el almacén de sesiones llegan en F2-03A.

## Identificadores y numeración (F1-05, ADR-004)

- `core.ids.new_id()`: UUIDv7 de la stdlib (`uuid.uuid7()`); nunca se usa `uuid` directamente. `core.db.models.uuid7_primary_key()` añade `DEFAULT uuidv7()` (PostgreSQL 18) de respaldo para inserts SQL directos (hoy: `organizations.id`).
- `org_sequences` (tenant-owned, RLS + FORCE, PK `(organization_id, sequence_key)`, FK a `organizations`).
- `core.sequences.allocate(ctx, key, prefix=None)` → `COT-000001`: un único `INSERT … ON CONFLICT DO UPDATE … RETURNING` en la transacción del llamador. Falla fuera de `transaction.atomic()` o si `ctx` no es el tenant activo. Un rollback no consume número; las transacciones concurrentes de la misma clave se serializan (bloqueo de fila).
- Los números comerciales nunca autorizan nada.
- Un test exige que toda PK de `core`/`apps` sea UUIDv7 (`uuid7_primary_key()`) o compuesta: `DEFAULT_AUTO_FIELD` sigue siendo `BigAutoField` porque Django no admite UUID ahí.

## Outbox y auditoría (F1-06)

`core.outbox.emit()` y `apps.audit.services.record()` escriben en la transacción del `tenant_scope` activo: un rollback no deja ni evento ni auditoría. `audit_logs` es append-only para `crm_app` y está particionada por mes, y el redactor (`core.redaction`) se aplica siempre. Diseño y decisiones: [docs/architecture/outbox-audit.md](../docs/architecture/outbox-audit.md).

## Observabilidad (F1-07, ADR-011)

Logs JSON en stdout (structlog + `logging` estándar, redactados con `core.redaction`) con `request_id`, `correlation_id` e IDs de tenant/actor. El `X-Request-ID` es siempre un UUIDv7 generado por la aplicación. La correlación pasa de HTTP a Celery por cabecera. Errores: `NoopReporter` sin `SENTRY_DSN`, `SentryReporter` endurecido con él. Diseño: [docs/architecture/observability.md](../docs/architecture/observability.md).

## Object storage y HTTP saliente (F1-08)

`core.storage` (ADR-008): `S3CompatibleStorage` (boto3) / `InMemoryStorage`, claves `org/{organization_id}/…` y URLs firmadas de ≤ 5 min. La tabla `files` es tenant-owned con RLS. `core.http`: HTTPS con allowlist de hosts, IP pública validada al conectar (anti-SSRF) y sin redirecciones. La suite de contrato S3 corre contra Garage v2.4.1 en CI. Diseño: [docs/architecture/storage-http.md](../docs/architecture/storage-http.md).

## Contrato OpenAPI (F1-08A)

DRF + drf-spectacular. `GET /api/schema/` sirve el contrato; `backend/openapi/schema.yaml` es la versión commiteada y la **fuente de verdad** para el cliente TypeScript (orval, F1-09). CI lo regenera y falla si hay diferencias. Tras cambiar la API:

```bash
DJANGO_SETTINGS_MODULE=config.settings.local uv run python manage.py spectacular --validate --fail-on-warn --file openapi/schema.yaml
```

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
