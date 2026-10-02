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

## Membresías (F2-02, ADR-002 §3.2)

`apps.organizations.OrganizationMembership` (tabla `organization_memberships`, **tenant-owned**) une un usuario global con una organización. Un usuario puede tener cero, una o varias.

- **Campos:** `id`, `organization_id`, `user`, `status` (`INVITED`, `ACTIVE`, `SUSPENDED`, `DEACTIVATED`), `created_at`, `updated_at`. Solo `ACTIVE` da acceso. **No lleva rol:** los roles se asignarán a la membresía (F2-04).
- **Constraints en BD:** `UNIQUE (organization_id, user_id)`, `CHECK` de `status`, FK a `organizations` y FK a `users`.
- **RLS con FORCE, sin `tenant_isolation`:** cuatro políticas, una por comando. Con tenant activo, `SELECT` solo ve ese tenant. Sin tenant, dentro de `user_scope(user)`, el usuario ve solo sus propias membresías y no puede escribir. Sin contexto no se ve nada. Así se resuelve "¿es miembro?" sin haber entrado todavía al tenant y sin BYPASSRLS.
- **Resolvedor:** `TENANCY_MEMBERSHIP_RESOLVER = "apps.organizations.selectors.active_membership"`. Usuario activo con membresía `ACTIVE` → tenant resuelto. Cualquier otro caso (sin membresía, membresía no activa, usuario inactivo, staff de plataforma sin membresía) → el mismo 404 que una organización inexistente.
- **Selectores** (`apps.organizations.selectors`): `active_membership` y `organizations_for_user`. El manager `OrganizationMembership.for_user` solo se usa dentro de `user_scope`; con tenant activo se usa `objects`.

## Roles y permisos: modelo (F2-04, ADR-003 §5)

Esta sección cubre el **modelo** RBAC de `apps.access`; el cálculo de permisos efectivos y su verificación están en el motor (sección siguiente, F2-05A).

- **`permissions`** (global): catálogo definido en `apps/access/catalog.py` y sincronizado tras cada `migrate`. El runtime (`crm_app`) solo puede leerlo.
- **`roles`**, **`role_permissions`** y **`membership_roles`** (tenant-owned, RLS con FORCE): roles por organización, concesiones con alcance (`OWN`, `TEAM`, `BRANCH`, `ORGANIZATION`, o `NULL` si el permiso no lo admite) y roles asignados a membresías.
- **Integridad en la BD:** FK compuestas con `organization_id` impiden enlazar una membresía de una organización con un rol de otra, también con SQL directo.
- **Roles plantilla** (`owner`, `admin`, `supervisor`, `seller`): `clone_role_templates(ctx)` los crea en una organización de forma idempotente y no asigna roles a nadie. Una organización puede crear roles propios sin cambios de esquema.
- **Nada decide por el código o el nombre de un rol:** la autorización depende de permisos y alcances.

## Autorización: motor (F2-05A, ADR-003 §5)

`apps.access.selectors` decide si una membresía puede hacer algo. Solo cuentan permisos y alcances: nunca el código o el nombre de un rol, ni `is_platform_staff`.

- `execution_context(ctx)`: membresía activa del usuario y sus permisos efectivos (unión de los alcances de todos sus roles), en dos consultas. Sin membresía activa lanza `AccessDenied`.
- `has_permission`, `can(ectx, code, obj)`, `require(...)` y `scoped(ectx, code, queryset)`: permiso, alcance sobre un objeto y filtro de listado. Todo dentro del `tenant_scope` del propio contexto.
- `apps.access.scopes.register(Modelo, FieldScopes(...))`: cada modelo declara una vez sus columnas de propietario, equipo y sucursal, por el nombre de la columna (`assigned_user_id`, no `assigned_user`); de ahí salen el filtro y la verificación por objeto.
- Hasta E01-09 no hay equipos ni sucursales: `TEAM` y `BRANCH` equivalen a `OWN` (OBS-F2-05A-2).
- El `ExecutionContext` es una foto de su transacción: usarlo en otro `tenant_scope` posterior falla; hay que recalcularlo.
- Falla cerrado: un código de permiso inexistente lanza `UnknownPermission`; un modelo sin política lanza `ScopePolicyMissing`, también para quien tiene `ORGANIZATION`.

