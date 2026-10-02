import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderIntl } from "@/test-utils";

import ErrorPage from "./error";
import NotFound from "./not-found";

describe("páginas de error propias", () => {
  it("la 404 enlaza al inicio y no inserta estilos en línea", () => {
    const { container } = renderIntl(<NotFound />);
    expect(screen.getByRole("heading", { name: "Página no encontrada" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver al inicio" })).toHaveAttribute("href", "/");
    expect(container.querySelector("style, [style]")).toBeNull();
  });

  it("el error no muestra el detalle técnico y permite reintentar", () => {
    const reset = vi.fn();
    const { container } = renderIntl(
      <ErrorPage error={new Error("SELECT fallido en 10.0.0.5")} reset={reset} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("No pudimos mostrar esta página");
    expect(container).not.toHaveTextContent("SELECT");
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
