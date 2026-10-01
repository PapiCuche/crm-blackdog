"use client";

import Link from "next/link";
import { useRef } from "react";

import { Button } from "@/components/ui/button";

import { WORKSPACE_HOME } from "./data";

// "Acceso demo" del Figma (35:266): overlay sin credenciales; solo lleva al workspace.
export function AccessDialog() {
  const dialog = useRef<HTMLDialogElement>(null);
  return (
    <>
      <Button
        variant="ink"
        size="ink"
        className="w-[160px] text-[15px] font-normal"
        aria-haspopup="dialog"
        onClick={() => dialog.current?.showModal()}
      >
        Ingresar demo <span aria-hidden>↗</span>
      </Button>
      <dialog
        ref={dialog}
        aria-labelledby="gd-access-title"
        className="border-gd-foreground bg-gd-paper text-gd-foreground backdrop:bg-gd-foreground/40 m-auto w-[min(460px,calc(100vw-32px))] rounded-[24px] border p-8 shadow-[0_1px_8px_rgba(32,32,32,0.12)]"
      >
        <div className="flex flex-col items-start gap-5 leading-[1.5]">
          <p>GOOD DOGGY / DEMO</p>
          <h2
            id="gd-access-title"
            className="text-[32px] leading-[1.15] font-bold tracking-[0.64px]"
          >
            Tu espacio te espera.
          </h2>
          <p>
            Explora el CRM con datos de ejemplo.
            <br />
            No necesitas introducir credenciales.
          </p>
          <div className="border-gd-edge bg-gd-surface flex w-full flex-col gap-2 rounded-[6px] border px-4 py-3.5">
            <p>Espacio de trabajo</p>
            <p>Mi organización · Sandbox</p>
          </div>
          <Button asChild variant="ink" size="ink" className="w-full">
            <Link href={WORKSPACE_HOME}>
              Continuar a la demo <span aria-hidden>→</span>
            </Link>
          </Button>
          <form method="dialog" className="w-full">
            <Button variant="ink" size="ink" className="w-full">
              Volver a la landing
            </Button>
          </form>
          <p>Acceso simulado · No crea una cuenta</p>
        </div>
      </dialog>
    </>
  );
}
