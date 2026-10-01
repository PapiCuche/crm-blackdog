import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));

import TenantLayout from "./layout";

describe("TenantLayout", () => {
  it.each(["caf%C3%A9", "..%2F..%2Fx", "a b", "", "x".repeat(64)])(
    "rechaza el slug %j",
    async (slug) => {
      await expect(
        TenantLayout({ children: null, params: Promise.resolve({ orgSlug: slug }) }),
      ).rejects.toThrow("NEXT_NOT_FOUND");
    },
  );

  it("acepta un slug válido", async () => {
    await expect(
      TenantLayout({ children: null, params: Promise.resolve({ orgSlug: "acme_01" }) }),
    ).resolves.toBeTruthy();
  });
});
