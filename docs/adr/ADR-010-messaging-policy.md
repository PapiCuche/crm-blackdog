# ADR-010: MessagingPolicyService y modelo de ventana de atención y plantillas

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-005 (Output Guard), ADR-007, `docs/fase-0/03-tenancy-rbac-inbox-ia.md` §I.5

## Context

- WhatsApp solo permite mensajes de formato libre dentro de la **ventana de atención al cliente** (24 h desde el último mensaje entrante del cliente). Fuera de ella exige **plantillas aprobadas** (con categoría, idioma y variables). Instagram y Messenger tienen reglas equivalentes (ventana de 24 h + etiqueta de agente humano con un plazo mayor, solo para humanos).
- Los seguimientos automáticos, el envío de cotizaciones, las automatizaciones y la IA **querrán** enviar mensajes. Que alguien quiera enviar no implica que el canal lo permita.
- Los errores del proveedor (ventana cerrada, plantilla pausada, número de baja calidad) deben ser visibles y accionables.

## Decision

### 1. Datos en el dominio de canales

| Dónde | Campos |
|---|---|
| `conversations` | `last_inbound_at`, `customer_window_expires_at` (derivado: `last_inbound_at + capabilities.window_hours`), `window_status` (OPEN/CLOSED, calculado al leer) |
| `channel_accounts` | `status`, `quality_rating`, `messaging_limit_tier`, capacidades efectivas |
| `ChannelCapabilities` (código, por adapter) | `window_hours`, `supports_free_form`, `supports_templates`, `supports_human_agent_tag`, `human_agent_window_hours`, `max_text_length`, `media_types`, `supports_read_receipts` |
| `message_templates` | `channel_account_id`, `name`, `language`, `category` (MARKETING/UTILITY/AUTHENTICATION), `approval_status` (APPROVED/PENDING/REJECTED/PAUSED/DISABLED), `components`, `variables_schema`, `purpose` (QUOTE_SENT, FOLLOW_UP, REENGAGE…), `last_synced_at` |
| `messages` (salientes) | `send_mode` (FREE_FORM/TEMPLATE/HUMAN_AGENT_TAG), `template_id`, `template_language`, `template_variables` (JSONB), `policy_decision` (JSONB snapshot de la decisión), `delivery_status`, `provider_error_code`, `provider_error_title`, `provider_error_detail`, `failed_at` |
| `contacts` | `marketing_opt_in` + origen y fecha (necesario para plantillas MARKETING), `is_blocked` |

### 2. `MessagingPolicyService`

**Toda** salida hacia un canal pasa por él: humanos, IA, automatizaciones, seguimientos, cotizaciones y reenvíos.

```text
MessagingPolicyService.evaluate(ctx, OutboundIntent) -> PolicyDecision

OutboundIntent(
  conversation_id | (contact_id + channel_account_id),
  content_kind: TEXT | MEDIA | TEMPLATE | INTERACTIVE,
  purpose: CUSTOMER_REPLY | FOLLOW_UP | QUOTE_SEND | REMINDER | MARKETING | NOTIFICATION,
  initiated_by: USER | AI_AGENT | AUTOMATION | SYSTEM,
  template_ref? (purpose o template_id), language?,
)

PolicyDecision(
  allowed: bool,
  mode: FREE_FORM | TEMPLATE_REQUIRED | HUMAN_AGENT_TAG | BLOCKED,
  template?: (id, name, language, category, required_variables),
  window_expires_at?,
  reasons: [WINDOW_CLOSED, TEMPLATE_NOT_APPROVED, TEMPLATE_MISSING_FOR_LANGUAGE,
            NO_MARKETING_OPT_IN, CONTACT_BLOCKED, CHANNEL_DISCONNECTED, CHANNEL_QUALITY_LOW,
            AI_DISABLED, QUIET_HOURS, RATE_LIMITED, INTERNAL_NOTE_NOT_SENDABLE, …],
  evaluated_at
)
```

**Reglas (orden de evaluación):**

1. Mensaje interno o nota → BLOCKED (`INTERNAL_NOTE_NOT_SENDABLE`).
2. Cuenta de canal desconectada o en error → BLOCKED.
3. Contacto bloqueado → BLOCKED.
4. Si `initiated_by = AI_AGENT`: kill switch y estado del agente (y el Output Guard ya validado, ADR-005).
5. Ventana abierta y el canal admite formato libre → FREE_FORM.
6. Ventana cerrada:
   - `initiated_by = USER` y el canal admite HUMAN_AGENT_TAG dentro de su plazo → HUMAN_AGENT_TAG.
   - En otro caso → TEMPLATE_REQUIRED: busca una plantilla APPROVED para el `purpose` y el idioma del contacto (con idioma de respaldo de la organización). Si no existe → BLOCKED (`TEMPLATE_NOT_APPROVED` / `TEMPLATE_MISSING_FOR_LANGUAGE`).
   - La IA **nunca** usa HUMAN_AGENT_TAG.
7. `purpose = MARKETING` → exige `marketing_opt_in` y una plantilla de categoría MARKETING.
8. Automatizaciones o seguimientos: respetan las horas de silencio de la organización (reprogramación, no descarte) y los rate limits por contacto.

**Uso:**

- **UI:** el editor consulta la política (`GET …/conversations/{id}/messaging-policy`) para mostrar el tiempo restante de la ventana, deshabilitar el texto libre y ofrecer plantillas.
- **Worker de envío:** re-evalúa **justo antes** de enviar (la ventana pudo cerrarse mientras el mensaje esperaba en la cola), guarda `policy_decision` en el mensaje y, si queda bloqueado, marca el mensaje FAILED con el motivo legible y notifica.
- **Automatizaciones y seguimientos:** si la decisión es BLOCKED por falta de plantilla → crean una tarea para un humano en lugar de fallar en silencio.
- Los errores del proveedor al enviar se normalizan (`provider_error_code` → un código interno + mensaje en español) y pueden disparar un cambio de estado de la plantilla o de la cuenta.

### 3. Fases

- **Fase 6 (Inbox + Sandbox):** servicio, capacidades del adapter Sandbox (con una ventana configurable para probar), columnas de conversación y mensaje.
- **Fase 7 (WhatsApp):** plantillas (sincronización y estados), HUMAN_AGENT_TAG no aplica, errores reales de Meta, envío de cotizaciones por plantilla UTILITY.
- **Fase 12:** capacidades de Instagram y Messenger.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Que cada módulo (cotizaciones, automatizaciones, IA) verifique la ventana | Lógica duplicada e inconsistente |
| Intentar enviar y reaccionar al error del proveedor | Mala UX, mensajes perdidos y riesgo sobre la calidad del número |
| Verificar solo en la UI | Las automatizaciones y la IA no pasan por la UI; además la ventana cambia con el tiempo |

## Consequences

- Todos los envíos tienen una decisión registrada y explicable ("¿por qué no se envió el seguimiento?").
- Las automatizaciones necesitan plantillas configuradas por propósito para funcionar fuera de la ventana; el panel mostrará qué propósitos no tienen plantilla aprobada.

## Security implications

- Evita el uso del canal contra las políticas de Meta (riesgo de bloqueo del número), el marketing sin consentimiento y el envío de notas internas.
- La decisión se evalúa en el servidor; el cliente solo la muestra.

## Operational implications

- Sincronización periódica de plantillas y alerta cuando una plantilla usada por automatizaciones pasa a PAUSED o REJECTED.
- Métricas: envíos bloqueados por motivo, errores del proveedor por código, calidad del número.
