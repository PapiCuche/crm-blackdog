# R–S · Backlog y roadmap

**Prioridades:** **P0** = imprescindible para el MVP · **P1** = MVP deseable (entra si no pone en riesgo P0; si no, justo después) · **P2** = post-MVP · **P3** = futuro.
**Fase** = fase del roadmap propuesto (sección S), no la del prompt original.

---

## R. Backlog

### E00 · Fundaciones técnicas / infraestructura base (Fase 1)

| ID | Feature / Historia | Prio | Fase |
|---|---|---|---|
| E00-01 | Monorepo (`backend/`, `frontend/`, `infra/`, `docs/`) con docker-compose (Postgres + pgvector, Redis ×3 lógicas, MinIO, Mailpit) | P0 | 1 |
| E00-02 | Settings por entorno (12-factor), validación de settings críticos en el arranque (`DEBUG`, claves, hosts) | P0 | 1 |
| E00-03 | CI: ruff, mypy (django-stubs), pytest con cobertura, import-linter, eslint, tsc, `pip-audit`/`pnpm audit`, build de Next.js, verificación del contrato OpenAPI | P0 | 1 |
| E00-04 | `core`: `TenantModel`, `SoftDeleteModel`, `ExecutionContext`, `Money`, errores de dominio, `org_sequences` | P0 | 1 |
| E00-05 | Tenancy: middleware, contextvar, `SET LOCAL`, políticas RLS vía migración genérica, roles de BD, `@tenant_task` | P0 | 1 |
| E00-06 | Outbox + publisher + registro de handlers de eventos | P0 | 1 |
| E00-07 | `audit` con `audit.record(ctx, action, entity, changes)` y redactor | P0 | 1 |
| E00-08 | Observabilidad base: logs JSON con `request_id`/`correlation_id`, Sentry (backend/frontend/Celery) con scrubbing, `/health` y `/ready` | P0 | 1 |
| E00-09 | API: DRF + drf-spectacular + cliente TS generado (orval) + convención de errores (`{code, message, fields}`) + paginación por cursor | P0 | 1 |
| E00-10 | Frontend shell: layout, navegación del §8, tema (design tokens), tabla/formularios base, manejo de errores y toasts, i18n preparado (es-PE) | P0 | 1 |
| E00-11 | Test harness: factories (factory_boy), fixtures de dos organizaciones, **suite automática de aislamiento cruzado** | P0 | 1 |
| E00-12 | ADRs iniciales (una por cada decisión de U cerrada) | P0 | 1 |

### E01 · Identidad, organizaciones y acceso (Fase 2)

| ID | Historia | Prio |
|---|---|---|
| E01-01 | Como usuario, quiero iniciar sesión con email y contraseña con una cookie segura para acceder al CRM | P0 |
| E01-02 | Como usuario, quiero recuperar mi contraseña por email con un enlace de un solo uso que caduque | P0 |
| E01-03 | Como Owner o Admin, quiero configurar MFA TOTP y que sea obligatorio para los roles sensibles | P0 |
| E01-04 | Como staff de plataforma, quiero crear una organización con su Owner inicial, roles plantilla y configuración por defecto | P0 |
| E01-05 | Como usuario con varias organizaciones, quiero cambiar de organización sin volver a iniciar sesión | P1 |
| E01-06 | Como Admin, quiero invitar usuarios por email asignándoles rol, equipo y sucursal | P0 |
| E01-07 | Como Admin, quiero activar, desactivar y reasignar usuarios (y que al desactivar se revoquen sus sesiones y se reasignen sus conversaciones) | P0 |
| E01-08 | Como Owner, quiero crear y editar roles asignando permisos con alcance, sin poder conceder lo que no tengo | P0 |
| E01-09 | Como Admin, quiero gestionar sucursales y equipos (supervisor, integrantes, estrategia de asignación) | P0 |
| E01-10 | Como Admin, quiero definir horarios de trabajo reutilizables | P1 |
| E01-11 | Como usuario, quiero ver y cerrar mis sesiones activas | P1 |
| E01-12 | Como staff, quiero impersonar una organización con motivo, tiempo límite y auditoría | P2 |
| E01-13 | Como Admin, quiero ver el log de auditoría filtrable por actor, acción y entidad | P0 |

### E02 · Catálogo (Fase 3)

