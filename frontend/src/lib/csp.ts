// Content Security Policy (F2-07, security-boundaries B1). Estricta por nonce: ningún script se
// ejecuta sin el nonce de la petición. Cómo añadir un origen: frontend/README.md.
const NONCE_BYTES = 16;

export function newNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(NONCE_BYTES));
  return btoa(String.fromCharCode(...bytes));
}

export function buildCsp(nonce: string, dev = false): string {
  const directives: Record<string, string[]> = {
    "default-src": ["'self'"],
    // 'strict-dynamic': los scripts con nonce cargan sus chunks. 'unsafe-eval' solo en desarrollo
    // (React lo usa para reconstruir trazas); nunca en el build de producción.
    "script-src": [
      "'self'",
      `'nonce-${nonce}'`,
      "'strict-dynamic'",
      ...(dev ? ["'unsafe-eval'"] : []),
    ],
    "style-src": ["'self'", dev ? "'unsafe-inline'" : `'nonce-${nonce}'`],
    // Excepción documentada: next/image y los estilos calculados (p. ej. la altura de una barra)
    // llegan como atributo `style` en el HTML del servidor. Un atributo no ejecuta código.
    "style-src-attr": ["'unsafe-inline'"],
    "img-src": ["'self'", "blob:", "data:"],
    "font-src": ["'self'"],
    "connect-src": ["'self'"],
    "object-src": ["'none'"],
    "frame-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
  };
  return Object.entries(directives)
    .map(([name, values]) => `${name} ${values.join(" ")}`)
    .join("; ");
}