## Autorización en DRF (F2-05B)

DRF deniega por defecto: `apps.access.permissions.HasPermission` y `ScopeFilter` son sus clases por defecto. Una vista de tenant declara el permiso de cada método:

```python
class ContactDetail(generics.RetrieveUpdateAPIView):
    required_permissions = {
        "GET": "contacts.view",
        "PUT": "contacts.update",
        "PATCH": "contacts.update",
    }

    def get_queryset(self):  # nunca `queryset = ...` de clase: no hay tenant al importar
        return Contact.objects.all()
```

- Vista sin `required_permissions` o método sin declarar: 403. HEAD usa el permiso de GET. Pedir con `Accept` un formato que la API no sirve da 406 `NOT_ACCEPTABLE`.
- `ScopeFilter` aplica `scoped()` al queryset de listados y de `get_object()`: se filtra en SQL. Solo actúa donde la vista llama a `filter_queryset()`: una vista que consulte por su cuenta debe pasar su queryset por `scoped()`.
- Cada método usa su permiso y, sobre un objeto que ya existe, su alcance. Crear (POST) solo comprueba el permiso, y el filtro mira la fila antes de escribirla, no los valores que llegan (OBS-F2-05B-5). Un método de escritura responde con el objeto, así que poder escribirlo implica leer esa respuesta.
- Un serializador de tenant nunca acepta del cliente la clave primaria ni `organization_id`.
- El contexto es el que resolvió el middleware, nunca `request.user` ni datos del cliente. Los permisos se leen una vez por petición.

| Caso | Respuesta | Quién responde |
|---|---|---|
| Sin sesión | 401 `NOT_AUTHENTICATED` | middleware de tenant |
| Organización inexistente o sin membresía activa | 404 `NOT_FOUND` | middleware de tenant |
| Miembro sin el permiso, vista o método sin declarar | 403 `PERMISSION_DENIED` | `HasPermission` |
| Objeto fuera de alcance, de otra organización o inexistente | 404 `NOT_FOUND`, con los mismos bytes que los del middleware | `ScopeFilter` |

Las vistas de plataforma son las rutas fuera de `/api/v1/o/<slug>/`. Se excluyen por la ruta, nunca por el actor: declaran sus propias `permission_classes` (y `filter_backends` si son genéricas: sin tenant, `ScopeFilter` devuelve vacío) y se añaden a `PLATFORM` en `tests/test_access_api.py`. Ser staff de plataforma no abre ninguna ruta de tenant.

Ese test recorre todo el URLconf y falla si una ruta de tenant no es una vista de DRF con `HasPermission`, un permiso del catálogo por cada método que implementa y, si es genérica, `ScopeFilter`, o si aparece una vista de DRF de plataforma que no está en `PLATFORM`. Mira lo que usa cada ruta (también `as_view(...)` y `@action(...)`). Exige las dos clases tal cual: una subclase o una composición (`A | B`) se rechazan y se revisan a mano. Rechaza también las vistas que redefinen `get_permissions`, `check_permissions`, `permission_denied`, `initial` o `dispatch`, las genéricas que redefinen `get_object` o `filter_queryset`, y las envueltas en un decorador (`cache_page`, por ejemplo). Una ruta fuera de `api/v1/o/` que pueda casar con una ruta de tenant (segmento dinámico antes del prefijo, o `re_path` sin `^`) también falla. Es una auditoría estática: no sustituye a la revisión de una vista con consultas o escrituras propias.