| ID | Historia | Prio |
|---|---|---|
| E02-01 | Como gestor de productos, quiero administrar marcas y categorías (árbol) | P0 |
| E02-02 | Como gestor, quiero crear un producto con opciones (capacidad, color, condición) y generar sus variantes | P0 |
| E02-03 | Como gestor, quiero editar SKU, estado y visibilidad para la IA por variante | P0 |
| E02-04 | Como gestor, quiero añadir alias de búsqueda ("16 pro max", "ip16pm") para que vendedores e IA encuentren el producto | P0 |
| E02-05 | Como gestor, quiero subir fotos por producto o variante | P1 |
| E02-06 | Como gestor, quiero registrar servicios técnicos (producto SERVICE con variantes por equipo y calidad) sin stock | P2 |
| E02-07 | Como Admin, quiero una papelera para restaurar productos eliminados | P1 |

### E03 · Precios (Fase 3)

| ID | Historia | Prio |
|---|---|---|
| E03-01 | Como Admin, quiero configurar listas de precios (visibilidad por permiso, exposición a IA, derivación) | P0 |
| E03-02 | Como gestor de precios, quiero fijar el precio de una variante en una lista, con motivo, para que quede en el historial | P0 |
| E03-03 | Como gestor, quiero programar un precio con fecha de inicio futura | P1 |
| E03-04 | Como gestor, quiero ver el historial de precios de una variante (anterior, nuevo, usuario, motivo, fecha) | P0 |
| E03-05 | Como gestor, quiero crear promociones con vigencia que apliquen a variantes, productos, categorías o marcas | P0 |
| E03-06 | Como vendedor, quiero ver el precio final vigente (con la promoción aplicada) y hasta cuándo vale | P0 |
| E03-07 | Como gestor autorizado, quiero registrar costos por variante y ver el margen; los demás no deben verlos | P0 |
| E03-08 | Como gestor, quiero actualizar precios de forma masiva (±monto/±%) con preview antes de confirmar | P0 |
| E03-09 | Como gestor, quiero importar catálogo y precios desde Excel con validación, preview y errores por fila | P1 |
| E03-10 | Como desarrollador, quiero una suite de tests del motor de precios (vigencias, solapes, promociones, permisos, redondeo) | P0 |

### E04 · Inventario (Fase 3)

| ID | Historia | Prio |
|---|---|---|
| E04-01 | Como Admin, quiero gestionar almacenes por sucursal e indicar cuáles cuentan para la venta | P0 |
| E04-02 | Como almacenero, quiero registrar ingresos, salidas y ajustes con motivo (movimiento + saldo atómico) | P0 |
| E04-03 | Como vendedor, quiero ver el stock disponible por variante y sucursal | P0 |
| E04-04 | Como almacenero, quiero transferir stock entre almacenes | P1 |
| E04-05 | Como sistema, quiero reservar y liberar stock (con vencimiento) al aceptar cotizaciones o cancelarlas | P1 |
| E04-06 | Como Admin, quiero alertas de stock bajo por variante | P1 |
| E04-07 | Como gestor, quiero importar stock inicial desde Excel | P1 |
| E04-08 | Tests de concurrencia: dos reservas simultáneas sobre la última unidad → solo una tiene éxito | P0 |

### E05 · Contactos (Fase 4)

| ID | Historia | Prio |
|---|---|---|
| E05-01 | Como vendedor, quiero crear y editar contactos con teléfonos, email, documento, responsable, sucursal y origen | P0 |
| E05-02 | Como sistema, quiero registrar identidades por plataforma sin columnas fijas | P0 |
| E05-03 | Como vendedor, quiero etiquetar contactos | P0 |
| E05-04 | Como vendedor, quiero añadir notas al contacto | P0 |
| E05-05 | Como vendedor, quiero ver el perfil 360° con pestañas (resumen, conversaciones, oportunidades, cotizaciones, compras, tareas, notas, archivos, actividad) | P0 (pestañas según fase) |
| E05-06 | Como vendedor, quiero ver el timeline cronológico del cliente | P1 |
| E05-07 | Como sistema, quiero detectar posibles duplicados (mismo teléfono o email, nombre similar) | P1 |
| E05-08 | Como supervisor, quiero fusionar dos contactos con preview y registro, o marcarlos como distintos | P1 |
| E05-09 | Como Admin, quiero anonimizar un contacto (derecho de supresión) | P2 |
| E05-10 | Como usuario, quiero buscar contactos por nombre, teléfono, email o @usuario | P0 |

### E06 · Inbox (Fase 6)

