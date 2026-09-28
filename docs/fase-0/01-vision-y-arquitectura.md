# A–D · Visión, evaluación de arquitectura, dominios y diagrama

---

## A. Resumen ejecutivo

### Qué vamos a construir

Un **CRM omnicanal SaaS multiempresa** para equipos comerciales y de soporte que atienden a sus clientes por mensajería (WhatsApp primero; luego Instagram, Messenger y TikTok). En el mismo Inbox trabajan **agentes humanos y agentes de IA**, y la conversación puede pasar de unos a otros sin perder contexto.

El diferencial no es "tener un chatbot". Es que **la IA opera sobre los datos comerciales oficiales del sistema** (catálogo, variantes, listas de precios, promociones y stock disponible) a través de **herramientas internas auditadas**, sin inventar información. Toda acción de la IA deja rastro: qué herramienta llamó, con qué argumentos, qué devolvió el backend, qué modelo y qué cuenta usó, cuánto costó y qué versión de configuración del agente estaba activa.

### Flujo de valor central

```
Mensaje entrante → Contacto único (identidades multicanal) → Conversación
  → Router (IA o humano) → Consulta de precio/stock vía tools → Respuesta exacta
  → Lead (con score y datos extraídos, con procedencia) → Oportunidad en pipeline
  → Cotización (snapshot inmutable, aprobación por descuento) → Seguimiento
  → Ganado (venta registrada) / Perdido (motivo) → Reportes
```

### Primer cliente objetivo (inferido)

Retail de tecnología (iPhone, Mac y accesorios) en Perú: precios en S/, variantes por capacidad/color/condición, trade-in, servicio técnico, clientes que escriben por WhatsApp e Instagram y **mucha nota de voz**. El diseño es genérico y multiempresa, pero las decisiones por defecto (moneda PEN, zona horaria `America/Lima`, IGV, Yape/Plin como métodos de pago) se optimizan para este caso.

### Qué NO es (por ahora) [REQUISITO §105]

No es ERP, contabilidad, facturación electrónica SUNAT, planillas ni un WMS. El inventario se limita a stock físico, reservado y disponible por almacén.

### Criterio de éxito del MVP

Un cliente escribe por WhatsApp, la IA identifica la variante exacta, responde con precio y stock reales, crea el lead y la oportunidad, prepara un borrador de cotización, un humano lo aprueba, el sistema lo envía y programa el seguimiento. Todo queda auditado y **la IA no dice ningún dato que no haya salido de una tool en ese mismo turno**.

---

## B. Evaluación de arquitectura

### Veredicto general

**El stack es adecuado y lo confirmo.** Django + DRF + PostgreSQL + Redis + Celery + Channels es una combinación madura para un monolito modular con tiempo real y jobs en segundo plano. Next.js + TanStack Query es sólido para una aplicación de trabajo intensiva como el Inbox. La decisión de **no usar microservicios** es correcta: el dominio está muy acoplado transaccionalmente (precio → cotización → stock → oportunidad) y separarlo ahora multiplicaría la complejidad sin beneficio.

### Evaluación pieza por pieza

