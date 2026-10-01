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

- `src/app/`: `/` muestra el estado del backend (consultado desde el servidor); `/o/[orgSlug]` es la ruta de tenant con el App Shell.
- `src/components/app-shell/`: Sidebar + Topbar + Workspace. Dark-first, Geist, acento dorado con moderación, WCAG AA, `prefers-reduced-motion`.
- `src/components/ui/`: componentes shadcn/ui.
- `src/lib/api/`: cliente generado por orval. **Nunca** tipos de API a mano: si cambia el contrato, regenerar el schema del backend y después ejecutar `pnpm api:generate`.
- `messages/es-PE.json`: catálogo i18n.

Sin autenticación, RBAC ni pantallas de negocio (llegan en fases posteriores desde el diseño de Figma).