| ID | Historia | Prio |
|---|---|---|
| E06-01 | Como agente, quiero ver la lista de conversaciones con filtros básicos (todos, míos, sin asignar, pendientes, no respondidos, cerrados, archivados, canal, IA/humanos) | P0 |
| E06-02 | Como agente, quiero abrir un chat, ver el historial paginado y enviar texto y adjuntos | P0 |
| E06-03 | Como agente, quiero recibir mensajes en tiempo real y ver los estados de entrega | P0 |
| E06-04 | Como agente, quiero escribir notas internas diferenciadas que jamás se envían | P0 |
| E06-05 | Como agente, quiero diferenciar visualmente mensajes de cliente, humano, IA, sistema y notas | P0 |
| E06-06 | Como agente, quiero tomar una conversación sin asignar (atómico) | P0 |
| E06-07 | Como agente, quiero transferir a un usuario, equipo o agente IA con motivo, prioridad y comentario | P0 |
| E06-08 | Como agente, quiero cambiar el estado, la prioridad y las etiquetas de la conversación | P0 |
| E06-09 | Como agente, quiero ver el perfil rápido del cliente en el panel derecho y editarlo sin salir del Inbox | P0 |
| E06-10 | Como agente, quiero usar respuestas rápidas con `/atajo` y variables | P0 |
| E06-11 | Como Admin, quiero gestionar respuestas rápidas y sus categorías | P0 |
| E06-12 | Como agente, quiero ver quién está escribiendo o viendo la conversación | P1 |
| E06-13 | Como agente, quiero filtros avanzados (responsable, equipo, prioridad, etiqueta, fecha, producto, lead, etapa, nuevo/recurrente, tiempo esperando) | P1 |
| E06-14 | Como sistema, quiero asignación automática por round robin y por carga dentro de un equipo | P1 |
| E06-15 | Como sistema, quiero aplicar la política de reapertura y crear una conversación nueva tras CLOSED | P0 |
| E06-16 | Como desarrollador y demo, quiero un canal Sandbox para simular clientes | P0 |
| E06-17 | Como agente, quiero notificaciones (in-app y sonido) de nuevos chats y asignaciones | P0 |
| E06-18 | Como supervisor, quiero un panel con carga por agente, tiempos de espera y la posibilidad de reasignar, tomar o elevar prioridad | P1 |
| E06-19 | Como agente, quiero asignación por especialidad y reglas | P2 |

### E07 · WhatsApp (Fase 7)

| ID | Historia | Prio |
|---|---|---|
| E07-01 | Como Admin, quiero conectar un número de WhatsApp Cloud API (credenciales cifradas, verificación de webhook, prueba) | P0 |
| E07-02 | Como sistema, quiero recibir mensajes (texto, imagen, audio, video, documento, ubicación, contactos, reacciones, botones) de forma idempotente | P0 |
| E07-03 | Como sistema, quiero enviar texto, media y documentos, y procesar los estados | P0 |
| E07-04 | Como sistema, quiero descargar y guardar la media antes de que caduque | P0 |
| E07-05 | Como Admin, quiero sincronizar plantillas y ver su estado | P0 |
| E07-06 | Como agente, quiero enviar una plantilla cuando la ventana de 24 h está cerrada | P0 |
| E07-07 | Como agente, quiero ver cuánto tiempo queda de la ventana de 24 h | P0 |
| E07-08 | Como sistema, quiero guardar el referral de anuncios Click-to-WhatsApp en el contacto y el lead | P1 |
| E07-09 | Como sistema, quiero transcribir notas de voz | P1 |
| E07-10 | Como Admin, quiero ver la salud del número (calidad, límite de mensajería, errores) | P1 |
| E07-11 | Como Admin, quiero reintentar webhooks fallidos desde el panel | P1 |

### E08 · Gateway de IA (Fase 8)

| ID | Historia | Prio |
|---|---|---|
| E08-01 | Como staff, quiero mantener el catálogo de proveedores, modelos (capacidades) y precios por token | P0 |
| E08-02 | Como Admin, quiero añadir una cuenta de IA (proveedor, nombre, API key), probar la conexión y guardarla cifrada, viendo solo los últimos 4 caracteres | P0 |
| E08-03 | Como Admin, quiero rotar la API key de una cuenta sin deploy y que quede auditado (last_four anterior y nuevo) | P0 |
| E08-04 | Como Admin, quiero sincronizar los modelos disponibles de una cuenta y habilitar o deshabilitar modelos | P0 |
| E08-05 | Como sistema, quiero adapters OpenAI y Anthropic con formato neutro de mensajes y tools | P0 |
| E08-06 | Como sistema, quiero una cadena de fallback con clasificación de errores y circuit breaker | P0 |
| E08-07 | Como Admin, quiero límites diarios y mensuales por cuenta con alerta al 80 % y bloqueo o fallback al 100 % | P0 |
| E08-08 | Como Admin, quiero ver el consumo (tokens y coste) por cuenta, modelo, agente y día | P0 |
| E08-09 | Como Owner, quiero un botón global para desactivar la IA | P0 |

