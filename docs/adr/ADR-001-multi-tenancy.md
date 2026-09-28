# ADR-001: Multi-tenancy con base de datos y esquema compartidos

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-002 (RLS), ADR-003 (auth), [tenancy-context.md](../architecture/tenancy-context.md), decisiones D1, D2, D3, D7

## Context

El producto es un SaaS multiempresa. Cada organización tiene sus propios usuarios, contactos, conversaciones, catálogo, precios, stock, agentes IA, credenciales e integraciones. **No puede existir ninguna fuga de información entre organizaciones.**

Además:

- un mismo usuario puede trabajar en varias organizaciones (D2);
- el personal de la plataforma (Superadmin) no es miembro de las organizaciones (D1);
- la organización activa aparece en la URL (D3), pero la URL **no autoriza nada**;
- los permisos admiten alcances OWN / TEAM / BRANCH / ORGANIZATION (D7).

## Decision

### 1. Modelo de aislamiento

**Base de datos compartida, esquema compartido y `organization_id NOT NULL` en toda tabla tenant-owned.** PostgreSQL RLS actúa como segunda barrera (ADR-002).

### 2. Clasificación de tablas

| Clase | Ejemplos | `organization_id` | RLS |
|---|---|---|---|
| **Tenant-owned** | contacts, conversations, messages, products, product_prices, roles, ai_agents, audit_logs de la organización | NOT NULL | Sí, con FORCE |
| **Membership-bridge** | organization_memberships | NOT NULL | Sí, con FORCE y **una única política SELECT condicional**: con tenant activo, solo filas de ese tenant; sin tenant y con `app.user_id`, solo las membresías del usuario. Las escrituras exigen tenant activo. No se usa una segunda política permisiva (se sumaría con OR). Detalle en ADR-002 §3.2 |
| **Platform-owned** | organizations, users, platform_files, permissions, ai_providers, ai_models, webhook_ingress | No (o nullable) | No usan la política de tenant; acceso solo mediante selectores de plataforma |

### 3. Identidad y membresía

- `users` es la identidad global de la persona (login, MFA).
- `organization_memberships (organization_id, user_id, status, …)`, con UNIQUE (`organization_id`, `user_id`), es la **pertenencia**.
- Los roles se asignan a la membresía (`membership_roles`), no al usuario global.
- **Convención de FKs de negocio a personas:** las columnas se llaman `*_user_id` (p. ej., `assigned_user_id`, `created_by_user_id`) y tienen una **FK compuesta** `(organization_id, *_user_id) → organization_memberships(organization_id, user_id)`. Esto garantiza en la base de datos que la persona referenciada es miembro de la misma organización. *(`docs/fase-0/02-modelo-de-datos.md` §E.0 aplica esta convención.)*
- El Superadmin tiene `users.is_platform_staff = true` y **ninguna membresía implícita**. Para ver datos de un tenant necesita una sesión de impersonación explícita, con tiempo limitado y auditada.

### 4. Resolución del tenant en cada petición

```text
URL /o/{org_slug}/…  (frontend)   →  API /api/v1/o/{org_slug}/…
  1. Usuario autenticado (sesión)
  2. slug → organization (selector de plataforma; si no existe → 404)
  3. membership ACTIVE de (organization, user)? si no → 404 (no 403: no revelar existencia)
  4. organization.status permite acceso? (SUSPENDED → 403 con código ORG_SUSPENDED)
  5. ExecutionContext(organization, membership, permissions, actor, request_id)
  6. tenant_scope(organization.id) → transacción + SET LOCAL (ADR-002)
```

El slug es solo un **selector**. La autorización sale siempre de la membresía, los permisos y el contexto.

### 5. Reglas de implementación obligatorias

1. `organization_id` se asigna siempre desde el `ExecutionContext` en la capa de servicios. **Nunca** se acepta del payload.
2. Toda FK recibida por la API se valida dentro del tenant (`TenantPrimaryKeyRelatedField`), y las relaciones críticas tienen además una FK compuesta `(organization_id, fk_id)`.
3. Toda restricción UNIQUE de una tabla tenant-owned empieza por `organization_id`.
4. El manager por defecto de `TenantModel` **falla** si no hay contexto de tenant; no devuelve "todo".
5. Las claves de caché, los nombres de grupo WebSocket y las keys de objetos llevan el prefijo del tenant.
6. Una respuesta sobre un recurso de otro tenant es **404**, idéntica a la de un recurso inexistente.

### 6. Alcances de permisos (D7)

Se implementan como **atributo de la concesión** (`role_permissions.scope`), no como permisos distintos. Ver ADR-003 §RBAC y [security-boundaries.md](../architecture/security-boundaries.md).

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Base de datos por tenant | Máximo aislamiento, pero migraciones N×, pooling complejo y coste operativo alto para un equipo pequeño |
| Esquema por tenant (django-tenants) | Migraciones lentas con muchos tenants, dificulta reportes de plataforma y la búsqueda cruzada controlada; el aislamiento no es superior a RLS bien configurado |
| Filtro solo en la aplicación | Depende de que nadie olvide nunca un filtro (Celery, scripts, tools IA). Riesgo inaceptable (ver ADR-002) |
| `organization_id` en el header en lugar de la URL | D3 exige la URL. La URL da soporte multipestaña correcto y enlaces compartibles |
| FK a `organization_memberships.id` en lugar de `user_id` + FK compuesta | Funciona, pero complica los joins con `users` y la lectura del esquema; la FK compuesta da la misma integridad con nombres más claros |

## Consequences

- **Positivas:** un solo esquema, migraciones simples, reportes de plataforma posibles con un rol explícito, aislamiento fuerte con RLS.
- **Negativas:** cada tabla tenant-owned necesita índices que empiecen por `organization_id`, una política RLS y tests de aislamiento. Un tenant muy grande puede afectar a los demás (*noisy neighbour*); se mitigará con límites por plan y, si hiciera falta, moviendo ese tenant a una base dedicada (el diseño lo permite porque todas las filas llevan `organization_id`).
- Un usuario en varias organizaciones ve un selector de organización; sus sesiones son únicas, pero el contexto cambia por URL.

## Security implications

- La fuga entre tenants es la amenaza nº 1 del producto (threat model #1). Defensa en capas: membresía → servicios con contexto → querysets con scope → RLS → FKs compuestas → tests automáticos.
- 404 uniforme para evitar la enumeración de organizaciones y de recursos.
- El personal de la plataforma no tiene acceso implícito: la impersonación está auditada.

## Operational implications

- La suite de aislamiento cruzado es un **gate obligatorio de CI** desde la Fase 1.
- Toda migración que cree una tabla tenant-owned debe incluir su política RLS (lo verifica un test de introspección del esquema).
- La exportación o eliminación de un tenant completo es posible filtrando por `organization_id` (útil para bajas y para la ley de protección de datos).
