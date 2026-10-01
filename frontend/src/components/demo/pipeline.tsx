"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

import { type Contact, CONTACTS, moduleHref, type Stage, STAGES, usd } from "./data";

const BOX = "border-gd-edge/8 border";

// Pipeline del Figma (5:652). Las tarjetas cambian de etapa con un <select> (teclado y lector de
// pantalla); el cambio vive en memoria y se reinicia al recargar.
export function Pipeline() {
  const [stages, setStages] = useState<Record<string, Stage>>(() =>
    Object.fromEntries(CONTACTS.map((contact) => [contact.id, contact.stage])),
  );
  const [moved, setMoved] = useState<{ id: string; text: string } | null>(null);
  const [detail, setDetail] = useState<Contact | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);

  // La tarjeta se vuelve a montar en su nueva columna: se devuelve el foco a su selector.
  useEffect(() => {
    if (moved) document.getElementById(`gd-stage-${moved.id}`)?.focus();
  }, [moved]);

  function move(contact: Contact, stage: Stage) {
    setStages((current) => ({ ...current, [contact.id]: stage }));
    setMoved({ id: contact.id, text: `${contact.name} pasó a ${stage}.` });
  }

  return (
    <>
      <p role="status" className="sr-only">
        {moved?.text ?? ""}
      </p>
      <div className="mt-[29px] grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {STAGES.map((stage) => {
          const cards = CONTACTS.filter((contact) => stages[contact.id] === stage);
          return (
            <section
              key={stage}
              aria-label={`${stage}: ${cards.length} ${cards.length === 1 ? "oportunidad" : "oportunidades"}`}
              className={`${BOX} rounded-[8px] px-[11px] pb-3 xl:min-h-[500px]`}
            >
              <h2 className="flex justify-between px-[3px] pt-[17px] pr-4">
                <span>
                  <span
                    aria-hidden
                    className="bg-gd-foreground mr-1.5 inline-block size-3 rounded-full align-[-1px]"
                  />
                  {stage}
                </span>
                <span>{cards.length}</span>
              </h2>
              <ul className="mt-[15px] flex flex-col gap-3">
                {cards.map((contact) => (
                  <li key={contact.id} className={`${BOX} rounded-[7px] pt-[15px] pb-[5px] pl-3`}>
                    <p className="bg-gd-surface inline-block rounded-[4px] px-2.5 py-[3px]">
                      Sandbox
                    </p>
                    <h3 className="mt-[17px]">{contact.name}</h3>
                    <p className="mt-2.5">{contact.interest}</p>
                    <p className="mt-3 text-[22px]">{usd(contact.value)}</p>
                    <label htmlFor={`gd-stage-${contact.id}`} className="mt-[19px] block">
                      ETAPA <span className="sr-only">de {contact.name}</span>
                    </label>
                    <select
                      id={`gd-stage-${contact.id}`}
                      value={stage}
                      onChange={(event) => move(contact, event.target.value as Stage)}
                      className="bg-gd-surface h-[25px] max-w-full rounded-[4px] pl-1.5"
                    >
                      {STAGES.map((option) => (
                        <option key={option}>{option}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="mt-1 block hover:underline"
                      aria-haspopup="dialog"
                      onClick={() => {
                        setDetail(contact);
                        dialog.current?.showModal();
                      }}
                    >
                      Ver oportunidad <span className="sr-only">de {contact.name}</span>
                    </button>
                  </li>
                ))}
                {cards.length === 0 && (
                  <li className="px-[3px]">Sin oportunidades en esta etapa.</li>
                )}
              </ul>
            </section>
          );
        })}
      </div>
      <p className="mt-9">Prototipo de navegación · Las operaciones se implementarán en el CRM.</p>

      <dialog
        ref={dialog}
        aria-labelledby="gd-opportunity-title"
        className="border-gd-foreground bg-gd-paper text-gd-foreground backdrop:bg-gd-foreground/40 m-auto w-[min(460px,calc(100vw-32px))] rounded-[24px] border p-8 shadow-[0_1px_8px_rgba(32,32,32,0.12)]"
      >
        {detail && (
          <div className="flex flex-col items-start gap-5 leading-[1.5]">
            <p>GOOD DOGGY / OPORTUNIDAD</p>
            <h2
              id="gd-opportunity-title"
              className="text-[32px] leading-[1.15] font-bold tracking-[0.64px]"
            >
              {detail.name}
            </h2>
            <dl className="border-gd-edge bg-gd-surface flex w-full flex-col gap-2 rounded-[6px] border px-4 py-3.5">
              <div className="flex justify-between gap-4">
                <dt>Interés</dt>
                <dd>{detail.interest}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>Valor</dt>
                <dd>{usd(detail.value)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt>Etapa</dt>
                <dd>{stages[detail.id]}</dd>
              </div>
            </dl>
            <Button asChild variant="ink" size="ink" className="w-full">
              <Link href={moduleHref("cotizaciones")}>
                Ver cotización <span aria-hidden>→</span>
              </Link>
            </Button>
            <form method="dialog" className="w-full">
              <Button variant="ink" size="ink" className="w-full">
                Cerrar
              </Button>
            </form>
            <p>Datos ficticios · No se guarda ningún cambio</p>
          </div>
        )}
      </dialog>
    </>
  );
}
