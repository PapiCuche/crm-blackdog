# R–S · Backlog y roadmap

**Prioridades:** **P0** = imprescindible para el MVP · **P1** = MVP deseable (entra si no pone en riesgo P0; si no, justo después) · **P2** = post-MVP · **P3** = futuro.
**Fase** = fase del roadmap propuesto (sección S), no la del prompt original.

---

## R. Backlog

### E00 · Fundaciones técnicas (Fase 0.5)

| ID | Feature / Historia | Prio | Fase |
|---|---|---|---|
| E00-01 | Monorepo (`backend/`, `frontend/`, `infra/`, `docs/`) con docker-compose (Postgres + pgvector, Redis ×3 lógicas, MinIO, Mailpit) | P0 | 0.5 |
| E00-02 | Settings por entorno (12-factor), validación de settings críticos en el arranque (`DEBUG`, claves, hosts) | P0 | 0.5 |
| E00-03 | CI: ruff, mypy (django-stubs), pytest con cobertura, import-linter, eslint, tsc, `pip-audit`/`pnpm audit`, build de Next.js, verificación del contrato OpenAPI | P0 | 0.5 |
| E00-04 | `core`: `TenantModel`, `SoftDeleteModel`, `ExecutionContext`, `Money`, errores de dominio, `org_sequences` | P0 | 0.5 |
| E00-05 | Tenancy: middleware, contextvar, `SET LOCAL`, políticas RLS vía migración genérica, roles de BD, `@tenant_task` | P0 | 0.5 |
| E00-06 | Outbox + publisher + registro de handlers de eventos | P0 | 0.5 |
| E00-07 | `audit` con `audit.record(ctx, action, entity, changes)` y redactor | P0 | 0.5 |
| E00-08 | Observabilidad base: logs JSON con `request_id`/`correlation_id`, Sentry (backend/frontend/Celery) con scrubbing, `/health` y `/ready` | P0 | 0.5 |
| E00-09 | API: DRF + drf-spectacular + cliente TS generado (orval) + convención de errores (`{code, message, fields}`) + paginación por cursor | P0 | 0.5 |
| E00-10 | Frontend shell: layout, navegación del §8, tema (design tokens), tabla/formularios base, manejo de errores y toasts, i18n preparado (es-PE) | P0 | 0.5 |
| E00-11 | Test harness: factories (factory_boy), fixtures de dos organizaciones, **suite automática de aislamiento cruzado** | P0 | 0.5 |
| E00-12 | ADRs iniciales (una por cada decisión de U cerrada) | P0 | 0.5 |

### E01 · Identidad, organizaciones y acceso (Fase 1)

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

### E02 · Catálogo (Fase 2)

| ID | Historia | Prio |
|---|---|---|
| E02-01 | Como gestor de productos, quiero administrar marcas y categorías (árbol) | P0 |
| E02-02 | Como gestor, quiero crear un producto con opciones (capacidad, color, condición) y generar sus variantes | P0 |
| E02-03 | Como gestor, quiero editar SKU, estado y visibilidad para la IA por variante | P0 |
| E02-04 | Como gestor, quiero añadir alias de búsqueda ("16 pro max", "ip16pm") para que vendedores e IA encuentren el producto | P0 |
| E02-05 | Como gestor, quiero subir fotos por producto o variante | P1 |
| E02-06 | Como gestor, quiero registrar servicios técnicos (producto SERVICE con variantes por equipo y calidad) sin stock | P2 |
| E02-07 | Como Admin, quiero una papelera para restaurar productos eliminados | P1 |

### E03 · Precios (Fase 2)

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

### E04 · Inventario (Fase 2)

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

### E05 · Contactos (Fase 3)

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

### E06 · Inbox (Fase 4)

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

### E07 · WhatsApp (Fase 5)

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

### E08 · Gateway de IA (Fase 6)

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

