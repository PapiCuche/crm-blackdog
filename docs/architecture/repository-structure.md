# Estructura del repositorio (monorepo)

**Relacionado:** ADR-009, [module-dependencies.md](module-dependencies.md), [ci-pipeline.md](ci-pipeline.md)
**Estado:** estructura objetivo. En la Fase 0.5 solo existen las carpetas raíz con su README; el contenido se crea en la fase que lo necesite.

---

## 1. Raíz

```text
/
├── backend/                 Django (API, WS, workers)                 → Fase 1
├── frontend/                Next.js (UI)                               → Fase 1
├── infra/                   Docker, compose local, proxy, init de BD    → Fase 0.5 (compose base) / Fase 1
├── docs/                    Fase 0, ADRs, arquitectura, runbooks
├── .github/                 CI, plantillas de PR, Dependabot
├── .editorconfig            Estilo básico común (indentación, EOL)
├── .gitattributes           EOL y archivos generados
├── .gitignore
├── .gitleaks.toml           Configuración del escaneo de secretos
└── README.md
```

## 2. `backend/`

```text
backend/
├── pyproject.toml            dependencias (uv), ruff, mypy, pytest, import-linter
├── uv.lock
├── manage.py
├── Dockerfile
├── config/
│   ├── settings/
│   │   ├── base.py           settings comunes; lectura de env validada (fallo al arrancar si falta algo crítico)
│   │   ├── local.py
│   │   ├── test.py
│   │   ├── production.py     runtime (web/worker/ws/beat): solo DATABASE_URL (crm_app); rechaza credenciales del migrador
│   │   └── migrate.py        job de migraciones: DATABASE_MIGRATOR_URL (crm_migrator); sin secretos de runtime
│   ├── urls.py               /api/v1/…, /api/v1/o/<slug>/…, /webhooks/…, /health/…
│   ├── asgi.py               HTTP + WebSocket (ProtocolTypeRouter)
│   ├── wsgi.py               (no se usa en producción; útil para herramientas)
│   └── celery.py             app Celery, colas, verificación @tenant_task/@platform_task
├── core/                     kernel compartido (L0)
│   ├── tenancy/              context, scope, middleware, celery, channels, commands, resolvers
│   ├── db/                   TenantModel, SoftDeleteModel, operaciones de migración (EnableRLS, CompositeTenantFK)
│   ├── ids.py                new_id() (UUIDv7)
│   ├── sequences.py          allocate() de numeración comercial
│   ├── money.py              Money, redondeo
│   ├── outbox/               modelo, publisher, registro de handlers
│   ├── storage/              ObjectStorageService, S3CompatibleStorage, InMemoryStorage
│   ├── observability/        logging (structlog), correlation, ErrorReporter, health
│   ├── http.py               cliente HTTP saliente con allowlist (anti-SSRF)
│   ├── i18n.py               utilidades de traducción (gettext_lazy), locale por organización
│   └── errors.py             errores de dominio → respuestas API uniformes
├── apps/                     un paquete por bounded context (se crean por fase)
│   └── <modulo>/
│       ├── models.py  services.py  selectors.py  events.py  permissions.py  scopes.py
│       ├── api/ (views.py, serializers.py, urls.py)
│       ├── tasks.py  admin.py
│       ├── migrations/
│       └── tests/
├── locale/                   catálogos gettext (es, en)
└── tests/                    tests transversales: aislamiento de tenant, RLS, introspección, arquitectura
```

**Módulos por fase** (ver roadmap): F1 `core`, `platform` (mínimo), `audit`, `files` · F2 `accounts`, `organizations`, `access` · F3 `catalog`, `pricing`, `inventory`, `imports` · F4 `contacts` · F5 `leads`, `deals`, `tasks`, `quotes`, `orders` · F6 `channels`, `inbox`, `notifications` · F7 adapters de WhatsApp en `channels`, `integrations` · F8 `ai_gateway`, `ai_agents` · F11 `automations` · F14 `analytics`, `search`.

## 3. `frontend/`

