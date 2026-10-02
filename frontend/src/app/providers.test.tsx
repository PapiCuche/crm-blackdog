import { useQueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/http";

import { Providers, shouldRetry } from "./providers";

describe("política de reintentos", () => {
  it("no repite una respuesta 4xx y reintenta una vez lo demás", () => {
    for (const status of [400, 401, 403, 404, 429, 499]) {
      expect(shouldRetry(0, new ApiError(status, "X"))).toBe(false);
    }
    for (const error of [new ApiError(500, "X"), new ApiError(0, "NETWORK_ERROR"), new Error()]) {
      expect(shouldRetry(0, error)).toBe(true);
      expect(shouldRetry(1, error)).toBe(false);
    }
  });

  it("el cliente de consultas la usa y nunca repite una escritura", () => {
    let options: ReturnType<ReturnType<typeof useQueryClient>["getDefaultOptions"]> = {};
    function Probe() {
      options = useQueryClient().getDefaultOptions();
      return null;
    }
    render(
      <Providers>
        <Probe />
      </Providers>,
    );
    expect(options.queries?.retry).toBe(shouldRetry);
    expect(options.mutations?.retry).toBe(false);
  });
});
