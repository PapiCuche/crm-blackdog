# ADR-003: Autenticación por sesión con cookie HttpOnly, MFA y RBAC con alcances

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-001, [security-boundaries.md](../architecture/security-boundaries.md), decisiones D5, D6, D7

## Context

- La aplicación web (Next.js) consume la API de Django. No se deben guardar tokens sensibles en `localStorage` (D5).
- MFA es obligatorio antes de producción para Owner, Admin y usuarios con permisos sensibles (D6).
- Los permisos necesitan alcances OWN / TEAM / BRANCH / ORGANIZATION sin multiplicar el catálogo (D7).
- Los WebSockets deben autenticarse con el mismo mecanismo.

## Decision

### 1. Topología: same-origin

```text
https://app.<dominio>/            → Next.js
https://app.<dominio>/api/…       → Django (HTTP)
https://app.<dominio>/ws/…        → Django Channels
https://app.<dominio>/webhooks/…  → Django (sin sesión; firma del proveedor)
```

El reverse proxy enruta por prefijo. Same-origin elimina CORS, simplifica SameSite y CSRF, y comparte la cookie con los WebSockets. En desarrollo, Next.js hace proxy (`rewrites`) de `/api` y `/ws` a Django para reproducir la misma topología.

### 2. Sesión

- Sesiones de Django en base de datos (o en caché Redis con respaldo en BD: decisión de implementación de la Fase 2). Cookie `__Host-crm_session` con `Secure; HttpOnly; SameSite=Lax; Path=/`. El prefijo `__Host-` impide que un subdominio la sobrescriba.
- Rotación del ID de sesión en login, logout y elevación MFA.
- Expiración por inactividad (12 h, configurable) y absoluta (7 días); "cerrar las demás sesiones"; al desactivar una membresía o un usuario se revocan sus sesiones y se emite `session.revoked` por WS.
- Contraseñas con **Argon2id**; validador contra contraseñas comunes o filtradas; bloqueo progresivo (django-axes o equivalente) por usuario + IP.

### 3. CSRF

- Cookie `csrftoken` legible por JS (no HttpOnly) + cabecera `X-CSRFToken` en toda mutación. El cliente de API generado la añade automáticamente.
- `CSRF_TRUSTED_ORIGINS` explícito; verificación de `Origin` también en el handshake WS.
- Los endpoints de webhooks están exentos de CSRF **y** de sesión: se autentican por firma (ADR de canales, Fase 7).

### 4. MFA

- TOTP (RFC 6238) + códigos de respaldo de un solo uso (hash).
- **Política:** el requisito se evalúa por membresía. Si el usuario tiene rol Owner/Admin o algún permiso sensible en **cualquiera** de sus organizaciones, debe tener MFA para acceder a esa organización. Hasta la salida a producción, la política se aplica con un feature flag (`MFA_ENFORCEMENT = warn | enforce`) para no bloquear el desarrollo.
- **Step-up:** las acciones sensibles (conceder permisos sensibles, gestionar credenciales de IA o de canales, ver o exportar costos, edición masiva de precios, kill switch) exigen MFA verificado hace ≤ 15 minutos (`session.mfa_verified_at`).
- WebAuthn/passkeys: futuro (el modelo `user_mfa_devices.type` lo admite).

### 5. RBAC con alcances (D7) sin duplicar permisos

**El alcance es un atributo de la concesión, no parte del código del permiso.** Existe `contacts.view`, no `contacts.view.own` + `contacts.view.team` + …

```text
permissions(code PK, module, is_sensitive, supports_scope)            -- catálogo desde el código
roles(organization_id, code, …)
role_permissions(role_id, permission_code, scope NULL|OWN|TEAM|BRANCH|ORGANIZATION)
membership_roles(membership_id, role_id)
```

**Cálculo de permisos efectivos** (se cachea por membresía y se invalida al cambiar roles):

```text
effective[perm] = conjunto de scopes de todas las concesiones de ese permiso en los roles de la membresía
```

