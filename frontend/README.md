# frontend/

Next.js 16 (App Router) + TypeScript estricto (`strict`, `noUncheckedIndexedAccess`), Tailwind 4, shadcn/ui, TanStack Query y next-intl (`es-PE`). Versiones: ADR-012 §4.1.

## Uso

Requiere Node 24.21.0 (`.nvmrc`) y pnpm 12.8.1 (`packageManager`).

```bash
cd frontend
pnpm install --frozen-lockfile
BACKEND_ORIGIN=http://127.0.0.1:8000 pnpm dev   # /api y /ws → Django (same-origin, ADR-003)
```

| Script                              | Qué hace                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| `pnpm format:check` / `pnpm format` | Prettier (con orden de clases de Tailwind)                                     |
| `pnpm lint`                         | ESLint (Next + `react/no-danger`, sin `innerHTML`), sin warnings               |
| `pnpm typecheck`                    | `tsc --noEmit`                                                                 |
| `pnpm test --run`                   | Vitest + Testing Library                                                       |
| `pnpm build`                        | Build de producción (`BACKEND_ORIGIN` se fija en el build)                     |
| `pnpm api:generate`                 | orval: `../backend/openapi/schema.yaml` → `src/lib/api/` (generado, no editar) |

## Estructura

- `src/app/`: `/` muestra el estado del backend (consultado desde el servidor); `/o/[orgSlug]` es la ruta de tenant con el App Shell; `/demo` es la demo visual (ver abajo).
- `src/components/app-shell/`: Sidebar + Topbar + Workspace. Dark-first, Geist, acento dorado con moderación, WCAG AA, `prefers-reduced-motion`.
- `src/components/ui/`: componentes shadcn/ui.
- `src/lib/api/`: cliente generado por orval. **Nunca** tipos de API a mano: si cambia el contrato, regenerar el schema del backend y después ejecutar `pnpm api:generate`.
- `src/components/demo/`: landing y workspace de la demo visual, con sus datos ficticios.
- `messages/es-PE.json`: catálogo i18n.

Sin autenticación, RBAC ni pantallas de negocio (llegan en fases posteriores desde el diseño de Figma).

## Demo visual (UI-01)

Prototipo navegable del diseño de Figma [GOOD DOGGY · CRM independiente y landing page](https://www.figma.com/design/nRg83fFjnBDp8EouIPvTEZ/GOOD-DOGGY-%C2%B7-CRM-independiente-y-landing-page?node-id=5-108), que es la referencia visual. Con `pnpm dev`, abrir `http://localhost:3000/demo`.

| Ruta                                | Pantalla del Figma                                                                                                                                |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/demo`                             | `GD-00-Landing` (5:108), vista previa con pestañas (35:154) y acceso demo (35:266)                                                                |
| `/demo/workspace`                   | `GD-01-Resumen` (5:212); en móvil, `GD-16-Mobile` (5:2183)                                                                                        |
| `/demo/workspace/inbox`             | `GD-02-Inbox` (5:370)                                                                                                                             |
| `/demo/workspace/pipeline`          | `GD-04-Pipeline` (5:652)                                                                                                                          |
| `/demo/workspace/reportes`          | `GD-14-Reportes` (10:160)                                                                                                                         |
| `/demo/workspace/<módulo>` (tablas) | Contactos, Cotizaciones, Ventas, Tareas, Catálogo, Precios, Inventario, Agentes IA, Canales, Automatizaciones y Configuración (`GD-03` … `GD-15`) |

Límites de la demo:

- Datos ficticios definidos en `src/components/demo/data.ts`. No llama a la API, no envía mensajes y no guarda nada: los cambios (chat, etapa de una oportunidad, búsquedas) viven en memoria y se pierden al recargar.
- Sin autenticación ni permisos: el "acceso demo" solo lleva al workspace. Las rutas de tenant (`/o/[orgSlug]`) no cambian.
- Los tokens del Figma (`--gd-*`) y la fuente DM Sans solo se aplican bajo `/demo`; el resto de la aplicación conserva su tema. DM Sans se descarga de Google Fonts durante el build (`next/font`) y se sirve desde el propio origen.
- El texto de la demo vive en los componentes, no en `messages/es-PE.json`: es contenido de prototipo, no catálogo del producto.
