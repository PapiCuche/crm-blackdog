import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HealthStatus } from "@/components/health-status";
import { renderIntl } from "@/test-utils";

import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("tiene landmarks, enlace para saltar al contenido y el enlace al slug validado", () => {
    renderIntl(<AppShell orgSlug="acme-01">contenido</AppShell>);
    expect(screen.getByRole("navigation", { name: "Navegación principal" })).toBeInTheDocument();
    expect(screen.getByRole("banner")).toHaveTextContent("acme-01");
    expect(screen.getByRole("main")).toHaveTextContent("contenido");
    expect(screen.getByRole("link", { name: "Saltar al contenido" })).toHaveAttribute(
      "href",
      "#workspace",
    );
    expect(screen.getByRole("link", { name: "Inicio" })).toHaveAttribute("href", "/o/acme-01");
  });
});

describe("HealthStatus", () => {
  it.each([
    ["ok", "Operativo"],
    ["fail", "No disponible"],
  ] as const)("%s → %s", (status, text) => {
    renderIntl(<HealthStatus label="Backend" status={status} />);
    expect(screen.getByRole("status")).toHaveTextContent(text);
  });
});