`HasPermission` comprueba además cada objeto que pase por `check_object_permissions` y responde 404. Es una red de seguridad, no un sustituto de `scoped()`: su cuerpo puede diferir del de un objeto inexistente.

## Contrato de errores de la API (F2-12, ADR-014 §1)

**Un solo cuerpo de error:** `{"code": "…", "message"?: "…", "fields"?: {…}}`. El cliente decide solo por `code`.

- `core.api.errors.exception_handler` (el `EXCEPTION_HANDLER` de DRF) lo produce para los errores de una vista. Los 401 y los 404 van sin `message`.
- `VALIDATION_ERROR` lleva `fields`: cada campo, una lista de `{code, message}`; los errores generales, en `_`; un serializador anidado, un objeto; una lista, un objeto por índice de fila. El nombre `non_field_errors` de DRF no sale a ningún nivel.
- Un servicio lanza un código de dominio con `core.api.errors.ApiError(code, status, message)`.
- `core.api.middleware.ApiEnvelopeMiddleware` es el middleware más externo. Convierte al contrato todo error bajo `/api/` que no salga ya en JSON, venga de donde venga: una ruta sin resolver, un `Host` no permitido, una excepción en otro middleware. También con `DEBUG`. Conserva las cabeceras de la respuesta original (`Allow`, cookies). Un 500 es siempre `{"code":"INTERNAL_ERROR"}`: el detalle va al log.
- Las respuestas de la API llevan `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`.
- La API solo sirve JSON: `?format=` no existe (`URL_FORMAT_OVERRIDE`). `APPEND_SLASH` está desactivado: una ruta sin su barra final es un 404 del contrato, no una redirección.
- En OpenAPI, el componente común es `core.api.schema.ERROR`: `@extend_schema(responses={200: …, **errors(401, 404)})`. Aparece en `openapi/schema.yaml` con el primer endpoint que lo use (F2-03A): drf-spectacular no publica componentes sin referencias.

**Una petición de tenant que acaba en error no deja nada escrito.** `TenantResolutionMiddleware` es dueño de la transacción de la petición y la deshace si la respuesta es 400 o superior, la haya producido una excepción de dominio, una validación o un fallo inesperado. Lo que deba sobrevivir a una petición fallida (por ejemplo, una futura auditoría de accesos denegados) tiene que escribirse fuera de ese `tenant_scope`.

Un slug imposible bajo `/api/v1/o/` responde 404 sin llegar a ninguna vista. El resolvedor de tenant consulta la membresía exista o no la organización, para que el tiempo de respuesta del 404 no delate qué slugs existen.

## Sesión, CSRF y rutas de plataforma (F2-13, ADR-014 §2 y §4)

