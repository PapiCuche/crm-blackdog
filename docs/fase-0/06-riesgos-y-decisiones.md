# T–U · Riesgos, inconsistencias y decisiones pendientes

---

## T. Riesgos

**P** = probabilidad, **I** = impacto (A/M/B).

### T.1 Riesgos de producto y de proyecto

| # | Riesgo | P | I | Mitigación |
|---|---|---|---|---|
| R1 | **Alcance del MVP demasiado grande** (§104 incluye ~20 capacidades mayores). Riesgo de no llegar nunca a producción | A | A | Fase 10 como hito de producción con un tenant real; P1 recortable; piloto interno en la Fase 8; nada de fases 11+ hasta estabilizar |
| R2 | **Equipo pequeño frente a un producto de tamaño SaaS** | A | A | Monolito, sin microservicios, código generado para el contrato de API, shadcn, reglas estrictas de frontera para no reescribir |
| R3 | **Dependencia de la plataforma Meta** (verificación de negocio, App Review, límites de mensajería, calidad del número, cambios de políticas y precios) | A | A | Iniciar los trámites ya; adapter aislado; monitor de calidad y tier; plantillas en regla; no depender de un único número |
| R4 | **Políticas de Meta sobre IA en WhatsApp.** Meta ha restringido en sus términos los chatbots de IA de propósito general en WhatsApp Business; los asistentes de atención de un negocio propio se consideran permitidos | M | A | Mantener la IA acotada al negocio (ventas y soporte de la propia empresa); revisar los términos vigentes antes del lanzamiento; handoff siempre disponible |
| R5 | **TikTok: disponibilidad limitada de la API de mensajería** según región y partner | A | M | Fase 13 condicionada a una investigación previa (E19-01); no comprometer fecha |
| R6 | **Cambios de identidad en WhatsApp** (nombres de usuario e IDs con alcance de negocio que pueden ocultar el teléfono) | M | M | `contact_identities` con `external_id` genérico y alcance por cuenta; no asumir que siempre existe un teléfono; verificar el estado actual de la API de Meta al implementar la Fase 5 |
| R7 | **Adopción por los vendedores** (si el Inbox es más lento que WhatsApp Web, no lo usarán) | M | A | Desktop first, atajos de teclado, respuestas rápidas, latencia < 300 ms en el envío (optimista), pruebas con usuarios reales desde la Fase 4 |
| R8 | **Fusiones de contactos erróneas** (familias con un número compartido) | M | M | Nunca fusionar automáticamente salvo identidad exacta verificada; fusión con preview y `merged_snapshot` para revertir |
| R9 | **Expectativas sobre la IA** ("que venda sola desde el día 1") | A | M | Despliegue gradual (sombra → asistida → autónoma) guiado por métricas |
| R10 | **Notas de voz e imágenes**: gran parte de las consultas llegan como audio o captura | A | M | Transcripción (E07-09) y modelos con visión; si no está disponible → handoff |
| R11 | **Cumplimiento de protección de datos (Perú)** | M | A | Consentimiento de marketing, anonimización, retención, registro; validar con asesoría legal antes del SaaS comercial |

### T.2 Riesgos técnicos