| Pieza | Veredicto | Por qué | Riesgos / ajustes |
|---|---|---|---|
| **Django + DRF** | ✅ Confirmado | ORM maduro, migraciones seguras, admin interno útil, ecosistema (drf-spectacular, django-filter, django-axes, django-otp) | Ejecutar bajo **ASGI** (uvicorn) desde el día 1 porque Channels lo exige. Separar procesos: `web` (HTTP) y `ws` (WebSocket) aunque ejecuten el mismo código |
| **PostgreSQL** | ✅ Confirmado. [RECOMENDACIÓN] versión **17 o 18** | Necesitamos RLS, `EXCLUDE USING gist` (vigencia de precios sin solapes), JSONB, `pg_trgm` (búsqueda difusa de nombres y teléfonos), `tsvector` (búsqueda global) y **pgvector** (base de conocimiento) | Confirmar que el hosting elegido ofrezca pgvector [D11]. PG18 trae `uuidv7()` nativo |
| **Redis** | ✅ Confirmado | Broker de Celery, capa de Channels, caché, locks distribuidos, rate limiting y circuit breakers | **Riesgo real:** usar una sola instancia con `maxmemory-policy allkeys-lru` para caché hace que Redis **expulse mensajes del broker**. [RECOMENDACIÓN] Instancias o bases lógicas separadas con políticas distintas: `broker` (noeviction + AOF), `channels` (noeviction), `cache` (allkeys-lru) |
| **Celery** | ✅ Confirmado | Webhooks, IA, envíos salientes, jobs programados, importaciones | Configurar `acks_late=True`, `task_reject_on_worker_lost=True`, colas separadas, tareas **idempotentes** y `visibility_timeout` mayor que la tarea más larga. RabbitMQ solo si Redis se queda corto (no hoy) |
| **Django Channels** | ✅ Confirmado | Tiempo real integrado con auth de sesión y permisos de Django | Los WebSockets **solo notifican**; la verdad se lee por REST. Así un evento perdido no corrompe la UI (ver P) |
| **Next.js (App Router) + TS** | ✅ Confirmado con matiz | Buen DX, rutas limpias, layout anidado ideal para Inbox y admin | El Inbox es casi 100 % *client-side* (tiempo real, estado local). No forzar Server Components donde no aportan. **Next.js no contiene lógica de negocio ni secretos**: es solo UI. No crear un BFF que duplique reglas |
| **Tailwind + shadcn/ui** | ✅ Confirmado | Componentes propios (el código vive en el repo), accesibles (Radix) y fáciles de tematizar para una identidad propia | Definir *design tokens* desde el inicio para no terminar con "otro dashboard shadcn genérico" |
| **TanStack Query** | ✅ Confirmado | Caché de servidor, invalidación por eventos WS y *optimistic updates* en el chat | Complementar con **Zustand** (estado UI mínimo: panel activo, borradores), **React Hook Form + Zod** (formularios) y **TanStack Table** (tablas de productos y precios) |
| **Monolito modular** | ✅ Confirmado | Transacciones ACID entre dominios, un solo deploy, menos coste operativo | Sin reglas de frontera, un monolito modular se degrada a "big ball of mud". [RECOMENDACIÓN] **import-linter** en CI con contratos por módulo (ver C) |

### Piezas que faltan en el stack y son necesarias

| Falta | Por qué es necesaria | Recomendación |
|---|---|---|
| **Almacenamiento de objetos** | Las URLs de media de WhatsApp caducan (hay que descargar y guardar). También PDFs de cotizaciones, Excel importados y avatares | S3-compatible: AWS S3, Cloudflare R2 o MinIO en self-hosted. Acceso solo mediante **URLs firmadas de corta duración** [D10] |
| **Contrato de API tipado** | Evitar duplicar tipos entre Django y TypeScript (regla "no duplicar lógica") | **drf-spectacular** genera OpenAPI 3.1 y **orval** u **openapi-typescript** generan tipos y hooks de TanStack Query. El contrato se valida en CI |
| **Seguimiento de errores** | Observabilidad (§95) | **Sentry** (backend, frontend y Celery) con *scrubbing* de PII y secretos |
| **Métricas** | Latencias, colas, costes de IA | Prometheus (`django-prometheus` + exporter de Celery) + Grafana. En el MVP puede bastar Sentry Performance + tablas propias de uso |
| **Reverse proxy / TLS** | Mismo sitio para cookies seguras y WS | Caddy o Nginx delante de `web`, `ws` y `next` |
| **Generador de PDF** | Cotizaciones (§52) | **WeasyPrint** (HTML/CSS → PDF) ejecutado en Celery |
| **Lectura de Excel** | Importación (§45) | `openpyxl` en modo `read_only`, siempre en Celery y con límites de filas y tamaño |
| **Embeddings** | Base de conocimiento (§60) | Anthropic no ofrece API de embeddings. Opciones: OpenAI embeddings o Voyage AI (recomendado por Anthropic) [D-IA-1] |
| **Speech-to-text** | Los clientes envían notas de voz | Sin transcripción, la IA no entiende audios. Opción: transcripción vía OpenAI u otro proveedor, configurable como un "modelo" más del gateway [D-CH-6] |
| **PgBouncer** | Más adelante, cuando haya muchas conexiones (web + ws + workers) | Modo *transaction pooling*. Es compatible con RLS usando `SET LOCAL` dentro de la transacción (ver G) |

