"use client";

import { useRef } from "react";

import type { DemoModule } from "./data";
import { Sidebar } from "./sidebar";

// Menú móvil (Figma 5:2183, "☰"): la misma barra lateral dentro de un <dialog> nativo.
export function MobileNav({ active }: { active: DemoModule }) {
  const dialog = useRef<HTMLDialogElement>(null);
  return (
    <>
      <button
        type="button"
        className="lg:hidden"
        aria-label="Abrir menú"
        aria-haspopup="dialog"
        onClick={() => dialog.current?.showModal()}
      >
        <span aria-hidden>☰</span>
      </button>
      <dialog
        ref={dialog}
        aria-label="Menú del workspace"
        className="text-gd-foreground backdrop:bg-gd-foreground/40 m-0 h-dvh max-h-none"
        onClick={(event) => {
          // Cierra al elegir un módulo o al pulsar fuera del panel.
          const target = event.target as HTMLElement;
          if (target === dialog.current || target.closest("a")) dialog.current?.close();
        }}
      >
        <Sidebar active={active} />
      </dialog>
    </>
  );
}
