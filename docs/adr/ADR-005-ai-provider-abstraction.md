# ADR-005: Abstracción de proveedores de IA, seguridad de tools y validación de salida

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** `docs/fase-0/03-tenancy-rbac-inbox-ia.md` §J, ADR-001, ADR-002, [security-boundaries.md](../architecture/security-boundaries.md)

## Context

- Soportar OpenAI y Anthropic desde el inicio, y más proveedores después (Gemini, xAI, modelos locales).
- Las cuentas, API keys, modelos, routing y fallback se configuran desde el panel, **sin deploy** (§67–68).
- Los agentes públicos atienden a clientes: nunca deben acceder a datos de otros clientes, inventar datos dinámicos ni ejecutar acciones peligrosas. **No se confía en que el prompt lo impida.**
- Antes de enviar al cliente cualquier afirmación sobre datos dinámicos (precio, stock, promoción, estado de pedido o reparación), debe existir **evidencia** de una tool autorizada.

## Decision

### Parte A — Capas

```text
ai_agents (runtime)  ──usa──►  ai_gateway (proveedores)      ──usa──►  integrations.credentials
   │                              │
   │ Tool Registry ──► servicios de negocio (con ExecutionContext del agente)
   │ Output Guard  ──► evidencia en ai_actions
```

`ai_gateway` no conoce el CRM. `ai_agents` solo toca el negocio a través del **Tool Registry**.

### Parte B — Gateway de proveedores

- **Provider ≠ Account ≠ Model.** `ai_providers` (global, requiere adapter en código) → `ai_provider_accounts` (por organización, credencial cifrada) → `ai_models` (catálogo global con capacidades) ← `ai_account_models` (qué modelos se habilitan en cada cuenta).
- **Interfaz `LLMProviderAdapter`:** `chat(LLMRequest) -> LLMResponse` (P0), `stream()` (P1), `list_models()`, `test_connection()`, `classify_error(exc) -> ErrorClass`, `extract_usage(response) -> Usage`.
- **Formato neutro:** mensajes con roles system/user/assistant/tool, bloques de contenido, `tool_calls` normalizados y JSON Schema para tools y salidas estructuradas. Cada adapter traduce a su API. Esto permite hacer fallback incluso a mitad de un tool loop.
- **Routing** por versión de agente y propósito (`CHAT`, `CLASSIFY`, `EXTRACT`, `SUMMARY`) con una cadena ordenada `[principal, fallback…]`.
- **Fallback** solo por errores de disponibilidad: timeout, 429, 5xx, credencial inválida o presupuesto agotado (según la configuración). **Nunca por "respuesta mala"** (§76). Los errores 400/validación **no** hacen fallback (son bugs). El fallback exige las mismas capacidades (`supports_tools`, `supports_structured_output`); se valida al guardar la configuración.
- **Circuit breaker** por cuenta en Redis; **presupuestos** diarios y mensuales por cuenta (80 % alerta; 100 % BLOCK o FALLBACK).
- **Secretos:** `SecretStore.get(credential_id)` descifra solo en memoria, justo antes de la llamada; nunca se loguea ni se serializa. El frontend solo ve `last_four`, `provider`, `name` y `status`.
- **Ningún model ID está hardcodeado en el código.** Los datos semilla del catálogo son revisables y la sincronización marca los modelos nuevos como DISABLED hasta que un Admin los habilita.
- Endpoints configurables (`base_url_override`) solo con **allowlist** de hosts (anti-SSRF).

### Parte C — Seguridad de tools

**1. Registro explícito en código.** Cada tool declara:

```text
code, description (para el LLM), input_model (Pydantic → JSON Schema), output_model,
risk: READ | WRITE_LOW | WRITE_HIGH,
audience: PUBLIC_SAFE | INTERNAL_ONLY,
required_permission (equivalente humano),
resource_scope: CURRENT_CONTACT | CURRENT_CONVERSATION | CATALOG | EXPLICIT_GRANT,
evidence_kinds: [PRICE, STOCK, PROMOTION, ORDER_STATUS, REPAIR_STATUS, …],
idempotent: bool, handler(ctx, args)
```

No hay tools dinámicas, SQL, URLs arbitrarias ni "ejecutar endpoint".

