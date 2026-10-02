"use client";

import { type ReactNode, useEffect, useRef } from "react";

type Props = { label: string; title: string; closeLabel: string; children: ReactNode };

// Menú del shell en pantallas pequeñas: la barra lateral dentro de un <dialog> nativo, que ya
// atrapa el foco, se cierra con Escape y deja inerte el resto de la página.
export function MobileMenu({ label, title, closeLabel, children }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    // Al pasar a escritorio (girar una tableta) la barra lateral fija vuelve: el menú sobra.
    const desktop = window.matchMedia?.("(min-width: 64rem)");
    const close = () => desktop?.matches && dialog.current?.close();
    desktop?.addEventListener("change", close);
    return () => desktop?.removeEventListener("change", close);
  }, []);

  return (
    <>
      <button
        type="button"
        className="hover:bg-surface-raised -ml-2.5 flex size-11 shrink-0 items-center justify-center rounded-md lg:hidden"
        aria-label={label}
        aria-haspopup="dialog"
        onClick={() => dialog.current?.showModal()}
      >
        <span aria-hidden>☰</span>
      </button>
      <dialog
        ref={dialog}
        aria-label={title}
        className="shell-drawer text-foreground m-0 h-dvh max-h-none"
        onClick={(event) => {
          // Cierra al elegir un destino o al pulsar fuera del panel.
          const target = event.target as HTMLElement;
          if (target === dialog.current || target.closest("a")) dialog.current?.close();
        }}
      >
        {children}
        {/* Después del contenido: el foco inicial cae en la navegación, no en cerrar. */}
        <form method="dialog" className="absolute top-4 right-2">
          <button
            aria-label={closeLabel}
            className="hover:bg-surface-raised flex size-11 items-center justify-center rounded-md text-xl"
          >
            <span aria-hidden>×</span>
          </button>
        </form>
      </dialog>
    </>
  );
}
