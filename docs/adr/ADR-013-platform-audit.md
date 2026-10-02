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
| `actor_id` | `users.id` cuando se conoce; `NULL` si no |
| `identifier_hash` | Huella del identificador presentado (ver §4); `NULL` si no aplica |
| `action` | `dominio.entidad.verbo`, del catálogo de [04 §N.2](../fase-0/04-precios-pipeline-seguridad-infra.md) |
| `entity_type`, `entity_id` | Entidad afectada, si existe (por ejemplo `organization` en un alta) |
| `metadata` | JSONB, siempre pasado por el redactor |
| `ip`, `user_agent`, `request_id`, `correlation_id` | Trazabilidad. `user_agent` se trunca a 512 caracteres |
| `result` | `SUCCESS`, `DENIED` o `FAILED` |

Particionada por mes desde su creación (ADR-011), con el mismo mecanismo que `audit_logs`: una función propiedad de `crm_migrator`, sin EXECUTE para `crm_app`, que crea el mes actual más doce desde la migración y el `post_migrate`. Sin partición DEFAULT: si el horizonte se agota, la inserción falla.

### 3. Privilegios: solo inserción

- `crm_app` tiene **solo `INSERT`** en la tabla padre. No tiene `SELECT`, `UPDATE`, `DELETE` ni `TRUNCATE`, ni privilegios directos sobre las particiones.
- El runtime web no puede leer el historial de accesos. Una lectura futura (panel de plataforma, o "mis accesos recientes") se diseña en su propio work item, con una vía estrecha y auditada.
- No se crea el rol `crm_platform` ni se usa BYPASSRLS. No hace falta: la tabla no tiene RLS de tenant.

### 4. Identidad y datos personales

- Con usuario identificado, la fila guarda `actor_id` y **nunca el email**.
- En un intento fallido, el identificador presentado puede no corresponder a ningún usuario. La fila guarda `identifier_hash`: un HMAC-SHA-256 del email canónico con una clave derivada de `DJANGO_SECRET_KEY` (`salted_hmac`, con una sal propia de este uso). Permite ver que varios intentos apuntan al mismo identificador sin almacenar la dirección, y no es reversible con solo la base de datos. Si el intento corresponde a un usuario que existe, se guarda además su `actor_id`.
- Nunca se guarda la contraseña, ni correcta ni incorrecta, ni su longitud. Nunca el ID de sesión, el token CSRF ni ninguna cookie.
- La IP y el agente de usuario son datos personales necesarios para investigar un acceso; se conservan con la retención de §6.
- Rotar `DJANGO_SECRET_KEY` rompe la correlación entre huellas anteriores y posteriores. Se acepta.

### 5. Contrato de escritura

```python
apps.audit.platform.record(
    action, *, actor_type, actor_id=None, identifier=None, entity=None,
    metadata=None, result=Result.SUCCESS, request=None,
) -> UUID
```

- No recibe `TenantContext` ni `organization_id`. Lanza un error si `core.tenancy.context.current()` devuelve un tenant.
- `identifier` es el email en claro; el servicio lo convierte en `identifier_hash` y no lo guarda.
- `request` aporta IP, agente de usuario y los identificadores de petición y correlación.
- Escribe en la transacción del llamador, si la hay. **Falla cerrado:** si la inserción falla, la operación auditada falla. Un inicio de sesión que no puede auditarse no crea sesión.
- No usa `RETURNING` (el rol no tiene `SELECT`).

Eventos de acceso que escribe F2-03A: `auth.login.succeeded`, `auth.login.failed` (con un motivo interno en `metadata`, nunca devuelto al cliente) y `auth.logout`. El alta de una organización (F2-06) escribe `organization.bootstrapped` con el operador y el motivo.

### 6. Retención y lectura

- Retención mínima de dos años, igual que `audit_logs` (ADR-011). El archivado o borrado de particiones antiguas lo hace el job de migraciones u operación, nunca el runtime.
- La lectura solo se hace mediante selectores de plataforma (ADR-001 §2). Hasta que exista uno, solo el rol propietario puede leer.

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
- La respuesta al cliente no depende de lo que se audita: el motivo de un fallo de acceso solo queda en la fila.
- Los tests comprueban los privilegios por introspección y que ningún campo contiene contraseña, email en claro ni cookies.

## Operational implications

- El job de migraciones debe ejecutarse al menos una vez al año para extender las particiones, como con `audit_logs`.
- Las alertas por picos de `auth.login.failed` (ADR-003, Operational implications) leen este sumidero con el rol de operación, no con `crm_app`.
