import { defineConfig } from "orval";

// Única fuente del contrato: backend/openapi/schema.yaml (F1-08A). Nunca tipos API a mano.
export default defineConfig({
  crm: {
    input: { target: "../backend/openapi/schema.yaml" },
    output: {
      target: "src/lib/api/client.ts",
      schemas: "src/lib/api/model",
      client: "react-query",
      httpClient: "fetch",
      baseUrl: "", // same-origin: /api/… lo enruta el proxy (Next en local, Caddy en F1-10)
      clean: true,
      formatter: "prettier",
      override: {
        // Todo pasa por `apiFetch` (CSRF, cookies del mismo origen, errores por `code`); las
        // funciones devuelven el cuerpo, no el sobre `{ data, status, headers }`.
        mutator: { path: "./src/lib/http.ts", name: "apiFetch" },
        fetch: { includeHttpResponseReturnType: false },
      },
    },
  },
});
