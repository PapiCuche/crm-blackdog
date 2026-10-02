// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildCsp } from "@/lib/csp";

import { config, proxy } from "./proxy";

const CSP = "content-security-policy";
const nonceOf = (csp: string | null) => /'nonce-([^']+)'/.exec(csp ?? "")?.[1];

afterEach(() => vi.unstubAllEnvs());

describe("proxy", () => {
  it("emite la política de producción hacia el navegador y hacia el render de Next", () => {
    const response = proxy(new NextRequest("http://localhost/o/acme"));
    const csp = response.headers.get(CSP);
    expect(nonceOf(csp)).toMatch(/^[A-Za-z0-9+/]{22}==$/);
    expect(csp).toBe(buildCsp(nonceOf(csp) ?? ""));
    // NextResponse.next({ request }) reenvía las cabeceras al render con este prefijo.
    expect(response.headers.get(`x-middleware-request-${CSP}`)).toBe(csp);
    expect(response.headers.get("x-middleware-override-headers")).toContain(CSP);
  });

  it("solo relaja la política con NODE_ENV=development", () => {
    vi.stubEnv("NODE_ENV", "development");
    const dev = proxy(new NextRequest("http://localhost/")).headers.get(CSP);
    expect(dev).toBe(buildCsp(nonceOf(dev) ?? "", true));
    vi.stubEnv("NODE_ENV", "production");
    expect(proxy(new NextRequest("http://localhost/")).headers.get(CSP)).not.toContain(
      "unsafe-eval",
    );
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

  it("cubre todo lo que responde Next y deja fuera solo la API y los WebSockets", () => {
    const matcher = new RegExp(`^${config.matcher[0]}$`);
    const covered = ["/", "/o/acme", "/demo/workspace/inbox", "/apix", "/wsx"];
    // Los 404 de Next son HTML: también llevan la CSP.
    covered.push("/favicon.ico", "/_next/staticx", "/_next/static/chunk.js", "/_next/image");
    for (const path of covered) expect(matcher.test(path), path).toBe(true);
    for (const path of ["/api/v1/auth/login/", "/api/", "/ws/o/acme/"]) {
      expect(matcher.test(path), path).toBe(false);
    }
  });
});
