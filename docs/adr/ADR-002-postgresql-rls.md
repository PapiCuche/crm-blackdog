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
| `crm_migrator` | Sí | **Sí** | Sí | Solo migraciones (job de migraciones del deploy o comando manual). Nunca lo usa el runtime. **Credencial de máximo privilegio** (ver §1.1) |
| `crm_app` | Sí | **No** | **No** | Runtime: web, ws, workers. Solo DML (`SELECT/INSERT/UPDATE/DELETE`) según grants; sin DDL |
| `crm_platform` | Sí | No | Sí | Opcional. Comandos y jobs de plataforma explícitamente marcados; alias de conexión separado; cada uso se audita. **No se crea hasta que haga falta** |
| `crm_readonly` | Sí | No | No | Futuro: réplicas, BI, soporte (sujeto a RLS) |

- Grants por `ALTER DEFAULT PRIVILEGES FOR ROLE crm_migrator … GRANT … TO crm_app`.
- En tablas append-only (`audit_logs`, `ai_actions`, `inventory_movements`, `*_history`) se revoca `UPDATE` y `DELETE` a `crm_app`.
- El usuario de conexión de la aplicación **nunca** es superusuario (en local tampoco: el script de init de Docker crea los roles).
- **`CREATEDB` en `crm_migrator` es solo una comodidad del bootstrap Docker local** (permite que el runner de tests cree la BD de test). En producción la base de datos la aprovisiona la infraestructura y el rol de migraciones **no** tiene `CREATEDB`, `CREATEROLE` ni `SUPERUSER`.
- El script de init local revoca además `EXECUTE` a `PUBLIC` sobre las funciones que cree `crm_migrator` (`ALTER DEFAULT PRIVILEGES … REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC`), como base para §3.3.

### 1.1 Distribución de credenciales (aislamiento de `crm_migrator`)

`crm_migrator` tiene BYPASSRLS y es propietario del esquema: **su credencial equivale a acceso total a todos los tenants.** Se trata como un secreto del nivel más alto.

| Proceso (producción) | Recibe | Nunca recibe |
|---|---|---|
| `web` (HTTP) | `DATABASE_URL` → `crm_app` | `DATABASE_MIGRATOR_URL`, `CRM_MIGRATOR_PASSWORD` |
| `worker` (Celery) | `DATABASE_URL` → `crm_app` | ídem |
| `ws` (Channels) | `DATABASE_URL` → `crm_app` | ídem |
| `beat` (Celery beat) | `DATABASE_URL` → `crm_app` | ídem |
| Job de migraciones (efímero, una vez por deploy) | `DATABASE_MIGRATOR_URL` → `crm_migrator` + el mínimo de settings para arrancar Django | `DATABASE_URL` de runtime y los secretos de runtime que no necesita (KEK de credenciales, tokens de Meta, DSN de Sentry opcional, etc.) |

Reglas:

1. Los settings de runtime **no definen** un alias de conexión con el migrador. El job de migraciones usa un módulo de settings propio (`config.settings.migrate`) que toma `DATABASE_MIGRATOR_URL` como conexión por defecto.
2. **Comprobación defensiva al arrancar:** si `web`, `worker`, `ws` o `beat` detectan `DATABASE_MIGRATOR_URL` o `CRM_MIGRATOR_PASSWORD` en su entorno, **se niegan a arrancar** (error de configuración). También fallan si el rol conectado tiene `rolsuper` o `rolbypassrls`, o si es propietario de alguna tabla.
3. En el gestor de secretos, la credencial del migrador tiene su propia política de acceso (solo el pipeline de deploy) y se rota tras cualquier sospecha y periódicamente.
4. En local y en CI conviven ambas credenciales (el runner de tests migra con `crm_migrator` y ejecuta los tests con `crm_app`). Es aceptable porque no hay datos reales.

### 2. Variables de contexto (siempre transaccionales)

| GUC | Contenido | Quién la fija |
|---|---|---|
| `app.tenant_id` | UUID de la organización activa | `tenant_scope()` |
| `app.user_id` | UUID del usuario humano (si lo hay) | `tenant_scope()` / `user_scope()` |
| `app.actor_type` | USER / AI_AGENT / SYSTEM / INTEGRATION | Informativo (triggers de auditoría futuros) |

