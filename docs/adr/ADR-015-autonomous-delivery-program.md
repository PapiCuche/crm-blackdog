# ADR-015: Programa de entrega autónoma con merge por gates

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Product Owner (mantenedor)
- **Related:** ADR-009, [AGENTS.md](../../AGENTS.md), [delivery-automation.md](../architecture/delivery-automation.md)

## Context

ADR-009 establece que la aprobación final de un PR es humana y que un agente no hace merge de su propio trabajo. Con un único mantenedor, cada work item esperaba una confirmación manual aunque todos los controles automáticos estuvieran en verde.

El 2026-10-02 el mantenedor decidió dos cosas:

1. Good Doggy CRM deja de construirse como demo: cada capacidad debe llegar al CRM oficial, contra el backend y PostgreSQL reales.
2. Autoriza a un programa de agentes a ejecutar el roadmap de forma continua, incluido el squash merge, mientras se cumplan unos gates fijos.

## Decision

### 1. Alcance de la autorización

Mientras el programa esté en curso, un agente puede, sin pedir confirmación entre work items: crear y actualizar documentación, ADRs e issues; cambiar etiquetas y dependencias del roadmap; crear ramas; implementar; abrir PRs; y hacer **squash merge** de los PRs que el propio programa creó.

La autorización es del mantenedor, está fechada y es revocable: basta con que lo indique en un issue o en la conversación con el agente. Fuera del programa siguen vigentes ADR-009 y AGENTS.md sin cambios.

### 2. Gates de merge

Un PR del programa se mergea solo si se cumplen los diez:

1. El alcance del issue está implementado completo.
2. Los tests focales pasan.
3. Se hizo una revisión adversarial independiente del autor, con lentes acordes al cambio (seguridad, tenancy y RLS, autorización, concurrencia, validación, contrato, accesibilidad, regresión, documentación).
4. No queda ningún hallazgo clasificado como `FIX NOW`.
5. La validación completa pasa en local (`make check`).
6. El CI del HEAD exacto está en verde.
7. No hay conversaciones de revisión sin resolver.
8. El diff final fue revisado.
9. No hay trabajo fuera del alcance que bloquee.
10. No hay un bloqueo de seguridad.

El merge se hace con `gh pr merge <N> --squash --match-head-commit <sha>`. El auto-merge de GitHub sigue prohibido. Después se comprueba en GitHub que el PR quedó mergeado, el issue cerrado con `status:done` y `main` actualizado.

### 3. Lo que el programa nunca hace

- Forzar `main`, reescribir historia publicada o modificar la protección de ramas.
- Desactivar checks de seguridad o debilitar un control para que pase un test.
- Usar BYPASSRLS, exponer secretos o borrar datos de producción.
- Usar `large-pr-approved` como rutina: un cambio de más de 800 líneas relevantes se divide.

Si hace falta una operación destructiva e irreversible sobre datos reales, o información que no puede inferirse con seguridad (credenciales reales, un contrato, una decisión legal), el programa se detiene en ese punto, lo documenta y sigue con otro work item independiente si existe.

### 4. Elección del siguiente work item

Con varios issues en `status:ready`, el programa elige por este orden: camino crítico hacia el producto funcional, mayor número de dependencias desbloqueadas, menor riesgo de arquitectura, menor alcance y menor trabajo desechable.

### 5. Decisiones

- Las decisiones técnicas ordinarias las toma el programa cuando hay una opción claramente preferible por seguridad, respaldada por los ADR, reversible y sin efecto comercial. Quedan documentadas; con ADR si cambian o amplían uno aceptado.
- En una decisión de producto ambigua, elige la opción más conservadora y reversible, y deja escritas las suposiciones.
- No inventa comportamiento financiero o legal irreversible.

### 6. Trazabilidad

Cada PR conserva el handoff de AGENTS.md §9. El campo `Merge performed` indica quién hizo el merge y bajo qué gates. La revisión adversarial queda resumida en el PR: hallazgos, clasificación y correcciones.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Mantener el merge humano por PR | Es el cuello de botella con un solo mantenedor; los controles automáticos ya cubren lo que esa confirmación verificaba |
| Auto-merge de GitHub | Mergea en cuanto pasan los checks requeridos, sin revisión adversarial ni revisión del diff final |
| Aprobación por un segundo agente como "review" en GitHub | GitHub no deja aprobar un PR propio con la misma cuenta; la revisión independiente se exige por proceso y queda en el PR |

## Consequences

- ADR-009 sigue vigente salvo en dos frases de "Trabajo con agentes de IA" y "Protección de `main`": dentro del programa, la aprobación final la da el cumplimiento de los gates, bajo una autorización previa del mantenedor.
- AGENTS.md, CLAUDE.md y delivery-automation.md describen el programa como una excepción con nombre, no como la regla general.
- El mantenedor revisa después: cualquier commit de `main` se puede revertir con un PR.

## Security implications

- Desaparece una revisión humana previa al merge. La sustituyen la revisión adversarial obligatoria, los checks requeridos del ruleset (`secret scanning (gitleaks)`, `PR governance (trusted)`, `backend gate`) y la suite de aislamiento entre tenants.
- El ruleset de `main` no cambia y el programa no puede saltárselo.

## Operational implications

- El programa deja el stack local en ejecución y documenta, al final, el estado real de cada capacidad.
- Para detenerlo, el mantenedor lo indica; el siguiente PR vuelve al flujo de ADR-009.