### Decisiones de arquitectura transversales (propuestas)

1. **Capa de servicios explícita.** Cada módulo expone `services.py` (comandos que escriben y auditan) y `selectors.py` (consultas). Las vistas DRF son delgadas: validan entrada, llaman al servicio y serializan. **Las tools de IA llaman exactamente a los mismos servicios que la API.** Así la lógica existe una sola vez y los permisos también (principio 3).
2. **Contexto de ejecución obligatorio.** Todo servicio recibe un `ExecutionContext(organization, actor, permissions, request_id, channel)`. `actor` puede ser `User`, `AIAgent`, `System` o `Integration`. Esto unifica auditoría, permisos y tenancy entre API, Celery e IA.
3. **Eventos de dominio con *transactional outbox*.** Los cambios importantes escriben un evento en `outbox_events` **dentro de la misma transacción**. Un worker los publica a WebSockets, automatizaciones, timeline y notificaciones. Evita el clásico "se guardó pero no se notificó" o "se notificó pero hizo rollback".
4. **Dinero:** `NUMERIC(14,2)` + `currency CHAR(3)` + `Decimal` en Python. Nunca `float`. Redondeo `ROUND_HALF_UP` centralizado en un tipo `Money`.
5. **Tiempo:** `timestamptz` en UTC en la base; zona horaria por organización (`America/Lima`) para mostrar y para horarios.
6. **IDs:** UUIDv7 como PK (ordenables e inadivinables) + **números humanos por organización** (`CONV-00191`, `COT-000123`) generados con `org_sequences` bajo bloqueo de fila.
7. **Monorepo:** `backend/` (Django), `frontend/` (Next.js), `infra/` (docker, compose, IaC) y `docs/`. Un solo PR puede cambiar el contrato de API y la UI a la vez.

### Estructura de repositorio propuesta

```text
crm/
├── backend/
│   ├── config/                 # settings (base/dev/test/prod), asgi, celery, urls
│   ├── core/                   # shared kernel (ver C)
│   ├── apps/<modulo>/          # models.py, services.py, selectors.py, api/,
│   │                           # events.py, tasks.py, permissions.py, tests/
│   └── pyproject.toml          # ruff, mypy (django-stubs), pytest, import-linter
├── frontend/
│   ├── src/app/                # rutas App Router
│   ├── src/features/<modulo>/  # componentes y hooks por dominio
│   ├── src/lib/api/            # cliente generado desde OpenAPI (no editar)
│   └── src/components/ui/      # shadcn
├── infra/                      # docker-compose.yml, Dockerfiles, Caddyfile
└── docs/                       # fase-0, ADRs, runbooks
```

---

## C. Dominios del sistema (bounded contexts)

Ajusto la lista del §5. Cambios principales: **`roles` se integra en `access`**, **`sales` se divide** en `deals` (pipeline/oportunidades), `quotes` y `orders`, **`ai` se divide** en gateway y agentes, y se añaden `notifications`, `search`, `imports`, `files` y `platform`, que el prompt usa pero no asigna a ningún módulo.

### Mapa de módulos

