import { fixupConfigRules } from "@eslint/compat";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// fixupConfigRules: eslint-plugin-react (incluido en eslint-config-next) aún usa la API de
// contexto anterior a ESLint 10; la capa oficial de compatibilidad la restaura.
const config = [
  ...fixupConfigRules([...nextVitals, ...nextTs]),
  {
    rules: {
      "react/no-danger": "error", // sin dangerouslySetInnerHTML (ADR-003: XSS)
      "no-restricted-syntax": [
        "error",
        {
          selector: "MemberExpression[property.name=/^(innerHTML|outerHTML|insertAdjacentHTML)$/]",
          message: "Sin inserción de HTML (XSS).",
        },
      ],
    },
  },
  { ignores: [".next/", "next-env.d.ts", "src/lib/api/"] },
];

export default config;