**2. `ToolContext` inyectado por el runtime, nunca por el LLM:**

```text
ToolContext(
  organization_id,           # de la conversación (ya bajo tenant_scope)
  conversation_id,           # actual
  contact_id,                # actual
  agent_id, agent_version_id,
  audience,                  # PUBLIC (agente de cara al cliente) | INTERNAL (copiloto)
  granted_resources,         # recursos explícitamente autorizados (p. ej., quote_id del hilo)
  run_id, tool_call_id,
)
```

- Los esquemas de input **no incluyen** `organization_id`, `contact_id` ni `conversation_id`. Una tool como `get_current_customer()` no recibe argumentos de identidad.
- Un agente PUBLIC **no puede** habilitar tools `INTERNAL_ONLY` (`search_customer`, `assign_conversation`, etc.). La restricción está en el registro del código y se valida también al guardar la configuración del agente.
- Cada invocación pasa por el pipeline:

```text
validar input (Pydantic, límites de longitud y enum)
→ ¿tool habilitada en la versión del agente? ¿audience compatible?
→ tenant context activo = ctx.organization_id
→ permiso equivalente (el actor es el AIAgent; se aplican los mismos servicios que para un humano)
→ resource scoping (¿el recurso pertenece al contacto/conversación actual o a granted_resources?)
→ ejecutar el servicio de negocio
→ redactar el output (sin costos, secretos ni datos de terceros)
→ registrar ai_actions (args y resultado redactados, estado, duración, idempotency_key = run_id + tool_call_id)
→ devolver {ok, data, error{code, message_for_agent}, meta{source, as_of, evidence_id}}
```

- Denegación → `ok=false, error.code=FORBIDDEN|NOT_FOUND`. El intento queda registrado (`status=DENIED`) y, si se repite, eleva el riesgo de la conversación.

### Parte D — AI Output Guard: afirmaciones → evidencia → validación → envío

**Principio:** el modelo **no escribe cifras dinámicas en texto libre**. Las declara como afirmaciones ligadas a evidencia, y el sistema es quien las renderiza.

**1. Salida estructurada obligatoria del agente** (JSON Schema, soportada por ambos proveedores):

```json
{
  "reply_template": "El {{c1}} tiene un precio de {{c2}} y está {{c3}} en tienda.",
  "claims": [
    {"id": "c1", "kind": "PRODUCT_NAME", "evidence_ref": "tc_01", "path": "variant.display_name"},
    {"id": "c2", "kind": "PRICE",        "evidence_ref": "tc_02", "path": "final_amount"},
    {"id": "c3", "kind": "STOCK",        "evidence_ref": "tc_03", "path": "availability_label"}
  ],
  "intent": "price_question",
  "wants_handoff": false
}
```

- `evidence_ref` apunta a un `tool_call_id` **de este run** registrado en `ai_actions`.
- `path` selecciona un campo del output de esa tool. **El valor lo toma el sistema del resultado de la tool, no del modelo.**

**2. Pipeline de validación antes de enviar:**

```text
AI response (estructurada)
 → Claims: parsear claims y placeholders; cada placeholder del template tiene su claim y viceversa
 → Tool evidence: por claim, cargar ai_actions[evidence_ref] y verificar:
      - pertenece a este run y a esta conversación;
      - la tool estaba autorizada y status = SUCCESS;
      - la tool declara ese evidence_kind (p. ej., PRICE solo de get_product_price);
      - el path existe en el output;
      - frescura: meta.as_of dentro del TTL del tipo (precio/stock ≤ 10 min por defecto);
      - coherencia: el sujeto (variant_id) de las claims relacionadas coincide.
 → Detección independiente de claims no declaradas (el texto fuera de placeholders):
      a) detectores deterministas: montos y monedas, números con formato de precio,
         términos de disponibilidad ("hay stock", "agotado", "quedan"), porcentajes de descuento,
         fechas de entrega y estados de pedido o reparación;
      b) clasificador secundario (modelo barato, salida estructurada) que responde:
         "¿el texto contiene afirmaciones sobre precio, stock, promoción o estado no cubiertas por placeholders?"
      Cualquier positivo = claim dinámica sin evidencia.
 → Validation: PASS solo si todas las claims tienen evidencia válida y no hay claims sin declarar.
 → Final send: el renderizador sustituye los placeholders por los valores formateados
   (Money con la moneda y el formato de la organización) obtenidos de las evidencias, aplica
   las reglas del canal (longitud, formato) y pasa por MessagingPolicyService.
```

