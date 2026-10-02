import { fireEvent, screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { HealthStatus } from "@/components/health-status";
import { renderIntl } from "@/test-utils";

import { AppShell } from "./app-shell";

beforeAll(() => {
  // jsdom no implementa la API de <dialog>.
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});

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
    const home = screen.getByRole("link", { name: "Inicio" });
    expect(home).toHaveAttribute("href", "/o/acme-01");
    expect(home).toHaveAttribute("aria-current", "page");
    const skip = screen.getByRole("link", { name: "Saltar al contenido" });
    const target = document.querySelector(skip.getAttribute("href") ?? "");
    expect(target).toBe(screen.getByRole("main"));
    expect(target).toHaveAttribute("tabindex", "-1"); // el enlace puede llevar el foco ahí
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); // el menú móvil, cerrado
  });

  it("el menú móvil se abre con su propio nombre y se cierra al elegir o al pulsar fuera", () => {
    renderIntl(<AppShell orgSlug="acme-01">contenido</AppShell>);
    const open = screen.getByRole("button", { name: "Abrir menú" });
    expect(open).toHaveAttribute("aria-haspopup", "dialog");
    fireEvent.click(open);
    const menu = screen.getByRole("dialog", { name: "Menú" });
    expect(within(menu).getByRole("navigation", { name: "Navegación del menú" })).toBeVisible();
    const close = within(menu).getByRole("button", { name: "Cerrar menú" });
    expect(close.closest("form")).toHaveAttribute("method", "dialog"); // cierra sin JavaScript
    fireEvent.click(within(menu).getByText("Organización")); // dentro del panel: sigue abierto
    expect(menu).toHaveAttribute("open");
    const destination = within(menu).getByRole("link", { name: "Inicio" });
    destination.addEventListener("click", (event) => event.preventDefault()); // jsdom no navega
    fireEvent.click(destination);
    expect(menu).not.toHaveAttribute("open");
    fireEvent.click(open);
    fireEvent.click(menu); // el fondo
    expect(menu).not.toHaveAttribute("open");
  });
});

describe("MobileMenu", () => {
  it("se cierra al pasar a escritorio y deja de escuchar al desmontarse", () => {
    const listeners = new Set<() => void>();
    const desktop = {
      matches: false,
      addEventListener: (_: string, listener: () => void) => listeners.add(listener),
      removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
    };
    vi.stubGlobal("matchMedia", () => desktop);
    const shell = renderIntl(<AppShell orgSlug="acme-01">contenido</AppShell>);
    fireEvent.click(screen.getByRole("button", { name: "Abrir menú" }));
    const menu = screen.getByRole("dialog", { name: "Menú" });
    listeners.forEach((listener) => listener()); // cambia, pero sigue siendo pantalla pequeña
    expect(menu).toHaveAttribute("open");
    desktop.matches = true;
    listeners.forEach((listener) => listener());
    expect(menu).not.toHaveAttribute("open");
    shell.unmount();
    expect(listeners.size).toBe(0);
    vi.unstubAllGlobals();
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
