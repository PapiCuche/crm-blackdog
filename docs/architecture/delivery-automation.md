# Delivery automation: flujo supervisado por IA

**Relacionado:** [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md), ADR-009 (GitHub Flow), [ci-pipeline.md](ci-pipeline.md)
**Objetivo:** que un agente pueda ejecutar un incremento recibiendo **solo el número de un issue**, con trazabilidad completa y aprobación final humana.

---

## 1. Flujo

**Flujo operativo (A-04):**

```text
usuario: "continuar"
  → Builder: consulta GitHub y toma el ÚNICO work item status:ready (0 → informa qué bloquea; N → pregunta)
  → implementa, valida y abre el PR con "## Handoff para Reviewer" actualizado al HEAD
  → usuario: "revisa"
  → Reviewer: lee el PR en GitHub (handoff + diff + checks) → APPROVE / REQUEST CHANGES
  → merge explícito y humano (squash, --match-head-commit)
  → work-item-state (trusted): issue → status:done
  → work-item-dependencies (trusted): siguiente status:blocked → status:ready si sus dependencias están CLOSED y sus gates existen
  → usuario: "continuar"
```

Nadie copia resúmenes entre agentes: el handoff vive en el PR, y los estados y dependencias en los issues.

**Detalle:**

```text
BACKLOG (roadmap: docs/fase-0/05, docs/phases/)
  → READY ISSUE (work item con status:ready, dependencias mergeadas)
  → BUILDER (rama del issue, implementación, validaciones)
  → PR (template, "Closes #N", sin merge)
  → GOVERNANCE (check "PR governance (trusted)": estructura + work item)
  → CI (security + backend + frontend)
  → REVIEWER (segundo agente o persona: lee el diff)
  → CHANGES REQUESTED ↺ BUILDER   |   APPROVED
  → HUMAN MERGE (squash, fijando el SHA revisado)
  → DONE (issue cerrado por "Closes #N"; se desbloquean los dependientes)
```

**No se automatiza:** la aprobación final, el merge, el auto-merge ni la merge queue sin revisión.

## 2. Estados de un work item

| Estado | Cómo se representa | Quién lo cambia |
|---|---|---|
| BLOCKED | label `status:blocked` | Estado inicial (issue form) o el mantenedor |
| READY | label `status:ready` | Mantenedor, cuando las dependencias están mergeadas |
| IN_PROGRESS | label `status:in-progress` | Workflow `work-item-state` al abrir el PR (o al pasarlo a ready for review) |
| REVIEW | PR abierto, no draft, con CI terminado | Derivado del PR (sin label, para no duplicar estado) |
| DONE | label `status:done` + issue cerrado | Workflow al mergear; GitHub cierra el issue por `Closes #N` |

- `work-item-state` es trusted (A-02): `pull_request_target` y un checkout **solo de la rama por defecto**. Ejecuta `.github/scripts/work_item_state.py`, que **reutiliza** la identificación del work item de `pr_governance.py` para evitar implementaciones divergentes.
- **Invariante:** ningún workflow con permisos de escritura muta un work item que no corresponda exactamente al PR. Antes de escribir se exige:
  - exactamente **un** issue de cierre (`Closes/Fixes/Resolves`; `Refs` nunca cuenta);
  - que el issue exista y no sea un PR (`GET /issues/N` sin campo `pull_request`);
  - que tenga el label `work-item`;
  - que su `### Rama` coincida **exactamente** con la rama del PR, recibida como dato por la variable de entorno `PR_HEAD_REF`;
  - PRs del mismo repositorio.

  Si algo no se cumple: **ninguna mutación** (el paso termina bien y deja el motivo en el log).
- **Orquestador de dependencias (A-04):** `work-item-dependencies.yml` es trusted:
  - se dispara con los eventos `issues` (closed, edited, labeled) y con `workflow_dispatch`;
  - hace checkout solo de la rama por defecto y ejecuta `work_item_dependencies.py`;
  - permisos: `contents: read` e `issues: write`.

  Lee **solo** dos secciones del issue:
  - `### Dependencias`: una por línea, `- #N`;
  - `### Gates`: `required-check:<nombre exacto>`.

  Pasa **únicamente** `status:blocked` → `status:ready` si se cumple todo esto:
  - el issue está abierto y es `work-item`;
  - no está en `in-progress` ni `done`;
  - todas las dependencias existen, no son PRs y están **CLOSED**;
  - todos los `required-check` existen en el ruleset de `main`.

  Sin sección de dependencias, o sin `- #N` ni "Ninguna", no infiere nada. En cada transición real comenta en el issue y deja un comentario compacto en su maestro (`Issue maestro: #N`). Cambiar el ruleset no genera un evento de issue: después de añadir un required check, lanzar el workflow a mano (`gh workflow run work-item-dependencies.yml`).
