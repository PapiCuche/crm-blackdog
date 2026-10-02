# ADR-014: Contrato de errores de la API, autenticación por sesión y rutas de plataforma

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Product Owner (mantenedor)
- **Related:** ADR-001 §4–5, ADR-003 §2–3, [tenancy-context.md](../architecture/tenancy-context.md) §2, [security-boundaries.md](../architecture/security-boundaries.md) B1 y B2, OBS-F2-05A-5, OBS-F2-05B-1 y D-F2-2 en [phase-2.md](../phases/phase-2.md)

## Context

F2-03A publica el primer endpoint real y congela su forma en el contrato OpenAPI y en el cliente generado. Antes hay que cerrar cuatro puntos que la Fase 2 dejó abiertos:

- conviven dos cuerpos de error: `{"code": …}` del middleware de tenant y `{"detail": …}` de DRF (OBS-F2-05A-5);
- las vistas de DRF no pasan por la protección CSRF de Django y no hay clase de autenticación (OBS-F2-05B-1);
- no está definido cuándo se responde 401 y cuándo 403;
- las rutas de plataforma (`/api/v1/auth/…`) no usan el motor de permisos de tenant, y esa excepción no debe convertirse en una vía para saltarse el RBAC.

## Decision

### 1. Un solo cuerpo de error

Toda respuesta de error de la API es un objeto JSON con esta forma:

```json
{ "code": "VALIDATION_ERROR", "message": "…", "fields": { "email": [{ "code": "required", "message": "…" }] } }
```