### E09 · Leads, pipeline y oportunidades (Fase 7, adelantada)

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
| E09-12 | Como vendedor, quiero ver en el Inbox el lead y la oportunidad vinculados y crearlos con un clic | P0 |

### E10 · Tareas (Fase 7)

| ID | Historia | Prio |
|---|---|---|
| E10-01 | Como vendedor, quiero crear tareas (tipo, fecha y hora, descripción) vinculadas a contacto, oportunidad o cotización | P0 |
| E10-02 | Como vendedor, quiero ver mis tareas de hoy, vencidas y próximas | P0 |
| E10-03 | Como responsable, quiero recibir un recordatorio y una notificación al vencer | P0 |
| E10-04 | Como supervisor, quiero reasignar tareas | P1 |

### E11 · Agentes IA (Fase 8)

| ID | Historia | Prio |
|---|---|---|
| E11-01 | Como Admin, quiero crear un agente (nombre, rol, objetivo, tono, prompt, canales, horario, autonomía, umbrales, límites) | P0 |
| E11-02 | Como Admin, quiero elegir cuenta y modelo principal más fallbacks por agente | P0 |
| E11-03 | Como Admin, quiero habilitar tools por agente respetando las restricciones de agentes públicos | P0 |
| E11-04 | Como Admin, quiero publicar versiones del agente y revertir a una anterior | P0 |
| E11-05 | Como sistema, quiero un orquestador con debounce, lock por conversación, tool loop y guardrails | P0 |
| E11-06 | Como cliente, quiero preguntar por un producto y recibir el precio y stock exactos (con aclaración de variante si hace falta) | P0 |
| E11-07 | Como sistema, quiero bloquear respuestas con cifras que no vengan de tools | P0 |
| E11-08 | Como sistema, quiero detectar intención, sentimiento y la petición de humano | P0 |
| E11-09 | Como sistema, quiero que la IA cree y actualice leads con datos extraídos marcados AI_EXTRACTION | P0 |
| E11-10 | Como Admin, quiero una base de conocimiento (documentos publicados, embeddings, asignación a agentes) | P0 |
| E11-11 | Como sistema, quiero memoria corta y larga (resúmenes) | P0 |
| E11-12 | Como agente humano, quiero el copiloto: sugerir y mejorar respuesta, resumir, identificar qué quiere el cliente, consultar precio y stock, crear seguimiento, lead y oportunidad | P0 (sugerir/resumir/consultar), P1 (resto) |
| E11-13 | Como agente humano en modo AI_ASSISTED, quiero aprobar, editar o rechazar la sugerencia | P0 |
| E11-14 | Como supervisor, quiero ver las conversaciones de IA con sus tool calls, decisiones y costes | P0 |
| E11-15 | Como agente humano, quiero dar feedback (👍/👎 + categoría) a una respuesta de IA | P1 |
| E11-16 | Como Admin, quiero métricas de IA (resueltas, transferencias, tiempos, leads, cotizaciones, tokens, coste por conversación) | P1 |
| E11-17 | Como sistema, quiero que la IA cree oportunidades y borradores de cotización (nivel 4) | P1 |
| E11-18 | Como Admin, quiero ejecutar un conjunto de evaluación antes de publicar una versión | P2 |
| E11-19 | Supervisor IA (reglas deterministas): lead caliente sin seguimiento, cotización sin seguimiento, vendedor saturado | P2 |

### E12 · Handoff IA ↔ humano (Fase 8, junto con la IA)

| ID | Historia | Prio |
|---|---|---|
| E12-01 | Como cliente, quiero que al pedir un asesor me transfieran (siempre) | P0 |
| E12-02 | Como sistema, quiero generar un resumen estructurado de transferencia | P0 |
| E12-03 | Como sistema, quiero elegir equipo o usuario destino según reglas, horario y carga | P0 |
| E12-04 | Como agente humano, quiero ver la solicitud de handoff destacada, aceptarla y continuar con todo el contexto | P0 |
| E12-05 | Como agente humano, quiero devolver la conversación a la IA | P0 |
| E12-06 | Como sistema, quiero hacer handoff por baja confianza, fallo de tool, presupuesto agotado, reclamo o kill switch | P0 |
| E12-07 | Como cliente fuera de horario, quiero que me avisen de cuándo me atenderán | P1 |

