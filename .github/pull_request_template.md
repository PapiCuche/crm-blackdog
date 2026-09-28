## Issue / Fase

Closes #

<!-- ID del work item (p. ej., F1-02) y fase. "Refs #N" solo si el PR no cierra el issue. -->

## Objetivo

## Cambios

<!-- Archivos o módulos principales. Migraciones incluidas (si aplica). -->

## No incluye

<!-- Qué queda fuera explícitamente (trabajo de otros issues o fases). -->

## Cómo se verificó

<!-- Comandos ejecutados y su resultado. Declarar lo que NO se pudo ejecutar. -->

## Definition of Done

<!-- Marcar o poner "N/A — motivo". -->

- [ ] Tenant context respetado (`organization_id` desde el contexto; nada del payload)
- [ ] RLS en tablas tenant-owned nuevas (una política PERMISSIVE por comando)
- [ ] Permisos y scopes en endpoints nuevos
- [ ] Auditoría en cambios importantes
- [ ] Tests nuevos o actualizados (incluida la suite de aislamiento si hay endpoints o tablas nuevas)
- [ ] Sin secretos ni PII en código, logs o respuestas
- [ ] Documentación / ADR actualizados si cambia una decisión
- [ ] Dentro del scope del issue (sin adelantar otros work items)

## Riesgos y deuda técnica

<!-- Deuda consciente → issue con label tech-debt y fase objetivo. -->

## Autoría

- [ ] Generado o asistido por IA (indicar el agente). La aprobación final es humana; el autor no hace merge.
