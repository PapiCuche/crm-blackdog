# ADR-004: UUIDv7 como identificador técnico y numeración comercial por organización

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-001, ADR-002, decisión D8

## Context

- Necesitamos identificadores técnicos globalmente únicos, no enumerables y eficientes en índices B-tree.
- Los usuarios necesitan identificadores legibles y **secuenciales por organización**: `COT-000001`, `OPP-000001`, `CONV-000001`.
- La numeración debe ser **segura ante concurrencia**: dos vendedores creando cotizaciones a la vez no pueden obtener el mismo número.

## Decision

### 1. Identificador técnico: UUIDv7

- Todas las PK son `uuid`, **generadas en la aplicación** (UUIDv7, RFC 9562), para que el ID exista antes del INSERT (útil en outbox, idempotencia y logs correlacionados).
- `DEFAULT uuidv7()` de PostgreSQL 18 como respaldo para inserts SQL directos (migraciones de datos, scripts).
- Generación en Python: el stdlib `uuid.uuid7()` si la versión de Python elegida lo incluye (3.14+), o una librería pequeña y mantenida si se fija 3.13. **Se decide en la Fase 1** junto con el pin de versiones (ver decisión D-ENG-1). La función se encapsula en `core.ids.new_id()` para no depender de la librería en el resto del código.
- Las URLs y las APIs exponen UUIDs, nunca IDs secuenciales internos.

### 2. Identificador comercial: `org_sequences`

```sql
CREATE TABLE org_sequences (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  sequence_key    text NOT NULL,          -- 'COT', 'OPP', 'CONV', 'VTA', 'LEAD'
  next_value      bigint NOT NULL,
  PRIMARY KEY (organization_id, sequence_key)
);  -- tenant-owned: RLS + FORCE
```

Asignación **en la misma transacción** que crea la entidad, en una sola sentencia atómica:

```sql
INSERT INTO org_sequences (organization_id, sequence_key, next_value)
VALUES (app_current_tenant(), 'COT', 2)
ON CONFLICT (organization_id, sequence_key)
DO UPDATE SET next_value = org_sequences.next_value + 1
RETURNING next_value - 1 AS allocated;
```

- El `ON CONFLICT DO UPDATE` bloquea la fila hasta el commit. Las transacciones concurrentes de **la misma organización y la misma clave** se serializan; las de otras organizaciones no se afectan.
- Si la transacción hace rollback, el incremento también se revierte → **numeración sin huecos** en condiciones normales.
- Formato: `f"{prefix}-{n:06d}"` → `COT-000001`. Al superar 999 999, crece a 7 dígitos (`COT-1000000`) sin romper nada. El prefijo es configurable por organización.
- Respaldo en BD: `UNIQUE (organization_id, number)` en cada tabla numerada.
- Los números son **inmutables** y nunca se reutilizan (tampoco tras un soft delete).
- Las revisiones de cotización comparten número y añaden `revision` (`COT-000123 v2`).
- Servicio: `core.sequences.allocate(ctx, key) -> str`. Falla si no se llama dentro de `transaction.atomic()`.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| `bigserial` como PK | Enumerable (IDOR más fácil), revela volumen de negocio y complica el merge de datos entre entornos |
| UUIDv4 | Aleatorio: fragmenta índices B-tree y no es ordenable por tiempo |
| ULID / KSUID | Equivalentes a UUIDv7, pero no nativos en PostgreSQL |
| Una `SEQUENCE` de PostgreSQL por organización y clave | No transaccional (deja huecos al hacer rollback) y crea miles de objetos DDL; el rol de la app necesitaría privilegios DDL |
| `MAX(number) + 1` | Race condition clásica |
| Advisory locks | Funciona, pero el upsert con bloqueo de fila es más simple y auto-documentado |

## Consequences

- Contención: la creación de cotizaciones de una misma organización se serializa durante la transacción que asigna el número. Con volúmenes de CRM (decenas o cientos por minuto) es irrelevante. **Regla:** asignar el número lo más tarde posible dentro de la transacción y mantenerla corta.
- Las entidades tienen dos identificadores: el UUID (técnico) y el número (humano). La búsqueda global indexa ambos.

## Security implications

- UUIDv7 no es enumerable en la práctica, pero **incluye el timestamp de creación** (precisión de milisegundos). Es aceptable: la fecha de creación no es secreta en este dominio. Los UUIDs **no** se usan como secretos: los enlaces públicos (cotización) usan tokens aleatorios de 256 bits almacenados como hash.
- Los números comerciales son enumerables por diseño: **nunca** autorizan nada. Buscar `COT-000123` requiere tenant y permisos como cualquier otra consulta.

## Operational implications

- Las migraciones de datos o importaciones que creen entidades numeradas deben usar `core.sequences.allocate`, nunca números manuales.
- Cambiar el prefijo de una organización solo afecta a los números nuevos.