### E09 · Leads, pipeline y oportunidades (Fase 5 — sales core)

| ID | Historia | Prio |
|---|---|---|
| E09-01 | Como vendedor, quiero crear leads desde el Inbox o el contacto con producto, presupuesto y próxima acción | P0 |
| E09-02 | Como vendedor, quiero una lista de leads filtrable con score e interés | P0 |
| E09-03 | Como sistema, quiero calcular el score (0–100) con señales explicables | P0 |
| E09-04 | Como vendedor, quiero convertir un lead en oportunidad | P0 |
| E09-05 | Como Admin, quiero configurar pipelines y etapas (tipo, probabilidad, días hasta estancarse) | P0 |
| E09-06 | Como vendedor, quiero un kanban con drag & drop, filtros, monto, producto, responsable, próxima acción, prioridad y días sin actividad | P0 |
| E09-07 | Como vendedor, quiero una vista de tabla de oportunidades | P0 |
| E09-08 | Como vendedor, quiero marcar como ganada (monto, productos, pago, sucursal, vendedor) y que se registre la venta | P0 |
| E09-09 | Como vendedor, quiero marcar como perdida con motivo obligatorio | P0 |
| E09-10 | Como supervisor, quiero ver las oportunidades estancadas | P1 |
| E09-11 | Como Admin, quiero configurar los motivos de pérdida | P0 |
| E09-12 | Como vendedor, quiero ver en el Inbox el lead y la oportunidad vinculados y crearlos con un clic | P0 · **Fase 6** (requiere Inbox) |

### E10 · Tareas (Fase 5)

| ID | Historia | Prio |
|---|---|---|
| E10-01 | Como vendedor, quiero crear tareas (tipo, fecha y hora, descripción) vinculadas a contacto, oportunidad o cotización | P0 |
| E10-02 | Como vendedor, quiero ver mis tareas de hoy, vencidas y próximas | P0 |
| E10-03 | Como responsable, quiero recibir un recordatorio y una notificación al vencer | P0 |
| E10-04 | Como supervisor, quiero reasignar tareas | P1 |

### E11 · Agentes IA (Fases 8, 9 y 10 — ver la columna de cada historia)

*Historias sin fase indicada = Fase 8. La memoria larga llega en la Fase 9; E11-19 (Supervisor IA) en la Fase 14.*

| ID | Historia | Prio |
|---|---|---|
| E11-01 | Como Admin, quiero crear un agente (nombre, rol, objetivo, tono, prompt, canales, horario, autonomía, umbrales, límites) | P0 |
| E11-02 | Como Admin, quiero elegir cuenta y modelo principal más fallbacks por agente | P0 |
| E11-03 | Como Admin, quiero habilitar tools por agente respetando las restricciones de agentes públicos | P0 |
| E11-04 | Como Admin, quiero publicar versiones del agente y revertir a una anterior | P0 |
| E11-05 | Como sistema, quiero un orquestador con debounce, lock por conversación, tool loop y guardrails | P0 |
| E11-06 | Como cliente, quiero preguntar por un producto y recibir el precio y stock exactos (con aclaración de variante si hace falta) | P0 |
| E11-07 | Como sistema, quiero un Output Guard (claims → evidencia de tools → validación) que bloquee afirmaciones dinámicas sin evidencia (ADR-005 §D) | P0 · Fase 8 |
| E11-08 | Como sistema, quiero detectar intención, sentimiento y la petición de humano | P0 |
| E11-09 | Como sistema, quiero que la IA cree y actualice leads con datos extraídos marcados AI_EXTRACTION | P0 · **Fase 10** |
| E11-10 | Como Admin, quiero una base de conocimiento (documentos publicados, embeddings con pgvector, asignación a agentes) | P0 · **Fase 9** |
| E11-11 | Como sistema, quiero memoria corta y larga (resúmenes) | P0 |
| E11-12 | Como agente humano, quiero el copiloto: sugerir y mejorar respuesta, resumir, identificar qué quiere el cliente, consultar precio y stock (**Fase 8**); crear seguimiento, lead y oportunidad (**Fase 10**) | P0 |
| E11-13 | Como agente humano en modo AI_ASSISTED, quiero aprobar, editar o rechazar la sugerencia | P0 |
| E11-14 | Como supervisor, quiero ver las conversaciones de IA con sus tool calls, decisiones y costes | P0 |
| E11-15 | Como agente humano, quiero dar feedback (👍/👎 + categoría) a una respuesta de IA | P1 |
| E11-16 | Como Admin, quiero métricas de IA (resueltas, transferencias, tiempos, leads, cotizaciones, tokens, coste por conversación) | P1 |
| E11-17 | Como sistema, quiero que la IA cree oportunidades y borradores de cotización (nivel 4) | P1 · **Fase 10** |
| E11-18 | Como Admin, quiero ejecutar un conjunto de evaluación antes de publicar una versión | P2 · Fase 14 |
| E11-19 | Supervisor IA (reglas deterministas): lead caliente sin seguimiento, cotización sin seguimiento, vendedor saturado | P2 |

