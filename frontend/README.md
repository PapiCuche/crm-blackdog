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

Sin autenticación, RBAC ni pantallas de negocio todavía. Las pantallas reales se construyen en `/o/[orgSlug]`, sobre la API y el cliente generado, con el Figma GOOD DOGGY como referencia visual ([AGENTS.md](../AGENTS.md) §11).

## Seguridad del navegador (F2-07)

Next emite todas las cabeceras de seguridad del HTML; Caddy no añade ninguna.

| Cabecera                                                                                                                                        | Dónde                                  | Valor            |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------- |
| `Content-Security-Policy`                                                                                                                       | `src/proxy.ts` (un nonce por petición) | `src/lib/csp.ts` |
| `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Strict-Transport-Security`, `Cross-Origin-Opener-Policy`, `Permissions-Policy` | `next.config.ts`                       | Fijas            |

La política de producción:

```text
default-src 'self'; script-src 'self' 'nonce-…' 'strict-dynamic'; style-src 'self' 'nonce-…';
style-src-attr 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self'; connect-src 'self';
object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

- **Scripts:** solo se ejecutan los que llevan el nonce de la petición, y los que esos cargan (`'strict-dynamic'`). Sin `'unsafe-inline'` ni `'unsafe-eval'`. Un `<script>` insertado en el HTML, un manejador en línea (`onerror=…`) y `eval` quedan bloqueados.
- **Render dinámico:** Next pone el nonce al renderizar, así que ninguna página se prerenderiza en el build. El layout raíz llama a `connection()`. Efecto medido en el build: `/demo`, `/demo/workspace`, sus 14 módulos y la página 404 eran estáticas y ahora se renderizan en cada petición; `/` y `/o/[orgSlug]` ya eran dinámicas.
- **Excepción documentada:** `style-src-attr 'unsafe-inline'`. `next/image` y los estilos calculados (la altura de una barra) llegan como atributo `style` en el HTML del servidor. Un atributo `style` no ejecuta código y las etiquetas `<style>` siguen necesitando el nonce.
- **Desarrollo (`next dev`):** se añaden `'unsafe-eval'` a los scripts (React lo usa para las trazas) y `'unsafe-inline'` a los estilos. El build de producción nunca los incluye.
- **Sin `upgrade-insecure-requests`:** el stack local sirve HTTP y todas las fuentes son del propio origen. En producción el proxy con TLS redirige y HSTS fija HTTPS.
- **Fuera de la CSP:** `/api`, `/ws` y `/_next/static`. La API responde JSON con sus propias cabeceras (Django).

**Cómo añadir un origen.** Solo si el producto lo necesita y con su motivo en el PR: añadirlo a la directiva más estrecha en `src/lib/csp.ts` (por ejemplo `img-src` para un CDN de imágenes), nunca a `default-src`, y actualizar `src/lib/csp.test.ts`. Un script de terceros recibe el nonce con `<Script nonce>`; no se añade su dominio a `script-src`.

Comprobaciones: `src/lib/csp.test.ts`, `src/proxy.test.ts` y la prueba de humo de la imagen, que exige la cabecera (`SMOKE_HEADER_PATTERN` en `make check` y en CI).

## Demo visual (UI-01)

**Congelada desde el 2026-10-02.** `/demo` es un prototipo heredado: no recibe funcionalidades nuevas, solo el mantenimiento que lo mantenga funcionando, y se retirará con un work item propio cuando existan las pantallas oficiales equivalentes. Su estado ficticio no se copia al producto.

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
