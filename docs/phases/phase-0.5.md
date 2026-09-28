# Fase 0.5 — Decisiones y scaffolding

- **Estado:** cerrada (pendiente de merge del PR)
- **Rama:** `feature/phase-0.5-architecture`
- **Objetivo:** cerrar formalmente las decisiones de la Fase 0, documentar la arquitectura que guiará la implementación y dejar el scaffolding mínimo de ingeniería. **Sin funcionalidad de negocio.**

## Entregables

| Entregable | Ubicación |
|---|---|
| 11 ADRs (9 solicitados + mensajería + observabilidad) | `docs/adr/` |
| Arquitectura: estructura del repo, tenant context, fronteras de seguridad, dependencias de módulos, pipeline de CI | `docs/architecture/` |
| Decisiones cerradas y abiertas, riesgos actualizados | `docs/fase-0/06-riesgos-y-decisiones.md` |
| Roadmap corregido + matriz de dependencias de tools IA | `docs/fase-0/05-backlog-y-roadmap.md` §S |
| Scaffolding: carpetas raíz, `.editorconfig`, `.gitattributes`, `.gitignore`, `.gitleaks.toml`, compose base (Postgres 18 + roles RLS, Redis, Mailpit), plantilla de entorno | raíz, `infra/` |
| CI de seguridad (gitleaks) + Dependabot (github-actions) + plantilla de PR | `.github/` |

## Lo que **no** se hizo (a propósito)

- Ni `backend/` ni `frontend/` tienen código: los workflows `backend.yml` y `frontend.yml` se crean en la Fase 1, cuando existan sus manifiestos (una CI que no puede ejecutarse sería ruido).
- Sin emulador S3 en el compose: MinIO ya no publica imágenes (D-ENG-2).
- Sin migraciones ni tablas.

---

## Propuesta: Fase 1 — Infraestructura base

**Objetivo:** un esqueleto de backend y frontend ejecutable en local con Docker, cuyo kernel (`core`) garantice aislamiento de tenant (RLS incluido), identificadores, numeración, outbox, auditoría, almacenamiento de objetos y observabilidad, con CI completo. **Sin usuarios reales, RBAC ni dominio de negocio** (eso es la Fase 2+).

### PRs propuestos (pequeños, en orden)

| # | Rama | Contenido | Verificación |
|---|---|---|---|
| 1 | `feature/f1-engineering-versions` | ADR-012 con versiones fijadas (D-ENG-1) y emulador S3 (D-ENG-2) tras una prueba corta | ADR revisado |
| 2 | `feature/f1-backend-skeleton` | `backend/` con uv, Django (settings por entorno validados), ASGI, `/health/live` y `/health/ready`, ruff/mypy/pytest configurados; `backend.yml` en CI | CI verde; `docker compose up` levanta la API |
| 3 | `feature/f1-db-roles-rls-core` | Dos conexiones (`crm_app` / `crm_migrator`), operaciones de migración `EnableRLS` y `CompositeTenantFK`, función `app_current_tenant()`, `TenantModel`, `TenantManager`, `tenant_scope`, `user_scope`, verificación de conexión limpia | Tests T1–T6 y T13 con un modelo de prueba solo para tests |
| 4 | `feature/f1-tenancy-entrypoints` | Middleware HTTP (`/api/v1/o/{slug}/`) con `organizations` mínima y membresía **simulada en tests** (la tabla real llega en la Fase 2); `@tenant_task` / `@platform_task` + verificación al arrancar el worker; `TenantConsumerMixin`; `TenantCommand` | Tests T7 (harness genérico de rutas), T9, T10 |
| 5 | `feature/f1-ids-sequences` | `core.ids.new_id()` (UUIDv7), `org_sequences` + `allocate()` | Test de concurrencia (N hilos → números únicos y sin huecos) |
| 6 | `feature/f1-outbox-audit` | `outbox_events` + publisher Celery; `audit_logs` (particionada, append-only, redactor) + `audit.record` | Tests de transaccionalidad (rollback = sin evento ni auditoría) y de redacción |
| 7 | `feature/f1-observability` | structlog JSON, `request_id` / `correlation_id` propagados a Celery, `ErrorReporter` (Sentry/Noop) con scrubbing | Tests del scrubbing y de la propagación |
| 8 | `feature/f1-object-storage` | `ObjectStorageService`, `S3CompatibleStorage`, `InMemoryStorage`, tabla `files`, emulador S3 en compose, cliente HTTP con allowlist (`core.http`) | Tests de integración contra el emulador; tests anti-SSRF |
| 9 | `feature/f1-frontend-skeleton` | Next.js + TS estricto + Tailwind + shadcn + TanStack Query + i18n (es), layout base con ruta `/o/[orgSlug]`, rewrites same-origin, ESLint/Prettier/Vitest; cliente OpenAPI generado (orval); `frontend.yml` | CI verde; página de salud que consume `/api/health` |
| 10 | `feature/f1-local-stack` | Compose completo (backend, worker, ws, frontend, Caddy), `make check`, pre-commit | Arranque en limpio documentado y probado |

### Definition of Done de la Fase 1

- `docker compose up` levanta todo en limpio, siguiendo `infra/README.md`.
- CI verde en backend, frontend y seguridad; import-linter activo con los módulos existentes.
- Los tests de aislamiento se ejecutan con el rol `crm_app` y el pipeline falla si el rol de test es superusuario o tiene BYPASSRLS.
- Ninguna tabla de negocio. Solo existen `organizations` (mínima), `org_sequences`, `outbox_events`, `audit_logs` y `files`.
- ADR-012 aceptado y runbook "arranque local" escrito.

### Qué necesito para iniciarla

- Confirmación de este PR (merge).
- Opcional: decisión D-ENG-3 (protección real de `main`).