### E12 · Handoff IA ↔ humano (Fase 9)

| ID | Historia | Prio |
|---|---|---|
| E12-01 | Como cliente, quiero que al pedir un asesor me transfieran (siempre) | P0 |
| E12-02 | Como sistema, quiero generar un resumen estructurado de transferencia | P0 |
| E12-03 | Como sistema, quiero elegir equipo o usuario destino según reglas, horario y carga | P0 |
| E12-04 | Como agente humano, quiero ver la solicitud de handoff destacada, aceptarla y continuar con todo el contexto | P0 |
| E12-05 | Como agente humano, quiero devolver la conversación a la IA | P0 |
| E12-06 | Como sistema, quiero hacer handoff por baja confianza, fallo de tool, presupuesto agotado, reclamo o kill switch | P0 |
| E12-07 | Como cliente fuera de horario, quiero que me avisen de cuándo me atenderán | P1 |

### E13 · Cotizaciones y ventas (Fase 5; envío por canal en la Fase 7)

| ID | Historia | Prio |
|---|---|---|
| E13-01 | Como vendedor, quiero crear una cotización desde contacto, lead u oportunidad con precios del motor (desde el Inbox: **Fase 6**) | P0 |
| E13-02 | Como vendedor, quiero aplicar descuentos dentro de mi límite; por encima, pedir aprobación | P0 |
| E13-03 | Como supervisor, quiero aprobar o rechazar cotizaciones pendientes con comentario | P0 |
| E13-04 | Como vendedor, quiero generar el PDF (Fase 5) y enviarlo por WhatsApp como documento o plantilla vía `MessagingPolicyService` (**Fase 7**) | P0 |
| E13-05 | Como sistema, quiero congelar el snapshot al emitir y crear revisiones ante cambios | P0 |
| E13-06 | Como sistema, quiero expirar cotizaciones vencidas | P0 |
| E13-07 | Como sistema, quiero crear un seguimiento a +24 h (tarea: Fase 5) cancelable si el cliente responde (**Fase 7**: requiere mensajes entrantes) | P0 |
| E13-08 | Como vendedor, quiero marcar la cotización como aceptada o rechazada y mover la oportunidad | P0 |
| E13-09 | Como sistema, quiero un enlace público de la cotización que registre VIEWED | P1 |
| E13-10 | Como vendedor, quiero registrar una venta directa (sin cotización) | P1 |
| E13-11 | Como Admin, quiero configurar métodos de pago, validez por defecto, términos y garantía de la plantilla | P0 |

### E14 · Notificaciones (desde la Fase 6, incremental)

| ID | Historia | Prio |
|---|---|---|
| E14-01 | Centro de notificaciones in-app con contador y leído/no leído | P0 |
| E14-02 | Tipos: nuevo chat, transferencia, handoff, tarea vencida, aprobación pendiente, reclamo, stock bajo, API con problema, webhook fallido | P0 (primeros 5), P1 (resto) |
| E14-03 | Preferencias por usuario (in-app, sonido, email) | P1 |
| E14-04 | Web push | P2 |

### E15 · Dashboards y reportes (básicos al cierre del MVP, Fase 10; avanzados en la Fase 14)

| ID | Historia | Prio |
|---|---|---|
| E15-01 | Dashboard general: conversaciones nuevas/pendientes, IA vs humanos, leads, oportunidades, ventas, cotizaciones, tiempo medio de respuesta, conversión | P0 |
| E15-02 | Dashboard administrativo: usuarios, conversaciones hoy, % IA automatizada, ventas hoy, estado de servicios, alertas | P0 |
| E15-03 | Gráficos: ventas y leads por canal, actividad IA, pipeline | P1 |
| E15-04 | Reportes de ventas, atención, marketing, pipeline e IA con filtros y exportación | P2 |

