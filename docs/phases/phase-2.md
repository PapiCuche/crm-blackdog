# Fase 2 — Identidad, organizaciones y acceso

- **Estado:** en curso (bloque inicial F2-00 … F2-13; mergeados F2-00, F2-01, F2-02, F2-04, F2-05A, F2-05B y F2-05C)
- **Issue maestro:** [#36](https://github.com/PapiCuche/crm-gooddoggy/issues/36)
- **Objetivo:** usuarios, membresías, sesión por cookie y RBAC con alcance reales sobre el kernel de la Fase 1, y la primera pantalla funcional (login y entrada al shell de tenant).
- **Origen:** [roadmap §S.1](../fase-0/05-backlog-y-roadmap.md) (fila "Fase 2") e historias E01 del [backlog §R](../fase-0/05-backlog-y-roadmap.md).

La fase empieza por el backend y conecta el frontend mediante el contrato OpenAPI y el cliente generado por orval. Desde el 2026-10-02 el producto se construye como CRM oficial, no como demo ([AGENTS.md](../../AGENTS.md) §11): cada capacidad termina en `/o/[orgSlug]` contra el backend real. `/demo` queda **congelado** como prototipo visual con datos ficticios ([frontend/README.md](../../frontend/README.md)): no recibe funcionalidades nuevas.

## Work items

Cada work item es un issue con el alcance completo (Incluye / No incluye / criterios / validaciones). Este documento solo los ordena; **el issue es la fuente de verdad**.

| ID | Issue | Rama | Depende de | Tipo |
|---|---|---|---|---|
| F2-00 | [#37](https://github.com/PapiCuche/crm-gooddoggy/issues/37) Phase 2 plan | `docs/phase-2-plan` | — | docs |
| F2-01 | [#38](https://github.com/PapiCuche/crm-gooddoggy/issues/38) User model | `feature/f2-user-model` | #37 | backend |
| F2-02 | [#39](https://github.com/PapiCuche/crm-gooddoggy/issues/39) Organization memberships | `feature/f2-memberships` | #38 | backend |
| F2-03A | [#40](https://github.com/PapiCuche/crm-gooddoggy/issues/40) Session authentication API | `feature/f2-session-auth` | #39, #55, #56, #59, #64 | backend + API |
| F2-04 | [#41](https://github.com/PapiCuche/crm-gooddoggy/issues/41) RBAC model | `feature/f2-rbac-model` | #39 | backend |
| F2-05A | [#42](https://github.com/PapiCuche/crm-gooddoggy/issues/42) RBAC enforcement engine | `feature/f2-rbac-enforcement` | #41 | backend |
| F2-05B | [#50](https://github.com/PapiCuche/crm-gooddoggy/issues/50) RBAC: DRF integration | `feature/f2-rbac-drf` | #42 | backend |
| F2-05C | [#51](https://github.com/PapiCuche/crm-gooddoggy/issues/51) RBAC: anti-escalation and last Owner | `feature/f2-rbac-anti-escalation` | #42 | backend |
| F2-06 | [#43](https://github.com/PapiCuche/crm-gooddoggy/issues/43) Organization bootstrap | `feature/f2-org-bootstrap` | #41, #56 | backend |
| F2-07 | [#44](https://github.com/PapiCuche/crm-gooddoggy/issues/44) Frontend security / CSP | `feature/f2-frontend-csp` | #37 | frontend |
| F2-08 | [#45](https://github.com/PapiCuche/crm-gooddoggy/issues/45) Frontend access integration | `feature/f2-frontend-access` | #40, #43, #44, #57 | frontend |
| F2-09 | [#55](https://github.com/PapiCuche/crm-gooddoggy/issues/55) Production delivery rule and access decisions | `docs/f2-production-rule-decisions` | — | docs |
| F2-10 | [#56](https://github.com/PapiCuche/crm-gooddoggy/issues/56) Platform audit sink | `feature/f2-platform-audit` | #55 | backend |
| F2-11 | [#57](https://github.com/PapiCuche/crm-gooddoggy/issues/57) Self context endpoint | `feature/f2-self-context` | #40 | backend + API |
| F2-12 | [#59](https://github.com/PapiCuche/crm-gooddoggy/issues/59) API error contract | `feature/f2-api-conventions` | #55 | backend |
| F2-13 | [#64](https://github.com/PapiCuche/crm-gooddoggy/issues/64) API session authentication, CSRF and platform routes | `feature/f2-api-session-csrf` | #59 | backend |
| F2-03B | [#61](https://github.com/PapiCuche/crm-gooddoggy/issues/61) Login attempt throttling | `feature/f2-login-throttle` | #40 | backend |

Mergeados: #37 … #39, #41, #42, #50 y #51. Lo que queda:

```text
#55 F2-09 ─┬─► #56 F2-10 ─┬─► #43 F2-06 ────────────────────┐
           │              └─┬─► #40 F2-03A ─► #57 F2-11 ────┤
           └─► #59 F2-12 ─► #64 F2-13 ─┘                    │
#44 F2-07 ───────────────────────────────────────────────────┴─► #45 F2-08
```

### Serie: acceso al CRM oficial

F2-09, F2-10, F2-12, F2-13, F2-06, F2-03A, F2-11 y F2-07 son prerrequisitos de **F2-08**, que cierra la serie con comportamiento real: un usuario creado por el bootstrap inicia sesión, elige organización y entra al shell oficial con la navegación que sus permisos permiten.

- Los work items de backend llevan el gate `required-check:backend gate`.
- El orquestador `work-item-dependencies` pasa cada issue a `status:ready` cuando sus dependencias están cerradas ([delivery-automation.md](../architecture/delivery-automation.md)).
- Tras F2-00 quedan listos a la vez F2-01 y F2-07: no dependen entre sí. Con más de un issue listo, el mantenedor elige; dentro del programa autónomo aplican los criterios de [ADR-015](../adr/ADR-015-autonomous-delivery-program.md) §4.
- **Punto de integración del frontend:** F2-08. Hasta entonces ninguna ruta real muestra datos.

### Tamaño

Objetivo: ≤ 400 líneas relevantes por PR. Más de 800 no se acepta ([ADR-009](../adr/ADR-009-git-strategy.md)). Si un work item amenaza con superarlo, se divide **antes** de implementar, sin recortar tests ni migraciones. La excepción de tamaño aplicada a UI-01 (PR #35) no es un precedente.

Candidatos conocidos a división:

- **F2-03A:** si el bloqueo progresivo de intentos no cabe, pasa a un F2-03B.
- **F2-05:** dividido antes de implementar (2026-10-01). El diseño estimó unas 1.290 líneas para el alcance original de #42. Quedan F2-05A (#42, motor de autorización), F2-05B (#50, integración con DRF) y F2-05C (#51, anti-escalada y último Owner). B y C dependen solo de A y no entre sí. La caché de permisos sigue fuera.

## Historias E01 fuera de este bloque

Se planifican como work items al cerrar el bloque inicial. Cada historia es una serie (AGENTS.md §11): puede repartirse en varios work items, y el que la cierra entrega la pantalla oficial sobre la API real.

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

Un ADR `Accepted` no se modifica: si una decisión lo contradice o amplía, se propone un ADR nuevo. Las decisiones resueltas quedan marcadas con ✅ y enlazan dónde se registran.

| ID | Decisión | Estado actual | Bloquea |
|---|---|---|---|
| D-F2-1 | **Auditoría de plataforma.** ✅ Resuelta el 2026-10-02 en [ADR-013](../adr/ADR-013-platform-audit.md): un sumidero propio (`platform_audit_logs`), sin `organization_id`, solo de inserción para `crm_app`. `audit_logs` no cambia. No se usa un `organization_id` ficticio, una organización arbitraria, un rol con BYPASSRLS ni el log de aplicación. | Resuelta. Implementada en F2-10 (#56) | — |
| D-F2-2 | **Almacén de sesiones.** ✅ Resuelta el 2026-10-02: **sesiones de Django en base de datos** (`django.contrib.sessions.backends.db`), la primera opción de [ADR-003](../adr/ADR-003-auth-session.md) §2. Detalle abajo. | Resuelta. Lo implementa F2-03A (#40) | — |
| D-F2-3 | **Email case-insensitive.** ✅ Resuelta en F2-01 (#38): canonicalización explícita en la aplicación (`apps.accounts.emails`) más `UNIQUE (email)` y `CHECK (email = lower(email))` en la BD. No se usa `citext`, previsto en [02-modelo-de-datos.md](../fase-0/02-modelo-de-datos.md) §E.2: evita una extensión y deja el comportamiento explícito. La parte local debe ser ASCII; un dominio internacionalizado se guarda en forma IDNA. Sin reglas por proveedor. Detalle en [backend/README.md](../../backend/README.md). | Resuelta | — |
| D-F2-4 | **Dependencias nuevas** (bloqueo progresivo, TOTP). No se añaden sin su fila en [ADR-012](../adr/ADR-012-engineering-runtime-baseline.md). | `argon2-cffi` ya está fijado; el resto no | F2-03A / F2-03B, E01-03 |
| D-F2-5 | **Envío de correo.** Mailpit es infraestructura local, no el diseño del envío en producción. Hace falta una abstracción. | Sin diseño | E01-06, E01-02 |
| D-F2-6 | **Secretos TOTP.** Cifrado, KEK y rotación; nunca en claro. | Sin diseño | E01-03 |
| D-F2-7 | **Lenguaje visual del shell real.** `/o/[orgSlug]` usa hoy el tema oscuro; el Figma GOOD DOGGY es la referencia para las pantallas nuevas. | Se concreta en F2-08 | F2-08 (#45) |

### D-F2-2 — Sesiones en base de datos

- **Motivos:** es simple y durable; PostgreSQL ya lo comparten todas las instancias; revocar es borrar una fila; no añade dependencias (D-F2-4) ni una segunda invalidación en Redis. ADR-003 §2 permite pasar a caché Redis con respaldo en BD más adelante, sin ADR nuevo, si las lecturas de sesión llegan a ser un coste medido.
- **Tabla:** `django_session` es platform-owned, sin RLS de tenant. F2-03A verifica los privilegios de `crm_app` sobre ella y no usa el rol migrador en el runtime.
- **Cookie:** `HttpOnly`, `SameSite=Lax`, `Path=/`, sin `Domain`. En producción, `Secure` y nombre `__Host-crm_session`. En local sobre HTTP, nombre `crm_session`: el prefijo `__Host-` solo es válido con HTTPS ([ADR-014](../adr/ADR-014-api-errors-and-authentication.md) §2). Producción no se relaja.
- **Caducidad:** 12 horas de inactividad y 7 días absolutos. Las filas caducadas se purgan con una tarea de plataforma. Django solo renueva la caducidad al guardar la sesión: F2-03A implementa la inactividad con un guardado con umbral (no una escritura por petición) y el límite absoluto con una marca de inicio de sesión, comprobada antes de resolver el tenant. Una petición en curso cuya sesión se borra acaba en 401 `NOT_AUTHENTICATED`.
- **Fuera de F2-03A:** el vínculo usuario-sesión para cerrar las demás sesiones y listar las activas (E01-07, E01-11). En base de datos se resuelve con una columna o tabla propia.

Otras decisiones cerradas el 2026-10-02 en [ADR-014](../adr/ADR-014-api-errors-and-authentication.md), que implementan F2-12 (#59) y F2-13 (#64): cuerpo de error único (OBS-F2-05A-5), CSRF en todo método no seguro y clase de autenticación (OBS-F2-05B-1), semántica de 401, 403 y 404, y separación entre rutas de plataforma y de tenant. La política de contraseñas vigente (OBS-F2-01-3) no cambia.

Decisiones de producto cerradas por el mantenedor el 2026-10-02, para F2-05C (#51):

| ID | Pregunta | Decisión |
|---|---|---|
| PO-1 | Al quitar un rol a otra membresía, ¿el actor debe tener todas las concesiones de ese rol, con alcance igual o superior? | **Sí.** Quitar un rol exige lo mismo que asignarlo |
| PO-2 | ¿"Nadie modifica sus propios roles" impide también cambiar las concesiones de un rol que el actor tiene asignado? | **Sí.** Cuenta como modificarse a uno mismo |

Observaciones de la Fase 1 que afectan a esta fase: OBS-F1-03-1 (reversibilidad de `CompositeTenantFK`, antes de F2-02), OBS-F1-04-1 (FK de tenant en la primera tabla de negocio, F2-02), OBS-F1-09-1 (CSP, F2-07) y OBS-F1-09-2 (fixes de Next.js pendientes upstream).

## Principios para cada slice

Resumen operativo; la fuente es la arquitectura enlazada.

- **Tenancy** ([tenancy-context.md](../architecture/tenancy-context.md), [ADR-001](../adr/ADR-001-multi-tenancy.md), [ADR-002](../adr/ADR-002-postgresql-rls.md)): `organization_id` sale del contexto, nunca del payload. Las operaciones tenant-owned ocurren dentro de `tenant_scope`, con FORCE RLS, tests cruzados con dos organizaciones y runtime con `crm_app`.
- **Autorización** ([ADR-003](../adr/ADR-003-auth-session.md) §5, [security-boundaries.md](../architecture/security-boundaries.md) B2): usuario autenticado, membresía activa, organización activa, permiso y scope se verifican por separado, y cada denegación tiene su test.
- **Auditoría** ([ADR-011](../adr/ADR-011-observability-and-logs.md)): los cambios relevantes usan `audit.record`. Nunca contraseñas, tokens ni secretos.
- **API:** DRF y drf-spectacular, errores con la convención vigente, schema commiteado sin drift y cliente TypeScript generado con orval. Sin `fetch` manual que duplique un contrato generable.
- **Orden de un slice:** modelo e invariantes → migraciones y RLS → servicio → autorización → API → OpenAPI → tests de backend → orval → frontend → tests de frontend → revisión de tenancy y seguridad. La regla completa, y cuándo una capacidad está terminada, en [AGENTS.md](../../AGENTS.md) §11.
- **Rutas reales:** cada dato mostrado tiene fuente, autorización, tenant, contrato, estados de error y tests. Una pantalla de `/demo` no adelanta su dominio.

## Definition of Done de la fase

Del roadmap §S.1, además del DoD general:

- Login, MFA y roles con scope.
- Tests anti-escalada.
- Tests T14 y T15 de `organization_memberships`.
- Auditoría de login y de roles.

El bloque inicial F2-00 … F2-13 no cierra la fase: MFA y la gestión de roles llegan con las historias E01 pendientes.

## Observaciones vivas (de revisiones)

Se registran como `OBS-F2-<nn>-<n>`.

### OBS-F2-13-1 — Lo que la auditoría del URLconf sigue sin ver
Es estática. No detecta una vista que redefina `initialize_request` (los viewsets de DRF lo hacen de serie), un decorador que no use `functools.wraps`, ni una caché puesta por otra vía que un decorador del manejador. Una respuesta de tenant sigue sin poder cachearse por URL (OBS-F2-05B-6).
- Revisar a mano en cada PR que añada una vista con caché o con autenticación propia.

### OBS-F2-13-2 — El control de CSRF usa funciones internas de Django
Para aceptar el token solo en la cabecera, sin leer el cuerpo, `core.api.middleware` reescribe `_check_token` con `_get_secret`, `_check_token_format` y `_does_token_match`, que no son API pública de Django 5.2.
- Si una actualización de Django las cambia, fallan los tests de `tests/test_api_conventions.py`. Revisarlo al subir de versión (ADR-012).

### OBS-F2-12-3 — Un error deshace toda la petición, también la auditoría de ese intento
Desde F2-12 una petición de tenant con respuesta 400 o superior no deja nada escrito. Cuando se auditen los accesos denegados (OBS-F2-05A-4, E01-13), esa fila tendrá que escribirse fuera de la transacción de la petición.
- Decidir con E01-13.

### OBS-F2-10-1 — Los privilegios de las tablas de auditoría no viajan en un volcado lógico
`crm_app` solo tiene `INSERT` en `platform_audit_logs`, y no tiene `UPDATE` ni `DELETE` en `audit_logs`, porque cada migración revoca lo que conceden los privilegios por defecto de `01-roles.sh`. `pg_dump` no guarda esa revocación: al restaurar un volcado lógico sobre una base que ya tiene esos privilegios por defecto, el runtime recupera todos. Una restauración física (PITR, snapshot) no cambia nada.
- `platform_audit_logs` se repara sola en cada `post_migrate`. `audit_logs` no, y nada lo comprueba al desplegar: issue [#62](https://github.com/PapiCuche/crm-gooddoggy/issues/62), antes de producción.

### OBS-F2-10-2 — Lo que la tabla de auditoría de plataforma no impide
Los `CHECK` de `platform_audit_logs` cubren la forma de la acción, el tamaño de `metadata` y que un `ANONYMOUS` no lleve `actor_id`. No impiden que un runtime comprometido inserte un `occurred_at` distinto de ahora, dentro de las particiones existentes. `audit_logs` no tiene ninguno de esos `CHECK` y su servicio inserta sin calificar el esquema.
- Mismo issue [#62](https://github.com/PapiCuche/crm-gooddoggy/issues/62).

### OBS-F2-10-3 — Toda clave `*session_id` se redacta
Desde F2-10 el redactor compartido trata como credencial cualquier clave que termine en `session_id`, también en la auditoría de un tenant, en los logs y en el reporte de errores. La FK `ai_runs.session_id` prevista en [02-modelo-de-datos.md](../fase-0/02-modelo-de-datos.md) se redactaría.
- Al llegar el módulo de IA: otro nombre de columna o una excepción explícita con su test.

### OBS-F2-09-1 — El tiempo de respuesta distingue una organización que existe
El 404 de una ruta de tenant es idéntico en estado y cuerpo para "no existe" y "no eres miembro". El trabajo no lo es: `resolve_tenant` solo abre `user_scope` y consulta la membresía cuando la organización existe. Un usuario con sesión podría medir esa diferencia y saber qué slugs existen.
- ✅ Resuelta en F2-12 (#59): `resolve_tenant` consulta la membresía siempre, exista o no la organización, y un test compara las consultas de los dos casos.

### OBS-F2-09-2 — El límite de intentos de acceso necesita su propio almacén
`platform_audit_logs` es solo de inserción para `crm_app` (ADR-013): el límite de intentos no puede contar los fallos leyendo la auditoría. Necesita un almacén compartido entre instancias (una tabla platform-owned o una caché compartida), contado por IP y por identificador presentado, exista o no la cuenta (ADR-014 §3).
- Decidir en F2-03A o F2-03B, con D-F2-4.

### OBS-F2-05C-1 — Ningún Owner puede ampliar el rol Owner
Por PO-2, quien tiene un rol no cambia sus concesiones, y todo Owner tiene el rol Owner. Un permiso sensible solo lo delega un Owner. Resultado: ningún Owner puede usar `grant_permission` para añadir concesiones al rol Owner, y nadie puede añadirle un permiso sensible. No hay excepción para el Owner ni para el staff de plataforma. Agrava OBS-F2-04-1: cada work item que amplíe el catálogo debe llevar esos permisos al rol Owner de las organizaciones existentes por otra vía (migración de datos o un paso de plataforma), y decidirlo antes de añadir el primero.

### OBS-F2-05C-2 — La garantía de Owner activo tiene dos huecos fuera de este módulo
`remove_role` la aplica. Desactivar una membresía (E01-07, en `apps.organizations`) debe llamar a `ensure_owner_remains` en el mismo `tenant_scope` y antes de escribir; hoy nada lo hace porque esa operación no existe. Desactivar un usuario global (`users.is_active`) no se puede comprobar desde un tenant: quien lo implemente debe revisar todas sus organizaciones.

### OBS-F2-05C-3 — Los servicios aún no tienen quien los llame
No hay API HTTP (E01-08) ni bootstrap (F2-06). Tampoco existen revocar una concesión, cambiar su alcance, ni crear, renombrar o borrar roles: conceder un permiso ya concedido con otro alcance lanza `ValueError`. El step-up MFA para permisos sensibles llega con MFA (E01-03). Las denegaciones no se auditan (OBS-F2-05A-4). Un rol que conserve una concesión de un código retirado del catálogo no se puede asignar ni quitar con estos servicios: falla cerrado, y retirar un permiso sigue necesitando su migración de datos (OBS-F2-04-4).

### OBS-F2-05C-4 — Todos los cambios de RBAC de una organización van en serie
Comparten el bloqueo del rol Owner. Un cambio que escribe lo mantiene hasta el COMMIT de la petición; una denegación lo libera al deshacer su savepoint. `ensure_owner_remains` no abre savepoint: su bloqueo dura hasta el final del `tenant_scope`, también si deniega, porque quien la llama debe escribir bajo ese mismo bloqueo. Es deliberado: son operaciones poco frecuentes y así la relectura de permisos y el recuento de Owners no tienen carreras. Una organización sin rol Owner no admite ningún cambio.

### OBS-F2-05B-1 — Las vistas de DRF no pasan por la protección CSRF de Django
✅ Resuelta en F2-13 (#64): `ApiCsrfMiddleware` exige CSRF en todo método no seguro bajo `/api/`, y `SessionAuthentication` hace que la falta de sesión sea un 401 ([ADR-014](../adr/ADR-014-api-errors-and-authentication.md) §2–3). Lo que sigue describe el estado anterior. `APIView.as_view()` marca la vista como `csrf_exempt`; DRF solo comprueba CSRF dentro de `SessionAuthentication`, y el proyecto no tiene clases de autenticación hasta F2-13. Hoy no hay endpoints reales. Antes del primer endpoint que escriba, F2-13 aporta el control de CSRF para todo `/api/`. Con una clase de autenticación, DRF solo responde 401 en lugar de 403 a una petición sin autenticar si `authenticate_header()` de la primera clase de `authentication_classes` devuelve un valor; `SessionAuthentication` hereda el de `BaseAuthentication`, que devuelve `None`, y sigue respondiendo 403, con otro `detail`.

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
✅ Resuelta en F2-12 (#59): `TenantResolutionMiddleware` deshace la transacción de la petición cuando la respuesta es 400 o superior. Un servicio sigue comprobando antes de escribir, pero un error ya no deja escrituras a medias. Lo que sigue describe el estado anterior.

El middleware de tenant convierte la excepción en respuesta dentro del `tenant_scope`, así que un 403 o un 500 hacen COMMIT de lo ya escrito. Todo servicio debe comprobar antes de escribir y envolver sus escrituras en un savepoint. Es comportamiento previo a esta fase; afecta a F2-05C y a todo servicio posterior. En DRF (F2-05B) el permiso se comprueba antes de ejecutar el método de la vista; el alcance se comprueba dentro, en `get_object()` y `filter_queryset()`. Las vistas genéricas de serie no escriben antes de esa consulta, así que una denegación no deja escrituras. Una vista que escriba antes de llamar a `get_object()` (o a `scoped()`) responde 404 y confirma lo ya escrito, igual que un error posterior dentro de la vista; la auditoría del URLconf no detecta ese orden.

### OBS-F2-05A-4 — Denegaciones sin auditar
ADR-011 prevé auditar los accesos denegados. El motor no escribe filas `DENIED`. F2-05B crea el punto HTTP (`HasPermission`) pero no audita: falta decidir qué denegaciones se registran y con qué detalle. Queda para E01-13.

### OBS-F2-05A-5 — Cuerpo de error de la API
✅ Resuelta en F2-12 (#59): un único cuerpo `{"code": …}` para los errores de DRF, del middleware y de Django bajo `/api/`, con `URL_FORMAT_OVERRIDE` desactivado ([ADR-014](../adr/ADR-014-api-errors-and-authentication.md) §1 y §3). Lo que sigue describe el estado anterior. No hay manejador de excepciones propio: una denegación en una vista de DRF devuelve `{"detail": …}` y no la convención `{"code": …}` del middleware. Con F2-05B conviven las dos: 401, 404 y 403 `ORG_SUSPENDED` del middleware con `{"code": …}`; 403 y 404 de DRF con `{"detail": …}`. En las vistas genéricas con `ScopeFilter`, los 404 son idénticos entre sí (fuera de alcance, otra organización, inexistente); el 404 de `HasPermission.has_object_permission` tiene otro texto (OBS-F2-05B-2). La decisión, antes del primer endpoint real, debe dejar un único cuerpo para todos los 404 de una ruta de tenant. DRF negocia el formato antes de comprobar el permiso: en una ruta de tenant, un miembro activo que pida un formato que la API no sirve recibe 404 (`?format=xml`) o 406 (`Accept: application/xml`) en lugar del 403 o del 404 de alcance, tenga o no el permiso. No concede ni revela nada: la vista no se ejecuta y el 401 y el 404 del middleware van antes. Esa decisión debe cubrir también estas dos respuestas; como la API es solo JSON, una opción es fijar `URL_FORMAT_OVERRIDE: None`, que hoy no está configurado.

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
- ✅ Resuelta el 2026-10-02: F2-09 (#55) cierra las dos decisiones y #40 depende de #55 y de #56.

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
- ✅ Resuelta en [ADR-013](../adr/ADR-013-platform-audit.md) §4 para los eventos de acceso: `user_id` del actor autenticado, y en los intentos fallidos una huella HMAC del identificador más la cuenta afectada como entidad. Nunca el email en claro. El redactor compartido sigue sin tratar el email como secreto (la auditoría de un tenant registra cambios de email); el escritor de plataforma añade su propio filtro (F2-10, #56).

### OBS-F2-01-3 — Longitud mínima de contraseña
ADR-003 §2 exige validar contraseñas comunes o filtradas, pero no fija una longitud. F2-01 usa 12 caracteres. La comprobación contra contraseñas filtradas (servicio externo) no está implementada.
- Pendiente de confirmación del PO.
