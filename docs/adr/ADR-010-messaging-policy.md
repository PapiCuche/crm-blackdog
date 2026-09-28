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
| `conversations` | `last_inbound_at` (**fuente de verdad** de la ventana), `customer_window_expires_at` (denormalizado **solo** para UI, ordenación e índices; ver §2 regla 0) |
| `channel_accounts` | `status`, `quality_rating`, `messaging_limit_tier`, capacidades efectivas |
| `ChannelCapabilities` (código, por adapter) | `window_hours`, `supports_free_form`, `supports_templates`, `supports_human_agent_tag`, `human_agent_window_hours`, `max_text_length`, `media_types`, `supports_read_receipts` |
| `message_templates` | `channel_account_id`, `name`, `language`, `category` (MARKETING/UTILITY/AUTHENTICATION), `approval_status` (APPROVED/PENDING/REJECTED/PAUSED/DISABLED), `components`, `variables_schema`, `purpose` (QUOTE_SENT, FOLLOW_UP, REENGAGE…), `last_synced_at` |
| `messages` (salientes) | `send_mode` (FREE_FORM/TEMPLATE/HUMAN_AGENT_TAG), `template_id`, `template_language`, `template_variables` (JSONB), `policy_decision` (JSONB snapshot de la decisión), `delivery_status`, `provider_error_code`, `provider_error_title`, `provider_error_detail`, `failed_at` |
| `contacts` | `is_blocked` |
| `contact_consents` (+ `contact_consent_events`) | Consentimiento vigente por contacto, **canal** (WHATSAPP/INSTAGRAM/MESSENGER/TIKTOK/EMAIL/SMS/PHONE/ANY) y **propósito** (MARKETING/PROMOTIONS/FOLLOW_UP/TRANSACTIONAL/ALL_PROACTIVE…), con `status`, `source`, `granted_at`, `revoked_at`, `evidence`; el historial de cambios queda en `contact_consent_events` (modelo en `docs/fase-0/02` E.5) |

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
            CONSENT_MISSING, CONSENT_REVOKED, CONTACT_BLOCKED, CHANNEL_DISCONNECTED, CHANNEL_QUALITY_LOW,
            AI_DISABLED, QUIET_HOURS, RATE_LIMITED, INTERNAL_NOTE_NOT_SENDABLE, …],
  evaluated_at
)
```

**Reglas (orden de evaluación):**

0. **La ventana se recalcula siempre**: `window_open = now() < last_inbound_at + capabilities.window_hours`, usando las **capacidades vigentes del adapter** y las reglas actuales del canal. `customer_window_expires_at` **no** se usa para autorizar (puede estar desactualizado si cambian las reglas del canal o si falla su actualización).

1. Mensaje interno o nota → BLOCKED (`INTERNAL_NOTE_NOT_SENDABLE`).
2. Cuenta de canal desconectada o en error → BLOCKED.
3. Contacto bloqueado → BLOCKED.
4. Si `initiated_by = AI_AGENT`: kill switch y estado del agente (y el Output Guard ya validado, ADR-005).
5. Ventana abierta y el canal admite formato libre → FREE_FORM.
6. Ventana cerrada:
   - `initiated_by = USER` y el canal admite HUMAN_AGENT_TAG dentro de su plazo → HUMAN_AGENT_TAG.
   - En otro caso → TEMPLATE_REQUIRED: busca una plantilla APPROVED para el `purpose` y el idioma del contacto (con idioma de respaldo de la organización). Si no existe → BLOCKED (`TEMPLATE_NOT_APPROVED` / `TEMPLATE_MISSING_FOR_LANGUAGE`).
   - La IA **nunca** usa HUMAN_AGENT_TAG.
7. **Consentimientos** (`contact_consents`):
   - Si existe una revocación aplicable (mismo canal o `ANY`; mismo propósito o `ALL_PROACTIVE`) → BLOCKED (`CONSENT_REVOKED`), salvo `purpose = CUSTOMER_REPLY` dentro de la ventana (responder a quien escribe no es un mensaje proactivo).
   - Si el propósito lo **exige** (MARKETING y PROMOTIONS siempre; otros según la configuración de la organización por canal) → requiere un consentimiento GRANTED vigente para ese canal (o `ANY`) y propósito; si no → BLOCKED (`CONSENT_MISSING`).
   - `purpose = MARKETING` exige además una plantilla de categoría MARKETING fuera de la ventana.
   - Un mensaje entrante con una palabra de baja ("STOP", "BAJA", configurable) registra la revocación (`source = KEYWORD_STOP`).
8. Automatizaciones o seguimientos: respetan las horas de silencio de la organización (reprogramación, no descarte) y los rate limits por contacto.

**Uso:**

- **UI:** el editor consulta la política (`GET …/conversations/{id}/messaging-policy`) para mostrar el tiempo restante de la ventana, deshabilitar el texto libre y ofrecer plantillas.
- **Worker de envío:** re-evalúa **justo antes** de enviar (la ventana pudo cerrarse mientras el mensaje esperaba en la cola), guarda `policy_decision` en el mensaje y, si queda bloqueado, marca el mensaje FAILED con el motivo legible y notifica.
- **Automatizaciones y seguimientos:** si la decisión es BLOCKED por falta de plantilla → crean una tarea para un humano en lugar de fallar en silencio.
- Los errores del proveedor al enviar se normalizan (`provider_error_code` → un código interno + mensaje en español) y pueden disparar un cambio de estado de la plantilla o de la cuenta.

### 3. Fases

- **Fase 4 (Contactos):** `contact_consents` y su historial (registro manual e importación).
- **Fase 6 (Inbox + Sandbox):** servicio (incluida la evaluación de consentimientos), capacidades del adapter Sandbox (con una ventana configurable para probar), columnas de conversación y mensaje.
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