### E16 · Automatizaciones (Fase 11)

| ID | Historia | Prio |
|---|---|---|
| E16-01 | Como Admin, quiero crear reglas cuando/si/entonces con un constructor visual | P2 |
| E16-02 | Plantillas de reglas: lead sin respuesta 24 h → tarea; intención garantía → Postventa; cliente molesto → prioridad alta + supervisor; oportunidad estancada → tarea | P2 |
| E16-03 | Historial de ejecuciones y errores por regla | P2 |
| E16-04 | Protección anti-bucles (profundidad, cooldown, máximo por entidad) | P2 |

*Nota: las automatizaciones "fijas" del MVP (seguimiento +24 h, estancadas, SLA) se implementan como jobs configurables en las fases 5–7, no con el motor genérico.*

### E17 · Búsqueda global (Fase 10, cierre del MVP)

| ID | Historia | Prio |
|---|---|---|
| E17-01 | Búsqueda global (⌘K) por nombre, teléfono, email, @usuario, producto, SKU, oportunidad, cotización y conversación, respetando permisos | P1 |

### E18 · Instagram y Messenger (Fase 12) · E19 · TikTok (Fase 13)

| ID | Historia | Prio |
|---|---|---|
| E18-01 | Conectar una página de Facebook y una cuenta de IG (OAuth de Meta, permisos de app aprobados) | P2 |
| E18-02 | Recibir y enviar DMs, respetar la ventana de 24 h y la etiqueta HUMAN_AGENT | P2 |
| E18-03 | Sugerencia de fusión de identidades IG/FB ↔ WhatsApp | P2 |
| E18-04 | Respuestas a comentarios → DM (private replies) | P3 |
| E19-01 | Investigación de disponibilidad de la API de mensajería de TikTok en Perú + prueba de concepto | P2 |
| E19-02 | TikTokAdapter (si E19-01 es viable) | P3 |

### E20 · SaaS comercial y servicio técnico (Fase 14+)

| ID | Historia | Prio |
|---|---|---|
| E20-01 | Alta self-service de organizaciones, planes, límites por plan y facturación de suscripción | P3 |
| E20-02 | Módulo de servicio técnico: servicios por modelo de equipo, precio de servicio vía tool, órdenes de reparación y estados | P3 |
| E20-03 | Seriales/IMEI | P3 |
| E20-04 | Trade-in con tasación | P3 |

---

## S. Roadmap

> **Actualizado el 2026-09-28 (Fase 0.5).** Sustituye al roadmap anterior. Regla verificada: **ninguna fase usa entidades de una fase posterior, y ninguna tool de IA crea una entidad que no exista todavía.** Cada migración corresponde a funcionalidad real de su fase (el ERD de ~95 tablas es el mapa, no el plan de migraciones).

### S.1 Fases

