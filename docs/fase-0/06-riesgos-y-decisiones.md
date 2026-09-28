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
| T12 | **Crecimiento de tablas** (`messages`, `audit_logs`, `webhook_events`, `ai_llm_calls`) | M | M | Particionamiento por mes desde el inicio en las tablas de log; retención |
| T13 | **Next.js + Django = dos runtimes que desplegar** | M | B | docker-compose idéntico en dev y prod; imágenes versionadas; health checks |
| T14 | **"Temporal que se vuelve permanente"** | A | M | Toda deuda consciente se registra como ADR o issue con etiqueta `tech-debt` y fase objetivo |

---

## Inconsistencias detectadas en el prompt maestro

| # | Dónde | Inconsistencia | Propuesta |
|---|---|---|---|
| I1 | §38 vs §42 | Promoción como `price_type` y también como entidad `promotions` → dos fuentes de verdad | Solo `promotions`; las listas sustituyen a los tipos de precio (K.2) |
| I2 | §15 | `assigned_type` + `assigned_id` polimórfico: sin integridad referencial y sin equipo y usuario simultáneos | Tres FKs + CHECK + `assignee_kind` generado (I.1) |
| I3 | §17 vs §13/§14 | `HANDOFF_REQUESTED` no pertenece a ningún enum definido | `handoff_status` + `ai_handoffs` |
| I4 | §12 vs §13 | Filtro "Pendientes" frente al estado PENDING; "Archivados" no es un estado | Definir PENDING = en cola sin tomar; archivado = flag (D-INB-1) |
| I5 | §103 | Las tools de IA (Fase 7) dependen de leads y oportunidades (Fase 9) y cotizaciones (Fase 10) | Reordenar (S) |
| I6 | §103 | Handoff (Fase 8) después de agentes autónomos (Fase 7) | Fusionar en la Fase 8 |
| I7 | §7 | "Owner" y "Superadmin" como roles de organización: ¿quién está por encima de quién? | Superadmin = staff de plataforma, fuera de la organización (D1) |
| I8 | §58 vs §118 | `search_customer()`/`get_customer_history()` en agentes públicos contradicen la seguridad IA del §118 | Tools ligadas a la conversación; `search_customer` solo interna (J.4) |
| I9 | §47 | VIEWED sin mecanismo para detectarlo | Enlace público con token o eliminar el estado (D-COM-3) |
| I10 | §54, §47 (SENT) | Seguimiento automático y envío de cotización sin considerar la ventana de 24 h y las plantillas de WhatsApp | Plantillas UTILITY + `message_templates` + UI de ventana |
| I11 | §8, §33 vs §96 | Menú "Ventas > Ventas" y datos de "Ganado" sin tabla que los registre | `orders` + `order_items` + `payment_methods` (sin facturación) |
| I12 | §53 | `due_date` + `due_time` separados | `due_at` timestamptz + `is_all_day` |
| I13 | §46 vs §105 | "Reservas" sin definir cuándo se reserva | Reservar al aceptar la cotización (D-INV-2) |
| I14 | §65 | Umbrales de confianza del LLM tratados como fiables | Señal compuesta + calibración con feedback (J.8) |
| I15 | §57 vs §14 | Nivel de autonomía (agente) y modo de atención (conversación) se solapan | El nivel es el techo; el modo es el estado actual (I.1) |
| I16 | §96 | `ai_decisions` separada de la ejecución | Integrada en `ai_runs` |
| I17 | §66 | "Modelos locales" sin considerar SSRF de `base_url` configurable | Allowlist y proveedor local solo en self-hosted (M.2 #10) |

---

## U. Decisiones pendientes

**Leyenda de bloqueo:** 🔴 bloquea la Fase 0.5/1 · 🟠 bloquea la Fase 2–5 · 🟡 bloquea la Fase 6+.

### Plataforma, tenancy y acceso

| ID | Decisión | Opciones | Mi recomendación | Bloquea |
|---|---|---|---|---|
| D1 | ¿Qué es "Superadmin"? | (a) staff de la plataforma SaaS; (b) rol de organización por encima del Admin | **(a)**. En la organización: Owner > Admin | 🔴 |
| D2 | ¿Un usuario puede pertenecer a varias organizaciones? | Sí / No | **Sí** (membresías) | 🔴 |
| D3 | ¿Cómo se identifica la organización activa? | Subdominio (`acme.crm.com`) / segmento de ruta (`/acme/inbox`) / solo sesión | **Segmento de ruta** en el frontend + cabecera en la API (multipestaña correcta, un solo certificado). Subdominios cuando se abra el SaaS | 🔴 |
| D4 | ¿RLS de PostgreSQL desde el inicio? | Sí / solo filtro en la app | **Sí** | 🔴 |
| D5 | Topología de dominios y auth | Same-origin vía proxy / subdominios same-site / JWT | **Same-origin** (`app.dominio.com` y `/api`), sesión con cookie HttpOnly | 🔴 |
| D6 | ¿MFA obligatorio para quién? | Todos / roles sensibles / opcional | **Obligatorio para Owner, Admin y roles con permisos sensibles**; opcional para el resto | 🔴 |
| D7 | ¿Alcances OWN/TEAM/BRANCH/ALL desde el MVP? | Sí / solo ALL | **Sí en el modelo**; en la UI inicial, OWN/ALL | 🔴 |
| D8 | Identificadores | UUIDv7 + número humano / bigint | **UUIDv7 + secuencias por organización** | 🔴 |
| D9 | Estrategia de Git | GitHub Flow + tags / GitFlow | **GitHub Flow** (ver S) | 🔴 |
| D10 | Hosting y object storage | VPS con Docker (Hetzner, DigitalOcean) / cloud gestionado (AWS, GCP) / PaaS (Render, Railway) | Para el MVP: **VPS o PaaS con Postgres gestionado (con pgvector y PITR) + S3-compatible (R2 o S3)**. Evitar Kubernetes | 🔴 |
| D11 | Versión de PostgreSQL | 16 / 17 / 18 | **17 o 18** según lo que soporte el proveedor elegido (pgvector obligatorio) | 🔴 |
| D12 | ¿Tamaño del equipo y ritmo? | — | Necesito saberlo para dimensionar fases y el alcance del MVP | 🔴 |
| D13 | Idioma de la UI | Solo español / i18n desde el inicio | **Español (es-PE), con claves i18n preparadas** (costo bajo, ahorra un refactor) | 🔴 |
| D14 | Retención y supresión de datos | Solo soft delete / anonimización / purga | **Soft delete + papelera 30 días + anonimización** para el derecho de supresión | 🟠 |

### Catálogo, precios e inventario

| ID | Decisión | Opciones | Mi recomendación | Bloquea |
|---|---|---|---|---|
| D-PRC-1 | ¿Precios con IGV incluido? | Incluido / excluido / por lista | **Incluido** (retail B2C); mayorista configurable por lista | 🟠 |
| D-PRC-2 | Monedas | Solo PEN / PEN + USD | **PEN activa**, modelo multimoneda preparado, sin conversión | 🟠 |
| D-PRC-3 | Promociones apilables | Sí / No | **No en el MVP** (solo la de mayor prioridad) | 🟠 |
| D-PRC-4 | Listas derivadas ("Efectivo = Regular − 3 %") | Sí / precios explícitos por lista | **Ambas**: derivada por defecto y explícita si existe | 🟠 |
| D-PRC-5 | Redondeo | 2 decimales / terminación .90 / enteros | Configurable; por defecto **enteros** (habitual en retail de tecnología en Perú; confirmar) | 🟠 |
| D-PRC-6 | ¿Qué listas puede comunicar la IA pública? | Solo Regular / Regular + Efectivo / … | **Regular + (opcional) Efectivo/Transferencia**, indicando la condición | 🟡 |
| D-INV-1 | ¿Seriales/IMEI en el MVP? | Sí / No | **No**, modelo preparado | 🟠 |
| D-INV-2 | ¿Cuándo se reserva stock? | Al crear la cotización / al aceptarla / al confirmar el pago | **Al aceptar la cotización**, con vencimiento (p. ej., 48 h) | 🟠 |
| D-INV-3 | ¿Stock visible para el cliente/IA: número exacto o nivel? | Exacto / nivel (Disponible, Últimas unidades, Agotado) | **Nivel**, con umbral configurable (no revelar inventario exacto a la competencia) | 🟡 |
| D-CAT-1 | ¿Condición (nuevo/usado/open box) como columna o como opción? | Columna / opción | **Columna** (afecta a garantía, filtros y reportes) | 🟠 |

### Inbox y canales

| ID | Decisión | Opciones | Mi recomendación | Bloquea |
|---|---|---|---|---|
| D-INB-1 | Significado de PENDING | En cola sin tomar / pospuesto / "pendiente de algo" | **En cola sin tomar** (coincide con el filtro "Pendientes") | 🟠 |
| D-INB-2 | Política de reapertura | Siempre reabrir / nueva conversación tras CLOSED / ventana | **RESOLVED + ventana (72 h) reabre; CLOSED crea una nueva** | 🟠 |
| D-INB-3 | Cierre automático | Nunca / RESOLVED → CLOSED tras X días | **RESOLVED → CLOSED a los 7 días** (configurable) | 🟠 |
| D-CH-1 | ¿Cloud API de Meta directa o un BSP (360dialog, Twilio, Gupshup)? | Directa / BSP | **Cloud API directa** (sin sobrecoste por mensaje ni intermediario; el adapter permite cambiar) | 🟠 |
| D-CH-2 | ¿Cuántos números de WhatsApp por organización? | Uno / varios (por sucursal) | **Varios** soportados en el modelo; el MVP arranca con uno | 🟠 |
| D-CH-3 | ¿Migrar el número actual de la tienda (WhatsApp Business app) a la Cloud API? | Migrar / número nuevo / coexistencia | Evaluar la **coexistencia** (app + API en el mismo número) si Meta la tiene disponible para la cuenta; si no, **número nuevo para el piloto**. **Implica cambios operativos importantes: decisión de negocio** | 🟠 |
| D-CH-4 | ¿Descargar y guardar toda la media? ¿Retención? | Todo / solo documentos / con TTL | **Todo**, con retención configurable (p. ej., 1 año para media, indefinida para documentos de venta) | 🟠 |
| D-CH-5 | Asignación automática por defecto | Manual / round robin / carga | **Round robin por equipo** con disponibilidad y límite de conversaciones concurrentes | 🟠 |
| D-CH-6 | ¿Transcribir notas de voz? ¿Con qué proveedor? | Sí (OpenAI u otro) / No | **Sí**, configurado como un modelo más del gateway (`modality = TRANSCRIPTION`) | 🟡 |

### IA

| ID | Decisión | Opciones | Mi recomendación | Bloquea |
|---|---|---|---|---|
| D-IA-1 | Proveedor de embeddings para la KB | OpenAI / Voyage / otro | **OpenAI o Voyage**, configurable; guardar `embedding_model_id` para poder re-embeddear | 🟡 |
| D-IA-2 | Debounce | 2–8 s | **4 s**, configurable por organización | 🟡 |
| D-IA-3 | Autonomía inicial en producción | 1 / 2 / 3 | **Nivel 1 (asistida) → 2** por métricas | 🟡 |
| D-IA-4 | ¿La IA crea cotizaciones en el MVP? | Solo borrador con aprobación / no | **Borrador + aprobación humana** (§51) — en P1 dentro de la Fase 8/9 | 🟡 |
| D-IA-5 | ¿Los agentes públicos leen notas internas? | Sí / No | **No** (el copiloto interno sí) | 🟡 |
| D-IA-6 | ¿La IA se identifica como asistente virtual? | Sí / No | **Sí**, en el primer mensaje | 🟡 |
| D-IA-7 | Comportamiento fuera de horario | IA sigue / IA informa y encola / solo mensaje fijo | **IA sigue con consultas de precio y stock; los handoffs se encolan con un mensaje de horario** | 🟡 |
| D-IA-8 | ¿Quién mantiene el catálogo de modelos y precios por token? | Plataforma / cada organización | **Plataforma** (el Admin de la organización solo habilita) | 🟡 |
| D-IA-9 | ¿Las API keys las aporta cada organización o las paga la plataforma? | BYO key / plataforma / ambas | **BYO key** en el MVP (cada organización configura sus cuentas, como pide §67); "plataforma" como opción SaaS futura | 🟡 |
| D-IA-10 | Idioma de respuesta de la IA | Solo español / detectar idioma | **Español**, con respuesta en el idioma del cliente si escribe en otro | 🟡 |

### Comercial

| ID | Decisión | Opciones | Mi recomendación | Bloquea |
|---|---|---|---|---|
| D-COM-1 | Lead y oportunidad | Mantener ambos / solo oportunidad + lifecycle en el contacto | **Mantener ambos** con las reglas de conversión de L.1 | 🟡 |
| D-COM-2 | ¿Cotización siempre ligada a una oportunidad? | Sí (auto-crear) / opcional | **Sí** | 🟡 |
| D-COM-3 | Estado VIEWED | Enlace público / quitar el estado | **Enlace público con token** (P1); sin él, no se muestra VIEWED | 🟡 |
| D-COM-4 | Motor de PDF | WeasyPrint / servicio externo | **WeasyPrint** | 🟡 |
| D-COM-5 | Límites de descuento iniciales | — | Necesito tus valores reales por rol (vendedor X %, supervisor Y %) | 🟡 |
| D-COM-6 | Métodos de pago iniciales | — | Propuesta: Efectivo, Transferencia, Tarjeta, Yape, Plin, Financiamiento. **Confirmar** | 🟡 |
| D-COM-7 | Pipelines iniciales | Solo Retail / Retail + Mayoristas | **Retail** (y Mayoristas si ya hay operación) | 🟡 |

---

## Qué necesito de ti para arrancar la Fase 0.5 / 1

Respuestas a las decisiones 🔴: **D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13**.

Con ellas escribo los ADRs, preparo el esqueleto del repositorio (Fase 0.5) y el plan detallado de la Fase 1 (archivos, migraciones y tests), sin avanzar a la siguiente fase hasta que la actual esté estable (§123).

**En paralelo, fuera del código:** iniciar la verificación del negocio en Meta Business Manager y decidir el número para el piloto (D-CH-3). Es el camino crítico de calendario más probable.