### E13 · Cotizaciones y ventas (Fase 9)

| ID | Historia | Prio |
|---|---|---|
| E13-01 | Como vendedor, quiero crear una cotización desde el Inbox, contacto, lead u oportunidad con precios del motor | P0 |
| E13-02 | Como vendedor, quiero aplicar descuentos dentro de mi límite; por encima, pedir aprobación | P0 |
| E13-03 | Como supervisor, quiero aprobar o rechazar cotizaciones pendientes con comentario | P0 |
| E13-04 | Como vendedor, quiero generar el PDF y enviarlo por WhatsApp (documento o plantilla) | P0 |
| E13-05 | Como sistema, quiero congelar el snapshot al emitir y crear revisiones ante cambios | P0 |
| E13-06 | Como sistema, quiero expirar cotizaciones vencidas | P0 |
| E13-07 | Como sistema, quiero crear un seguimiento a +24 h cancelable si el cliente responde | P0 |
| E13-08 | Como vendedor, quiero marcar la cotización como aceptada o rechazada y mover la oportunidad | P0 |
| E13-09 | Como sistema, quiero un enlace público de la cotización que registre VIEWED | P1 |
| E13-10 | Como vendedor, quiero registrar una venta directa (sin cotización) | P1 |
| E13-11 | Como Admin, quiero configurar métodos de pago, validez por defecto, términos y garantía de la plantilla | P0 |

### E14 · Notificaciones (Fases 4–9, incremental)

| ID | Historia | Prio |
|---|---|---|
| E14-01 | Centro de notificaciones in-app con contador y leído/no leído | P0 |
| E14-02 | Tipos: nuevo chat, transferencia, handoff, tarea vencida, aprobación pendiente, reclamo, stock bajo, API con problema, webhook fallido | P0 (primeros 5), P1 (resto) |
| E14-03 | Preferencias por usuario (in-app, sonido, email) | P1 |
| E14-04 | Web push | P2 |

### E15 · Dashboards y reportes (MVP básico en Fase 10; avanzados en Fase 14)

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

*Nota: las automatizaciones "fijas" del MVP (seguimiento +24 h, estancadas, SLA) se implementan como jobs configurables en las fases 7–9, no con el motor genérico.*

### E17 · Búsqueda global (Fase 10)

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

### Cambios respecto al orden del §103 (y por qué)

| Cambio | Motivo |
|---|---|
| **Nueva Fase 0.5 "Fundaciones"** | Tenancy + RLS, outbox, auditoría, CI, contrato de API y shell de UI son transversales. Si se hacen "de paso" en la Fase 1, se hacen mal |
| **Leads/pipeline/oportunidades/tareas pasan de la Fase 9 a la 7** (antes de agentes IA) | Las tools `create_lead`, `create_opportunity` y `create_task` (§58) los necesitan. En el orden original, la IA de la Fase 7 no tendría dónde escribir |
| **El handoff (Fase 8) se fusiona con agentes IA** | No debe existir ni un día en producción una IA autónoma sin handoff ni kill switch |
| **Canal Sandbox en la Fase 4** | Permite construir y probar el Inbox y la IA sin depender de Meta (la verificación de negocio y la configuración pueden tardar semanas) |
| **Dashboards básicos dentro del MVP** | El §9–10 los pide; con los datos ya existentes son baratos |
| **Trámites de Meta en paralelo desde ya** | Verificación de Business Manager, número, nombre visible y, más adelante, App Review para IG/Messenger. Es tiempo de calendario, no de desarrollo |

### Fases