| # | Riesgo | P | I | Mitigación |
|---|---|---|---|---|
| T1 | **La IA inventa precios o stock** | M | A | Tools obligatorias + guardrail de cifras + memoria sin precios + conjunto de evaluación + handoff |
| T2 | **Prompt injection / fuga de datos** | M | A | J.7 + tools ligadas a la conversación + agentes públicos sin notas internas ni costos + red-team antes de la autonomía |
| T3 | **Fuga entre tenants** | B (con RLS) | A | Capítulo G completo + suite automática |
| T4 | **Costes de IA descontrolados** | M | M | Presupuestos por cuenta, rate limits por contacto, modelos baratos para tareas auxiliares, métricas de coste por conversación |
| T5 | **Complejidad de RLS con Django** (contexto olvidado en Celery o comandos, conexiones persistentes) | M | M | `@tenant_task`, `SET LOCAL` siempre dentro de una transacción, tests de "sin contexto = 0 filas", rol `crm_platform` explícito |
| T6 | **Condiciones de carrera** (stock, asignaciones, mensajes duplicados, IA frente a humano) | M | A | Restricciones en BD (CHECK, UNIQUE parcial, EXCLUDE), `FOR UPDATE`, versión optimista, revalidación antes de enviar, tests de concurrencia reales (hilos contra Postgres, no SQLite) |
| T7 | **Escalado de Channels/WebSockets** | B (MVP) | M | Proceso `ws` separado, eventos mínimos, redis channel layer dedicado; si hiciera falta, servicio de WS gestionado |
| T8 | **Webhooks lentos que Meta deshabilita** | M | A | ACK < 1 s, procesamiento asíncrono, alertas sobre el lag |
| T9 | **Latencia de la respuesta IA** (debounce + LLM + tools = 5–15 s) | A | M | Indicador "escribiendo…", modelos rápidos para intents simples, límite de tool calls, streaming en el copiloto (P1) |
| T10 | **Deprecación de modelos por los proveedores** | A | M | Modelos como datos; sincronización que marca RETIRED; alerta al Admin si un agente usa un modelo en deprecación; fallback configurado |
| T11 | **Diferencias de tool calling entre proveedores** | M | M | Formato neutro + tests de contrato por adapter con respuestas grabadas (cassettes) |
| T12 | **Crecimiento de tablas** (`messages`, `audit_logs`, `webhook_ingress`, `ai_llm_calls`) | M | M | Particionamiento por mes desde el inicio en las tablas de log; retención |
| T13 | **Next.js + Django = dos runtimes que desplegar** | M | B | docker-compose idéntico en dev y prod; imágenes versionadas; health checks |
| T14 | **"Temporal que se vuelve permanente"** | A | M | Toda deuda consciente se registra como ADR o issue con etiqueta `tech-debt` y fase objetivo |
| T15 | **Dependencias de infraestructura que dejan de distribuirse** (caso real: MinIO dejó de publicar imágenes comunitarias en Docker Hub) | M | M | Interfaces propias (`ObjectStorageService`, adapters) + estándares abiertos (S3); versiones fijadas y revisadas por Dependabot |
| T16 | **Revisión humana no forzada técnicamente**: el ruleset protege `main`, pero con 0 aprobaciones requeridas (único mantenedor) | M | M | Revisión por un segundo agente o persona por proceso (plantilla de PR); subir a 1 aprobación cuando haya un segundo revisor con escritura |
| T17 | **Tests que no prueban RLS** por ejecutarse como superusuario | M | A | Los tests conectan con un rol equivalente a `crm_app`; el pipeline falla si el rol de test tiene `rolsuper` o `rolbypassrls` (tenancy-context T1–T17) |

---

## Inconsistencias detectadas en el prompt maestro

| # | Dónde | Inconsistencia | Resolución | Estado |
|---|---|---|---|---|
| I1 | §38 vs §42 | Promoción como `price_type` y también como entidad `promotions` | Solo `promotions`; las listas sustituyen a los tipos de precio | ✅ CLOSED — ADR-006 |
| I2 | §15 | `assigned_type` + `assigned_id` polimórfico | FKs explícitas + CHECK + historial `conversation_assignments` | ✅ CLOSED — ADR-007 |
| I3 | §17 vs §13/§14 | `HANDOFF_REQUESTED` sin enum | `handoff_status` + `ai_handoffs` | ✅ Aceptado (se implementa en la Fase 9) |
| I4 | §12 vs §13 | Filtro "Pendientes" frente al estado PENDING; "Archivados" no es un estado | Propuesta en D-INB-1 | ⏳ OPEN (D-INB-1) |
| I5 | §103 | Tools IA dependían de entidades de fases futuras | Roadmap corregido (05 §S) | ✅ CLOSED |
| I6 | §103 | Handoff después de la IA autónoma | La IA de la Fase 8 no envía de forma autónoma; la autonomía llega con el handoff (Fase 9) | ✅ CLOSED |
| I7 | §7 | Owner frente a Superadmin | Superadmin = staff de plataforma | ✅ CLOSED — D1 |
| I8 | §58 vs §118 | `search_customer()` en agentes públicos | Tools ligadas al contacto y la conversación actuales; audience PUBLIC/INTERNAL | ✅ CLOSED — ADR-005 |
| I9 | §47 | VIEWED sin mecanismo | Propuesta en D-COM-3 | ⏳ OPEN (D-COM-3) |
| I10 | §54, §47 | Envíos sin considerar la ventana de 24 h ni las plantillas | `MessagingPolicyService` | ✅ CLOSED — ADR-010 |
| I11 | §8, §33 | "Ventas > Ventas" sin tabla | `orders` + `order_items` + `payment_methods` | ✅ Aceptado (Fase 5) |
| I12 | §53 | `due_date` + `due_time` separados | `due_at` + `is_all_day` | ✅ Aceptado (Fase 5) |
| I13 | §46 | Reservas sin momento definido | Propuesta en D-INV-2 | ⏳ OPEN (D-INV-2) |
| I14 | §65 | Confianza del LLM tratada como fiable | Señal compuesta + calibración; el control de datos dinámicos es el Output Guard | ✅ Aceptado — ADR-005 |
| I15 | §57 vs §14 | Nivel de autonomía frente a modo de atención | El nivel es el techo; el modo es el estado actual | ✅ Aceptado |
| I16 | §96 | `ai_decisions` separada | Integrada en `ai_runs` | ✅ Aceptado |
| I17 | §66 | SSRF por `base_url` configurable | Allowlist | ✅ Aceptado — ADR-005, security-boundaries B9 |

