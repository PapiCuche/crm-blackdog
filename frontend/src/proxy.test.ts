// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { config, proxy } from "./proxy";

const CSP = "content-security-policy";
const nonceOf = (csp: string | null) => /'nonce-([^']+)'/.exec(csp ?? "")?.[1];

describe("proxy", () => {
  it("emite la misma CSP hacia el navegador y hacia el render de Next", () => {
    const response = proxy(new NextRequest("http://localhost/o/acme"));
    const csp = response.headers.get(CSP);
    expect(nonceOf(csp)).toBeTruthy();
    // NextResponse.next({ request }) reenvía las cabeceras al render con este prefijo.
    expect(response.headers.get(`x-middleware-request-${CSP}`)).toBe(csp);
    expect(response.headers.get("x-middleware-override-headers")).toContain(CSP);
  });

  it("usa un nonce nuevo en cada petición", () => {
    const first = proxy(new NextRequest("http://localhost/"));
    const second = proxy(new NextRequest("http://localhost/"));
    expect(nonceOf(first.headers.get(CSP))).not.toBe(nonceOf(second.headers.get(CSP)));
  });

  it("descarta una CSP enviada por el cliente", () => {
    const forged = "script-src 'nonce-forjado' 'unsafe-inline'";
    const request = new NextRequest("http://localhost/demo", { headers: { [CSP]: forged } });
    const response = proxy(request);
    expect(response.headers.get(`x-middleware-request-${CSP}`)).toBe(response.headers.get(CSP));
    expect(response.headers.get(CSP)).not.toContain("forjado");
  });

  it("cubre los documentos y deja fuera la API, los WebSockets y los estáticos", () => {
    const matcher = new RegExp(`^${config.matcher[0]}$`);
    for (const path of ["/", "/o/acme", "/demo/workspace/inbox", "/apix", "/wsx"]) {
      expect(matcher.test(path), path).toBe(true);
    }
    for (const path of ["/api/v1/auth/login/", "/ws/o/acme/", "/_next/static/chunk.js"]) {
      expect(matcher.test(path), path).toBe(false);
    }
  });
});
