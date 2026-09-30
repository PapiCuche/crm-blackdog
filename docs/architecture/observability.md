# Observabilidad de aplicación (F1-07)

**Relacionado:** ADR-011, ADR-012, [tenancy-context.md](tenancy-context.md), [outbox-audit.md](outbox-audit.md)
**Estado:** implementado en F1-07 (#9)

## Tres registros distintos

`application log` ≠ `audit_logs` ≠ `AI action log` (Fase 8).

- **Application log** (este documento): JSON técnico en stdout para operar el sistema. Es efímero y **no es evidencia**.
- **`audit_logs`** (F1-06): evidencia inmutable en PostgreSQL, escrita en la transacción del cambio.
- Ningún log técnico se guarda en PostgreSQL, y Sentry no es auditoría.

## Flujo de correlación

```text
Petición HTTP
  → RequestContextMiddleware: request_id = new_id() (UUIDv7); correlation_id = request_id
  → TenantResolutionMiddleware: TenantContext.correlation_id = correlation_id actual
  → outbox.emit / audit.record: heredan ctx.correlation_id
  → apply_async: before_task_publish añade la cabecera crm_correlation_id
  → worker: task_prerun fija correlation_id (request_id = None); task_postrun lo restaura
  → @tenant_task: TenantContext.correlation_id = kwarg explícito o el de la cabecera; ese valor
    también rige los logs y las tareas hijas durante la tarea
```

- **Cabeceras entrantes:** `X-Request-ID` y `X-Correlation-ID` **se ignoran** en la Fase 1 (OBS-F1-07-1). La respuesta devuelve `X-Request-ID` con el UUIDv7 generado.
- **Nombre de la cabecera:** `crm_correlation_id`, porque Celery ya usa `correlation_id` en las propiedades del mensaje para el id de la tarea. El `request_id` no viaja a los workers.
- **Fuente de verdad:** los ContextVars propios de `core.observability.context`. structlog solo los lee.

## Pipeline de logs

```text
contexto → nivel/logger → timestamp UTC → IDs (request, correlation, organization, user, actor)
→ excepción como texto → REDACCIÓN (core.redaction) → JSON → stdout
```

- Es el mismo pipeline para structlog y para el `logging` estándar: Django, Celery y librerías pasan por `ProcessorFormatter` en el handler de LOGGING.
  - Los argumentos posicionales (`%s`) se redactan **antes** de interpolar, así un dict conserva sus reglas por clave.
  - Los objetos no serializables (excepciones, modelos) se convierten a texto redactado.
- Celery no instala su propio logging (receptor de `setup_logging`). Los loggers de uvicorn se reencaminan al handler JSON, y `celery.app.trace` queda en WARNING porque su INFO incluye el `repr` del resultado.
- `str(excepción)` se redacta: el traceback se convierte en texto antes del redactor.
- **Log de petición:** `http.request.completed` (`http.request.failed` si el estado es 5xx, sin traceback, porque `django.request` ya lo registra). Solo método, ruta sin query, estado, `duration_ms` y los IDs de tenant/actor. Nunca cuerpos, query string, cookies ni cabeceras.
- **Celery:** `celery.task.failed` con `task_name`, `task_id` y `exception_type`. Nunca args ni kwargs.

## Reporte de errores

- `core.observability.reporting.reporter()` devuelve `NoopReporter` si no hay `SENTRY_DSN`: sin inicialización ni red.
- Con `SENTRY_DSN` devuelve `SentryReporter`: `send_default_pii=False`, `traces_sample_rate=0`, sin profiling, `include_local_variables=False`, `max_request_body_size="never"`, `auto_enabling_integrations=False`.
  - Integraciones: Django y Celery para los errores no controlados. `LoggingIntegration` no crea eventos ni breadcrumbs, para evitar la doble captura.
- `before_send = scrub_sentry_event` siempre:
  - elimina cuerpo, cookies y query string, y deja solo las cabeceras `host`, `user-agent`, `content-type`, `content-length` y `accept` (allowlist);
  - reduce `user` a `id`;
  - elimina las variables locales;
  - redacta los mensajes de excepción;
  - pasa todo el evento por `core.redaction.redact`;
  - añade solo los tags `request_id`, `correlation_id`, `organization_id`, `user_id` y `actor_type`.
- `sentry_sdk` solo se importa en `core.observability`: lo impone un contrato `protected` de import-linter.
- Las capturas explícitas pasan por `ErrorReporter`.

## Fuera de alcance

Prometheus, Grafana, OpenTelemetry, APM y traces; logs de IA (Fase 8); nuevos health checks.