```text
frontend/
├── package.json              pnpm; scripts: dev, build, lint, format, typecheck, test, api:generate
├── pnpm-lock.yaml
├── next.config.ts            rewrites /api y /ws → backend (topología same-origin en local)
├── tsconfig.json             strict: true, noUncheckedIndexedAccess: true
├── eslint.config.mjs         next + reglas de fronteras + no dangerouslySetInnerHTML
├── .prettierrc
├── vitest.config.ts
├── Dockerfile
├── messages/                 catálogos i18n (es.json, en.json) — next-intl o equivalente
└── src/
    ├── app/
    │   ├── (auth)/login/…
    │   ├── o/[orgSlug]/      rutas de tenant: dashboard, inbox, contacts, leads, sales/*, products/*, tasks, ai/*, settings/*, admin/*
    │   └── layout.tsx
    ├── features/<dominio>/   componentes + hooks + estado por dominio
    ├── components/ui/        shadcn/ui
    ├── components/           componentes compartidos (tablas, formularios, layout)
    └── lib/
        ├── api/              CLIENTE GENERADO desde OpenAPI (orval) — no editar a mano
        ├── ws/               cliente WebSocket + invalidación de TanStack Query
        ├── i18n/
        └── format/           dinero, fechas (zona horaria de la organización)
```

Estructura de rutas: todo lo que depende de la organización cuelga de `/o/[orgSlug]/…` (D3); la organización en la URL solo selecciona, la API autoriza.

## 4. `infra/`

```text
infra/
├── README.md
├── docker/
│   ├── compose.yaml          servicios locales (Fase 0.5: postgres, redis, mailpit; Fase 1: emulador S3 (D-ENG-2), backend, worker, ws, frontend, proxy)
│   ├── postgres/init/        creación de roles crm_migrator / crm_app y BD de test
│   ├── storage/              init del emulador S3 y del bucket local (Fase 1)
│   └── proxy/Caddyfile       same-origin: / → next, /api /ws /webhooks → django (Fase 1)
├── env/
│   └── .env.example          variables documentadas (sin valores reales)
└── deploy/                   IaC / scripts de despliegue (cuando se elija hosting)
```

**Procesos de despliegue y credenciales (ADR-002 §1.1):**

| Proceso | Settings | Credencial de BD |
|---|---|---|
| `web`, `worker`, `ws`, `beat` | `config.settings.production` | `DATABASE_URL` → `crm_app` únicamente |
| `migrate` (job efímero previo al despliegue de la nueva versión) | `config.settings.migrate` | `DATABASE_MIGRATOR_URL` → `crm_migrator` únicamente |

La IaC define secretos separados para cada grupo; ningún proceso de runtime monta el secreto del migrador.

## 5. `docs/`

```text
docs/
├── fase-0/                   análisis A–U (histórico; decisiones actualizadas en 06)
├── adr/                      decisiones formales (inmutables una vez aceptadas)
├── architecture/             documentos vivos: estructura, tenancy, seguridad, dependencias, CI
├── runbooks/                 operación: restauración de backups, rotación de secretos, incidentes (Fase 1+)
└── phases/                   plan y cierre de cada fase (objetivo, archivos, tests, resultado)
```

## 6. `.github/`

```text
.github/
├── workflows/
│   ├── security.yml          secret scanning (gitleaks) — activo desde la Fase 0.5
│   ├── backend.yml           formato, lint, tipos, tests, migraciones — Fase 1
│   └── frontend.yml          formato, lint, typecheck, tests, build — Fase 1
├── dependabot.yml            actualizaciones y alertas: github-actions (ya), pip/uv y npm (Fase 1)
├── pull_request_template.md
└── CODEOWNERS                cuando haya más de un revisor
```

## 7. Versiones objetivo (se fijan en la Fase 1, D-ENG-1)

| Componente | Objetivo |
|---|---|
| PostgreSQL | 18 |
| Python | 3.13 o 3.14 (según el soporte de la versión de Django elegida y de las dependencias) |
| Django | Última LTS o estable soportada en el momento de iniciar la Fase 1 |
| Node.js | LTS activa |
| Next.js | Última estable (App Router) |
| Redis | 8.x (o Valkey compatible); en producción, instancias separadas para broker y caché (políticas de expulsión distintas) |
| Gestor de paquetes | `uv` (Python), `pnpm` (Node) |
