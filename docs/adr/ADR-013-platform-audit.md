# ADR-013: Auditoría de plataforma en un sumidero propio, sin tenant y solo de inserción

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Product Owner (mantenedor)
- **Related:** ADR-001 §2, ADR-002, ADR-003 §2, ADR-011, [outbox-audit.md](../architecture/outbox-audit.md), D-F2-1 y OBS-F2-01-4 en [phase-2.md](../phases/phase-2.md), OBS-F1-06-1 en [phase-1.md](../phases/phase-1.md)

## Context

ADR-011 define un único registro de auditoría: la tabla `audit_logs`. F1-06 la creó tenant-owned: `organization_id NOT NULL` dentro de la clave primaria, RLS con FORCE y una política `tenant_isolation` (ADR-001 §2). `apps.audit.services.record()` exige un `tenant_scope` activo.

Hay eventos de seguridad que ocurren **sin organización**:

- el inicio de sesión, el intento fallido y el cierre de sesión ocurren antes de elegir organización, en rutas de plataforma que no abren `tenant_scope` ([tenancy-context.md](../architecture/tenancy-context.md) §2);
- los comandos de plataforma (alta de una organización) actúan antes de que el tenant exista o sobre varios.

Hoy no existe un lugar válido donde escribirlos. El mantenedor descartó tres atajos: un `organization_id` ficticio, una organización arbitraria y relajar RLS. ADR-011 §1 descarta el log de aplicación como sustituto, porque puede perderse.

## Decision

### 1. Un segundo sumidero, platform-owned

Se crea la tabla **`platform_audit_logs`** en `apps.audit`. Es platform-owned (ADR-001 §2): **no tiene columna `organization_id`** ni política de tenant. `audit_logs` no cambia: sigue siendo el registro de todo lo que ocurre dentro de una organización.

Regla de reparto: un evento va a `platform_audit_logs` solo si no pertenece a ninguna organización. Todo cambio hecho dentro de un `tenant_scope` se sigue auditando con `record()` en `audit_logs`. El servicio de plataforma **falla si hay un tenant activo**, para que no sirva de vía para sacar un evento del registro que ve el Owner.

### 2. Estructura

| Campo | Contenido |
|---|---|
| `id`, `occurred_at` | UUIDv7 y hora de la transacción. Clave primaria `(occurred_at, id)` |
| `actor_type` | `USER`, `SYSTEM`, `PLATFORM_STAFF` o `ANONYMOUS` |
| `actor_id` | `users.id` de un actor **autenticado**; `NULL` si no lo hay |
| `identifier_hash` | Huella del identificador presentado (ver §4); `NULL` si no aplica |
| `action` | `dominio.entidad.verbo`, del catálogo de [04 §N.2](../fase-0/04-precios-pipeline-seguridad-infra.md) |
| `entity_type`, `entity_id` | Entidad afectada, si existe: `organization` en un alta, o `user` cuando un acceso fallido apunta a una cuenta que existe |
| `metadata` | JSONB con tamaño acotado, filtrado según §4 |
| `ip`, `user_agent`, `request_id`, `correlation_id` | Trazabilidad. `ip` es la dirección del cliente que resuelve el servidor ASGI a partir de los proxies de confianza (`FORWARDED_ALLOW_IPS`), nunca una cabecera leída por la aplicación. `user_agent` se trunca a 512 caracteres. Los dos identificadores salen del contexto de observabilidad |
| `result` | `SUCCESS`, `DENIED` o `FAILED` |

Particionada por mes desde su creación (ADR-011), con el mismo mecanismo que `audit_logs`: una función propiedad de `crm_migrator`, sin EXECUTE para `crm_app`, que crea el mes actual más doce desde la migración y el `post_migrate`. Sin partición DEFAULT: si el horizonte se agota, la inserción falla.

### 3. Privilegios: solo inserción

