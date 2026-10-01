"use client";

import Link from "next/link";
import { type KeyboardEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { moduleHref } from "./data";

const VIEWS = [
  { id: "inbox", label: "Inbox", width: "w-[112px]" },
  { id: "pipeline", label: "Pipeline", width: "w-[112px]" },
  { id: "copiloto", label: "Copiloto IA", width: "w-[146px]" },
] as const;
type ViewId = (typeof VIEWS)[number]["id"];

const STAGE_CARDS = [
  { stage: "Nuevo", name: "Camila Torres", value: "USD 4,899" },
  { stage: "Propuesta", name: "Diego Mendoza", value: "USD 5,299" },
  { stage: "Seguimiento", name: "Valeria Rojas", value: "USD 899" },
] as const;

// "Live Preview" del Figma (35:154): tres vistas del producto; la pestaña activa se invierte.
export function LivePreview() {
  const [view, setView] = useState<ViewId>("inbox");
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = (index + step + VIEWS.length) % VIEWS.length;
    setView(VIEWS[next]!.id);
    tabs.current[next]?.focus();
  }

  return (
    <div className="border-gd-foreground bg-gd-paper flex min-h-[354px] flex-col gap-[18px] rounded-[24px] border p-6 leading-[1.5]">
      <div className="flex justify-between gap-4">
        <p>GD / Workspace</p>
        <p>
          <span aria-hidden>○ </span>DEMOSTRACIÓN
        </p>
      </div>
      <div role="tablist" aria-label="Vistas del producto" className="flex flex-wrap gap-2.5">
        {VIEWS.map((tab, index) => {
          const selected = tab.id === view;
          return (
            <Button
              key={tab.id}
              ref={(node) => {
                tabs.current[index] = node;
              }}
              role="tab"
              id={`gd-preview-tab-${tab.id}`}
              aria-selected={selected}
              aria-controls="gd-preview-panel"
              tabIndex={selected ? 0 : -1}
              variant="ink"
              size="ink"
              className={cn(
                tab.width,
                "px-0 text-[15px] font-normal",
                selected && "bg-gd-paper text-gd-foreground",
              )}
              onClick={() => setView(tab.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
            >
              {tab.label}
            </Button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id="gd-preview-panel"
        aria-labelledby={`gd-preview-tab-${view}`}
        className="flex flex-col items-start gap-3.5"
      >
        {view === "inbox" && (
          <>
            <p>Camila Torres · hace 2 min</p>
            <p className="border-gd-foreground w-full max-w-[470px] rounded-[24px] border px-4 py-3 shadow-[0_1px_8px_rgba(32,32,32,0.12)]">
              Hola, ¿podemos revisar el plan para mi equipo?
            </p>
            <p>Claro, Camila. Tengo una propuesta lista para ti.</p>
            <p>
              Una conversación. Todo el contexto. <span aria-hidden>→</span>
            </p>
          </>
        )}
        {view === "pipeline" && (
          <ul className="flex w-full flex-wrap gap-3">
            {STAGE_CARDS.map((card) => (
              <li
                key={card.stage}
                className="border-gd-foreground flex w-[182px] flex-col gap-3.5 rounded-[24px] border px-3.5 py-4 shadow-[0_1px_8px_rgba(32,32,32,0.12)]"
              >
                <p>{card.stage}</p>
                <p>{card.name}</p>
                <p className="text-[20px] leading-[1.15]">{card.value}</p>
                <p>
                  Ver oportunidad <span aria-hidden>→</span>
                </p>
              </li>
            ))}
          </ul>
        )}
        {view === "copiloto" && (
          <>
            <p className="text-[23px] leading-[1.15]">Una buena sugerencia. Tu decisión.</p>
            <p>
              Preparé una propuesta según el interés de Camila.
              <br />
              Precio y disponibilidad pendientes de revisión.
            </p>
            <Button asChild variant="ink" size="ink" className="w-[210px] px-0">
              <Link href={moduleHref("agentes-ia")}>
                Revisar sugerencia <span aria-hidden>→</span>
              </Link>
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