---

## U. Decisiones

**Estados:** ✅ **APPROVED/CLOSED** (decidido y registrado) · ⏳ **OPEN** (pendiente) · 🔁 **REFINED** (aprobado con matices respecto a la propuesta original).
**Bloqueo:** indica la **primera fase** (numeración nueva de 05 §S) que necesita la decisión cerrada.

### U.1 Decisiones cerradas el 2026-09-28

| ID | Decisión aprobada | Estado | Registro |
|---|---|---|---|
| D1 | Superadmin = exclusivamente personal interno de la plataforma. Owner = rol máximo de la organización | ✅ APPROVED | ADR-001 |
| D2 | Un usuario en varias organizaciones mediante `organization_memberships` | ✅ APPROVED | ADR-001 |
| D3 | Organización activa en la URL: `/o/{organization_slug}/…` (frontend) y `/api/v1/o/{slug}/…` (API). La URL nunca autoriza: se valida membresía, permisos y contexto de tenant | 🔁 APPROVED (la API también usa la ruta, en lugar de la cabecera propuesta) | ADR-001, tenancy-context |
| D4 | PostgreSQL RLS como defensa adicional; no sustituye validación de `organization_id`, scoping, RBAC ni membresía | ✅ APPROVED | ADR-002 |
| D5 | Sesión con cookie HttpOnly segura; nada sensible en `localStorage` | ✅ APPROVED (topología same-origin) | ADR-003 |
| D6 | MFA obligatorio antes de producción para Owner, Admin y usuarios con permisos sensibles | ✅ APPROVED (flag `warn`/`enforce` hasta producción) | ADR-003 |
| D7 | Scopes OWN / TEAM / BRANCH / ORGANIZATION como atributo de la concesión (sin duplicar permisos) | 🔁 APPROVED (`ALL` renombrado a `ORGANIZATION`) | ADR-003 |
| D8 | UUIDv7 + numeración comercial por organización concurrency-safe (`COT-000001`) | 🔁 APPROVED (sin año en el número) | ADR-004 |
| D9 | GitHub Flow: `main` protegida, `feature/*`, `fix/*`, PR obligatorio, squash merge, tags | ✅ APPROVED | ADR-009 |
| D10 | Abstracción S3-compatible; sin blobs pesados en PostgreSQL; entorno local con Docker; el hosting no bloquea | ✅ APPROVED (el proveedor de hosting sigue abierto: D10-H) | ADR-008 |
| D11 | PostgreSQL 18 | ✅ APPROVED | ADR-002 |
| D12 | Equipo humano pequeño apoyado por agentes IA; incrementos pequeños; sin PRs gigantes | ✅ APPROVED | ADR-009 |
| D13 | UI en español; frontend y backend preparados para i18n | ✅ APPROVED | repository-structure |
| D-PROMO | `price_lists` + `product_prices` para listas; `promotions` + `promotion_items` para promociones; `PricingService` como autoridad única; vigencia por timestamps al calcular (sin cron como mecanismo principal) | ✅ APPROVED | ADR-006 |
| D-ASSIGN | `assigned_team_id` / `assigned_user_id` / `assigned_ai_agent_id` + CHECK (usuario XOR IA) + historial `conversation_assignments` | ✅ APPROVED | ADR-007 |
| D-AITOOLS | Agentes públicos sin `search_customer` global; solo el contacto y la conversación actuales o recursos autorizados; tenant, permisos, scoping, auditoría y validación en cada tool | ✅ APPROVED | ADR-005 §C |
| D-AIGUARD | Output Guard: respuesta → claims → evidencia de tools → validación → envío; no depender solo de regex | ✅ APPROVED | ADR-005 §D |
| D-MSGPOL | Ventana de atención, plantillas, idioma, variables y errores modelados en el dominio de canales; `MessagingPolicyService` antes de todo envío | ✅ APPROVED | ADR-010 |
| D-STORAGE | `ObjectStorageService` (S3, R2, emulador local, cualquier S3-compatible); la BD guarda metadatos y claves | ✅ APPROVED | ADR-008 |
| D-PGVECTOR | pgvector preparado pero **no** dependencia de la Fase 1; se incorpora con la base de conocimiento | ✅ APPROVED | ADR-002 §6 |
| D-OBS | Logging estructurado, correlation/request IDs, `ErrorReporter` (Sentry), health checks, auditoría; logs de aplicación, auditoría e IA separados | ✅ APPROVED | ADR-011 |
| D-MIGR | El ERD documenta ~95 tablas, pero se crean gradualmente: cada migración corresponde a funcionalidad real | ✅ APPROVED | 05 §S |
| D-ROADMAP | Nuevo orden de fases sin dependencias hacia fases futuras | ✅ APPROVED | 05 §S |
| D-CI | CI: backend (formato, lint, tests, migraciones), frontend (formato, lint, typecheck, tests), seguridad (secretos, dependencias), sin herramientas redundantes | ✅ APPROVED | ci-pipeline |
| D-ENG-3 | Protección real de `main`: repositorio público + ruleset `main-protection` (PR obligatorio, resolución de conversaciones, check `secret scanning (gitleaks)`, sin force-push ni borrado). Aprobaciones requeridas = 0 temporalmente (único mantenedor) | ✅ CLOSED (2026-09-28) | ADR-009 |
| D-REV-1 | RLS de `organization_memberships`: una única política SELECT condicional (tenant activo → solo ese tenant; sin tenant → solo las del usuario); escrituras solo con tenant; como máximo una política PERMISSIVE por comando | ✅ APPROVED (revisión PR #1) | ADR-002 §3.2 |
| D-REV-2 | Aislamiento de `crm_migrator`: web/worker/ws/beat solo reciben `DATABASE_URL` (`crm_app`) y rechazan la credencial del migrador; `CREATEDB` solo en el bootstrap local | ✅ APPROVED (revisión PR #1) | ADR-002 §1.1 |
| D-REV-3 | Requisitos obligatorios de funciones SECURITY DEFINER, incluido `REVOKE ALL … FROM PUBLIC` + `GRANT EXECUTE … TO crm_app` | ✅ APPROVED (revisión PR #1) | ADR-002 §3.3 |
| D-REV-4 | gitleaks sin allowlists por archivo | ✅ APPROVED (revisión PR #1) | ci-pipeline |
| D-REV-5 | Avatar global en `platform_files` (platform-owned); avatar opcional por organización en `organization_memberships.avatar_file_id` | ✅ APPROVED (revisión PR #1) | ADR-008, 02 E.2/E.4 |
| D-REV-6 | Consentimientos por canal y propósito: `contact_consents` + `contact_consent_events`, consultados por `MessagingPolicyService` | ✅ APPROVED (revisión PR #1) | ADR-010, 02 E.5 |
| D-REV-7 | `customer_window_expires_at` solo denormalizado; la ventana se recalcula al enviar | ✅ APPROVED (revisión PR #1) | ADR-010 §2 |
| D-REV-8 | Imágenes locales fijadas por patch: PostgreSQL 18.6, Redis 8.8.3 (Mailpit: se fija el patch en F1-01) | ✅ APPROVED (revisión PR #1) | infra/docker/compose.yaml |

### U.2 Decisiones abiertas — ingeniería (se resuelven al inicio de la Fase 1)

| ID | Decisión | Recomendación | Bloquea |
|---|---|---|---|
| D-ENG-1 | Versiones exactas: Python, Django, Node, Next.js y librería UUIDv7 | Verificar el soporte vigente el día de inicio: Django LTS/estable + Python soportado (3.13/3.14), Node LTS, Next.js estable | Fase 1 |
| D-ENG-2 | Emulador S3 local (MinIO ya no publica imágenes en Docker Hub) | **Garage** (v2.x) o SeaweedFS; prueba de 1 h con boto3 antes de decidir | Fase 1 |
| D10-H | Proveedor de hosting de producción | Decidir antes del final de la Fase 6 (hace falta un endpoint público para los webhooks de la Fase 7) | Fase 7 |

### U.3 Decisiones abiertas — producto y dominio

| ID | Decisión | Recomendación | Bloquea |
|---|---|---|---|
| D14 | Retención y supresión de datos | Soft delete + papelera 30 días + anonimización para el derecho de supresión | Fase 4 |
| D-PRC-1 | ¿Precios con IGV incluido? | Incluido (B2C); configurable por lista | Fase 3 |
| D-PRC-2 | Monedas | PEN activa; modelo multimoneda sin conversión | Fase 3 |
| D-PRC-3 | Promociones apilables | No en el MVP | Fase 3 |
| D-PRC-4 | Listas derivadas | Derivada por defecto + explícita si existe | Fase 3 |
| D-PRC-5 | Redondeo | Configurable; por defecto enteros (confirmar) | Fase 3 |
| D-PRC-6 | Listas que la IA pública puede comunicar | Regular (+ Efectivo/Transferencia opcionales) | Fase 8 |
| D-CAT-1 | Condición del producto: columna u opción | Columna | Fase 3 |
| D-INV-1 | Seriales/IMEI en el MVP | No (modelo preparado) | Fase 3 |
| D-INV-2 | Momento de la reserva de stock | Al aceptar la cotización, con vencimiento | Fase 5 |
| D-INV-3 | Stock visible para cliente e IA: exacto o nivel | Nivel (Disponible / Últimas unidades / Agotado) | Fase 8 |
| D-COM-1 | Lead y oportunidad | Mantener ambos, con reglas de conversión | Fase 5 |
| D-COM-2 | ¿Cotización siempre ligada a una oportunidad? | Sí (auto-crear) | Fase 5 |
| D-COM-3 | Estado VIEWED | Enlace público con token (P1) | Fase 5 |
| D-COM-4 | Motor de PDF | WeasyPrint | Fase 5 |
| D-COM-5 | Límites de descuento por rol | **Necesito los valores reales** | Fase 5 |
| D-COM-6 | Métodos de pago iniciales | Efectivo, Transferencia, Tarjeta, Yape, Plin, Financiamiento (confirmar) | Fase 5 |
| D-COM-7 | Pipelines iniciales | Retail (+ Mayoristas si ya hay operación) | Fase 5 |
| D-INB-1 | Significado de PENDING | En cola sin tomar (= filtro "Pendientes") | Fase 6 |
| D-INB-2 | Política de reapertura | RESOLVED + 72 h reabre; CLOSED crea una nueva | Fase 6 |
| D-INB-3 | Cierre automático | RESOLVED → CLOSED a los 7 días | Fase 6 |
| D-CH-5 | Asignación automática por defecto | Round robin por equipo con disponibilidad | Fase 6 |
| D-CH-1 | Cloud API directa o BSP | Cloud API directa | Fase 7 |
| D-CH-2 | Números de WhatsApp por organización | Varios en el modelo; uno en el MVP | Fase 7 |
| D-CH-3 | Número del piloto (migrar, nuevo o coexistencia) | **Decisión de negocio**; iniciar los trámites de Meta ya | Fase 7 |
| D-CH-4 | Retención de media | Todo, con retención configurable | Fase 7 |
| D-CH-6 | Transcripción de notas de voz | Sí, como modelo del gateway | Fase 8 |
| D-IA-1 | Proveedor de embeddings | OpenAI o Voyage, configurable | Fase 9 (base de conocimiento) |
| D-IA-2 | Debounce | 4 s configurable | Fase 8 |
| D-IA-3 | Autonomía inicial | Sombra → asistida → nivel 2 por métricas | Fase 9 |
| D-IA-4 | ¿La IA crea cotizaciones? | Solo borrador + aprobación humana | Fase 10 |
| D-IA-5 | ¿Agentes públicos leen notas internas? | No | Fase 8 |
| D-IA-6 | ¿La IA se identifica como asistente virtual? | Sí | Fase 8 |
| D-IA-7 | Fuera de horario | IA consulta; handoffs en cola con aviso | Fase 9 |
| D-IA-8 | Catálogo de modelos y precios por token | Mantenido por la plataforma | Fase 8 |
| D-IA-9 | API keys por organización (BYO) o de plataforma | BYO en el MVP | Fase 8 |
| D-IA-10 | Idioma de respuesta | Español; idioma del cliente si escribe en otro | Fase 8 |

---

## Qué necesito de ti para arrancar la Fase 1

- **Nada bloqueante de producto.** La Fase 1 (infraestructura base) solo necesita D-ENG-1 y D-ENG-2, que resuelvo al inicio con verificación de versiones y una prueba corta, y que registraré como ADR.
- **En paralelo (calendario):** verificación del negocio en Meta y número del piloto (D-CH-3), y valores de descuento por rol (D-COM-5).