- `crm_app` tiene **solo `INSERT`** en la tabla padre. No tiene `SELECT`, `UPDATE`, `DELETE` ni `TRUNCATE`, ni privilegios directos sobre las particiones.
- El runtime web no puede leer el historial de accesos.
- No se crea el rol `crm_platform` ni se usa BYPASSRLS. No hace falta: la tabla no tiene RLS de tenant.
- **Lectura:** este ADR no crea ningún rol. Hoy solo puede leer el propietario (`crm_migrator`), cuya credencial es exclusiva del job de migraciones (ADR-002 §1.1): consultarla es una intervención de operación excepcional. La lectura habitual (investigación, panel de plataforma, "mis accesos recientes") necesita un rol propio de solo lectura sobre esta tabla, sin BYPASSRLS ni propiedad, en la línea del `crm_readonly` que ADR-002 §1 prevé. Se diseña y se crea en el work item que añada esa lectura.

### 4. Identidad y datos personales

- Con un actor autenticado (`auth.login.succeeded`, `auth.logout`), la fila guarda `actor_type = USER` y su `actor_id`, y **nunca el email**.
- Un intento fallido no tiene actor autenticado: `actor_type = ANONYMOUS` y `actor_id = NULL`. Quien envía la petición no es la cuenta atacada. Si el identificador corresponde a un usuario que existe, la cuenta va como entidad afectada (`entity_type = 'user'`, `entity_id`).
- El identificador presentado se guarda solo como `identifier_hash`: `salted_hmac(<sal propia>, identificador, algorithm="sha256")`, es decir, un HMAC-SHA-256 con una clave derivada de `DJANGO_SECRET_KEY`. Permite ver que varios intentos apuntan al mismo identificador sin almacenar la dirección, y no es reversible con solo la base de datos. Quien llama pasa el email canónico cuando el valor se puede canonicalizar (`apps.accounts.emails`), y el texto recibido cuando no; el servicio solo quita espacios y pasa a minúsculas, porque `apps.audit` no puede importar `apps.accounts`.
- Nunca se guarda la contraseña, ni correcta ni incorrecta, ni su longitud. Nunca el ID de sesión, el token CSRF ni ninguna cookie.
- **Filtro de `metadata` y `user_agent`.** El redactor compartido no trata un email como secreto, porque la auditoría de un tenant necesita registrar cambios de email de un contacto. Por eso el escritor de plataforma añade su propio filtro: enmascara cualquier cadena con forma de email, además de pasar por el redactor, que trata como secretas las claves de sesión y de CSRF (`session_key`, `sessionid`, `csrftoken`…). `metadata` tiene un tamaño máximo. Los tests de cada evento comprueban que la fila no contiene el identificador.
- La IP y el agente de usuario son datos personales necesarios para investigar un acceso; se conservan con la retención de §6.
- Rotar `DJANGO_SECRET_KEY` rompe la correlación entre huellas anteriores y posteriores. Se acepta.

### 5. Contrato de escritura

```python
apps.audit.platform.record(
    action, *, actor_type, actor_id=None, identifier=None, entity=None,
    metadata=None, result=Result.SUCCESS, ip=None, user_agent=None,
) -> UUID
```

- No recibe `TenantContext` ni `organization_id`. Lanza un error si `core.tenancy.context.current()` devuelve un tenant.
- `identifier` es el identificador presentado; el servicio lo convierte en `identifier_hash` y no lo guarda.
- `ip` es una dirección válida o `None`; `user_agent` se filtra y se trunca. Los identificadores de petición y de correlación los toma de `core.observability.context`.
- No usa `RETURNING` (el rol no tiene `SELECT`).

Cuándo se escribe depende del resultado, porque una fila escrita dentro de una transacción que se deshace desaparece con ella:

