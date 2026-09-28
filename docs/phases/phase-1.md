# Fase 1 — Infraestructura base

- **Estado:** en curso
- **Issue maestro:** [#13](https://github.com/PapiCuche/crm-blackdog/issues/13)
- **Objetivo:** un esqueleto de backend y frontend ejecutable en local con Docker, cuyo kernel (`core`) garantice aislamiento de tenant (RLS incluido), identificadores, numeración, outbox, auditoría, almacenamiento de objetos y observabilidad, con CI completo. **Sin usuarios reales, RBAC ni dominio de negocio.**

## Work items

Cada work item es un issue con el alcance completo (Incluye / No incluye / criterios / validaciones). Este documento solo los ordena; **el issue es la fuente de verdad**.

| ID | Issue | Rama | Depende de | Estado inicial |
|---|---|---|---|---|
| F1-01 | PR #2 | `feature/f1-engineering-versions` | — | ✅ Mergeado (ADR-012) |
| F1-02 | [#4](https://github.com/PapiCuche/crm-blackdog/issues/4) Backend skeleton | `feature/f1-backend-skeleton` | F1-01, A-02 (#15) | `status:blocked` |
| F1-03 | [#5](https://github.com/PapiCuche/crm-blackdog/issues/5) DB roles + RLS core | `feature/f1-db-roles-rls-core` | #4 | `status:blocked` |
| F1-04 | [#6](https://github.com/PapiCuche/crm-blackdog/issues/6) Tenancy entrypoints | `feature/f1-tenancy-entrypoints` | #5 | `status:blocked` |
| F1-05 | [#7](https://github.com/PapiCuche/crm-blackdog/issues/7) UUIDv7 + organization sequences | `feature/f1-ids-sequences` | #6 | `status:blocked` |
| F1-06 | [#8](https://github.com/PapiCuche/crm-blackdog/issues/8) Outbox + audit | `feature/f1-outbox-audit` | #7 | `status:blocked` |
| F1-07 | [#9](https://github.com/PapiCuche/crm-blackdog/issues/9) Observability | `feature/f1-observability` | #6 | `status:blocked` |
| F1-08 | [#10](https://github.com/PapiCuche/crm-blackdog/issues/10) Object storage + HTTP allowlist | `feature/f1-object-storage` | #7 | `status:blocked` |
| F1-09 | [#11](https://github.com/PapiCuche/crm-blackdog/issues/11) Frontend skeleton | `feature/f1-frontend-skeleton` | #4 | `status:blocked` |
| F1-10 | [#12](https://github.com/PapiCuche/crm-blackdog/issues/12) Local stack | `feature/f1-local-stack` | #4 … #11 | `status:blocked` |

Previos transversales: [#3](https://github.com/PapiCuche/crm-blackdog/issues/3) A-01 Project delivery automation → [#15](https://github.com/PapiCuche/crm-blackdog/issues/15) A-02 Harden trusted PR governance. **F1-02 no empieza hasta que A-02 esté mergeado.**

## Definition of Done de la fase

- `docker compose up` levanta todo en limpio siguiendo `infra/README.md`.
- CI verde en backend, frontend, security y PR governance; import-linter activo con los módulos existentes.
- Tests de aislamiento ejecutados con el rol `crm_app`; el pipeline falla si el rol de test es superusuario o tiene BYPASSRLS.
- Ninguna tabla de negocio: solo `organizations` (mínima), `org_sequences`, `outbox_events`, `audit_logs` y `files`.
- **Gate heredado de la Fase 0.5:** PostgreSQL y el script de roles/RLS ejecutados contra una instancia real (CI en F1-03, Docker local en F1-10).

## Observaciones vivas (de revisiones)

### OBS-A-01-1 — Trusted governance bootstrap
Con el trigger `pull_request`, aunque el script de governance se tome de `base.sha`, la **definición del workflow** pertenece al ref del evento: un PR puede modificar el propio `pr-governance.yml`.
- No se cambia a `pull_request_target` dentro de A-01 porque el workflow trusted aún no existe en `main` (problema de arranque).
- Se resuelve en **A-02 (#15)**: governance y `work-item-state` con trigger trusted, sin checkout del head, sin ejecutar código del PR, con permisos mínimos y siempre desde código ya presente en `main`. **Estado:** implementado en el PR de A-02; queda efectivo cuando se mergee y el ruleset requiera `PR governance (trusted)`.
- Los workflows que ejecutan código (backend, frontend, tests) siguen con `pull_request`.

*Registrado en el issue #15; bloquea F1-02 (#4).*

### OBS-A-02-1 — Retirar el legacy `PR governance`
Tras A-02, el workflow legacy `pr-governance.yml` (con `pull_request`, modificable por el PR) queda **solo informativo**: el ruleset deja de requerirlo.
- Se recomienda retirarlo en un `chore` pequeño después de que `PR governance (trusted)` haya protegido al menos un ciclo completo (p. ej., el PR de F1-02).
- Su existencia no bloquea F1-02 una vez que el ruleset exija exclusivamente el trusted.

### OBS-A-02-2 — Revisión estática de workflows modificados por un PR
`test_workflow_security.py` verifica los workflows **de `main`** (los que se ejecutan). Un PR que añada un workflow `pull_request_target` inseguro no se ejecuta hasta el merge, pero solo lo detecta la revisión humana o del Reviewer.
- Mejora futura (opcional): que la governance trusted descargue por API, **como dato**, los `.github/workflows/*.yml` modificados por el PR y les aplique las mismas reglas estáticas.

### OBS-F1-01-1 — Revalidación conjunta de dependencias del frontend
Antes de crear el frontend en **F1-09** hay que volver a verificar **juntos** Next.js, React, React DOM, @types/react, @types/react-dom y TypeScript. No basta con actualizar Next.js.
- La baseline de ADR-012 está validada para Next.js 16.3.6, y existe una security release 16.3.7 programada para el 30/09/2026.
- F1-09 usará la combinación estable, publicada y soportada en su fecha.
- No se inicia el frontend sobre una versión cuyo security patch ya se haya publicado o sea inminente.

*Registrado en el issue #11.*

### OBS-F1-01-2 — Licencia de Garage
Garage (AGPL-3.0) se usa **solo** como servicio de desarrollo local y CI, y no se incorpora al código propietario.
- Modificarlo, redistribuirlo, exponerlo como servicio a terceros o usarlo en producción requerirá una **revisión específica de licencia y compliance**.
- No cambia D-ENG-2 ni la elección de Garage v2.4.1.

*Registrado en el issue #10.*
