# ADR-006: PricingService como autoridad única de precios

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** `docs/fase-0/04-precios-pipeline-seguridad-infra.md` §K, ADR-005

## Context

- El prompt original modelaba la promoción dos veces: como `price_type` (§38) y como dominio `promotions` (§42). Dos fuentes de verdad producen precios contradictorios.
- La IA, las cotizaciones, los pedidos, la UI y los reportes necesitan **el mismo** precio para la misma pregunta.
- Las promociones deben empezar y terminar a su hora **aunque falle un job**.
- El costo nunca debe llegar a vendedores sin permiso, a agentes IA públicos ni a clientes.

## Decision

### 1. Modelo

| Tabla | Rol |
|---|---|
| `price_lists` | Listas base: Regular, Efectivo, Transferencia, Mayorista, Distribuidor, Interno. Atributos: `kind`, `currency`, `is_default`, `required_permission`, `ai_exposable`, `payment_condition`, `customer_segment` (tipo de cliente), `base_price_list_id` + `derived_adjustment_percent` |
| `product_prices` | Precio de una variante en una lista con vigencia `[starts_at, ends_at)`. `EXCLUDE USING gist` impide solapes. Cambiar un precio = cerrar el vigente + insertar uno nuevo (esta tabla **es** el historial) |
| `promotions` | Reglas: `discount_type` (FIXED_PRICE / PERCENT_OFF / AMOUNT_OFF), `value`, `starts_at`, `ends_at` NOT NULL, `status` (DRAFT/PUBLISHED/CANCELLED), `priority`, `stackable`, `channels`, `customer_segments`, `ai_exposable` |
| `promotion_items` | Objetivo: variante, producto, categoría o marca (exactamente uno) + `override_value` opcional |
| `promotion_price_lists` | Listas sobre las que aplica la promoción |
| `variant_costs` | Costo, **separado**; solo accesible mediante `CostService` con `product_cost.view` |

**"Promoción" no existe como tipo de precio ni como lista.**

### 2. `PricingService`: única autoridad

```text
PricingService.resolve(ctx, PriceQuery) -> PriceResolution

PriceQuery(variant_id, price_list_code=None, channel=None, customer_segment=None,
           quantity=1, at=None)   # at=None → now() de la transacción

Pasos:
 1. Organización: la del ctx (tenant_scope activo).
 2. Variante: existe, ACTIVE; si el actor es un agente PUBLIC → ai_visible.
 3. Lista: la indicada o la default para (currency, customer_segment).
    Permiso: actor humano → required_permission; agente PUBLIC → ai_exposable.
 4. Precio base vigente en `at`: product_prices [starts_at, ends_at).
    Si no existe y la lista es derivada → base de la lista padre × ajuste + redondeo.
    Si no hay precio → PriceResolution(found=False, reason=NO_PRICE). Nunca se estima.
 5. Promociones candidatas: PUBLISHED, now() ∈ [starts_at, ends_at), que aplican a la lista,
    al canal, al segmento y al objetivo (variant > product > category > brand).
 6. Selección: la de mayor priority; si empatan, la de menor precio final; no apilables en el MVP.
 7. Redondeo según la regla de la organización.
 8. PriceResolution{found, variant, list, currency, tax_included, base_amount, promotion?,
    final_amount, savings, valid_until = min(ends_at precio, ends_at promoción),
    price_id, promotion_id, resolved_at, evidence_kind=PRICE}
```

- **Vigencia por timestamps en el momento del cálculo.** No existe un cron que "active" o "desactive" promociones o precios. Los jobs auxiliares solo **notifican** ("la promoción X empezó") e **invalidan caché**. Si fallan, los precios siguen siendo correctos.
- **Todo** consumidor pasa por `PricingService`: la API de precios, `QuoteService` (que congela la `PriceResolution` en `quote_items`), `OrderService`, la tool `get_product_price` (su output es la `PriceResolution` redactada y sirve de evidencia para ADR-005) y los reportes de lista de precios. Import-linter prohíbe leer `product_prices` o `promotions` fuera del módulo `pricing`.
- `CostService` es independiente. `PricingService` **no** lee costos. La comparación "precio por debajo del costo" en la edición masiva la hace la capa de UI/servicio solo si el actor tiene `product_cost.view`.

### 3. Cambios y trazabilidad

- `PriceChangeService.set_price(ctx, variant, list, amount, starts_at, reason)` en una transacción: bloquea el precio vigente, cierra su vigencia, inserta el nuevo, registra auditoría y emite el evento `price.changed`.
- La edición masiva y la importación usan `price_change_batches` (preview → confirmar → aplicar) y llaman al mismo `set_price`.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| `product.price` | Sin historial, sin listas ni vigencias |
| Promoción como `price_type` en `product_prices` | Duplica el dominio de promociones; no admite reglas por categoría o marca ni porcentajes |
| Cron que escribe el precio promocional al inicio y lo restaura al final | Si el job falla o se retrasa, se venden productos a un precio incorrecto; estado mutable difícil de auditar |
| Calcular el precio en el frontend | Duplica lógica y expone reglas |

## Consequences

- Cada consulta de precio ejecuta 2–3 queries indexadas. Si las métricas lo justifican, se añade una caché con TTL acotado al siguiente cambio de vigencia.
- La restricción EXCLUDE requiere la extensión `btree_gist` (se habilita en la fase de catálogo y precios).
- Los tests del motor son de la máxima prioridad: vigencias en los bordes (`starts_at` inclusivo, `ends_at` exclusivo), zonas horarias, solapes, promociones por nivel, permisos de lista, IA frente a humano, redondeo.

## Security implications

- Los costos están aislados físicamente (tabla y servicio distintos). Hay tests que verifican que ninguna respuesta de la API pública de precios ni de las tools IA contiene campos de costo.
- La visibilidad de las listas se controla por permiso (humanos) o por `ai_exposable` (IA pública).
- Los cambios de precio se auditan con el valor anterior, el nuevo, el usuario y el motivo.

## Operational implications

- La UI muestra "precio vigente" y "próximo cambio programado".
- Las alertas de "promoción que empieza o termina en 24 h" son notificaciones, no mecanismos de cambio.
- Toda cotización o pedido guarda `price_id` y `promotion_id` en el snapshot para reconstruir el cálculo.
