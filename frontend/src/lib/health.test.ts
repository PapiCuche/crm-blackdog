import { describe, expect, it, vi } from "vitest";

import { backendHealth } from "./health";

describe("backendHealth", () => {
  it("consulta /health/ready del backend sin caché", async () => {
    const fetcher = vi.fn(async () => new Response("{}", { status: 200 }));
    await expect(backendHealth("http://backend:8000", fetcher)).resolves.toBe("ok");
    expect(fetcher).toHaveBeenCalledWith(
      "http://backend:8000/health/ready",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("503 o error de red → fail (nunca lanza)", async () => {
    const down = vi.fn(async () => new Response("", { status: 503 }));
    const broken = vi.fn(async () => Promise.reject(new TypeError("fetch failed")));
    await expect(backendHealth("http://b", down)).resolves.toBe("fail");
    await expect(backendHealth("http://b", broken)).resolves.toBe("fail");
  });
});