Se fijan **exclusivamente** con `SELECT set_config('app.tenant_id', %s, true)`: el tercer argumento `true` = `SET LOCAL`, que muere con la transacción. **Está prohibido `SET` a nivel de sesión** (lo verifica un test que busca `SET app.` en el código y un check en runtime).

### 3. Políticas

#### 3.1 Tablas tenant-owned (caso general)

```sql
-- Funciones auxiliares estables (evitan repetir NULLIF y el cast).
-- Tras un set_config local, current_setting(..., true) puede devolver '' en lugar de NULL.
CREATE FUNCTION app_current_tenant() RETURNS uuid LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$;
CREATE FUNCTION app_current_user() RETURNS uuid LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;

-- En cada tabla tenant-owned (generado por una operación de migración reutilizable)
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON contacts
  USING (organization_id = app_current_tenant())
  WITH CHECK (organization_id = app_current_tenant());
```

- Sin contexto → `app_current_tenant()` es NULL → `organization_id = NULL` es NULL → **0 filas** e INSERT rechazado.
- **Una sola política PERMISSIVE por tabla y comando.** PostgreSQL combina las políticas PERMISSIVE aplicables con **OR**, así que añadir una segunda política permisiva **amplía** la visibilidad. Cualquier excepción se diseña como una política única con lógica condicional (ver 3.2) o como política RESTRICTIVE, y se revisa en el PR. Un test de introspección lo verifica.

#### 3.2 `organization_memberships` (excepción controlada)

Un usuario necesita listar sus propias membresías **antes** de elegir una organización (sin tenant activo). Con tenant activo, en cambio, no debe ver sus membresías de otras organizaciones ni siquiera con una consulta raw.

```sql
ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships FORCE ROW LEVEL SECURITY;

-- SELECT: una única política; la rama por usuario solo aplica SIN tenant activo.
CREATE POLICY memberships_select ON organization_memberships FOR SELECT
  USING (
    CASE
      WHEN app_current_tenant() IS NOT NULL THEN organization_id = app_current_tenant()
      ELSE app_current_user() IS NOT NULL AND user_id = app_current_user()
    END
  );

-- Escrituras: estrictamente sujetas al tenant activo.
CREATE POLICY memberships_insert ON organization_memberships FOR INSERT
  WITH CHECK (organization_id = app_current_tenant());
CREATE POLICY memberships_update ON organization_memberships FOR UPDATE
  USING (organization_id = app_current_tenant())
  WITH CHECK (organization_id = app_current_tenant());
CREATE POLICY memberships_delete ON organization_memberships FOR DELETE
  USING (organization_id = app_current_tenant());
```

| Contexto | `app.tenant_id` | `app.user_id` | SELECT ve | INSERT/UPDATE/DELETE |
|---|---|---|---|---|
| `tenant_scope(A)` (con usuario) | A | U | Solo filas de A | Solo en A |
| `user_scope(U)` (sin tenant) | — | U | Solo filas de U (todas sus organizaciones) | **Rechazado** |
| Sin contexto | — | — | Nada | Rechazado |

Esta tabla **no** lleva la política genérica `tenant_isolation` (que se sumaría con OR). Aceptar una invitación (crear la membresía) ocurre dentro de `tenant_scope` de la organización que invita, tras validar el token.

#### 3.3 Funciones `SECURITY DEFINER` para lookups entre tenants

Los lookups legítimos que cruzan tenants (enrutar un webhook por `phone_number_id`, resolver el token público de una cotización) se hacen con **funciones `SECURITY DEFINER` mínimas**. Así el runtime no necesita un rol con BYPASSRLS. **Requisitos obligatorios** de cada una:

| Requisito | Cómo |
|---|---|
| Owner explícito privilegiado | `ALTER FUNCTION … OWNER TO crm_migrator` (propietario de las tablas; con BYPASSRLS) |
| `search_path` fijo | `SET search_path = pg_catalog, public` en la definición (evita el secuestro por objetos en otros esquemas); los objetos se referencian cualificados |
| Inputs tipados | Parámetros con tipo concreto (`text`, `uuid`); validación de formato/longitud dentro de la función |
| Retorno mínimo | Solo los identificadores necesarios (p. ej., `organization_id, channel_account_id`); nunca filas completas ni PII |
| Sin SQL dinámico | Sin `EXECUTE format(...)` salvo justificación explícita revisada |
| Sin acceso público | `REVOKE ALL ON FUNCTION … FROM PUBLIC;` **siempre** (en PostgreSQL, `PUBLIC` tiene `EXECUTE` sobre funciones nuevas por defecto; no se asume lo contrario) |
| Grant explícito | `GRANT EXECUTE ON FUNCTION … TO crm_app;` (y a nadie más) |
| Estabilidad | `STABLE` (o `VOLATILE` solo si escribe, cosa que no deberían hacer) |

