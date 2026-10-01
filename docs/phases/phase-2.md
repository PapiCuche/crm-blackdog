# Fase 2 — Identidad, organizaciones y acceso

- **Estado:** planificada (bloque inicial F2-00 … F2-08)
- **Issue maestro:** [#36](https://github.com/PapiCuche/crm-gooddoggy/issues/36)
- **Objetivo:** usuarios, membresías, sesión por cookie y RBAC con alcance reales sobre el kernel de la Fase 1, y la primera pantalla funcional (login y entrada al shell de tenant).
- **Origen:** [roadmap §S.1](../fase-0/05-backlog-y-roadmap.md) (fila "Fase 2") e historias E01 del [backlog §R](../fase-0/05-backlog-y-roadmap.md).

La fase empieza por el backend y conecta el frontend mediante el contrato OpenAPI y el cliente generado por orval. `/demo` sigue siendo una demo con datos ficticios ([frontend/README.md](../../frontend/README.md)): sirve de referencia visual, y las rutas reales viven en `/o/[orgSlug]`.

## Work items

Cada work item es un issue con el alcance completo (Incluye / No incluye / criterios / validaciones). Este documento solo los ordena; **el issue es la fuente de verdad**.

| ID | Issue | Rama | Depende de | Tipo |
|---|---|---|---|---|
| F2-00 | [#37](https://github.com/PapiCuche/crm-gooddoggy/issues/37) Phase 2 plan | `docs/phase-2-plan` | — | docs |
| F2-01 | [#38](https://github.com/PapiCuche/crm-gooddoggy/issues/38) User model | `feature/f2-user-model` | #37 | backend |
| F2-02 | [#39](https://github.com/PapiCuche/crm-gooddoggy/issues/39) Organization memberships | `feature/f2-memberships` | #38 | backend |
| F2-03A | [#40](https://github.com/PapiCuche/crm-gooddoggy/issues/40) Session authentication API | `feature/f2-session-auth` | #39 | backend + API |
| F2-04 | [#41](https://github.com/PapiCuche/crm-gooddoggy/issues/41) RBAC model | `feature/f2-rbac-model` | #39 | backend |
| F2-05 | [#42](https://github.com/PapiCuche/crm-gooddoggy/issues/42) RBAC enforcement | `feature/f2-rbac-enforcement` | #41 | backend |
| F2-06 | [#43](https://github.com/PapiCuche/crm-gooddoggy/issues/43) Organization bootstrap | `feature/f2-org-bootstrap` | #41 | backend |
| F2-07 | [#44](https://github.com/PapiCuche/crm-gooddoggy/issues/44) Frontend security / CSP | `feature/f2-frontend-csp` | #37 | frontend |
| F2-08 | [#45](https://github.com/PapiCuche/crm-gooddoggy/issues/45) Frontend access integration | `feature/f2-frontend-access` | #40, #44 | frontend |

```text
#37 F2-00 ─┬─► #38 F2-01 ─► #39 F2-02 ─┬─► #40 F2-03A ─────────────┐
           │                           └─► #41 F2-04 ─┬─► #42 F2-05 │
           │                                          └─► #43 F2-06 │
           └─► #44 F2-07 ───────────────────────────────────────────┴─► #45 F2-08
```

- Los work items de backend llevan el gate `required-check:backend gate`.
- El orquestador `work-item-dependencies` pasa cada issue a `status:ready` cuando sus dependencias están cerradas ([delivery-automation.md](../architecture/delivery-automation.md)).
- Tras F2-00 quedan listos a la vez F2-01 y F2-07: no dependen entre sí. Con más de un issue listo, el mantenedor elige.
- **Punto de integración del frontend:** F2-08. Hasta entonces ninguna ruta real muestra datos.

### Tamaño

Objetivo: ≤ 400 líneas relevantes por PR. Más de 800 no se acepta ([ADR-009](../adr/ADR-009-git-strategy.md)). Si un work item amenaza con superarlo, se divide **antes** de implementar, sin recortar tests ni migraciones. La excepción de tamaño aplicada a UI-01 (PR #35) no es un precedente.

Candidatos conocidos a división:

- **F2-03A:** si el bloqueo progresivo de intentos no cabe, pasa a un F2-03B.
- **F2-05:** la caché de permisos efectivos con invalidación por evento puede separarse.

## Historias E01 fuera de este bloque

Se planifican como work items al cerrar el bloque inicial, un slice por historia (backend y API primero; frontend en un issue aparte si supera el tamaño):

| Historia | Contenido | Condición previa |
|---|---|---|
| E01-06 | Invitaciones | Abstracción de envío de correo |
| E01-07 | Activar, desactivar y revocar sesiones | F2-03A |
| E01-08 | API y pantallas de roles | F2-05 |
| E01-09 | Sucursales y equipos | F2-05 |
| E01-02 | Recuperación de contraseña | Abstracción de envío de correo |
| E01-03 | MFA TOTP con `MFA_ENFORCEMENT` | Decisión de cifrado de secretos |
| E01-13 | Auditoría filtrable | F2-05 |
| E01-10, E01-11 | Horarios; sesiones activas (P1) | — |
| E01-12 | Impersonación (P2) | Auditoría de plataforma |

La reasignación de conversaciones al desactivar un usuario (parte de E01-07) depende del Inbox (Fase 6) y no entra en la Fase 2.

## Decisiones abiertas

Ninguna se resuelve en este documento. Un ADR `Accepted` no se modifica: si una decisión lo contradice o amplía, se propone un ADR nuevo.

| ID | Decisión | Estado actual | Bloquea |
|---|---|---|---|
| D-F2-1 | **Auditoría de plataforma.** `audit_logs.organization_id` es NOT NULL (OBS-F1-06-1 en [phase-1.md](phase-1.md)) y el login ocurre antes de elegir organización. No se inserta un `organization_id` ficticio, no se usa una organización arbitraria y no se relaja RLS. | Sin diseño. Probable ADR nuevo | F2-03A (#40) |
| D-F2-2 | **Almacén de sesiones.** BD, Redis o híbrido. Debe cubrir revocación, expiración, cierre de las demás sesiones, desactivación de usuario y varias instancias. | [ADR-003](../adr/ADR-003-auth-session.md) §2 lo deja a la Fase 2 | F2-03A (#40) |
| D-F2-3 | **Email case-insensitive.** ✅ Resuelta en F2-01 (#38): canonicalización explícita en la aplicación (`apps.accounts.emails`) más `UNIQUE (email)` y `CHECK (email = lower(email))` en la BD. No se usa `citext`, previsto en [02-modelo-de-datos.md](../fase-0/02-modelo-de-datos.md) §E.2: evita una extensión y deja el comportamiento explícito. La parte local debe ser ASCII; un dominio internacionalizado se guarda en forma IDNA. Sin reglas por proveedor. Detalle en [backend/README.md](../../backend/README.md). | Resuelta | — |
| D-F2-4 | **Dependencias nuevas** (bloqueo progresivo, TOTP). No se añaden sin su fila en [ADR-012](../adr/ADR-012-engineering-runtime-baseline.md). | `argon2-cffi` ya está fijado; el resto no | F2-03A / F2-03B, E01-03 |
| D-F2-5 | **Envío de correo.** Mailpit es infraestructura local, no el diseño del envío en producción. Hace falta una abstracción. | Sin diseño | E01-06, E01-02 |
| D-F2-6 | **Secretos TOTP.** Cifrado, KEK y rotación; nunca en claro. | Sin diseño | E01-03 |
| D-F2-7 | **Lenguaje visual del shell real.** `/o/[orgSlug]` usa hoy el tema oscuro; el Figma GOOD DOGGY es la referencia para las pantallas nuevas. | Se concreta en F2-08 | F2-08 (#45) |

Observaciones de la Fase 1 que afectan a esta fase: OBS-F1-03-1 (reversibilidad de `CompositeTenantFK`, antes de F2-02), OBS-F1-04-1 (FK de tenant en la primera tabla de negocio, F2-02), OBS-F1-09-1 (CSP, F2-07) y OBS-F1-09-2 (fixes de Next.js pendientes upstream).

## Principios para cada slice

Resumen operativo; la fuente es la arquitectura enlazada.

- **Tenancy** ([tenancy-context.md](../architecture/tenancy-context.md), [ADR-001](../adr/ADR-001-multi-tenancy.md), [ADR-002](../adr/ADR-002-postgresql-rls.md)): `organization_id` sale del contexto, nunca del payload. Las operaciones tenant-owned ocurren dentro de `tenant_scope`, con FORCE RLS, tests cruzados con dos organizaciones y runtime con `crm_app`.
- **Autorización** ([ADR-003](../adr/ADR-003-auth-session.md) §5, [security-boundaries.md](../architecture/security-boundaries.md) B2): usuario autenticado, membresía activa, organización activa, permiso y scope se verifican por separado, y cada denegación tiene su test.
- **Auditoría** ([ADR-011](../adr/ADR-011-observability-and-logs.md)): los cambios relevantes usan `audit.record`. Nunca contraseñas, tokens ni secretos.
- **API:** DRF y drf-spectacular, errores con la convención vigente, schema commiteado sin drift y cliente TypeScript generado con orval. Sin `fetch` manual que duplique un contrato generable.
- **Orden de un slice:** modelo e invariantes → migraciones y RLS → servicio → autorización → API → OpenAPI → tests de backend → orval → frontend → tests de frontend → revisión de tenancy y seguridad.
- **Rutas reales:** cada dato mostrado tiene fuente, autorización, tenant, contrato, estados de error y tests. Una pantalla de `/demo` no adelanta su dominio.

## Definition of Done de la fase

Del roadmap §S.1, además del DoD general:

- Login, MFA y roles con scope.
- Tests anti-escalada.
- Tests T14 y T15 de `organization_memberships`.
- Auditoría de login y de roles.

El bloque inicial F2-00 … F2-08 no cierra la fase: MFA y la gestión de roles llegan con las historias E01 pendientes.

## Observaciones vivas (de revisiones)

Se registran como `OBS-F2-<nn>-<n>`.

### OBS-F2-01-1 — Tablas de `django.contrib.auth` sin uso
Instalar `django.contrib.auth` crea `auth_permission`, `auth_group` y `auth_group_permissions`. El modelo `User` no usa `PermissionsMixin`: esas tablas quedan vacías de significado y el RBAC del producto será el de `access` (F2-04).
- No bloqueante. Revisar si conviene retirarlas cuando exista `access`.

### OBS-F2-01-2 — Parte local del email solo ASCII
El validador de Django rechaza partes locales con caracteres no ASCII (direcciones SMTPUTF8). Se acepta como límite conocido.
- No bloqueante. Reabrir si un cliente lo necesita.

### OBS-F2-01-4 — El redactor no trata el email como dato sensible
`core.redaction` redacta secretos (contraseñas, tokens, credenciales), pero no la clave `email`. F2-01 no registra emails: `User.__str__` devuelve el identificador, no la dirección.
- Decidir antes de F2-03A si los eventos de acceso registran el email, un hash o solo el `user_id`.

### OBS-F2-01-3 — Longitud mínima de contraseña
ADR-003 §2 exige validar contraseñas comunes o filtradas, pero no fija una longitud. F2-01 usa 12 caracteres. La comprobación contra contraseñas filtradas (servicio externo) no está implementada.
- Pendiente de confirmación del PO.
