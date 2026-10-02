import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TextField } from "./text-field";

describe("TextField", () => {
  it("une la etiqueta y la ayuda al control", () => {
    render(
      <TextField label="Correo" hint="El de tu cuenta" type="email" name="email" id="email" />,
    );
    const input = screen.getByLabelText("Correo");
    expect(input).toHaveAttribute("type", "email");
    expect(input).toHaveAttribute("id", "email");
    expect(input).toHaveAccessibleDescription("El de tu cuenta");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("el error sustituye a la ayuda, marca el control y se anuncia", () => {
    render(<TextField label="Correo" hint="El de tu cuenta" error="Escribe tu correo" />);
    const input = screen.getByLabelText("Correo");
    expect(input).toBeInvalid();
    expect(input).toHaveAccessibleDescription("Escribe tu correo");
    expect(screen.getByRole("alert")).toHaveTextContent("Escribe tu correo");
    expect(screen.queryByText("El de tu cuenta")).not.toBeInTheDocument();
  });

  it("un error vacío no es un error, y la descripción de quien llama se conserva", () => {
    render(
      <>
        <p id="ayuda-del-formulario">Todos los campos son obligatorios</p>
        <TextField
          label="Correo"
          hint="El de tu cuenta"
          error=""
          aria-describedby="ayuda-del-formulario"
        />
      </>,
    );
    const input = screen.getByLabelText("Correo");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).toHaveAccessibleDescription("Todos los campos son obligatorios El de tu cuenta");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
