# ADR-002: PostgreSQL Row Level Security como defensa en profundidad

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-001, [tenancy-context.md](../architecture/tenancy-context.md), decisiones D4, D11

## Context

El aislamiento en la aplicación (ADR-001) depende de que cada consulta esté bien filtrada. Hay muchos puntos de entrada (HTTP, Celery, WebSockets, webhooks, tools IA, comandos) y muchos desarrolladores y agentes de IA escribiendo código. Un solo filtro olvidado basta para una fuga.

**RLS no sustituye** la validación de `organization_id`, el scoping en servicios y querysets, el RBAC ni la validación de membresía. Es la **última barrera**.

Hay detalles de PostgreSQL que, si se ignoran, anulan RLS en silencio:

- El **propietario de la tabla ignora RLS** salvo que se use `FORCE ROW LEVEL SECURITY`.
- Los roles con **`BYPASSRLS`** y los superusuarios ignoran RLS siempre.
- Las **comprobaciones de FK no aplican RLS** (se puede referenciar una fila invisible).
- Una variable de sesión (`SET`) **sobrevive** en una conexión reutilizada por el pool y puede filtrar el contexto a la siguiente petición.
- Tras usar `set_config(..., true)` en una sesión, `current_setting('x', true)` puede devolver `''` en lugar de `NULL` en transacciones posteriores.

## Decision

### 1. Roles de base de datos

| Rol | LOGIN | Propietario de tablas | BYPASSRLS | Uso |
|---|---|---|---|---|
| `crm_migrator` | Sí | **Sí** | Sí | Solo migraciones (pipeline de deploy o comando manual). Nunca lo usa el runtime |
| `crm_app` | Sí | **No** | **No** | Runtime: web, ws, workers. Solo DML (`SELECT/INSERT/UPDATE/DELETE`) según grants; sin DDL |
| `crm_platform` | Sí | No | Sí | Opcional. Comandos y jobs de plataforma explícitamente marcados; alias de conexión separado; cada uso se audita. **No se crea hasta que haga falta** |
| `crm_readonly` | Sí | No | No | Futuro: réplicas, BI, soporte (sujeto a RLS) |

- Grants por `ALTER DEFAULT PRIVILEGES FOR ROLE crm_migrator … GRANT … TO crm_app`.
- En tablas append-only (`audit_logs`, `ai_actions`, `inventory_movements`, `*_history`) se revoca `UPDATE` y `DELETE` a `crm_app`.
- El usuario de conexión de la aplicación **nunca** es superusuario (en local tampoco: el script de init de Docker crea los roles).

### 2. Variables de contexto (siempre transaccionales)

| GUC | Contenido | Quién la fija |
|---|---|---|
| `app.tenant_id` | UUID de la organización activa | `tenant_scope()` |
| `app.user_id` | UUID del usuario humano (si lo hay) | `tenant_scope()` / `user_scope()` |
| `app.actor_type` | USER / AI_AGENT / SYSTEM / INTEGRATION | Informativo (triggers de auditoría futuros) |

Se fijan **exclusivamente** con `SELECT set_config('app.tenant_id', %s, true)`: el tercer argumento `true` = `SET LOCAL`, que muere con la transacción. **Está prohibido `SET` a nivel de sesión** (lo verifica un test que busca `SET app.` en el código y un check en runtime).

### 3. Políticas

```sql
-- Función auxiliar estable (evita repetir NULLIF y el cast)
CREATE FUNCTION app_current_tenant() RETURNS uuid
  LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$;

-- En cada tabla tenant-owned (generado por una operación de migración reutilizable)
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON contacts
  USING (organization_id = app_current_tenant())
  WITH CHECK (organization_id = app_current_tenant());
```

- Sin contexto → `app_current_tenant()` es NULL → `organization_id = NULL` es NULL → **0 filas** e INSERT rechazado.
- `organization_memberships` añade una política permisiva de solo lectura: `USING (user_id = NULLIF(current_setting('app.user_id', true), '')::uuid)`, para que un usuario pueda listar sus organizaciones antes de elegir una.
- **Lookups cross-tenant legítimos** (enrutar un webhook por `phone_number_id`, resolver un token público de cotización) se hacen con **funciones `SECURITY DEFINER` mínimas**, propiedad de `crm_migrator`, con `SET search_path` fijo, que devuelven solo `(organization_id, resource_id)`. `crm_app` tiene únicamente `EXECUTE` sobre ellas. Así no hace falta un rol con BYPASSRLS en el runtime.

