import { describe, expect, it, vi } from "vitest";

import { buildCsp, newNonce } from "./csp";

function directives(csp: string): Record<string, string[]> {
  return Object.fromEntries(
    csp.split("; ").map((directive) => {
      const [name, ...values] = directive.split(" ");
      return [name, values];
    }),
  );
}

describe("buildCsp", () => {
  it("es exactamente la política documentada", () => {
    expect(buildCsp("abc")).toBe(
      "default-src 'self'; script-src 'self' 'nonce-abc' 'strict-dynamic'; " +
        "style-src 'self' 'nonce-abc'; style-src-attr 'unsafe-inline'; " +
        "img-src 'self' blob: data:; font-src 'self'; connect-src 'self'; object-src 'none'; " +
        "frame-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
    );
  });

  it("permite scripts solo con el nonce de la petición", () => {
    const policy = directives(buildCsp("abc"));
    expect(policy["script-src"]).toEqual(["'self'", "'nonce-abc'", "'strict-dynamic'"]);
    expect(policy["style-src"]).toEqual(["'self'", "'nonce-abc'"]);
    expect(policy["default-src"]).toEqual(["'self'"]);
    expect(policy["connect-src"]).toEqual(["'self'"]);
  });

  it("no relaja script-src en producción", () => {
    const csp = buildCsp("abc");
    expect((directives(csp)["script-src"] ?? []).join(" ")).not.toMatch(/unsafe|https?:|\*/);
    expect(csp).not.toContain("unsafe-eval");
  });

  it("cierra objetos, marcos, base y formularios", () => {
    const policy = directives(buildCsp("abc"));
    expect(policy["object-src"]).toEqual(["'none'"]);
    expect(policy["frame-src"]).toEqual(["'none'"]);
    expect(policy["frame-ancestors"]).toEqual(["'none'"]);
    expect(policy["base-uri"]).toEqual(["'self'"]);
    expect(policy["form-action"]).toEqual(["'self'"]);
  });

  it("solo en desarrollo añade unsafe-eval y estilos en línea", () => {
    const policy = directives(buildCsp("abc", true));
    expect(policy["script-src"]).toContain("'unsafe-eval'");
    expect(policy["script-src"]).toContain("'nonce-abc'");
    expect(policy["style-src"]).toEqual(["'self'", "'unsafe-inline'"]);
  });

  it("la única excepción en línea es el atributo style", () => {
    const inline = Object.entries(directives(buildCsp("abc")))
      .filter(([, values]) => values.includes("'unsafe-inline'"))
      .map(([name]) => name);
    expect(inline).toEqual(["style-src-attr"]);
  });
});

describe("newNonce", () => {
  it("sale del generador criptográfico", () => {
    const random = vi.spyOn(crypto, "getRandomValues");
    newNonce();
    expect(random).toHaveBeenCalledOnce();
    expect(random.mock.calls[0]?.[0]).toHaveLength(16);
    random.mockRestore();
  });

  it("genera 128 bits en base64, distintos en cada llamada", () => {
    const nonces = new Set(Array.from({ length: 50 }, newNonce));
    expect(nonces.size).toBe(50);
    for (const nonce of nonces) expect(nonce).toMatch(/^[A-Za-z0-9+/]{22}==$/);
  });
});