**Cómo se aplica un scope a un recurso.** Cada tipo de recurso registra una `ScopePolicy` **una sola vez**:

```text
ScopePolicy(Opportunity):
  OWN          → Q(assigned_user_id = me) | Q(created_by_user_id = me)
  TEAM         → Q(team_id IN my_team_ids) | OWN
  BRANCH       → Q(branch_id IN my_branch_ids) | OWN
  ORGANIZATION → Q()   (sin filtro adicional; RLS ya limita al tenant)
```

- Filtro de listado: **OR** de los filtros de todos los scopes concedidos. Si incluye ORGANIZATION, se omite el filtro.
- Verificación por objeto: `can(ctx, "opportunities.update", obj)` evalúa el mismo predicado en memoria o con `exists()`.
- TEAM y BRANCH **no** se asumen anidados (un equipo puede abarcar varias sucursales). Por eso se usa la unión y no un "máximo".
- Los permisos sin sentido de propiedad (`prices.manage`, `roles.manage`) tienen `supports_scope = false` y el scope es NULL.
- **Resultado:** ~100 permisos de acción × 4 scopes posibles **sin** 400 códigos. Añadir un recurso nuevo = declarar su `ScopePolicy`.

**Reglas anti-escalada:** nadie concede un permiso que no tiene, ni con un scope más amplio que el suyo; nadie modifica sus propios roles; los permisos sensibles solo los concede un Owner con step-up MFA; siempre debe existir al menos un Owner activo.

### 6. WebSockets

`AuthMiddlewareStack` de Channels con la misma cookie. El handshake exige un `Origin` válido; la URL `/ws/o/{slug}/` resuelve la membresía igual que HTTP. Si la sesión se revoca, el consumer cierra con el código 4401.

### 7. API para terceros (futuro)

No forma parte del MVP. Cuando exista: tokens de API por organización (hash en BD, scopes, expiración) en un esquema de autenticación **separado** de la sesión web.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| JWT en `localStorage` | Robable por XSS; revocación difícil |
| JWT en cookie HttpOnly | Posible, pero reinventa lo que ya ofrecen las sesiones de Django (revocación, rotación) sin ventaja real en un monolito |
| BFF en Next.js que guarda la sesión | Duplica la autenticación y la lógica; Next.js quedaría con secretos |
| Subdominios `app.` y `api.` (same-site) | Viable, pero obliga a CORS con credenciales y complica la configuración; same-origin es más simple |
| Permisos con scope en el código (`contacts.view.own`) | Multiplica el catálogo y la UI de roles; duplica lógica |
| Solo roles fijos | No cumple el RBAC granular pedido |

## Consequences

- Next.js no guarda secretos ni tokens. Los Server Components que necesiten datos del usuario reenvían la cookie al backend (fetch server-side con la cabecera `cookie`), o se usan componentes cliente.
- Toda mutación necesita CSRF. El cliente generado lo resuelve una vez.
- El proxy es obligatorio también en local (rewrites de Next.js o Caddy en docker-compose).

## Security implications

- XSS no puede robar la sesión (HttpOnly). Aun así, un XSS puede actuar en nombre del usuario, por lo que se mantienen la CSP estricta y la prohibición de `dangerouslySetInnerHTML`.
- `SameSite=Lax` + token CSRF + verificación de Origin = triple defensa contra CSRF.
- MFA con step-up reduce el impacto de una contraseña robada sobre las acciones críticas.
- La caché de permisos se invalida por evento: una revocación tiene efecto en la siguiente petición.

## Operational implications

- Configurar el proxy (Caddy/Nginx) con los cuatro prefijos y el upgrade de WebSocket.
- La recuperación de acceso MFA (dispositivo perdido) es un procedimiento documentado: códigos de respaldo; si no hay, lo resuelve otro Owner, o soporte de plataforma con verificación de identidad y auditoría.
- Métricas de login fallido y alertas por picos.