### 4. Integridad referencial entre tenants

Como las FK no aplican RLS, las relaciones críticas usan **FKs compuestas** con `organization_id`:

```sql
ALTER TABLE contacts ADD CONSTRAINT contacts_org_id_uq UNIQUE (organization_id, id);
ALTER TABLE leads ADD CONSTRAINT leads_contact_same_org_fk
  FOREIGN KEY (organization_id, contact_id) REFERENCES contacts (organization_id, id);
```

Django no las genera de forma nativa: se añaden con una operación de migración reutilizable (`CompositeTenantFK`).

### 5. Pooling

- Compatible con **PgBouncer en modo transaction** porque todo el contexto es `SET LOCAL`.
- Con PgBouncer transaction pooling: `DISABLE_SERVER_SIDE_CURSORS = True` (requisito de Django) y sin prepared statements con nombre si la versión de PgBouncer no los soporta.
- `CONN_MAX_AGE` > 0 es seguro por la misma razón. Además, `CONN_HEALTH_CHECKS = True`.

### 6. Versión objetivo

**PostgreSQL 18** (D11). Se usa `uuidv7()` nativo como default de respaldo (ADR-004). La extensión `pgvector` **no** es dependencia de la Fase 1 (se habilita cuando se implemente la base de conocimiento). `btree_gist` sí se habilita en la fase de precios (restricciones EXCLUDE de vigencia, ADR-006).

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Sin RLS, solo filtros de aplicación | Un olvido = fuga. Retrofitear RLS después es caro |
| RLS con `SET` de sesión | Filtra el contexto entre peticiones al reutilizar conexiones |
| El rol de la app es propietario + FORCE RLS | Funciona para DML, pero la app tendría privilegios DDL (podría hacer `ALTER TABLE … DISABLE ROW LEVEL SECURITY`). Separar propietario y runtime es más seguro |
| Rol BYPASSRLS en el runtime para webhooks | Innecesario: las funciones SECURITY DEFINER mínimas cubren esos lookups con privilegio mínimo |
| Vistas por tenant | Complejidad sin ventaja sobre RLS |

## Consequences

- Toda query de la aplicación debe ejecutarse dentro de una transacción con contexto. Las vistas HTTP de tenant se envuelven automáticamente; Celery, WS y los comandos usan helpers (ver [tenancy-context.md](../architecture/tenancy-context.md)).
- Ligero coste de rendimiento (la condición RLS se suma a cada consulta). Es despreciable con índices que empiezan por `organization_id`.
- Las migraciones deben ejecutarse con `crm_migrator`: dos cadenas de conexión (`DATABASE_URL` y `DATABASE_MIGRATOR_URL`).
- Los tests deben ejecutarse con un rol **equivalente a `crm_app`** (no superusuario). Si no, RLS no se prueba. El entorno de tests crea ambos roles.

## Security implications

- Defensa en profundidad real frente a filtros olvidados, consultas raw y bugs en tools de IA.
- Riesgos residuales: funciones SECURITY DEFINER mal escritas (se revisan en PR con checklist: `search_path` fijo, parámetros tipados, retorno mínimo) y uso de `crm_platform` (auditado y restringido a módulos de plataforma por import-linter).
- **Tests obligatorios (gate de CI):**
  1. Sin contexto → 0 filas en cada tabla tenant-owned.
  2. Con el contexto de A → no se ve ninguna fila de B.
  3. INSERT con un `organization_id` distinto del contexto → error.
  4. Introspección: toda tabla con columna `organization_id` tiene `relrowsecurity` y `relforcerowsecurity` activos y una política `tenant_isolation`.
  5. Introspección: `crm_app` no es propietario de ninguna tabla, no tiene BYPASSRLS y no es superusuario.
  6. Fuga por pool: petición con A, la siguiente con B en la misma conexión → `current_setting` vacío al inicio de la segunda.
  7. Suite HTTP cruzada sobre todas las rutas.

## Operational implications

- El script de init de Docker local y la IaC de producción crean los roles y los grants. Los runbooks documentan la rotación de contraseñas de cada rol.
- Las consultas de soporte en producción se hacen con un rol sujeto a RLS y fijando el contexto explícitamente, o con `crm_platform` y registro de auditoría.
- La monitorización alerta si aparece una conexión de `crm_migrator` fuera de una ventana de deploy.
