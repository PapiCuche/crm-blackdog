# ADR-007: Modelo de asignación de conversaciones con FKs explícitas e historial

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** `docs/fase-0/03-tenancy-rbac-inbox-ia.md` §I, ADR-001, ADR-004

## Context

- El diseño original `assigned_type + assigned_id` es polimórfico: la base de datos no puede garantizar que el ID exista ni que pertenezca a la misma organización.
- Una conversación puede estar en la cola de un equipo **y** tener un responsable directo (humano **o** IA).
- Hay que conservar la trazabilidad completa de quién asignó qué, cuándo y por qué, y resolver las carreras (dos agentes tomando la misma conversación, IA respondiendo mientras un humano la toma).

## Decision

### 1. Estado actual en `conversations`

| Columna | Tipo | Regla |
|---|---|---|
| `assigned_team_id` | uuid NULL | FK compuesta `(organization_id, assigned_team_id) → teams(organization_id, id)` |
| `assigned_user_id` | uuid NULL | FK compuesta `(organization_id, assigned_user_id) → organization_memberships(organization_id, user_id)` (ADR-001) |
| `assigned_ai_agent_id` | uuid NULL | FK compuesta `(organization_id, assigned_ai_agent_id) → ai_agents(organization_id, id)` |
| `assignee_kind` | text GENERATED | `CASE WHEN assigned_user_id IS NOT NULL THEN 'USER' WHEN assigned_ai_agent_id IS NOT NULL THEN 'AI_AGENT' WHEN assigned_team_id IS NOT NULL THEN 'TEAM' ELSE 'UNASSIGNED' END` (STORED, indexable) |
| `assignment_version` | int | Bloqueo optimista de la asignación |
| `assigned_at` | timestamptz | Momento de la asignación actual |

```sql
ALTER TABLE conversations ADD CONSTRAINT conversations_single_direct_assignee
  CHECK (NOT (assigned_user_id IS NOT NULL AND assigned_ai_agent_id IS NOT NULL));
```

- El equipo **puede coexistir** con un usuario o con un agente IA.
- **Hasta la Fase 8 no existe `ai_agents`:** la columna `assigned_ai_agent_id`, su FK y la cláusula del CHECK se añaden en la migración de la fase de IA (**regla: cada migración corresponde a funcionalidad real**). La Fase 6 (Inbox) crea equipo y usuario; la Fase 8 amplía el CHECK.

### 2. Historial `conversation_assignments` (append-only)

| Columna | Descripción |
|---|---|
| `id`, `organization_id`, `conversation_id` | FK compuesta a la conversación |
| `previous_team_id`, `previous_user_id`, `previous_ai_agent_id` | Estado anterior |
| `new_team_id`, `new_user_id`, `new_ai_agent_id` | Estado nuevo |
| `reason_code` | MANUAL, TAKE, TRANSFER, ROUND_ROBIN, LOAD_BALANCE, SKILL_RULE, AI_ROUTING, HANDOFF, SUPERVISOR_TAKEOVER, USER_DEACTIVATED, AI_DISABLED, REOPEN |
| `reason_note` / `internal_comment` | Texto libre (visible solo internamente) |
| `priority_at_assignment` | Prioridad fijada al transferir |
| `assigned_by_user_id` | Si lo hizo un humano |
| `assigned_by_ai_agent_id` | Si lo hizo un agente IA (añadida en la Fase 8) |
| `assigned_by_system` | bool (reglas automáticas o jobs) |
| `handoff_id`, `summary_id` | Vínculo al handoff o al resumen IA (Fases 8–9) |
| `created_at` | |

- `CHECK` que exige **exactamente uno** de: `assigned_by_user_id`, `assigned_by_ai_agent_id` o `assigned_by_system = true`.
- `crm_app` no tiene `UPDATE` ni `DELETE` sobre esta tabla.
- *(Sustituye a la tabla `conversation_transfers` del borrador inicial de la Fase 0; `docs/fase-0/02-modelo-de-datos.md` ya usa este modelo.)*

### 3. Un único punto de escritura

`AssignmentService.assign(ctx, conversation_id, target: AssignmentTarget, reason, expected_version=None)` es **la única** forma de cambiar la asignación (API, tomar, transferir, round robin, handoff, kill switch, desactivación de un usuario). En una transacción:

```text
SELECT … FOR UPDATE de la conversación
→ si expected_version y no coincide → ConflictError("ya fue reasignada")
→ validar permisos y scope del actor; validar que el destino es miembro activo, del equipo, etc.
→ UPDATE conversations SET … , assignment_version = assignment_version + 1
→ INSERT conversation_assignments (anterior → nuevo)
→ audit_logs (conversation.assigned) + outbox (conversation.assigned → WS, notificaciones)
```

**"Tomar" una conversación sin asignar** es atómico sin bloqueo largo:

```sql
UPDATE conversations
   SET assigned_user_id = :me, assignment_version = assignment_version + 1, assigned_at = now()
 WHERE id = :id AND assigned_user_id IS NULL AND assigned_ai_agent_id IS NULL
RETURNING assignment_version;
-- 0 filas → "Otro agente la tomó"
```

**Carrera IA frente a humano (Fase 8+):** el worker de envío revalida `assigned_ai_agent_id` y `assignment_version` justo antes de enviar; si cambiaron, la respuesta de la IA se descarta (`SUPERSEDED`) y se ofrece como sugerencia.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| `assigned_type + assigned_id` | Sin integridad referencial ni garantía de tenant |
| Tabla `conversation_assignees` N:M como estado actual | Más flexible (varios responsables), pero complica las consultas del Inbox y no es un requisito; los colaboradores se modelan en `conversation_participants` |
| Solo historial (estado actual derivado) | Consultas del Inbox caras; el estado actual denormalizado es necesario por rendimiento |
| Añadir `assigned_ai_agent_id` desde la Fase 6 sin tabla `ai_agents` | Violaría la regla "cada migración = funcionalidad real" y dejaría una FK colgante |

## Consequences

- Filtros del Inbox baratos (`assignee_kind`, `assigned_user_id`, `assigned_team_id` indexados con `organization_id` y `status`).
- La lógica de asignación está en un único servicio: las reglas (round robin, carga, especialidad, IA) son **estrategias** que calculan un `AssignmentTarget` y llaman a `assign`.
- Cualquier nuevo tipo de responsable futuro (p. ej., un bot externo) requiere una columna y una migración, algo deseable por explícito.

## Security implications

- Las FKs compuestas impiden asignar a un usuario, equipo o agente de otra organización, aunque falle la validación del servicio.
- Solo `AssignmentService` escribe las columnas de asignación. Un test verifica que ningún otro módulo las actualiza (búsqueda estática + import-linter).
- La auditoría registra actor, motivo y cambio.

## Operational implications

- Métricas derivadas del historial: tiempo hasta la primera asignación, número de transferencias por conversación, tasa de handoff IA → humano.
- Desactivar un usuario dispara la reasignación masiva mediante el mismo servicio (`reason = USER_DEACTIVATED`).
