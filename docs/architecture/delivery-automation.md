# Delivery automation: flujo supervisado por IA

**Relacionado:** [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md), ADR-009 (GitHub Flow), [ci-pipeline.md](ci-pipeline.md)
**Objetivo:** que un agente pueda ejecutar un incremento recibiendo **solo el número de un issue**, con trazabilidad completa y aprobación final humana.

---

## 1. Flujo

```text
BACKLOG (roadmap: docs/fase-0/05, docs/phases/)
  → READY ISSUE (work item con status:ready, dependencias mergeadas)
  → BUILDER (rama del issue, implementación, validaciones)
  → PR (template, "Closes #N", sin merge)
  → GOVERNANCE (check "PR governance": estructura)
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

- Si un PR se cierra **sin merge**, el workflow devuelve el issue a `status:ready`.
- El workflow solo actúa sobre issues con label `work-item`, solo con palabras clave de cierre (`Closes`, `Fixes`, `Resolves`; `Refs` no cambia estados) y solo para PRs del propio repositorio (nunca forks).

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
  - `PR governance`: estructura del PR;
  - `secret scanning (gitleaks)`;
  - `backend` y `frontend`, a medida que existan.
- Ruleset `main-protection`:
  - PR obligatorio;
  - resolución de conversaciones;
  - checks requeridos;
  - sin force-push ni borrado.

### Humano (mantenedor)
- **Único** que da la aprobación final de producto y hace el merge (squash).

## 4. Qué valida `PR governance` (solo estructura, no calidad)

| Regla | Detalle |
|---|---|
| Título | Conventional Commits: `feat|fix|docs|test|refactor|perf|chore|ci|build|security` + `(scope)` opcional + `: descripción` |
| Rama | `feature/f<N>-<slug>`, `fix/<slug>`, `hotfix/<slug>`, `docs/<slug>`, `chore/<slug>` |
| Issue | `Closes|Fixes|Resolves|Refs #N` en el cuerpo |
| Work item real | Se consulta el issue por API (se validan los de `Closes/Fixes/Resolves`; si no hay, los de `Refs`). Debe existir, tener `work-item`, **no** tener `status:blocked` ni `status:done` (aunque también tenga otro estado) y tener `status:ready` o `status:in-progress`. Se aceptan ambos porque `work-item-state` puede cambiar el label mientras corre la governance. Además, la rama de su sección `### Rama` debe coincidir **exactamente** con la rama del PR |
| Secciones | Issue / Fase, Objetivo, Cambios, No incluye, Cómo se verificó, Definition of Done, Riesgos y deuda técnica, Autoría |
| Tamaño | Líneas relevantes (adiciones + borrados): **≤ 400** pasa; **401–800** pasa con aviso; **> 800** falla, salvo con el label `large-pr-approved` (que convierte el fallo en aviso) |

- **Excluidos del tamaño:** `docs/**`, `*.lock`, `uv.lock`, `pnpm-lock.yaml`, `package-lock.json`, `**/migrations/**`, `generated/**` y `frontend/src/lib/api/**`. Nunca se excluyen archivos de aplicación para pasar el límite.
- **Integridad:** el script se ejecuta **desde la rama base** para que un PR no pueda relajar su propia governance. Solo el PR que lo introduce usa su propia versión (arranque).
- **Limitación conocida (OBS-A-01-1):** con `pull_request`, la **definición del workflow** (YAML) sigue perteneciendo al ref del PR, así que un PR podría modificarla. Se resuelve en **A-02 (#15)** con un trigger trusted. Hasta entonces, cualquier cambio en `.github/workflows/**` o `.github/scripts/**` exige revisión humana específica.
- **Excepción:** los PRs de `dependabot[bot]` no siguen el template. Para ellos las reglas se informan como avisos y el check pasa, y la revisión humana sigue siendo obligatoria.
- `large-pr-approved` solo lo aplica el mantenedor, de forma consciente.

## 5. Política de triggers de GitHub Actions

| Tipo de workflow | Trigger | Reglas |
|---|---|---|
| Ejecuta código del PR (backend, frontend, tests, builds) | `pull_request` | Token de solo lectura en forks; nunca con secretos de producción |
| Trusted de metadata/governance (valida título, rama, body, labels, issues; sincroniza labels) | Puede usar `pull_request_target` | **No** hace checkout del head ni ejecuta código, scripts o acciones del PR; solo lee metadata por API; permisos mínimos; datos del evento solo por variables de entorno; revisión de seguridad específica en cada cambio |

`pull_request_target` no se aplica de forma indiscriminada. La migración de `PR governance` y `work-item-state` se evalúa en A-02 (#15).

## 6. Contrato de handoff

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
