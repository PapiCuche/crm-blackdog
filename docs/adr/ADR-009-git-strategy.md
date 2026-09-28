# ADR-009: GitHub Flow

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** decisiones D9, D12, [ci-pipeline.md](../architecture/ci-pipeline.md)

## Context

- Equipo humano pequeño apoyado por agentes de IA que generan código (D12).
- Se quieren incrementos pequeños, sin PRs gigantes y con trazabilidad.
- No se necesita una rama `develop`.

## Decision

### Ramas

| Rama | Uso |
|---|---|
| `main` | Siempre estable y desplegable. **Protegida.** |
| `feature/<fase>-<descripcion>` | Nueva funcionalidad (`feature/f1-tenant-context`) |
| `fix/<descripcion>` | Corrección |
| `hotfix/<descripcion>` | Corrección urgente sobre una release; se mergea a `main` y se etiqueta un parche |
| `docs/<descripcion>`, `chore/<descripcion>` | Opcionales para cambios no funcionales |

### Protección de `main`

- PR obligatorio para cambios relevantes (todo lo que toca código, migraciones, CI o ADRs aceptados).
- CI verde obligatorio (checks requeridos: `backend`, `frontend`, `security`, a medida que existan).
- Al menos 1 aprobación. Si el autor es un agente IA, la aprobación es **humana**.
- Sin force-push ni borrado de `main`. Historial lineal.
- **Squash merge** por defecto: un PR = un commit con mensaje Conventional Commit. Un merge commit solo con justificación (p. ej., preservar commits de una migración compleja).

> **Nota operativa:** en repositorios **privados** de cuentas personales gratuitas, GitHub no aplica las reglas de protección de ramas (requieren un plan de pago o que el repositorio sea público). Hasta tenerlo, la regla se cumple por proceso y el CI corre igualmente en los PRs.

### Tamaño de los PR (D12)

- Objetivo: **≤ 400 líneas cambiadas** (sin contar código generado, lockfiles ni migraciones autogeneradas). Más de 800 → dividir.
- Un PR = un objetivo verificable. Las migraciones van en el mismo PR que el código que las usa.
- Las funcionalidades incompletas se integran detrás de **feature flags** por organización, no en ramas largas.
- Vida de una rama: ≤ 3 días hábiles.

### Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat(pricing): add price resolution engine`, `fix(inbox): prevent duplicate webhook messages`, `docs(adr): …`, `chore(ci): …`, `test(tenancy): …`. Tipos: feat, fix, docs, test, refactor, perf, chore, ci, build, security.

### Releases

- Tags SemVer `vMAJOR.MINOR.PATCH` sobre `main`. `v0.x` hasta el MVP en producción.
- Un tag dispara el despliegue a producción (cuando exista el pipeline de CD); cada merge a `main` despliega a staging.
- Release notes generadas a partir de los títulos de los PR.

### Trabajo con agentes de IA

- Cada tarea de un agente se hace en su propia rama y termina en un PR con: objetivo, archivos cambiados, pruebas ejecutadas y su resultado, y riesgos.
- Revisión cruzada: un agente distinto (o un humano) revisa el PR; la aprobación final es humana.
- Los agentes nunca hacen push directo a `main` ni modifican la protección de ramas.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| GitFlow (`develop`, `release/*`) | Doble integración y más ceremonia sin beneficio con CI y flags |
| Trunk-based sin PR | Sin revisión obligatoria; inadecuado con código generado por IA |
| Merge commits siempre | Historial ruidoso; dificulta revertir un cambio completo |

## Consequences

- `main` refleja siempre algo desplegable; los PRs pequeños facilitan la revisión humana del código generado por IA.
- Hace falta disciplina con los feature flags y la división de trabajo.

## Security implications

- La revisión obligatoria y el CI (secret scanning, auditoría de dependencias) actúan antes del merge.
- Ningún secreto en el repositorio: `.env` en `.gitignore`, gitleaks en CI y un pre-commit opcional.

## Operational implications

- Configurar la protección de `main` cuando el plan de GitHub lo permita (ver la nota).
- Plantilla de PR en `.github/pull_request_template.md` y CODEOWNERS cuando haya más de un revisor.
