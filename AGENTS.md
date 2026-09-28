# AGENTS.md — Guía obligatoria para agentes

Reglas para cualquier agente de programación (o persona) que trabaje en este repositorio. El flujo completo, los roles y el contrato de handoff están en [docs/architecture/delivery-automation.md](docs/architecture/delivery-automation.md).

## 1. Fuente de verdad (en este orden)

1. El **GitHub Issue** del work item actual.
2. Los **ADR** con estado `Accepted` ([docs/adr/](docs/adr/README.md)).
3. [docs/architecture/](docs/architecture/).
4. [docs/phases/](docs/phases/) (plan y observaciones vivas de la fase).
5. El código existente.

**Si hay una contradicción, no improvises:**
- identifícala;
- detén solo la parte afectada;
- documéntala en el PR (sección "Riesgos y deuda técnica");
- continúa con el resto que sea seguro hacer.

Un ADR `Accepted` no se contradice ni se modifica en silencio: si hace falta cambiarlo, se propone un ADR nuevo.

## 2. Antes de trabajar

```bash
git status            # working tree limpio
git fetch origin
git switch main && git pull --ff-only origin main
gh issue view <N>     # abierto, con status:ready y dependencias mergeadas
```

Comprueba:
- el working tree está limpio;
- el issue está abierto y tiene `status:ready`;
- sus **dependencias** están mergeadas en `main`;
- `main` está actualizado.

Si algo falla, **para y repórtalo**. Nunca hagas `reset --hard` ni descartes trabajo ajeno.

Después lee: este archivo, el issue, los ADR y documentos que enlaza, y `docs/phases/phase-<N>.md`.

## 3. Una rama = un issue

- Usa la rama que declara el issue. Formatos válidos: `feature/f<N>-<slug>`, `fix/<slug>`, `hotfix/<slug>`, `docs/<slug>`, `chore/<slug>`.
- Nunca mezcles dos work items en una rama ni en un PR.
- Parte siempre de `origin/main` actualizado.

## 4. Disciplina de alcance

El issue define **Incluye**, **No incluye**, **Criterios de aceptación** y **Validaciones**.
- No implementes nada de "No incluye" ni de issues futuros (p. ej., F1-02 no adelanta F1-03).
- Si falta algo imprescindible para cumplir el issue, no lo inventes: pregúntalo en el issue o documéntalo en el PR como bloqueo.
- Cada migración corresponde a funcionalidad real del issue.
- Tamaño objetivo ≤ 400 líneas relevantes; más de 800 falla en CI (ADR-009).

## 5. Seguridad (no negociable)

- **Aislamiento de tenant:** `organization_id` siempre desde el contexto, nunca del payload. Toda consulta tenant-owned dentro de `tenant_scope` (docs/architecture/tenancy-context.md).
- **RLS:** con FORCE en toda tabla tenant-owned; una sola política PERMISSIVE por comando; nunca `SET` de sesión.
- **Credenciales:** el runtime solo usa `crm_app`; `crm_migrator` solo en el job de migraciones (ADR-002 §1.1).
- **Secretos:** nunca en el repo, en logs, en el frontend ni en `NEXT_PUBLIC_*`. La plantilla es `.env.example`, sin valores reales.
- **Autorización y trazabilidad:** RBAC con scopes (ADR-003) y auditoría de los cambios importantes (ADR-011).
- **Datos personales:** sin PII en logs. Nada de API keys en el frontend.
- **Arquitectura:** no la saltes por comodidad (fronteras de módulos, `PricingService`, `MessagingPolicyService`, `ObjectStorageService`, cliente HTTP con allowlist).
- **Revisión:** usa el checklist de docs/architecture/security-boundaries.md §6.

## 6. Git

- Commits en **Conventional Commits** (`feat(scope): …`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`, `build`, `security`).
- **Nunca:**
  - push directo a `main`;
  - merge de tu propio PR;
  - force-push a `main`;
  - borrar ramas ajenas;
  - eliminar o reescribir decisiones `Accepted`;
  - habilitar auto-merge.
- Pie de commit si hubo asistencia IA: `Co-Authored-By: <agente> <email>`.

## 7. Pull Request

Usa `.github/pull_request_template.md`. El check **PR governance** exige:
- título Conventional Commit;
- rama válida;
- referencia a un issue (`Closes #N`) que exista, sea `work-item`, esté en `status:ready` o `status:in-progress` (nunca `blocked` ni `done`) y declare en `### Rama` exactamente la rama del PR;
- las 8 secciones del template: Issue / Fase, Objetivo, Cambios, No incluye, Cómo se verificó, Definition of Done, Riesgos y deuda técnica, Autoría.

Declara también:
- lo que **no** pudiste ejecutar (p. ej., Docker no disponible);
- la deuda técnica, con issue `tech-debt` si aplica;
- si hubo asistencia IA.

El PR se abre **sin merge**. Lo revisa otro agente o persona, y el merge (squash) lo hace un humano.

## 8. Validaciones mínimas antes del PR

- Las que indique el issue.
- Además, siempre:
  - gitleaks sobre el working tree;
  - ningún archivo `.env` real trackeado;
  - enlaces Markdown válidos si tocaste documentación.
- Si cambiaste workflows: `actionlint`.

## 9. Entrega final (contrato de handoff del Builder)

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
