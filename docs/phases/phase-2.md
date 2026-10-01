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
| F2-05A | [#42](https://github.com/PapiCuche/crm-gooddoggy/issues/42) RBAC enforcement engine | `feature/f2-rbac-enforcement` | #41 | backend |
| F2-05B | [#50](https://github.com/PapiCuche/crm-gooddoggy/issues/50) RBAC: DRF integration | `feature/f2-rbac-drf` | #42 | backend |
| F2-05C | [#51](https://github.com/PapiCuche/crm-gooddoggy/issues/51) RBAC: anti-escalation and last Owner | `feature/f2-rbac-anti-escalation` | #42 | backend |
| F2-06 | [#43](https://github.com/PapiCuche/crm-gooddoggy/issues/43) Organization bootstrap | `feature/f2-org-bootstrap` | #41 | backend |
| F2-07 | [#44](https://github.com/PapiCuche/crm-gooddoggy/issues/44) Frontend security / CSP | `feature/f2-frontend-csp` | #37 | frontend |
| F2-08 | [#45](https://github.com/PapiCuche/crm-gooddoggy/issues/45) Frontend access integration | `feature/f2-frontend-access` | #40, #44 | frontend |

```text
#37 F2-00 ─┬─► #38 F2-01 ─► #39 F2-02 ─┬─► #40 F2-03A ─────────────┐
           │                           └─► #41 F2-04 ─┬─► #42 F2-05A ─┬─► #50 F2-05B
           │                                          │               └─► #51 F2-05C
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
- **F2-05:** dividido antes de implementar (2026-10-01). El diseño estimó unas 1.290 líneas para el alcance original de #42. Quedan F2-05A (#42, motor de autorización), F2-05B (#50, integración con DRF) y F2-05C (#51, anti-escalada y último Owner). B y C dependen solo de A y no entre sí. La caché de permisos sigue fuera.

## Historias E01 fuera de este bloque

Se planifican como work items al cerrar el bloque inicial, un slice por historia (backend y API primero; frontend en un issue aparte si supera el tamaño):

| Historia | Contenido | Condición previa |
|---|---|---|
| E01-06 | Invitaciones | Abstracción de envío de correo |
| E01-07 | Activar, desactivar y revocar sesiones | F2-03A |
| E01-08 | API y pantallas de roles | F2-05B y F2-05C |
| E01-09 | Sucursales y equipos | F2-05A |
| E01-02 | Recuperación de contraseña | Abstracción de envío de correo |
| E01-03 | MFA TOTP con `MFA_ENFORCEMENT` | Decisión de cifrado de secretos |
| E01-13 | Auditoría filtrable | F2-05B |
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

### OBS-F2-05B-1 — Las vistas de DRF no pasan por la protección CSRF de Django
`APIView.as_view()` marca la vista como `csrf_exempt`; DRF solo comprueba CSRF dentro de `SessionAuthentication`, y el proyecto no tiene clases de autenticación hasta F2-03A. Hoy no hay endpoints reales. Antes del primer endpoint que escriba, F2-03A debe aportar una clase de autenticación que exija CSRF. Al añadirla, DRF solo responderá 401 en lugar de 403 a una petición sin autenticar si `authenticate_header()` de la primera clase de `authentication_classes` devuelve un valor; `SessionAuthentication` hereda el de `BaseAuthentication`, que devuelve `None`, y sigue respondiendo 403, con otro `detail`.

### OBS-F2-05B-2 — `ScopeFilter` solo actúa en vistas genéricas
DRF aplica los filtros en `GenericAPIView`, y solo donde la vista llama a `filter_queryset()` (el listado y el `get_object()` de serie). Una vista que consulte por su cuenta debe pasar su queryset por `scoped()` (por ejemplo `get_object_or_404(scoped(...), pk=…)`). La auditoría del URLconf es estática: rechaza las vistas genéricas que redefinen `get_object` o `filter_queryset`, las que redefinen los ganchos de permiso de DRF y las que usan una subclase de `HasPermission` o de `ScopeFilter`, pero no puede revisar una consulta escrita a mano ni el orden en que un handler propio escribe. `HasPermission.has_object_permission` queda como red de seguridad para quien llame a `check_object_permissions`: responde 404, pero con un cuerpo que puede diferir del de un objeto inexistente, así que no equivale a filtrar con `scoped()`. Un serializador de tenant nunca acepta del cliente la clave primaria ni `organization_id`: la clave primaria es única entre organizaciones, y un `id` escribible convierte esa unicidad en un oráculo de existencia y deja que un PATCH inserte una fila. Los modelos reales usan `uuid7_primary_key()` (`editable=False`), que DRF expone como solo lectura.

### OBS-F2-05B-3 — Fuera del alcance del método es 404, aunque el objeto se pueda leer
El filtro usa el permiso del método en curso. Quien puede ver un objeto pero no tiene alcance para modificarlo recibe 404 en el PATCH, no 403. Es deliberado: una sola regla, sin revelar nada.

### OBS-F2-05B-4 — Poder escribir implica leer la respuesta
Cada método se autoriza con su propio permiso y alcance, y no hay implicación entre permisos (ADR-003 §5). Un PATCH responde con el objeto serializado: quien tiene el permiso de escritura con un alcance mayor que el de lectura, o sin el de lectura, ve esa respuesta. La gestión de roles (E01-08) debería mantener el alcance de escritura dentro del de lectura; un endpoint que no deba revelar nada puede responder 204.

### OBS-F2-05B-5 — El alcance se comprueba sobre la fila antes de escribir, no sobre el resultado
`HasPermission` solo comprueba que el permiso existe y `ScopeFilter` filtra la fila tal como está antes de la escritura. Un POST no tiene fila previa: crear no pasa por ningún alcance. Un PUT o PATCH que exponga una columna de la `ScopePolicy` (asignado, creador, equipo, sucursal) puede dejar la fila fuera del alcance de quien la escribe. Con alcance OWN se puede así crear o dejar una fila asignada a otra persona de la misma organización; la organización sale siempre del contexto. Hoy ninguna vista crea filas ni expone esas columnas. El primer endpoint que lo haga debe fijarlas desde el contexto, dejarlas de solo lectura o comprobar la instancia resultante con `require(ectx, código, instancia)` antes de guardar. La auditoría del URLconf no lo detecta.

### OBS-F2-05B-6 — Las respuestas de tenant no se cachean por URL
La auditoría rechaza un decorador alrededor de `as_view()` (uno que responda antes de la vista, como `cache_page`, se salta `HasPermission`). No ve un `cache_page` puesto sobre el handler: ahí el permiso sí se comprueba, pero la clave es solo la URL y la respuesta de un alcance se serviría a otro. Hoy no hay caché de respuestas ni rutas de tenant reales. Antes de cachear una respuesta de tenant hay que decidir una clave que incluya la membresía y sus permisos.

### OBS-F2-05A-1 — Los permisos son una foto por petición
`execution_context` lee la membresía y sus concesiones una vez, dentro del `tenant_scope` de la petición. Revocar un rol surte efecto en la siguiente petición, no a mitad de una (coherente con ADR-003 §5). Sin caché. La foto queda ligada a su transacción: usarla en un `tenant_scope` posterior falla con `TenantContextError`, aunque el contexto sea igual. En DRF (F2-05B) la foto se guarda en la petición HTTP, así que la comparten todos los envoltorios `Request` que DRF crea para ella (por ejemplo al describir la vista en un OPTIONS).

### OBS-F2-05A-2 — TEAM y BRANCH equivalen a OWN hasta E01-09
No existen tablas de equipos ni sucursales. `ExecutionContext.team_ids` y `branch_ids` están vacíos, así que esos alcances nunca dan más que OWN. E01-09 debe rellenarlos en `execution_context` sin añadir una consulta por rol.

### OBS-F2-05A-3 — La transacción de la petición se confirma aunque la vista falle
El middleware de tenant convierte la excepción en respuesta dentro del `tenant_scope`, así que un 403 o un 500 hacen COMMIT de lo ya escrito. Todo servicio debe comprobar antes de escribir y envolver sus escrituras en un savepoint. Es comportamiento previo a esta fase; afecta a F2-05C y a todo servicio posterior. En DRF (F2-05B) el permiso se comprueba antes de ejecutar el método de la vista; el alcance se comprueba dentro, en `get_object()` y `filter_queryset()`. Las vistas genéricas de serie no escriben antes de esa consulta, así que una denegación no deja escrituras. Una vista que escriba antes de llamar a `get_object()` (o a `scoped()`) responde 404 y confirma lo ya escrito, igual que un error posterior dentro de la vista; la auditoría del URLconf no detecta ese orden.

### OBS-F2-05A-4 — Denegaciones sin auditar
ADR-011 prevé auditar los accesos denegados. El motor no escribe filas `DENIED`. F2-05B crea el punto HTTP (`HasPermission`) pero no audita: falta decidir qué denegaciones se registran y con qué detalle. Queda para E01-13.

### OBS-F2-05A-5 — Cuerpo de error de la API
No hay manejador de excepciones propio: una denegación en una vista de DRF devuelve `{"detail": …}` y no la convención `{"code": …}` del middleware. Con F2-05B conviven las dos: 401, 404 y 403 `ORG_SUSPENDED` del middleware con `{"code": …}`; 403 y 404 de DRF con `{"detail": …}`. En las vistas genéricas con `ScopeFilter`, los 404 son idénticos entre sí (fuera de alcance, otra organización, inexistente); el 404 de `HasPermission.has_object_permission` tiene otro texto (OBS-F2-05B-2). La decisión, antes del primer endpoint real, debe dejar un único cuerpo para todos los 404 de una ruta de tenant. DRF negocia el formato antes de comprobar el permiso: en una ruta de tenant, un miembro activo que pida un formato que la API no sirve recibe 404 (`?format=xml`) o 406 (`Accept: application/xml`) en lugar del 403 o del 404 de alcance, tenga o no el permiso. No concede ni revela nada: la vista no se ejecuta y el 401 y el 404 del middleware van antes. Esa decisión debe cubrir también estas dos respuestas; como la API es solo JSON, una opción es fijar `URL_FORMAT_OVERRIDE: None`, que hoy no está configurado.

### OBS-F2-04-1 — Las concesiones del rol Owner no siguen al catálogo
`clone_role_templates` no toca un rol que ya existe y `sync_permissions` solo sincroniza `permissions`. El rol Owner se modela con concesiones explícitas de todo el catálogo, así que una organización ya creada no recibe los permisos que añada una fase posterior.
- Todo work item que añada permisos al catálogo debe decidir cómo llegan al rol Owner de cada organización (localizado por `is_owner_role`, nunca por código): migración de datos o un paso tras el `migrate`.
- Lo mismo aplica a las demás plantillas si se quiere que los cambios lleguen a roles ya clonados.

### OBS-F2-04-2 — Los roles de sistema se pueden borrar y renombrar
[02-modelo-de-datos.md](../fase-0/02-modelo-de-datos.md) §E.3 dice que un rol `is_system` no se borra y su código no cambia. F2-04 no lo impone: no existe gestión de roles hasta E01-08. Un rol plantilla borrado se vuelve a crear en el siguiente clonado.
- Imponerlo en E01-08, junto con las reglas de edición del rol Owner.

### OBS-F2-04-3 — `permissions`: PK UUIDv7 y `code` único
[ADR-003](../adr/ADR-003-auth-session.md) §5 esboza `permissions(code PK)`; [ADR-004](../adr/ADR-004-identifiers.md) §1 exige PK UUIDv7 en todas las tablas y un test lo comprueba. Se cumple ADR-004: `id` UUIDv7 y `code` `UNIQUE`, que es la clave que referencian las concesiones (`permission_code`). Ningún ADR cambia.

### OBS-F2-04-4 — Retirar, renombrar o cambiar el alcance de un permiso
La sincronización del catálogo borra un código retirado solo si nadie lo tiene concedido; si está concedido lo conserva y avisa en el log. Cambiar `supports_scope` de un permiso concedido hace fallar el `migrate` por la FK, a propósito.
- Cualquiera de esos cambios necesita una migración de datos que reescriba antes las concesiones.

### OBS-F2-04-5 — Concesiones de las plantillas
La matriz de [03 §H](../fase-0/03-tenancy-rbac-inbox-ia.md) no tiene filas para `organization.view`, `users.view`, `users.invite` ni `roles.view`. F2-04 asume mínimo privilegio: Owner, todo el catálogo; Administrador, `organization.view`, `users.view`, `users.manage`, `users.invite` y `roles.view`; Supervisor, `organization.view` y `users.view`; Vendedor, `organization.view`. Las plantillas Soporte, Marketing y Consulta se añadirán cuando el catálogo las distinga.
- Pendiente de confirmación del PO.

### OBS-F2-04-6 — Sin borrado lógico y un alcance por concesión
Los roles no llevan `deleted_at` (convención [SD]): no hay flujo de borrado hasta E01-08. Un rol tiene un solo alcance por permiso; combinar `TEAM` y `BRANCH` sobre el mismo permiso requiere dos roles, y los permisos efectivos (F2-05A) unen los alcances de todos los roles.

### OBS-F2-04-7 — Capas para el bootstrap
`apps.organizations` y `apps.access` son módulos hermanos que no se importan entre sí. El bootstrap (F2-06) y la regla "siempre un Owner activo" (F2-05C, #51) necesitan un punto de orquestación por encima de ambos.

### OBS-F2-02-1 — F2-03A no debe empezar con D-F2-1 y D-F2-2 abiertas
Al cerrarse F2-02, el orquestador pasa #40 a `status:ready` porque solo lee dependencias entre issues. Las decisiones D-F2-1 (auditoría de plataforma) y D-F2-2 (almacén de sesiones) siguen sin resolver.
- Propuesta: un work item de decisión (`docs/…`, con ADR nuevo si la auditoría de plataforma amplía ADR-001 o ADR-011) añadido como dependencia de #40. Lo crea el mantenedor.

### OBS-F2-02-2 — FK de tenant por tabla
`organization_memberships` añade su FK a `organizations` en la migración, igual que `files`. `TenantModel` sigue sin una FK genérica (OBS-F1-04-1 en [phase-1.md](phase-1.md)): cada tabla tenant-owned debe declararla.
- No bloqueante.

### OBS-F2-02-3 — Escrituras rechazadas en `user_scope`
Sin tenant activo, `INSERT` falla con error de RLS; `UPDATE` y `DELETE` no fallan: afectan a cero filas, porque la política `USING` no deja ver ninguna. El efecto es el mismo (no se escribe), pero el código que espere una excepción no la recibirá.
- No bloqueante.

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
