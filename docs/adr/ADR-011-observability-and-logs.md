# ADR-011: Observabilidad y separación de logs de aplicación, auditoría y acciones de IA

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-005 §E, `docs/fase-0/04-precios-pipeline-seguridad-infra.md` §N

## Context

Se necesitan desde la base: logging estructurado, IDs de correlación, reporte de errores (Sentry o equivalente), health checks y eventos de auditoría. Además, se exige **no mezclar** tres conceptos con audiencias, retención y garantías distintas: log de aplicación, log de seguridad/auditoría y log de acciones de IA.

## Decision

### 1. Tres registros, tres propósitos

| | **Application log** | **Security / audit log** | **AI action log** |
|---|---|---|---|
| Pregunta que responde | ¿Qué hizo el sistema técnicamente y por qué falló? | ¿Quién hizo qué sobre qué, cuándo y con qué resultado? | ¿Qué decidió la IA, con qué contexto, qué tools usó y cuánto costó? |
| Destino | stdout JSON → agregador (Loki, CloudWatch, Better Stack…); errores → Sentry | Tabla `audit_logs` (PostgreSQL, append-only, RLS) | Tablas `ai_runs`, `ai_llm_calls`, `ai_actions` (append-only, RLS) |
| Audiencia | Ingeniería / operación | Owner, Admin con `audit.view`, cumplimiento | Supervisores de IA, Admin, ingeniería |
| Retención | 14–30 días | ≥ 2 años (configurable) | 12 meses detalle; agregados indefinidos |
| Garantía | Best effort | **Transaccional**: se escribe en la misma transacción que el cambio | Transaccional con la acción; las llamadas LLM se registran incluso si fallan |
| PII | Mínima: IDs, no contenidos | Solo la necesaria (actor, entidad, cambios redactados) | Argumentos y resultados **redactados**; sin secretos ni costos |
| Mutabilidad | N/A | Sin UPDATE/DELETE para `crm_app` | Sin UPDATE/DELETE para `crm_app` |

**Reglas:** el log de aplicación **no** es un sustituto de la auditoría (puede perderse); la auditoría **no** guarda trazas técnicas; las acciones de IA **no** van al log de aplicación salvo como referencia (`ai_run_id`). Los tres comparten `correlation_id` para poder cruzarse.

### 2. Correlación

- `request_id`: generado en el proxy o en el middleware (UUIDv7), devuelto en la cabecera `X-Request-ID`.
- `correlation_id`: se propaga por HTTP → outbox → headers de Celery → WS → llamadas a proveedores. Se guarda en `audit_logs`, `ai_runs`, `webhook_ingress` y `outbox_events`.
- Implementación: `contextvars` + structlog (procesadores que añaden `request_id`, `correlation_id`, `organization_id`, `user_id`, `actor_type`), y señales de Celery para propagarlos.

### 3. Errores: interfaz `ErrorReporter`

`core.observability.ErrorReporter` con dos implementaciones: `SentryReporter` y `NoopReporter` (local o sin DSN). El código de dominio nunca importa `sentry_sdk` directamente. Scrubbing obligatorio: cabeceras `Authorization` y `Cookie`, campos `password`, `api_key`, `secret`, `token`, patrones de API keys y cuerpos de mensajes de clientes.

### 4. Health checks

| Endpoint | Qué verifica | Uso |
|---|---|---|
| `GET /health/live` | El proceso responde (sin dependencias) | Liveness |
| `GET /health/ready` | BD (`SELECT 1` con `crm_app`), Redis, storage (`head` del bucket) | Readiness / balanceador |
| `service_health_checks` (tabla, Fase 2+) | Workers, lag de colas, canales, cuentas de IA | Panel "Estado de servicios" |

Los endpoints de salud no exponen versiones, hosts ni errores detallados (solo `ok`/`fail` por componente).

### 5. Métricas

La Fase 1 deja preparada la instrumentación (middleware de latencia por ruta, tiempos de tareas Celery). La exportación a Prometheus/Grafana o a un APM se decide junto con el hosting. Métricas clave futuras: latencia p95 de la API, lag de colas, lag de webhooks, envíos fallidos, latencia y coste de IA, bloqueos del Output Guard.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Un único log para todo | Mezcla audiencias y retenciones; la auditoría quedaría best effort |
| Auditoría mediante triggers genéricos de BD | Captura cambios de columnas, pero no la intención (motivo, actor IA, contexto). Puede complementar en el futuro para tablas muy sensibles |
| Auditoría en un servicio externo desde el inicio | Coste y complejidad; la tabla particionada basta para el MVP |

## Consequences

- `audit.record(ctx, action, entity, changes, metadata)` es obligatorio en los servicios que cambian datos importantes (checklist de PR y tests).
- Particionamiento mensual de `audit_logs` y de las tablas de IA desde su creación.

## Security implications

- Auditoría inmutable para `crm_app`. Los accesos denegados también se auditan (`result = DENIED`).
- Nunca registrar secretos. El redactor es compartido por los tres registros y tiene tests con ejemplos de keys de OpenAI, Anthropic y Meta.
- El acceso al log de auditoría es un permiso sensible.

## Operational implications

- Runbook: cómo seguir una petición de punta a punta con `correlation_id` (log de aplicación → auditoría → IA).
- Alertas mínimas antes de producción: tasa de errores 5xx, workers caídos, lag de webhooks y fallos del health check.