| Fase | Objetivo | Entregables clave | Criterio de salida (además del DoD §124) |
|---|---|---|---|
| **0** | Arquitectura cerrada | Este documento + decisiones U cerradas + ADRs + wireframes de Inbox, Pipeline y Admin IA | Decisiones bloqueantes resueltas |
| **0.5** | Fundaciones técnicas | E00 completa | CI verde; la suite de aislamiento corre (aunque haya pocas rutas); RLS verificada |
| **1** | Identidad y acceso | E01 (P0) | Login + MFA + roles con alcance; tests de escalada de privilegios |
| **2** | Catálogo, precios y stock | E02, E03, E04 (P0) | Motor de precios con ≥ 95 % de cobertura; tests de concurrencia de stock |
| **3** | Contactos | E05 (P0) | Contacto 360° base; búsqueda |
| **4** | Inbox + tiempo real + Sandbox | E06 (P0), E14-01/02 | Chat funcional en tiempo real con el canal Sandbox; notas blindadas (tests) |
| **5** | WhatsApp | E07 (P0) | Número real conectado; tests de idempotencia y firma; plantillas |
| **6** | Gateway IA | E08 | Dos proveedores, fallback probado con fallos simulados, presupuestos, kill switch |
| **7** | Leads, pipeline, oportunidades, tareas | E09, E10 (P0) | Kanban operativo; ganado crea venta; tests de conversión |
| **8** | Agentes IA + handoff | E11 (P0), E12 (P0) | **Piloto interno**: IA en modo AI_ASSISTED con un número de prueba; guardrail de cifras con 0 fugas en el conjunto de pruebas |
| **9** | Cotizaciones, aprobaciones, seguimientos, ventas | E13 (P0) | Flujo §125 completo de punta a punta |
| **10** | Estabilización del MVP | E15 (P0), E17, P1 críticos, endurecimiento de seguridad, runbooks, backups probados | **MVP en producción** con la primera organización real; IA autónoma nivel 2–3 habilitada gradualmente |
| **11** | Automatizaciones | E16 | Reglas plantilla operativas |
| **12** | Instagram + Messenger | E18 | |
| **13** | TikTok | E19 (condicionado a la viabilidad) | |
| **14** | Reportes avanzados, optimización, SaaS comercial, servicio técnico | E15-04, E20 | |

### Estrategia de despliegue de la IA (dentro de las fases 8 y 10)

1. **Sombra:** la IA genera respuestas que nadie ve; se comparan con las de los humanos (solo métricas).
2. **Asistida (nivel 1):** el humano aprueba cada envío. Se miden la tasa de aceptación sin edición y el feedback.
3. **FAQ autónoma (nivel 2)** solo para intents en lista blanca.
4. **Autónoma limitada (nivel 3)** en horario valle o para un porcentaje de conversaciones.
5. Ampliación por métricas, nunca por fecha.

### Estrategia de Git [RECOMENDACIÓN, D9]

Para un equipo pequeño recomiendo **trunk-based con ramas cortas (GitHub Flow)** en lugar de GitFlow:

- `main` siempre desplegable y protegida (PR + CI verde + revisión).
- Ramas `feat/<modulo>-<desc>`, `fix/...`, `chore/...`, `docs/...` de vida corta (≤ 3 días).
- Despliegue a *staging* automático desde `main`; a producción mediante **tag** `vX.Y.Z` (release). Un hotfix es una rama desde `main` + tag de parche.
- Las funcionalidades incompletas se ocultan con **feature flags por organización** (tabla simple o `django-waffle`), no con ramas largas.
- Motivo: `develop` en GitFlow duplica la integración, genera merges dolorosos y no aporta nada si hay CI y flags. **Si prefieres GitFlow (`main`/`develop`) funciona igual**, pero es más ceremonia.
- Commits: Conventional Commits (`feat(pricing): add price resolution engine`), tal como propones ✅. Squash-merge de PRs.