| Módulo | Responsabilidad | Tablas que posee | Puede depender de |
|---|---|---|---|
| `core` (shared kernel) | Modelos base (`TenantModel`, `SoftDeleteModel`), `ExecutionContext`, `Money`, secuencias, outbox, errores de dominio, utilidades de tenancy/RLS | `org_sequences`, `outbox_events` | — (nadie más abajo) |
| `platform` | Operación SaaS: organizaciones como clientes, planes/límites (futuro), superadmin, impersonación, catálogo global de proveedores de IA, salud de servicios | `ai_providers`, `ai_models`, `ai_model_prices`, `service_health_checks`, `impersonation_sessions` | core |
| `accounts` | Identidad global: usuarios, login, sesiones, MFA, reset de contraseña, invitaciones | `users`, `user_mfa_devices`, `user_invitations` | core |
| `organizations` | Organizaciones, sucursales, membresías, equipos, horarios, configuración por organización | `organizations`, `organization_settings`, `branches`, `organization_memberships`, `teams`, `team_members`, `work_schedules`, `assignment_rules` | core, accounts |
| `access` | RBAC: catálogo de permisos, roles, alcances, políticas (descuento, visibilidad de listas) | `permissions`, `roles`, `role_permissions`, `membership_roles`, `discount_policies` | core, organizations |
| `files` | Subida/descarga segura, URLs firmadas, antivirus (futuro) | `files` | core |
| `contacts` | Perfil único del cliente, identidades, direcciones, etiquetas, notas, duplicados/fusión, timeline (proyección) | `contacts`, `contact_identities`, `contact_addresses`, `tags`, `contact_tags`, `notes`, `contact_merge_candidates`, `contact_merges`, `timeline_events`, `data_provenance` | core, organizations, access, files |
| `channels` | Cuentas de canal, **adaptadores** (WhatsApp/IG/FB/TikTok/Sandbox), plantillas, envío saliente, parseo de webhooks específicos | `channel_accounts`, `message_templates` | core, integrations, files |
| `integrations` | Credenciales cifradas (secret store), ingesta genérica de webhooks, idempotencia, reintentos y jobs de sincronización | `credentials`, `webhook_ingress`, `webhook_failures`, `sync_jobs` | core |
| `inbox` | Conversaciones, mensajes, adjuntos, estados de entrega, asignación, transferencias, participantes/no leídos, notas internas, respuestas rápidas | `conversations`, `conversation_participants`, `conversation_assignments`, `conversation_status_history`, `conversation_tags`, `messages`, `message_attachments`, `message_status_events`, `quick_replies`, `quick_reply_categories` | contacts, channels, organizations, access |
| `catalog` | Marcas, categorías, productos, opciones, variantes, alias de búsqueda, media, servicios | `brands`, `categories`, `products`, `product_options`, `product_option_values`, `product_variants`, `variant_option_values`, `product_search_aliases`, `product_media` | core, files |
| `pricing` | Listas de precios, precios con vigencia, costos, promociones, **motor de precios**, edición masiva e historial | `price_lists`, `product_prices`, `variant_costs`, `promotions`, `promotion_items`, `promotion_price_lists`, `price_change_batches`, `price_change_batch_items` | catalog, access |
| `inventory` | Almacenes, niveles de stock, movimientos (ledger) y reservas | `warehouses`, `inventory_levels`, `inventory_movements`, `inventory_reservations` | catalog, organizations |
| `imports` | Importación genérica de Excel con validación, preview y aplicación (catálogo, precios, stock y, más adelante, contactos) | `data_imports`, `data_import_rows` | catalog, pricing, inventory, files |
| `leads` | Leads, scoring y señales | `leads`, `lead_score_events` | contacts, catalog, inbox |
| `deals` | Pipelines, etapas, oportunidades, ítems de interés, historial de etapa y motivos de pérdida | `pipelines`, `pipeline_stages`, `opportunities`, `opportunity_items`, `opportunity_stage_history`, `lost_reasons` | contacts, leads, catalog |
| `quotes` | Cotizaciones, ítems snapshot, aprobaciones, PDF y enlace público | `quotes`, `quote_items`, `quote_approvals` | deals, pricing, inventory, contacts, files |
| `orders` | Venta registrada al ganar (mínima, sin facturación) y métodos de pago | `orders`, `order_items`, `payment_methods` | quotes, deals, inventory |
| `tasks` | Tareas y seguimientos, recordatorios y acciones programadas cancelables | `tasks`, `scheduled_actions` | contacts, deals, quotes, inbox |
| `ai_gateway` | Proveedores, cuentas, modelos, routing, fallback, circuit breakers, presupuestos y medición de uso. **No sabe nada de CRM** | `ai_provider_accounts`, `ai_account_models`, `ai_llm_calls`, `ai_usage_daily` | core, integrations (credenciales), platform |
| `ai_agents` | Agentes, versiones, prompts, tools (registro), runtime/orquestador, context builder, memoria, guardrails, handoff, copiloto, feedback, intents y base de conocimiento | `ai_agents`, `ai_agent_versions`, `ai_agent_model_configs`, `ai_agent_tools`, `ai_agent_channels`, `ai_agent_rules`, `ai_prompts`, `ai_intents`, `ai_sessions`, `ai_runs`, `ai_actions`, `ai_handoffs`, `ai_summaries`, `ai_suggestions`, `ai_feedback`, `kb_documents`, `kb_document_agents`, `kb_chunks` | ai_gateway + **servicios públicos** de los módulos de negocio (vía tools) |
| `automations` | Reglas cuando/si/entonces, ejecuciones e idempotencia | `automation_rules`, `automation_runs` | consume eventos; ejecuta acciones vía servicios públicos |
| `notifications` | Centro de notificaciones y preferencias | `notifications`, `notification_preferences` | core, organizations |
| `search` | Índice de búsqueda global (proyección) | `search_documents` | consume eventos |
| `analytics` | Dashboards y reportes (consultas de solo lectura, agregados materializados) | `daily_metrics_*` (vistas materializadas) | lee de todos, **no escribe en ninguno** |
| `audit` | Registro inmutable de auditoría | `audit_logs` | core |
| `service_catalog` (futuro §89) | No es un módulo aparte. Los servicios técnicos son `products.product_type = SERVICE` dentro de `catalog`/`pricing` | — | — |