- **Si falla la validación**, el mensaje **no se envía automáticamente**. Se reintenta **una vez** con feedback estructurado al modelo ("la claim c2 no tiene evidencia válida; llama a get_product_price"). Si vuelve a fallar → se guarda como `ai_suggestion` para un humano (modo AI_ASSISTED) o se hace **handoff** con el motivo `GUARDRAIL_BLOCKED`. Todo se registra en `ai_runs.guardrail_findings`.
- Los detectores deterministas son **una capa secundaria**, no la principal. La garantía principal es estructural: **una cifra dinámica solo puede llegar al cliente si el sistema la copió de una evidencia validada.**
- Tipos de claim y TTL configurables por organización; los kinds nuevos (p. ej., `REPAIR_STATUS`) se añaden junto con la tool que los evidencia.
- El copiloto interno (el humano revisa y envía) usa el mismo esquema y muestra las evidencias en la UI, pero la validación bloquea menos: advierte en lugar de impedir.

### Parte E — Registros de IA (separados del log de aplicación y de la auditoría)

| Registro | Contenido | Propósito |
|---|---|---|
| `ai_runs` | Una invocación: versión del agente, decisión, intent, tokens, coste, hallazgos del guard | Explicar qué decidió la IA y por qué |
| `ai_llm_calls` | Cada llamada al proveedor (incluye reintentos y fallbacks) | Coste, latencia, fiabilidad por cuenta y modelo |
| `ai_actions` | Cada tool call con args y resultado redactados | **Evidencia** para el Output Guard y trazabilidad |
| `audit_logs` | Solo los eventos de negocio y seguridad resultantes (`ai.lead.created`, `ai.guardrail.blocked`) | Auditoría |

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| LangChain / LlamaIndex como núcleo | Capa de abstracción amplia y cambiante; dificulta el control fino de tools, la auditoría y el formato neutro propio. Se pueden usar piezas aisladas si aportan |
| Un solo proveedor | Contradice el requisito de fallback y la independencia del proveedor |
| Validación solo por regex sobre el texto final | Frágil (formatos, idiomas, "cuatro mil"); falsos negativos. Queda como capa secundaria |
| Confiar en el prompt ("no inventes precios") | No es un control de seguridad |
| Que el modelo escriba las cifras y comparar después | Obliga a normalizar el texto libre y deja ambigüedades; el render desde evidencia es determinista |
| Tools genéricas con IDs como argumentos | Abren la puerta a que un prompt injection pida datos de otros clientes |

## Consequences

- Los agentes deben usar modelos con salida estructurada y tool calling (capacidad validada al configurar).
- La redacción de la respuesta queda algo más restringida (plantilla con placeholders). Mitigación: el prompt enseña el formato; los placeholders admiten formatos (`{{c2|money}}`).
- Una llamada extra al clasificador secundario por respuesta autónoma (modelo barato, ~cientos de tokens).
- Cada tool nueva debe declarar su audience, su scope y sus evidence_kinds: es un ítem del checklist de PR.

## Security implications

- **Prompt injection:** aunque el modelo sea manipulado, no puede leer otros contactos (sin argumentos de identidad), ni ejecutar tools no habilitadas, ni enviar cifras no evidenciadas.
- **Fuga de costos:** ningún output de tool pública contiene costos; el redactor lo refuerza y existe un test que lo verifica por tool.
- **Exfiltración de secretos:** las credenciales nunca entran en el contexto del LLM.
- **Ataques de coste:** presupuestos, rate limits por contacto y límite de tool calls por turno.

## Operational implications

- Dashboards: tasa de bloqueo del guard por kind, reintentos, handoffs por `GUARDRAIL_BLOCKED` y coste del clasificador.
- Toda tool nueva incluye tests de: aislamiento de tenant, resource scoping (acceso a otro contacto → NOT_FOUND), redacción y evidencia.
- Conjunto de evaluación con casos de inyección y de cifras inventadas; debe pasar antes de publicar una versión de agente (P2).
