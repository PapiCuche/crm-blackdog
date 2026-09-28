## Objetivo

<!-- Qué resuelve este PR y a qué fase / épica / historia pertenece. Un PR = un objetivo verificable. -->

## Cambios

<!-- Archivos o módulos principales. Migraciones incluidas (si aplica). -->

## Cómo se verificó

<!-- Comandos ejecutados y su resultado (tests, lint, typecheck, migraciones). -->

## Checklist (ver docs/architecture/security-boundaries.md §6)

- [ ] Respeta `organization_id` / tenant context (RLS en tablas nuevas, UNIQUE con `organization_id`)
- [ ] Permisos y scopes declarados en endpoints nuevos
- [ ] Auditoría en cambios importantes
- [ ] Sin secretos ni PII en logs o respuestas
- [ ] Tests nuevos o actualizados (incluida la suite de aislamiento si hay endpoints nuevos)
- [ ] Documentación / ADR actualizados si cambia una decisión
- [ ] Tamaño razonable (≤ 400 líneas netas salvo código generado)

## Riesgos y deuda técnica

<!-- Deuda consciente → issue con etiqueta tech-debt y fase objetivo. -->

## Autoría

- [ ] Generado o asistido por IA (indicar el agente). La aprobación final es humana.