| Fase | Nombre | Alcance | Tablas que crea (aprox.) | Criterio de salida (además del DoD §124) |
|---|---|---|---|---|
| **0** | Análisis | Documento A–U | — | ✅ Cerrada |
| **0.5** | Decisiones y scaffolding | ADRs, arquitectura, estructura del monorepo, compose base, CI de seguridad | — | ✅ Este PR |
| **1** | Infraestructura base | Backend y frontend esqueleto; `core` (tenancy, RLS, ids, sequences, outbox, storage, observabilidad, errores, http seguro); `audit`; `files`; health checks; CI backend/frontend; tenant de prueba mínimo (`organizations` platform-owned + tabla tenant de ejemplo solo en tests) | `organizations` (mínima), `org_sequences`, `outbox_events`, `audit_logs`, `files` | Suite de aislamiento T1–T13 en verde con el rol `crm_app`; CI completo; `docker compose up` funcional |
| **2** | Organizaciones, usuarios y RBAC | Auth por sesión, MFA (flag), usuarios, membresías, invitaciones, roles, permisos con scope, equipos, sucursales, horarios, auditoría de acceso; shell de UI con `/o/[slug]` | `users`, `user_mfa_devices`, `user_invitations`, `organization_memberships`, `branches`, `teams`, `team_members`, `work_schedules`, `permissions`, `roles`, `role_permissions`, `membership_roles` | Login + MFA + roles con scope; tests anti-escalada; auditoría de login y de roles |
| **3** | Catálogo, precios e inventario | Marcas, categorías, productos, opciones, variantes, alias; listas, precios con vigencia, costos, promociones, `PricingService`, edición masiva, historial; almacenes, stock, movimientos; importación Excel (P1) | catalog*, `price_lists`, `product_prices`, `variant_costs`, `promotions*`, `price_change_batches*`, `warehouses`, `inventory_levels`, `inventory_movements`, `discount_policies` | Motor de precios con cobertura alta en los bordes de vigencia; tests de concurrencia de stock; costos invisibles sin permiso |
| **4** | Contactos | Contactos, identidades, direcciones, etiquetas, notas, búsqueda, duplicados (P1), timeline base | contacts*, `tags`, `notes`, `contact_merge_candidates`, `timeline_events`, `data_provenance` | Contacto 360° base (resumen, notas, etiquetas); búsqueda por nombre, teléfono y email |
| **5** | Sales core básico | Leads (score explicable), pipelines y etapas, oportunidades (kanban y tabla), motivos de pérdida, tareas, cotizaciones (borrador, descuentos, aprobación, PDF, snapshot, revisiones, expiración), ventas (orders) y métodos de pago, reservas de stock (según D-INV-2) | `leads`, `lead_score_events`, `pipelines`, `pipeline_stages`, `opportunities*`, `lost_reasons`, `tasks`, `scheduled_actions`, `quotes`, `quote_items`, `quote_approvals`, `orders`, `order_items`, `payment_methods`, `inventory_reservations` | Flujo lead → oportunidad → cotización aprobada → ganada → venta, **sin canales** (el envío es manual o se descarga el PDF) |
| **6** | Inbox y mensajería | Canal Sandbox, conversaciones, mensajes, adjuntos, estados de entrega, asignación (`AssignmentService`, sin IA), historial `conversation_assignments`, notas internas, respuestas rápidas, tiempo real (WS), `MessagingPolicyService` (con capacidades del Sandbox), notificaciones; **vínculos** conversación ↔ lead/oportunidad/cotización (FKs añadidas en esta fase) | `channel_accounts`, `conversations`, `conversation_participants`, `conversation_assignments`, `conversation_status_history`, `conversation_tags`, `messages`, `message_attachments`, `message_status_events`, `quick_replies*`, `notifications*` | Inbox operativo en tiempo real con el Sandbox; notas blindadas; crear lead, oportunidad o cotización desde el Inbox |
| **7** | WhatsApp | Adapter WhatsApp Cloud API, credenciales cifradas, webhooks (ingesta, firma, idempotencia, reintentos), media al storage, plantillas y ventana de 24 h reales, envío de cotizaciones y seguimientos vía `MessagingPolicyService`, cancelación de seguimientos al responder el cliente | `credentials`, `webhook_ingress`, `webhook_failures`, `message_templates`, `sync_jobs` | Número real conectado; tests de firma, replay y duplicados; cotización enviada por plantilla fuera de la ventana |
| **8** | Infraestructura IA + tools de lectura seguras | Gateway (proveedores, cuentas, modelos, routing, fallback, presupuestos, uso), kill switch, agentes y versiones, prompts, **solo tools de lectura** (`search_product`, `get_product_variants`, `get_product_price`, `get_product_stock`, `get_active_promotions`, `get_current_customer`, `get_current_customer_history`), Output Guard, copiloto (sugerir, mejorar, resumir, consultar), modo **AI_ASSISTED y sombra únicamente** (sin envío autónomo) | `ai_provider_accounts`, `ai_account_models`, `ai_models`, `ai_model_prices`, `ai_agents`, `ai_agent_versions`, `ai_agent_model_configs`, `ai_agent_tools`, `ai_agent_channels`, `ai_agent_rules`, `ai_prompts`, `ai_intents`, `ai_sessions`, `ai_runs`, `ai_llm_calls`, `ai_actions`, `ai_suggestions`, `ai_feedback`, `ai_usage_daily`; columna `conversations.assigned_ai_agent_id` | Respuestas sugeridas con precio y stock evidenciados; Output Guard con 0 cifras sin evidencia en el conjunto de pruebas; fallback probado |
| **9** | Handoff + autonomía controlada | `handoff_to_human` (siempre habilitada), resúmenes de transferencia, cola humana, devolución a IA, detector de "quiero un humano", **habilitación de AI_AUTONOMOUS niveles 2–3 de solo lectura** (responder precio, stock y FAQ), base de conocimiento (pgvector) y memoria larga | `ai_handoffs`, `ai_summaries`, `kb_documents`, `kb_document_agents`, `kb_chunks` (+ extensión pgvector) | IA autónoma en lectura con handoff probado, kill switch y guardrails; piloto real |
| **10** | Acciones IA sobre entidades comerciales | Tools de escritura sobre entidades **ya existentes** (Fases 4–6): `create_lead`, `update_lead`, `create_task`, `add_customer_note`, `create_opportunity`, `create_quote_draft` (siempre con aprobación humana), extracción con `data_provenance`; dashboards básicos y búsqueda global; estabilización | (sin tablas nuevas de dominio; `search_documents`) | **MVP en producción** (flujo §125 completo) |
| **11** | Automatizaciones | Motor cuando/si/entonces, plantillas de reglas, anti-bucles | `automation_rules`, `automation_runs` | Reglas plantilla operativas |
| **12** | Instagram + Facebook | Adapters, OAuth de Meta, capacidades en `MessagingPolicyService`, sugerencia de fusión de identidades | — (usa las tablas de canales) | |
| **13** | TikTok | Condicionado a la investigación de viabilidad de la API | — | |
| **14** | Analytics y optimización | Reportes avanzados, vistas materializadas, evaluación de agentes, Supervisor IA, SaaS comercial (planes), servicio técnico, IMEI | `analytics`, … | |

