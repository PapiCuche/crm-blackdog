"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { type Contact, CONTACTS, moduleHref, usd } from "./data";
import { Avatar } from "./sidebar";

type Message = { from: "client" | "team"; text: string; meta: string };

function initialThread(contact: Contact): Message[] {
  const first = contact.name.split(" ")[0];
  // Camila conserva el texto literal del Figma (5:370); el resto sigue el mismo patrón.
  const product = contact.id === "camila-torres" ? "Consultoría estratégica" : contact.interest;
  return [
    {
      from: "client",
      text: `Hola, quisiera información sobre el ${product}.\n¿Tienen disponibilidad?`,
      meta: "10:42",
    },
    {
      from: "team",
      text: `¡Hola, ${first}! Claro, te ayudo a encontrar\nla mejor opción.`,
      meta: "10:43 · Leído",
    },
  ];
}

const BOX = "border-gd-edge/8 border";

// Inbox del Figma (5:370): lista, conversación y ficha. El chat es local: nada sale del navegador.
export function Inbox() {
  const [selectedId, setSelectedId] = useState(CONTACTS[0]!.id);
  const [threads, setThreads] = useState(() =>
    Object.fromEntries(CONTACTS.map((contact) => [contact.id, initialThread(contact)])),
  );
  const [draft, setDraft] = useState("");
  const contact = CONTACTS.find((item) => item.id === selectedId) ?? CONTACTS[0]!;
  const suggestion = `${contact.interest} por ${usd(contact.value)}.`;

  function send(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    const time = new Date().toLocaleTimeString("es-PE", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    setThreads((current) => ({
      ...current,
      [contact.id]: [
        ...(current[contact.id] ?? []),
        { from: "team", text, meta: `${time} · Local` },
      ],
    }));
    setDraft("");
  }

  return (
    <div
      className={`${BOX} mt-[22px] grid overflow-hidden rounded-[10px] lg:min-h-[623px] lg:grid-cols-[282px_minmax(0,1fr)_224px]`}
    >
      <nav aria-label="Conversaciones" className="border-gd-edge/8 lg:border-r">
        <ul>
          {CONTACTS.map((item, index) => (
            <li key={item.id}>
              <button
                type="button"
                aria-current={item.id === contact.id ? "true" : undefined}
                onClick={() => {
                  setSelectedId(item.id);
                  setDraft("");
                }}
                className={cn(
                  BOX,
                  "flex h-[94px] w-full items-start gap-[11px] px-[17px] pt-[23px] text-left",
                  item.id === contact.id && "bg-gd-canvas",
                )}
              >
                <Avatar>{item.initials}</Avatar>
                <span className="min-w-0">
                  <span className="block truncate">{item.name}</span>
                  <span className="block truncate">{item.interest}</span>
                  <span className="block truncate">Sandbox · Hace {index + 1} min</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <section aria-label={`Conversación con ${contact.name}`} className="flex min-w-0 flex-col">
        <div className="flex items-center gap-3.5 px-[22px] py-4">
          <Avatar>{contact.initials}</Avatar>
          <p>
            <span className="block">{contact.name}</span>
            <span className="block">Conversación de Sandbox</span>
          </p>
        </div>
        <div className={`${BOX} flex flex-1 flex-col px-6 pt-5 pb-[19px]`}>
          <p className="text-center">Hoy · Demostración</p>
          <ol aria-live="polite" className="mt-[15px] flex flex-col gap-6">
            {(threads[contact.id] ?? []).map((message, index) => (
              <li
                key={index}
                className={cn(
                  BOX,
                  "max-w-full rounded-[8px] pt-[13px] pr-[3px] pl-[15px] leading-[21px] whitespace-pre-line",
                  message.from === "team" ? "w-[416px] self-end" : "w-[434px]",
                )}
              >
                <span className="sr-only">
                  {message.from === "team" ? "Equipo: " : "Cliente: "}
                </span>
                {message.text}
                <span className="block text-right">{message.meta}</span>
              </li>
            ))}
          </ol>
          <div className={`${BOX} mt-[23px] rounded-[6px] px-[18px] pt-3 pb-1.5 leading-[19px]`}>
            <p>
              <span aria-hidden className="inline-block align-[-1px] text-[19px] leading-none">
                ◇
              </span>{" "}
              Copiloto comercial
            </p>
            <p className="mt-1">Ejemplo: {suggestion}</p>
            <p>Verifica precio y stock antes de enviar.</p>
            <button type="button" className="hover:underline" onClick={() => setDraft(suggestion)}>
              Usar sugerencia
            </button>
          </div>
        </div>
        <form onSubmit={send} className="flex flex-col gap-[15px] px-6 pt-5 pb-[21px]">
          <label htmlFor="gd-reply">Respuesta · Sandbox</label>
          <textarea
            id="gd-reply"
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey)
                event.currentTarget.form?.requestSubmit();
            }}
            placeholder="Escribe una respuesta…"
            className="placeholder:text-gd-foreground w-full resize-none bg-transparent"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p>No se envía a ningún canal externo</p>
            <Button
              type="submit"
              variant="honey"
              size="honey"
              className="w-[125px] border-transparent"
            >
              Enviar <span aria-hidden>↗</span>
            </Button>
          </div>
        </form>
      </section>

      <aside
        aria-label="Ficha del contacto"
        className="border-gd-edge/8 border-t pt-[31px] pb-6 pl-[25px] lg:border-t-0 lg:border-l"
      >
        <Avatar>{contact.initials}</Avatar>
        <p className="mt-[13px] text-[16px]">{contact.name}</p>
        <p className="mt-[7px]">Contacto de demostración</p>
        <dl className="mt-[35px] flex flex-col gap-[39px]">
          <div>
            <dt>INTERÉS</dt>
            <dd>{contact.interest}</dd>
          </div>
          <div>
            <dt>OPORTUNIDAD</dt>
            <dd>{usd(contact.value)}</dd>
          </div>
          <div>
            <dt>ASIGNADO A</dt>
            <dd>Andrea López</dd>
          </div>
        </dl>
        <p className="mt-[74px]">
          <span className="sr-only">Etapa: </span>
          <span className="bg-gd-surface inline-block rounded-[4px] px-2.5 py-[3px]">
            {contact.stage}
          </span>
        </p>
        <Button asChild variant="honey" size="honey" className="mt-10 w-[175px]">
          <Link href={moduleHref("cotizaciones")}>
            Ver cotización <span aria-hidden>↗</span>
          </Link>
        </Button>
      </aside>
    </div>
  );
}