### Reglas de frontera (se verifican en CI con import-linter)

1. Un módulo **no importa modelos de otro módulo** para escribir. Llama a su `services.py`. Leer mediante `selectors.py` públicos está permitido.
2. `ai_gateway` no depende de ningún módulo de negocio. Es reutilizable (copiloto, resúmenes, supervisor, embeddings).
3. `ai_agents` **solo toca el negocio a través del Tool Registry**, y cada tool llama a servicios públicos. Nunca usa el ORM ni SQL directamente desde un prompt (principio 3).
4. `analytics` y `search` son de solo lectura sobre los demás; se alimentan de eventos o de consultas.
5. Las dependencias cíclicas se prohíben. Si A necesita reaccionar a B, se usa un **evento de dominio**, no un import.

---

## D. Arquitectura propuesta (diagrama textual)

```text
                              ┌──────────────────────────────────────────────┐
  Usuarios (navegador)        │           PROVEEDORES EXTERNOS               │
        │                     │  Meta: WhatsApp Cloud API · IG · Messenger   │
        │ HTTPS / WSS         │  TikTok Business Messaging                   │
        ▼                     │  OpenAI · Anthropic · (Gemini/xAI/local)     │
┌─────────────────┐           │  Embeddings · Speech-to-text                 │
│ Reverse proxy   │           └───────▲──────────────────────┬───────────────┘
│ (Caddy/Nginx)   │                   │ llamadas salientes   │ webhooks entrantes
│ TLS, rate limit │                   │ (adapters)           │ (firmados)
└─┬──────┬──────┬─┘                   │                      ▼
  │      │      │            ┌────────┴──────────────────────────────────────────┐
  │      │      │            │                 BACKEND (monolito modular Django)  │
  │      │      │  /api/*    │                                                   │
  │      │      └───────────►│  web (ASGI/uvicorn): DRF API v1                    │
  │      │                   │   ├─ Middleware: auth sesión → tenant → RLS ctx   │
  │      │   /ws/*           │   ├─ /webhooks/<provider>/ (verifica firma,       │
  │      └──────────────────►│   │   persiste webhook_ingress, ACK rápido)       │
  │                          │  ws (ASGI/Channels): consumers autenticados       │
  │  /*                      │                                                   │
  ▼                          │  ┌───────────── Capa de dominio ────────────────┐ │
┌─────────────────┐          │  │ accounts organizations access contacts inbox │ │
│ Next.js (UI)    │          │  │ catalog pricing inventory leads deals quotes │ │
│ App Router, TS  │          │  │ orders tasks automations notifications audit │ │
│ TanStack Query  │          │  │         services.py / selectors.py            │ │
│ WS client       │          │  └───────▲───────────────────────▲──────────────┘ │
│ (sin secretos,  │          │          │ mismos servicios      │                │
│  sin lógica de  │          │  ┌───────┴────────────┐  ┌───────┴─────────────┐  │
│  negocio)       │          │  │ AI Agents          │  │ Channel Adapters    │  │
└─────────────────┘          │  │  Orchestrator      │  │  WhatsAppAdapter    │  │
                             │  │  Context Builder   │  │  InstagramAdapter   │  │
                             │  │  Tool Registry ────┼─►│  MessengerAdapter   │  │
                             │  │  Guardrails        │  │  TikTokAdapter      │  │
                             │  │  Memory / KB (RAG) │  │  SandboxAdapter     │  │
                             │  └───────┬────────────┘  └─────────────────────┘  │
                             │  ┌───────▼────────────┐                           │
                             │  │ AI Gateway         │  OpenAIAdapter            │
                             │  │  Routing, Fallback │  AnthropicAdapter         │
                             │  │  Circuit breaker   │  (futuros adapters)       │
                             │  │  Budgets, Usage    │                           │
                             │  └────────────────────┘                           │
                             │  Outbox publisher ─► automations · WS · timeline  │
                             │                       · notifications · search    │
                             └───────┬─────────────────────┬─────────────────────┘
                                     │                     │
              ┌──────────────────────▼──┐     ┌────────────▼──────────────────────┐
              │ PostgreSQL 17/18         │     │ Redis                              │
              │  RLS por organization_id │     │  db0 broker Celery (noeviction,AOF)│
              │  pgvector, pg_trgm       │     │  db1 channel layer (noeviction)    │
              │  btree_gist (vigencias)  │     │  db2 caché/locks/rate (LRU)        │
              └──────────────────────────┘     └────────────┬──────────────────────┘
                                                            │
              ┌─────────────────────────────────────────────▼─────────────────────┐
              │ Celery workers (colas separadas)                                   │
              │  webhooks · ai · outbound · default · scheduled · imports · reports│
              │ Celery beat (tareas programadas: SLA, estancados, seguimientos,    │
              │  health checks, agregados de uso, purga de papelera)               │
              └───────────────────────────────────┬───────────────────────────────┘
                                                  │
              ┌───────────────────────────────────▼───────────────────────────────┐
              │ Object storage (S3/R2/MinIO): media, PDFs, Excel · URLs firmadas   │
              │ Observabilidad: Sentry · logs JSON (request_id/correlation_id) ·   │
              │ Prometheus/Grafana · tablas ai_llm_calls / webhook_ingress         │
              └────────────────────────────────────────────────────────────────────┘
```