`*` = incluye sus tablas hijas (p. ej., `promotions*` → `promotions`, `promotion_items`, `promotion_price_lists`).

### S.2 Matriz de dependencias de las tools de IA

| Tool | Entidad que lee o crea | Fase de la entidad | Fase de la tool | ¿OK? |
|---|---|---|---|---|
| `search_product`, `get_product_variants` | Catálogo | 3 | 8 | ✅ |
| `get_product_price`, `get_active_promotions` | Precios, promociones (`PricingService`) | 3 | 8 | ✅ |
| `get_product_stock` | Inventario | 3 | 8 | ✅ |
| `get_current_customer`, `get_current_customer_history` | Contactos, conversaciones | 4, 6 | 8 | ✅ |
| `search_knowledge_base` | Base de conocimiento | 9 | 9 | ✅ |
| `handoff_to_human` | Handoffs, asignación | 9, 6 | 9 | ✅ |
| `create_lead`, `update_lead` | Leads | 5 | 10 | ✅ |
| `create_task` | Tareas | 5 | 10 | ✅ |
| `add_customer_note` | Notas | 4 | 10 | ✅ |
| `create_opportunity` | Oportunidades | 5 | 10 | ✅ |
| `create_quote_draft` | Cotizaciones | 5 | 10 | ✅ |
| `get_order_status` (futuro) | Ventas (orders) | 5 | 10+ | ✅ |
| `get_repair_status` (futuro) | Servicio técnico | 14 | 14 | ✅ |

### S.3 Otras dependencias verificadas

| Dependencia | Resolución |
|---|---|
| Leads, oportunidades y cotizaciones (Fase 5) necesitan referenciar la conversación de origen (Fase 6) | Las columnas `conversation_id` se añaden **en la Fase 6** (nullable) |
| El seguimiento +24 h cancelable por respuesta del cliente necesita mensajes entrantes | La tarea programada existe en la Fase 5; la cancelación por evento `message.received` se conecta en la Fase 7 |
| La asignación a agentes IA necesita `ai_agents` | `assigned_ai_agent_id` y su CHECK se añaden en la Fase 8 (ADR-007) |
| El envío de cotizaciones necesita un canal y la política de mensajería | Fase 5: PDF y descarga; Fase 7: envío por WhatsApp |
| La IA autónoma necesita handoff y kill switch | Fase 8: solo asistida o sombra (kill switch incluido); Fase 9: autonomía de lectura con handoff |
| La base de conocimiento necesita pgvector | Se habilita la extensión en la Fase 9 (no antes) |
| Los webhooks de la Fase 7 necesitan un endpoint público | Hosting (D10-H) decidido antes del final de la Fase 6; mientras tanto, un túnel para pruebas |
| El RBAC de la Fase 2 necesita tenancy | Fase 1 (infraestructura base) |

### S.4 Estrategia de despliegue de la IA

1. **Sombra** (Fase 8): la IA genera respuestas que nadie ve; solo métricas.
2. **Asistida** (Fase 8): el humano aprueba cada envío.
3. **Autónoma de lectura, nivel 2–3** (Fase 9): precio, stock y FAQ con Output Guard y handoff.
4. **Acciones** (Fase 10): creación de lead, tarea, oportunidad y borrador de cotización.
5. Ampliación por métricas, nunca por fecha.

### S.5 Git

Ver **ADR-009** (GitHub Flow aprobado: `main` protegida, `feature/*`, `fix/*`, PR obligatorio, squash merge, tags SemVer).