- **Transiciones permitidas:**

| Evento | Estado de origen | Resultado |
|---|---|---|
| opened / ready_for_review | `status:ready` | `status:in-progress` (quita `ready`) |
| opened / ready_for_review | `status:in-progress` | Sin cambio (idempotente) |
| opened / ready_for_review | `blocked`, `done` (aunque haya otro estado) o sin estado | Sin cambio |
| closed sin merge | `status:in-progress` (sin blocked/done) | `status:ready` |
| closed sin merge | cualquier otro | Sin cambio |
| closed con merge | cualquiera | Queda **solo** `status:done` (quita `ready`, `in-progress` y `blocked` si quedaron por inconsistencia) |

## 3. Roles

### Product Owner (humano)
- Decide prioridades, alcance y decisiones de negocio; responde las preguntas abiertas de los issues.
- Pasa los issues a `status:ready`.
- Da la aceptación final y hace el merge.

### Builder Agent
- Ejecuta un issue `status:ready` siguiendo AGENTS.md.
- Implementa, valida y abre el PR.
- **No se revisa a sí mismo ni hace merge.**
- Si encuentra una contradicción, detiene solo la parte afectada y la documenta.

### Reviewer Agent
- Lee **directamente el diff y el código** (`gh pr diff`, archivos, CI). No asume que el resumen del Builder es correcto.
- Verifica el alcance frente al issue, los ADR, la seguridad (checklist de security-boundaries §6) y los tests.
- Resultado: **APPROVE**, **APPROVE WITH OBSERVATIONS** o **REQUEST CHANGES**.
- Las observaciones no bloqueantes se registran como `OBS-<issue>-<n>` en `docs/phases/` o en un issue `tech-debt`.

### GitHub
- Checks:
  - `PR governance (trusted)`: estructura del PR y work item (frontera de seguridad; el legacy `PR governance` es solo informativo tras A-02);
  - `secret scanning (gitleaks)`;
  - `backend` y `frontend`, a medida que existan.
- Ruleset `main-protection`:
  - PR obligatorio;
  - resolución de conversaciones;
  - checks requeridos;
  - sin force-push ni borrado.

### Humano (mantenedor)
- **Único** que da la aprobación final de producto y hace el merge (squash).

## 4. Qué valida `PR governance (trusted)` (solo estructura, no calidad)

| Regla | Detalle |
|---|---|
| Título | Conventional Commits: `feat|fix|docs|test|refactor|perf|chore|ci|build|security` + `(scope)` opcional + `: descripción` |
| Rama | `feature/f<N>-<slug>`, `fix/<slug>`, `hotfix/<slug>`, `docs/<slug>`, `chore/<slug>` |
| Issue | **Exactamente un** work item cerrado con `Closes|Fixes|Resolves #N`: 0 falla y más de 1 falla (1 issue = 1 rama = 1 PR). `Refs #N` se permite solo para referencias adicionales (p. ej., el issue maestro) y nunca identifica al work item, porque no cerraría el issue ni actualizaría su estado |
| Work item real | Se consulta por API el work item cerrado por el PR. Debe existir, tener `work-item`, **no** tener `status:blocked` ni `status:done` (aunque también tenga otro estado) y tener `status:ready` o `status:in-progress`. Se aceptan ambos porque `work-item-state` puede cambiar el label mientras corre la governance. Además, la rama de su sección `### Rama` debe coincidir **exactamente** con la rama del PR |
| Secciones | Issue / Fase, Objetivo, Cambios, No incluye, Cómo se verificó, Definition of Done, Riesgos y deuda técnica, Autoría |
| Tamaño | Líneas relevantes (adiciones + borrados): **≤ 400** pasa; **401–800** pasa con aviso; **> 800** falla, salvo con el label `large-pr-approved` (que convierte el fallo en aviso) |