### Flujo de un mensaje entrante (camino crítico)

```text
Meta → POST /webhooks/meta/
  1. Verifica X-Hub-Signature-256 sobre el body crudo (HMAC-SHA256 con app secret)
  2. INSERT webhook_ingress ON CONFLICT (provider, event_key) DO NOTHING
  3. Encola process_webhook_ingress(ingress_id) → responde 200 en < 1 s
Worker [webhooks]:
  4. Resuelve channel_account por phone_number_id → organization con una función SECURITY DEFINER
     mínima (nunca desde el payload) y abre tenant_scope(organization)
  5. Resuelve/crea contact_identity → contact
  6. Busca conversación abierta o crea una (según política de reapertura)
  7. Upsert del mensaje (unique channel_account + external_message_id)
  8. Descarga de media → object storage (tarea separada)
  9. outbox: message.received → WS (inbox), timeline, automations
 10. Si la conversación está asignada a IA y la IA está habilitada:
     programa ai.process_conversation con debounce (p. ej., 4 s)
Worker [ai]:
 11. Lock por conversación → Context Builder → Gateway (modelo principal / fallback)
 12. Tool loop (servicios de negocio, auditados) → guardrails de salida
 13. Según autonomía/confianza: envía (vía outbound) | crea sugerencia | handoff
Worker [outbound]:
 14. Revalida que la conversación siga asignada a IA (versión) → Adapter.send_message()
 15. Guarda external_message_id; los estados llegan después por webhook
```
