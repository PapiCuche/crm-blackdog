import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { mockApi, renderApp } from "@/test-utils";

import { OrganizationList } from "./organization-list";

const router = { replace: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const MINE = "GET /api/v1/me/organizations/";
const acme = { id: "1", slug: "acme", name: "Acme SAC" };
const norte = { id: "2", slug: "acme-norte", name: "Acme Norte" };

afterEach(() => {
  router.replace.mockReset();
  vi.unstubAllGlobals();
});

describe("OrganizationList", () => {
  it("lista las organizaciones que devuelve la API, cada una con su enlace", async () => {
    mockApi({ [MINE]: { status: 200, body: [acme, norte] } });
    renderApp(<OrganizationList choose={false} />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando");
    expect(await screen.findByRole("link", { name: /Acme SAC/ })).toHaveAttribute(
      "href",
      "/o/acme",
    );
    const norteLink = screen.getByRole("link", { name: /Acme Norte/ });
    expect(norteLink).toHaveAttribute("href", "/o/acme-norte");
    expect(norteLink).toHaveTextContent("acme-norte"); // el slug distingue nombres parecidos
    expect(norteLink).toHaveAccessibleName(/^Acme Norte\s*acme-norte$/); // sin la flecha
    expect(screen.getByRole("status")).toHaveTextContent("2 organizaciones."); // se anuncia
    expect(document.body).toHaveFocus(); // la primera carga no mueve el foco
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("con una sola entra directamente, salvo que se pida elegir", async () => {
    mockApi({ [MINE]: { status: 200, body: [acme] } });
    const first = renderApp(<OrganizationList choose={false} />);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/o/acme"));
    first.unmount();
    router.replace.mockReset();
    renderApp(<OrganizationList choose />);
    expect(await screen.findByRole("link", { name: /Acme SAC/ })).toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("sin organizaciones lo explica, sin inventar ninguna", async () => {
    mockApi({ [MINE]: { status: 200, body: [] } });
    renderApp(<OrganizationList choose={false} />);
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Aún no perteneces a ninguna"),
    );
    expect(screen.getByText(/Pide a quien administra la tuya/)).toBeVisible();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("sin sesión no muestra un error: el login lo decide el proveedor", async () => {
    const api = mockApi({ [MINE]: { status: 401, body: { code: "NOT_AUTHENTICATED" } } });
    renderApp(<OrganizationList choose={false} />);
    await waitFor(() => expect(api).toHaveBeenCalledTimes(1)); // un 401 no se reintenta
    expect(await screen.findByRole("status")).toHaveTextContent("Cargando");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("un fallo se puede reintentar, y el foco no se pierde por el camino", async () => {
    let reply: { status: number; body: unknown } = {
      status: 503,
      body: { code: "INTERNAL_ERROR" },
    };
    const api = mockApi({ [MINE]: () => reply });
    const { container } = renderApp(<OrganizationList choose={false} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Algo salió mal");
    expect(api).toHaveBeenCalledTimes(2); // un reintento automático de un 5xx
    reply = { status: 403, body: { code: "PERMISSION_DENIED" } };
    const first = screen.getByRole("button", { name: "Reintentar" });
    first.focus();
    fireEvent.click(first);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("No tienes permiso"));
    const second = screen.getByRole("button", { name: "Reintentar" });
    await waitFor(() => expect(second).toHaveFocus()); // aunque el botón se vuelva a montar
    reply = { status: 200, body: [acme, norte] };
    fireEvent.click(second);
    expect(await screen.findByRole("link", { name: /Acme Norte/ })).toBeInTheDocument();
    await waitFor(() => expect(container.firstElementChild).toHaveFocus()); // lo que llegó
  });
});