- **Excluidos del tamaño:** `docs/**`, `*.lock`, `uv.lock`, `pnpm-lock.yaml`, `package-lock.json`, `**/migrations/**`, `generated/**` y `frontend/src/lib/api/**`. Nunca se excluyen archivos de aplicación para pasar el límite.
- **Integridad (A-02):** `pr-governance-trusted.yml` usa `pull_request_target`, así que GitHub ejecuta la **versión del workflow que está en la rama base**. Además hace checkout **solo de la rama por defecto** (`github.event.repository.default_branch`) y ejecuta el `pr_governance.py` de ese checkout. En el Step Summary registra la ref y el SHA exactos ejecutados. Si un PR modifica `pr-governance-trusted.yml` o `.github/scripts/pr_governance.py`, esa versión **no** es la que lo evalúa; empezará a aplicarse cuando se mergee (tras revisión).
- **Frontera de confianza verificada:** `test_workflow_security.py` (análisis estático, stdlib) comprueba que todo workflow `pull_request_target`:
  - no referencia `pull_request.head.sha`, y `pull_request.head.ref` solo como dato en una variable de `env:` (nunca en `ref:`, `uses:` ni `run`);
  - hace checkout solo de refs trusted;
  - no interpola `${{ }}` dentro de `run`;
  - no ejecuta instalaciones ni `eval`;
  - no usa acciones locales;
  - no pide permisos de escritura salvo `issues: write` en `work-item-state`.
- **Arranque:** el workflow trusted solo protege cuando ya está en `main`. El PR que lo introduce (A-02) todavía se protege con el legacy `PR governance`. Tras su merge, el ruleset pasa a requerir `PR governance (trusted)` en lugar del legacy (OBS-A-01-1 resuelto; retirada del legacy en OBS-A-02-1).
- **Excepción:** los PRs de `dependabot[bot]` no siguen el template. Para ellos las reglas se informan como avisos y el check pasa, y la revisión humana sigue siendo obligatoria.
- `large-pr-approved` solo lo aplica el mantenedor, de forma consciente.

## 5. Política de triggers de GitHub Actions

| Tipo de workflow | Trigger | Reglas |
|---|---|---|
| Ejecuta código del PR (backend, frontend, tests, builds) | `pull_request` | Token de solo lectura en forks; nunca con secretos de producción |
| Trusted de metadata/governance (valida título, rama, body, labels, issues; sincroniza labels) | Puede usar `pull_request_target` | **No** hace checkout del head ni ejecuta código, scripts o acciones del PR; solo lee metadata por API; permisos mínimos; datos del evento solo por variables de entorno; revisión de seguridad específica en cada cambio |

`pull_request_target` no se aplica de forma indiscriminada. Hoy lo usan solo `pr-governance-trusted.yml` (permisos de solo lectura) y `work-item-state.yml` (`issues: write`, con checkout solo de la rama por defecto). Cualquier workflow nuevo con este trigger debe pasar `test_workflow_security.py` y una revisión de seguridad específica.

## 6. Contrato de handoff (histórico; desde A-04 vive en el PR: AGENTS.md §9–§10)

**Builder → Reviewer / PO:**

```text
Issue:
PR:
Branch:
Commit:
Objective:
Files changed:
Tests:
CI:
Known limitations:
Risks:
Not implemented:
Merge performed: NO
```

**Reviewer → PO:**

```text
Result: APPROVE | APPROVE WITH OBSERVATIONS | REQUEST CHANGES
Blocking findings:
Non-blocking observations:
Security:
Tests reviewed:
Merge recommendation:
```

## 7. Uso diario

- **PO → Builder:** "Ejecuta el siguiente issue READY de la Fase 1 siguiendo AGENTS.md. Abre el PR y no hagas merge."
- **PO → Reviewer:** "Revisa el PR #N según docs/architecture/delivery-automation.md §3 y devuelve el contrato de handoff del Reviewer."
- **PO:**
  - hace squash merge fijando el SHA revisado (`gh pr merge N --squash --match-head-commit <sha>`);
  - pasa a `status:ready` los issues desbloqueados.
