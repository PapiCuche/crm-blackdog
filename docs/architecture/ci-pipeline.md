# Pipeline de CI

**Relacionado:** ADR-009, [repository-structure.md](repository-structure.md)
**Principio:** una herramienta por necesidad; sin solapes.

---

## 1. Workflows

| Workflow | Disparo | Estado |
|---|---|---|
| `security.yml` | PR + push a `main` + semanal | **Activo desde la Fase 0.5** |
| `backend.yml` | PR/push con cambios en `backend/**` | Se crea en la Fase 1 (cuando exista `pyproject.toml`) |
| `frontend.yml` | PR/push con cambios en `frontend/**` | Se crea en la Fase 1 (cuando exista `package.json`) |

Se usan `paths` filtros para no ejecutar el pipeline del backend cuando solo cambia el frontend, y viceversa. Los checks requeridos de `main` se añaden a medida que existen.

## 2. Backend (`backend.yml`, Fase 1)

| Paso | Herramienta | Comando | Motivo |
|---|---|---|---|
| Entorno | `uv` | `uv sync --frozen` | Reproducible con lockfile |
| Formato | **ruff format** | `ruff format --check .` | Un solo tool para formato y lint (sustituye a black + isort + flake8) |
| Lint | **ruff** | `ruff check .` | Incluye reglas de seguridad (`S`, derivadas de bandit) |
| Tipos | **mypy** + django-stubs | `mypy .` | Tipado fuerte requerido |
| Arquitectura | **import-linter** | `lint-imports` | Fronteras de módulos |
| Migraciones | Django | `manage.py makemigrations --check --dry-run` | Modelos y migraciones sincronizados |
| Migraciones aplicables | Django | `manage.py migrate` (con `crm_migrator`) sobre un Postgres 18 limpio | Detecta migraciones rotas |
| Tests | **pytest** + pytest-django | `pytest --cov` con Postgres 18 (service) y Redis; conexión de tests con el rol `crm_app` | Incluye la suite de aislamiento de tenant y los tests de RLS (gate) |
| Dependencias | **pip-audit** | `pip-audit` sobre el lock exportado | Vulnerabilidades conocidas |
| Contrato API | drf-spectacular | `manage.py spectacular --validate --fail-on-warn` + diff contra el schema commiteado | El cliente TS generado no queda desactualizado |

## 3. Frontend (`frontend.yml`, Fase 1)

| Paso | Herramienta | Comando |
|---|---|---|
| Entorno | pnpm | `pnpm install --frozen-lockfile` |
| Formato | **Prettier** | `pnpm format:check` |
| Lint | **ESLint** (config de Next + reglas propias) | `pnpm lint` |
| Tipos | **tsc** | `pnpm typecheck` (`tsc --noEmit`) |
| Tests | **Vitest** + Testing Library | `pnpm test --run` |
| Build | Next.js | `pnpm build` |
| Cliente API | orval | `pnpm api:generate` + `git diff --exit-code` (el cliente commiteado coincide con el schema) |
| Dependencias | pnpm | `pnpm audit --prod --audit-level=high` |

*Se valoró Biome (formato + lint en una herramienta), pero todavía no cubre las reglas específicas de Next.js y React Hooks con la misma madurez que ESLint. Se reevaluará.*

## 4. Seguridad (`security.yml`, activo)

| Control | Herramienta | Nota |
|---|---|---|
| Secret scanning | **gitleaks** (binario fijado por versión y verificado por SHA-256) | Escanea el historial completo en cada PR y push; `.gitleaks.toml` usa las reglas por defecto **sin allowlists**. Una excepción futura debe ser por regla y patrón exacto, nunca por archivo |
| Dependencias | **Dependabot** (alertas + PRs de actualización) | `github-actions` desde ya; `uv`/`pip` y `npm` al crear los manifiestos. En los pipelines: `pip-audit` y `pnpm audit` |
| Acciones de terceros | Fijadas por **SHA de commit** | Evita ataques a la cadena de suministro vía tags movidos |
| Permisos del token | `permissions: contents: read` por defecto | Mínimo privilegio |

**No se añaden (redundantes o no aplicables ahora):** CodeQL (requiere GitHub Advanced Security en repositorios privados), escaneo de contenedores (cuando haya imágenes publicadas), SAST adicional (ruff `S` cubre lo básico en Python).

## 5. Local

- `pre-commit` (opcional, recomendado): ruff, prettier, gitleaks `protect --staged`. Mismas versiones que CI.
- `make check` (Fase 1) ejecuta localmente lo mismo que CI.

## 6. Checks requeridos para merge

Configurados en el ruleset `main-protection` (ver ADR-009):

- **Activo:** `secret scanning (gitleaks)`.
- **Se añadirán en la Fase 1:** `backend / checks`, `backend / tests`, `frontend / checks`, `frontend / build`.