- `core.api.middleware.ApiCsrfMiddleware` exige el token CSRF en todo `POST`, `PUT`, `PATCH` y `DELETE` bajo `/api/`, haya sesión o no, y antes de resolver el tenant. No depende de la vista: DRF marca las suyas como exentas.
- El token solo se acepta en la cabecera `X-CSRFToken` (con la cookie `csrftoken`). El campo de formulario `csrfmiddlewaretoken` no vale, y el cuerpo no se lee antes de autenticar. El motivo de un rechazo va al log `django.security.csrf`; al cliente, solo `CSRF_FAILED`.
- `core.api.authentication.SessionAuthentication` es la clase por defecto de DRF: entrega a la vista el usuario de la sesión de Django y hace que la falta de sesión sea un 401 con `WWW-Authenticate: Session`. Además exige la marca del control de CSRF: una vista de DRF montada fuera de `/api/` rechaza los métodos no seguros.
- En desarrollo, `next dev` hace de proxy y cambia la cabecera `Host`: `config.settings.local` confía en `http://localhost:3000` para la comprobación de `Origin`. En producción, `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Con el cliente de tests de Django, usar `Client(enforce_csrf_checks=True)` para probar el CSRF.

| Caso en un método no seguro | Respuesta |
|---|---|
| Sin token CSRF válido, con sesión o sin ella | 403 `CSRF_FAILED` |
| Con token y sin sesión | 401 `NOT_AUTHENTICATED` |

**Rutas de plataforma** (todo `/api/` fuera de `/api/v1/o/<slug>/`): declaran exactamente una clase de `core.api.permissions`, `Public` (sin sesión) o `Authenticated` (sesión de un usuario activo), y se añaden a `PLATFORM` en `tests/test_access_api.py`. Las dos deniegan dentro de un `tenant_scope` y bajo el prefijo de tenant: no sirven para saltarse `HasPermission`.

La auditoría del URLconf falla si:

- una ruta bajo `api/` no es de tenant ni está en la lista, sea o no de DRF;
- una vista de DRF está fuera de `api/`;
- una ruta listada no declara una de las dos clases;
- una vista cambia `authentication_classes` o redefine `get_authenticators`, `perform_authentication`, `get_authenticate_header`, `handle_exception` o `check_object_permissions`;
- un manejador de una vista de tenant lleva un decorador (`method_decorator(cache_page(…))`);
- una expresión regular sin `$` puede casar con una ruta de tenant;
- dos rutas comparten el mismo texto y la primera, que es la que responde, no cumple.

Todavía no hay login ni cookie de sesión propia: llegan con F2-03A.

## Cambios de RBAC sin escalada (F2-05C, ADR-003 §5)

`apps.access.services` tiene los únicos servicios que cambian el RBAC de una organización. Son internos: no hay API HTTP (E01-08).

- `grant_permission(ctx, role_id=, code=, scope=)`, `assign_role(ctx, membership_id=, role_id=)` y `remove_role(ctx, membership_id=, role_id=)`. Reciben el `TenantContext`, no una foto de permisos.
- Cada cambio corre en un savepoint: toma el bloqueo del rol Owner de la organización (`SELECT … FOR NO KEY UPDATE`), relee los permisos del actor, comprueba las reglas, escribe y audita. Si algo falla, incluida la auditoría, no queda nada escrito.
- **Reglas:** hace falta `roles.manage` para conceder y `users.manage` para asignar o quitar. Nadie delega un permiso que no tiene ni con un alcance más amplio (`TEAM` y `BRANCH` no se contienen entre sí). Un permiso sensible solo lo delega quien tiene asignado el rol Owner, y además debe tenerlo. Asignar y quitar un rol exigen cubrir todas sus concesiones. Nadie se asigna ni se quita roles, ni concede permisos a un rol que tiene asignado.
- **Siempre queda un Owner activo** (membresía `ACTIVE` y usuario activo). `ensure_owner_remains(ctx, without_membership_id=)` es la misma garantía para quien desactive una membresía (E01-07).
- `is_owner_role` solo localiza el rol Owner para esas dos restricciones; por sí solo no concede nada. Nada decide por el código o el nombre de un rol, ni por `is_platform_staff`.
- Una denegación lanza `AccessDenied` con su motivo (`membership`, `permission`, `escalation`, `sensitive`, `self`, `last_owner`); un id de otra organización, o quitar un rol que la membresía no tiene (también al repetir la llamada), `DoesNotExist`. Repetir una concesión o una asignación no hace nada.
- Auditoría: `role.permission_granted`, `membership.role_assigned` y `membership.role_removed`, con el antes y el después.

## Identificadores y numeración (F1-05, ADR-004)

- `core.ids.new_id()`: UUIDv7 de la stdlib (`uuid.uuid7()`); nunca se usa `uuid` directamente. `core.db.models.uuid7_primary_key()` añade `DEFAULT uuidv7()` (PostgreSQL 18) de respaldo para inserts SQL directos (hoy: `organizations.id`).
- `org_sequences` (tenant-owned, RLS + FORCE, PK `(organization_id, sequence_key)`, FK a `organizations`).
- `core.sequences.allocate(ctx, key, prefix=None)` → `COT-000001`: un único `INSERT … ON CONFLICT DO UPDATE … RETURNING` en la transacción del llamador. Falla fuera de `transaction.atomic()` o si `ctx` no es el tenant activo. Un rollback no consume número; las transacciones concurrentes de la misma clave se serializan (bloqueo de fila).
- Los números comerciales nunca autorizan nada.
- Un test exige que toda PK de `core`/`apps` sea UUIDv7 (`uuid7_primary_key()`) o compuesta: `DEFAULT_AUTO_FIELD` sigue siendo `BigAutoField` porque Django no admite UUID ahí.

## Outbox y auditoría (F1-06)

`core.outbox.emit()` y `apps.audit.services.record()` escriben en la transacción del `tenant_scope` activo: un rollback no deja ni evento ni auditoría. `audit_logs` es append-only para `crm_app` y está particionada por mes, y el redactor (`core.redaction`) se aplica siempre. Diseño y decisiones: [docs/architecture/outbox-audit.md](../docs/architecture/outbox-audit.md).

## Auditoría de plataforma (F2-10, ADR-013)

`apps.audit.platform.record(action, *, actor_type, …)` registra los eventos que no pertenecen a ninguna organización (acceso, altas de plataforma) en `platform_audit_logs`.

- **Solo inserción.** La tabla no tiene `organization_id` ni política de tenant. `crm_app` solo tiene `INSERT`: el runtime escribe y no puede leer, modificar ni borrar el registro. Por eso el servicio no usa `RETURNING`. La sentencia nombra `public.platform_audit_logs`: una tabla temporal con el mismo nombre no captura la fila.
- **Sin tenant.** No recibe tenant y falla dentro de un `tenant_scope`: ahí corresponde `apps.audit.services.record`. Dentro de un `user_scope` sí funciona.
- **Falla cerrado.** Escribe en la transacción del llamador, si la hay, dentro de un savepoint. Si la inserción falla, lanza el error y la transacción del llamador sigue utilizable; quien no lo captura la deshace entera.
- **Qué no se guarda.** `identifier` (el email presentado en un acceso fallido) queda solo como huella HMAC-SHA-256 con una clave derivada de `DJANGO_SECRET_KEY`. `metadata` y `user_agent` pasan por el redactor y, además, por un filtro propio que sustituye por `[EMAIL]` cualquier cadena con forma de dirección, en cualquier alfabeto. Nunca se guarda el email, la contraseña ni una cookie.
- **Validación.** `action` con el formato de siempre y como máximo 100 caracteres; un actor `USER` lleva `actor_id` y uno `ANONYMOUS` no; `metadata` de 4096 bytes como máximo; `ip` es una dirección válida o `None` (se guarda sin zona y sin forma IPv4-en-IPv6). Lo que no cumple lanza `ValueError` antes de tocar la base de datos. La tabla repite las reglas principales con `CHECK`.
- **Particiones.** Mensuales, mes actual más doce, creadas por la migración y el `post_migrate`. Sin partición DEFAULT. En cada llamada, `platform_audit_ensure_partitions` vuelve a dejar los privilegios como deben estar en la tabla padre y en todas las particiones.
- `request_id` y `correlation_id` salen del contexto de observabilidad.

El redactor compartido (`core.redaction`) trata ahora como secretos las claves de sesión y de CSRF (`session_key`, `*session_id`, `csrftoken`, `csrfmiddlewaretoken`, `crm_session`…) y sus valores dentro de un texto (`session_key=…`, `X-CSRFToken: …`, `crm_session=…`). Los nombres son exactos: `csrf_failure_count=3` o un texto sobre una mascota llamada Cookie no se tocan. Una clave que termine en `session_id` se redacta siempre: para correlacionar hay que usar otro nombre.

Todavía no hay lectura desde la aplicación: solo el rol propietario puede consultar la tabla. Revertir la migración borra el registro; se niega a hacerlo si la tabla tiene filas.

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