- `code`: obligatorio. Constante estable en `MAYÚSCULAS_CON_GUION_BAJO`. Es lo único que el cliente usa para decidir.
- `message`: opcional. Texto seguro para mostrar. No contiene datos internos, SQL, rutas ni identificadores de otros tenants. El cliente no lo interpreta.
- `fields`: solo en `VALIDATION_ERROR`. Lista de errores por campo; los errores que no son de un campo van en la clave `_`.

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDATION_ERROR` | El cuerpo no cumple el contrato |
| 400 | `PARSE_ERROR` | JSON mal formado |
| 401 | `NOT_AUTHENTICATED` | No hay sesión válida |
| 401 | `INVALID_CREDENTIALS` | Solo en el login: credenciales rechazadas |
| 403 | `CSRF_FAILED` | Método no seguro sin token CSRF válido |
| 403 | `PERMISSION_DENIED` | Sesión válida y miembro activo, sin el permiso |
| 403 | `ORG_SUSPENDED` | Organización suspendida |
| 404 | `NOT_FOUND` | Ver §3 |
| 405 | `METHOD_NOT_ALLOWED` | |
| 406 | `NOT_ACCEPTABLE` | Formato no servido (la API es solo JSON) |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | |
| 429 | `RATE_LIMITED` | Límite de intentos o de peticiones |
| 500 | `INTERNAL_ERROR` | Error no previsto. Sin detalle |

Dos piezas producen este cuerpo, con un mismo serializador:

- un manejador de excepciones único de DRF, para los errores que nacen dentro de una vista;
- un middleware para las rutas `/api/`, que convierte al contrato cualquier respuesta de error que Django genere fuera de una vista: una ruta sin resolver, una excepción en un middleware, o los 400 y 403 de Django (por ejemplo `SessionInterrupted` o un cuerpo demasiado grande). No depende de `DEBUG`.

El middleware de tenant ya emite `{"code": …}`. "Idéntico" significa el mismo código de estado y el mismo documento JSON. Un servicio puede añadir códigos de dominio (por ejemplo `LAST_OWNER`) siguiendo la misma forma; cada uno se documenta en el contrato OpenAPI.

`URL_FORMAT_OVERRIDE` se desactiva: la API solo sirve JSON y `?format=` deja de tener efecto.

### 2. Autenticación

- La única autenticación de la API web es la **sesión de Django** (ADR-003 §2), con sesiones guardadas en base de datos (D-F2-2).
- **CSRF obligatorio en todo método no seguro** (`POST`, `PUT`, `PATCH`, `DELETE`), **haya sesión o no**. El login también lo exige. La cookie `csrftoken` es legible por JavaScript y el token viaja en la cabecera `X-CSRFToken` (ADR-003 §3). Un endpoint `GET` entrega la cookie antes del primer `POST`.
- **Dónde se aplica.** En una ruta de tenant quien autentica es el middleware, con el `request.user` de Django, antes de que exista ninguna vista. `APIView.as_view()` marca toda vista de DRF como exenta de CSRF. Por eso ni el CSRF ni la caducidad de la sesión pueden depender de un atributo de la vista: los aplica un **middleware para todo `/api/`**, colocado antes de `TenantResolutionMiddleware`. La clase de autenticación de DRF sigue existiendo (da el usuario a la vista y hace que la falta de sesión sea un 401), y la auditoría estática del URLconf rechaza toda vista bajo `/api/` que cambie `authentication_classes` o redefina `get_authenticators` o `perform_authentication`. `/webhooks/` queda fuera: se autentica por firma (ADR-003 §3).
- La cookie de sesión es `HttpOnly`, `SameSite=Lax`, `Path=/`, sin `Domain`. En producción es además `Secure` y se llama `__Host-crm_session`. El prefijo `__Host-` solo es válido sobre HTTPS: en desarrollo local sobre HTTP la cookie se llama `crm_session`. Producción no se relaja para acomodar el entorno local.
- La sesión caduca por inactividad (12 horas) y de forma absoluta (7 días). El identificador rota al iniciar y al cerrar sesión.

### 3. Semántica de 401, 403 y 404

- **401 `NOT_AUTHENTICATED`:** no hay sesión, caducó o fue revocada. Se comprueba **antes** que cualquier otra cosa en una ruta de tenant: sin sesión no se puede saber si una organización existe.
- **403:** hay sesión, pero la petición no se permite. `CSRF_FAILED` es la excepción que también aplica sin sesión.
- **404 `NOT_FOUND`:** en una ruta de tenant, el cuerpo es **exactamente** `{"code": "NOT_FOUND"}`, sin `message`, y es idéntico para una organización que no existe, una organización sin membresía activa del usuario, un objeto inexistente, un objeto de otra organización y un objeto fuera del alcance del usuario (ADR-001 §5.6).
- **Login:** el mismo 401 `INVALID_CREDENTIALS`, con el mismo cuerpo, para un email desconocido, una contraseña incorrecta y un usuario desactivado. El motivo real solo queda en la auditoría de plataforma (ADR-013). El límite de intentos (429 `RATE_LIMITED`) se cuenta por IP y por identificador presentado, exista o no la cuenta, y se evalúa antes de comprobar las credenciales: el 429 tampoco distingue un email desconocido de uno real.

### 4. Rutas de tenant y rutas de plataforma

| | Ruta de tenant | Ruta de plataforma |
|---|---|---|
| Prefijo | `/api/v1/o/{slug}/…` | El resto de `/api/v1/…` |
| Contexto | `TenantResolutionMiddleware` abre `tenant_scope` | Sin `tenant_scope`; tablas platform-owned o `user_scope` |
| Autorización | `HasPermission` + `ScopeFilter` (por defecto) | Una clase de permiso de plataforma declarada en la vista |

Reglas para las rutas de plataforma:

- Se clasifican **por la ruta**, nunca por el actor: ser staff de plataforma no autoriza nada en una ruta de tenant.
- Cada vista declara una de dos clases: acceso anónimo (login, token CSRF) o sesión autenticada (logout, sesión actual, mis organizaciones). No heredan la clase por defecto.
- No abren `tenant_scope`, no usan modelos tenant-owned y no devuelven datos de una organización más allá de los que el usuario ya tiene por sus membresías activas.
- La auditoría estática del URLconf lista cada ruta de plataforma de forma explícita. Hoy (F2-05B) solo falla ante una vista de DRF fuera del prefijo de tenant que no esté en la lista. F2-12 (#59) la extiende: toda ruta bajo `/api/` fuera del prefijo de tenant, sea o no de DRF, debe figurar en la lista y declarar una de las dos clases de plataforma; si no, el test falla.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Mantener `{"detail": …}` de DRF | Texto libre y traducible como única señal; el cliente tendría que comparar cadenas |
| RFC 9457 (`application/problem+json`) | Válido, pero cambia el tipo de contenido y los cuerpos que ya emite el middleware. Se puede adoptar más adelante sin romper `code` |
| 403 para "sin sesión" (comportamiento por defecto de `SessionAuthentication`) | Confunde "identifícate" con "no puedes"; el cliente no sabría cuándo redirigir al login |
| 403 para "no eres miembro" | Revela que la organización existe |
| CSRF solo con sesión (DRF por defecto) | Deja el login sin protección frente a login CSRF |

## Consequences

- El cliente generado trata los errores en un único punto: decide por `code` y redirige al login con `NOT_AUTHENTICATED`.
- Los tests de F2-05B que comparan cuerpos `{"detail": …}` se actualizan al contrato nuevo en el work item que añade el manejador.
- Cada endpoint declara sus respuestas de error en OpenAPI con un componente común.

## Security implications

- Los 404 de tenant no distinguen causas y el 401 va antes: no hay oráculo de existencia de organizaciones, membresías ni objetos **por el código de estado ni por el cuerpo**. El tiempo de respuesta todavía no está igualado: para un usuario con sesión, la consulta de membresía solo se hace cuando la organización existe (OBS-F2-09-1 en `phase-2.md`; F2-12 la iguala).
- El login no permite enumerar cuentas por el cuerpo ni por el código de estado. Django ejecuta el hash también para un email desconocido, lo que acerca los tiempos de respuesta.
- `INTERNAL_ERROR` no expone la excepción; el detalle va al log de aplicación con su `request_id`.
- La excepción de las rutas de plataforma queda acotada por una lista explícita y por tests cuando F2-12 extienda la auditoría (§4).

## Operational implications

- El frontend y cualquier cliente futuro dependen de la lista de códigos: retirar o renombrar uno es un cambio de contrato.
- Los cambios de cookie entre entornos se hacen por configuración (`production.py`), no por código.