| Evento | Cuándo se escribe | Si la inserción falla |
|---|---|---|
| Éxito de una operación de plataforma (`auth.login.succeeded`) | En la misma transacción que la operación | **Falla cerrado:** la operación no ocurre. Un inicio de sesión que no puede auditarse no crea sesión |
| Fallo o denegación (`auth.login.failed`) | Fuera de cualquier transacción que se vaya a deshacer; se confirma por sí misma | La respuesta sigue siendo el mismo rechazo. El error va al log y al reporte de errores |
| `auth.logout` | Después de invalidar la sesión | La sesión **ya está cerrada**: un fallo de auditoría nunca mantiene viva una sesión. El error se reporta |
| Operación que entra en un tenant (alta de una organización, F2-06) | Una fila de **intención** antes de abrir el `tenant_scope` y una de **resultado** (`SUCCESS` o `FAILED`) al terminar. `tenant_scope` es dueño de su transacción y este servicio no escribe dentro de él | Si falla la fila de intención, la operación no empieza. El cambio en sí queda además en `audit_logs` del tenant, dentro de su transacción |

Eventos de acceso que escribe F2-03A: `auth.login.succeeded`, `auth.login.failed` (con un motivo interno en `metadata`, nunca devuelto al cliente) y `auth.logout`. El alta de una organización (F2-06) escribe `organization.bootstrap.started` y `organization.bootstrapped`, con el operador y el motivo.

### 6. Retención y lectura

- Retención mínima de dos años, igual que `audit_logs` (ADR-011). El archivado o borrado de particiones antiguas lo hace el job de migraciones u operación, nunca el runtime.
- La lectura sigue §3: no existe todavía desde la aplicación.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| `audit_logs.organization_id` nullable con política condicional | Cambia la clave primaria y la política en todas las particiones, y deja en una tabla tenant-owned filas que ningún tenant debe ver. F1-06 ya la rechazó |
| Rol `crm_platform` con BYPASSRLS para escribir | Pone una credencial con bypass en el endpoint sin autenticar más expuesto. No resuelve el `NOT NULL` |
| `organization_id` ficticio u organización arbitraria | Falsea el registro del tenant. Excluido por el mantenedor |
| Log de aplicación | Puede perderse; no es auditoría (ADR-011 §1) |
| Copiar el login a la auditoría de cada organización del usuario | Revela a una organización la actividad del usuario en otras |

## Consequences

- Hay dos sumideros de auditoría. Se cruzan por `correlation_id` y `request_id`.
- Un Owner con `audit.view` no ve los accesos de sus miembros en la auditoría de la organización. Si el producto lo necesita, se diseña con la vista de auditoría (E01-13).
- ADR-011 §1 sigue vigente para `audit_logs`; este ADR añade el caso sin tenant que no cubría. ADR-001 §2 ya preveía la clase platform-owned.
- La impersonación (E01-12) y la inversión de dependencia para `TenantCommand` y `PlatformCommand` en `core` (OBS-F1-06-1) quedan fuera: se resuelven cuando exista quien las use.

## Security implications

- El aislamiento entre tenants no cambia: ninguna política de RLS se toca y no aparece ningún rol nuevo.
- El registro es inmutable para el runtime y, además, ilegible para él: comprometer `crm_app` no da el historial de accesos.
- El login escribe una fila por intento y el runtime no puede borrarlas. El endpoint de acceso debe tener un límite de intentos por IP y por identificador antes de salir a producción (ADR-003 §2; F2-03A o F2-03B), para que nadie haga crecer la tabla sin control.
- La respuesta al cliente no depende de lo que se audita: el motivo de un fallo de acceso solo queda en la fila.
- Los tests comprueban los privilegios por introspección y que ningún campo contiene contraseña, email en claro ni cookies.

## Operational implications

- El job de migraciones debe ejecutarse al menos una vez al año para extender las particiones, como con `audit_logs`.
- Las alertas por picos de accesos fallidos (ADR-003, Operational implications) se derivan de las métricas y del log de aplicación, que no necesitan leer esta tabla. La investigación de un incidente sí la lee, con el rol de §3.
- Si se agota el horizonte de particiones, los inicios de sesión fallan (falla cerrado) y los cierres de sesión siguen funcionando.
