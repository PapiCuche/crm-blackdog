import { type NextRequest, NextResponse } from "next/server";

import { buildCsp, newNonce } from "@/lib/csp";

// CSP con un nonce por petición (F2-07). Next lee la cabecera de la petición y pone el nonce en
// sus scripts y estilos; por eso todas las páginas se renderizan en cada petición (layout raíz).
export function proxy(request: NextRequest): NextResponse {
  const csp = buildCsp(newNonce(), process.env.NODE_ENV === "development");
  const headers = new Headers(request.headers);
  headers.set("Content-Security-Policy", csp); // sustituye cualquier valor enviado por el cliente
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  // Todo lo que sirve Next como documento. Fuera: la API y los WebSockets (los sirve Django) y
  // los archivos estáticos, que no llevan HTML.
  matcher: ["/((?!api/|ws/|_next/static|_next/image|favicon.ico).*)"],
};
