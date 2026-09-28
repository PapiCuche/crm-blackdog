# Architecture Decision Records (ADR)

Registro formal de las decisiones de arquitectura. Cada ADR es **inmutable una vez aceptado**: para cambiar una decisión, se crea un ADR nuevo que la reemplaza (`Superseded by ADR-0XX`) y se actualiza el estado del anterior.

## Índice

| ADR | Título | Estado | Fecha |
|---|---|---|---|
| [ADR-001](ADR-001-multi-tenancy.md) | Multi-tenancy con base de datos y esquema compartidos | Accepted | 2026-09-28 |
| [ADR-002](ADR-002-postgresql-rls.md) | PostgreSQL Row Level Security como defensa en profundidad | Accepted | 2026-09-28 |
| [ADR-003](ADR-003-auth-session.md) | Autenticación por sesión con cookie HttpOnly y MFA | Accepted | 2026-09-28 |
| [ADR-004](ADR-004-identifiers.md) | UUIDv7 y numeración comercial por organización | Accepted | 2026-09-28 |
| [ADR-005](ADR-005-ai-provider-abstraction.md) | Abstracción de proveedores de IA, tools y validación de salida | Accepted | 2026-09-28 |
| [ADR-006](ADR-006-pricing-engine.md) | PricingService como autoridad única de precios | Accepted | 2026-09-28 |
| [ADR-007](ADR-007-conversation-assignment.md) | Modelo de asignación de conversaciones con FKs explícitas | Accepted | 2026-09-28 |
| [ADR-008](ADR-008-object-storage.md) | Almacenamiento de objetos S3-compatible | Accepted | 2026-09-28 |
| [ADR-009](ADR-009-git-strategy.md) | GitHub Flow | Accepted | 2026-09-28 |
| [ADR-010](ADR-010-messaging-policy.md) | MessagingPolicyService, ventana de atención y plantillas | Accepted | 2026-09-28 |
| [ADR-011](ADR-011-observability-and-logs.md) | Observabilidad y separación de logs (aplicación / auditoría / IA) | Accepted | 2026-09-28 |

## Plantilla

```markdown
# ADR-0XX: Título

- **Status:** Proposed | Accepted | Deprecated | Superseded by ADR-0YY
- **Date:** YYYY-MM-DD
- **Deciders:** …
- **Related:** …

## Context
## Decision
## Alternatives considered
## Consequences
## Security implications
## Operational implications
```

## Estados

- **Proposed:** en discusión, no se implementa.
- **Accepted:** vigente; el código debe cumplirla.
- **Deprecated:** ya no aplica para código nuevo.
- **Superseded:** reemplazada por otro ADR (enlazado).