```sql
CREATE FUNCTION resolve_channel_account(p_platform text, p_external_account_id text)
  RETURNS TABLE (organization_id uuid, channel_account_id uuid)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = pg_catalog, public
AS $$
  SELECT ca.organization_id, ca.id
    FROM public.channel_accounts ca
   WHERE ca.platform = p_platform
     AND ca.external_account_id = p_external_account_id
     AND ca.deleted_at IS NULL
$$;
ALTER FUNCTION resolve_channel_account(text, text) OWNER TO crm_migrator;
REVOKE ALL ON FUNCTION resolve_channel_account(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION resolve_channel_account(text, text) TO crm_app;
```

(Ejemplo de diseño; se implementa en la Fase 7 junto con los canales, mediante una operación de migración reutilizable que aplica siempre el REVOKE y el GRANT.)

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
- Las migraciones deben ejecutarse con `crm_migrator` en un job separado con su propia credencial (`DATABASE_MIGRATOR_URL`); el runtime solo conoce `DATABASE_URL` (§1.1).
- Los tests deben ejecutarse con un rol **equivalente a `crm_app`** (no superusuario). Si no, RLS no se prueba. El entorno de tests crea ambos roles.

## Security implications

- Defensa en profundidad real frente a filtros olvidados, consultas raw y bugs en tools de IA.
- Riesgos residuales: funciones SECURITY DEFINER mal escritas (requisitos de §3.3, checklist de PR y test de introspección 9), una segunda política permisiva añadida por error (test 4b), fuga de la credencial del migrador (§1.1) y uso de `crm_platform` (auditado y restringido a módulos de plataforma por import-linter).
- **Tests obligatorios (gate de CI):**
  1. Sin contexto → 0 filas en cada tabla tenant-owned.
  2. Con el contexto de A → no se ve ninguna fila de B.
  3. INSERT con un `organization_id` distinto del contexto → error.
  4. Introspección: toda tabla con columna `organization_id` tiene `relrowsecurity` y `relforcerowsecurity` activos y una política `tenant_isolation`, **salvo** `organization_memberships`, que tiene exactamente `memberships_select/insert/update/delete`.
  4b. Introspección: ninguna tabla tiene **más de una política PERMISSIVE** para el mismo comando (evita ampliaciones por OR).
  5. Introspección: `crm_app` no es propietario de ninguna tabla, no tiene BYPASSRLS y no es superusuario.
  6. Fuga por pool: petición con A, la siguiente con B en la misma conexión → `current_setting` vacío al inicio de la segunda.
  7. Suite HTTP cruzada sobre todas las rutas.
  8. Memberships: usuario miembro de A y B → con `tenant_scope(A)` (+ `app.user_id`) un `SELECT` raw sobre `organization_memberships` devuelve **solo** la membresía de A; con `user_scope(user)` sin tenant devuelve A y B; con `user_scope` un INSERT/UPDATE/DELETE es rechazado.
  9. SECURITY DEFINER: para toda función `prosecdef` del esquema, `proconfig` contiene `search_path`, el propietario es `crm_migrator`, `PUBLIC` **no** tiene EXECUTE (`aclexplode(proacl)` sin grantee 0) y `crm_app` sí.
  10. Arranque: `web`, `worker`, `ws` y `beat` fallan si su entorno contiene `DATABASE_MIGRATOR_URL` o `CRM_MIGRATOR_PASSWORD`.

## Operational implications

- El script de init de Docker local y la IaC de producción crean los roles y los grants. Los runbooks documentan la rotación de contraseñas de cada rol.
- Las consultas de soporte en producción se hacen con un rol sujeto a RLS y fijando el contexto explícitamente, o con `crm_platform` y registro de auditoría.
- La monitorización alerta si aparece una conexión de `crm_migrator` fuera de una ventana de deploy.
