# Fase 0 — Análisis de arquitectura del CRM omnicanal + AI Workforce

Fecha: 2026-09-28 · Estado: **APROBADO con cambios** (Fase 0.5). Las decisiones formales están en [docs/adr/](../adr/README.md) y los documentos vivos de arquitectura en [docs/architecture/](../architecture/). Si hay contradicción, prevalecen los ADR.

Este directorio contiene la respuesta a los apartados A–U del prompt maestro.
Se divide en archivos para poder versionarlos y revisarlos por separado.

| Archivo | Apartados | Contenido |
|---|---|---|
| [01-vision-y-arquitectura.md](01-vision-y-arquitectura.md) | A, B, C, D | Resumen ejecutivo, evaluación del stack, dominios (bounded contexts), diagrama de arquitectura |
| [02-modelo-de-datos.md](02-modelo-de-datos.md) | E, F | Tablas definitivas por dominio, campos, claves, relaciones, ERD textual |
| [03-tenancy-rbac-inbox-ia.md](03-tenancy-rbac-inbox-ia.md) | G, H, I, J | Multi-tenancy, RBAC, modelo del Inbox, arquitectura de IA |
| [04-precios-pipeline-seguridad-infra.md](04-precios-pipeline-seguridad-infra.md) | K, L, M, N, O, P, Q | Precios, pipeline comercial, amenazas, auditoría, Celery, WebSockets, webhooks |
| [05-backlog-y-roadmap.md](05-backlog-y-roadmap.md) | R, S | Épicas, features, historias, prioridades, fases |
| [06-riesgos-y-decisiones.md](06-riesgos-y-decisiones.md) | T, U | Riesgos con mitigación, inconsistencias detectadas, decisiones pendientes |

## Convenciones del documento

- **[REQUISITO]**: lo que el prompt maestro define explícitamente.
- **[RECOMENDACIÓN]**: propuesta técnica mía. Requiere tu validación.
- **[INCONSISTENCIA]**: dos requisitos que chocan o dejan un hueco.
- **[DECISIÓN Dxx]**: remite a la lista del apartado U.

## Las 6 correcciones más importantes que propongo

1. **Asignación con FKs reales, no polimórfica.** El diseño original (tipo + ID genérico) no permite integridad referencial. Aprobado en ADR-007: `assigned_team_id`, `assigned_user_id` y `assigned_ai_agent_id` con un `CHECK` (usuario XOR IA) e historial `conversation_assignments`. Una conversación puede tener equipo y responsable directo a la vez.
2. **Promociones: un solo modelo, no dos.** El prompt las modela dos veces (`price_type = promoción` en §38 y `promotions` en §42). Propongo que las promociones sean reglas en `promotions` y que `product_prices` contenga solo precios de listas.
3. **Las promociones no se "activan" con un cron.** La vigencia se resuelve en el momento de la consulta (`starts_at/ends_at` + restricción de exclusión en PostgreSQL). Si un job falla, no debe quedar un precio promocional vivo.
4. **Reordenar fases.** Las tools de IA de la Fase 7 (`create_lead`, `create_opportunity`, `create_quote`) dependen de dominios que llegan en las Fases 9–10. Además, el handoff (Fase 8) debe salir junto con la IA autónoma, no después.
5. **Tools de IA ligadas a la conversación.** `search_customer()` y `get_customer_history()` no deben estar disponibles para agentes que hablan con clientes. Son un vector directo de prompt injection y de fuga de datos de otros clientes.
6. **Ventana de 24 h y plantillas de WhatsApp.** El prompt no las menciona. Condicionan el seguimiento automático "+24 h" (§54), el envío de cotizaciones y cualquier mensaje proactivo.
