import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

import { AccessDialog } from "./access-dialog";
import { DEMO_HOME, type ModuleSlug, moduleHref, WORKSPACE_HOME } from "./data";
import heroTeam from "./hero-team.webp";
import { LivePreview } from "./live-preview";

// Landing del Figma GOOD DOGGY (5:108, "GD-00-Landing"): ancho de diseño 1440 con margen de 120.
const CONTAINER = "mx-auto w-full max-w-[1440px] px-6 lg:px-[120px]";
const ACTION = "text-[15px] font-normal"; // las instancias del landing usan 15 px Regular
const CARD = "border-gd-foreground bg-gd-paper border shadow-[0_1px_8px_rgba(32,32,32,0.12)]";

const NAV = [
  { href: "#producto", label: "Producto" },
  { href: "#funcionalidades", label: "Funcionalidades" },
  { href: "#equipo", label: "Para tu equipo" },
] as const;

const FEATURES: readonly { label: string; slug: ModuleSlug }[] = [
  { label: "Inbox", slug: "inbox" },
  { label: "Contactos", slug: "contactos" },
  { label: "Pipeline", slug: "pipeline" },
  { label: "Propuestas", slug: "cotizaciones" },
  { label: "Tareas", slug: "tareas" },
  { label: "Copiloto IA", slug: "agentes-ia" },
];

const BENTO: readonly {
  eyebrow: string;
  title: string;
  rows: readonly (readonly [string, string])[];
  slug: ModuleSlug;
}[] = [
  {
    eyebrow: "CONVERSACIONES",
    title: "Escucha primero.",
    rows: [
      ["Una bandeja compartida", "Reúne mensajes y responsables."],
      ["Todo el contexto", "La historia del cliente, a mano."],
    ],
    slug: "inbox",
  },
  {
    eyebrow: "OPORTUNIDADES",
    title: "Avanza con claridad.",
    rows: [
      ["El siguiente paso visible", "Cada propuesta en su etapa."],
      ["Seguimiento compartido", "Tu equipo sabe qué hacer."],
    ],
    slug: "pipeline",
  },
  {
    eyebrow: "COPILOTO IA",
    title: "Decide con criterio.",
    rows: [
      ["Sugerencias con contexto", "Una ayuda para preparar respuestas."],
      ["La decisión sigue siendo tuya", "Revisión humana antes de actuar."],
    ],
    slug: "agentes-ia",
  },
];

function Section({
  id,
  eyebrow,
  title,
  description,
  honey = false,
  children,
}: {
  id?: string;
  eyebrow: string;
  title: ReactNode;
  description: string;
  honey?: boolean;
  children: ReactNode;
}) {
  return (
    <section id={id} className={honey ? "bg-gd-honey" : "bg-gd-paper"}>
      <div className={`${CONTAINER} flex flex-col items-start gap-6 py-16`}>
        <p>{eyebrow}</p>
        <h2 className="max-w-[1100px] text-[clamp(30px,3.34vw,48px)] font-bold tracking-[0.02em]">
          {title}
        </h2>
        <p className="max-w-[720px] text-[17px]">{description}</p>
        {children}
      </div>
    </section>
  );
}

export function Landing() {
  return (
    <div className="leading-[1.5]">
      <a
        href="#contenido"
        className="bg-gd-foreground text-gd-paper sr-only z-50 rounded-[16px] px-4 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Saltar al contenido
      </a>
      <div id="producto" className="bg-gd-honey">
        <header className={`${CONTAINER} flex items-center justify-between gap-4 pt-7`}>
          <Link href={DEMO_HOME} className="text-[18px] leading-[1.15] whitespace-nowrap">
            GD / GOOD DOGGY
          </Link>
          <nav aria-label="Secciones" className="hidden w-[450px] gap-9 md:flex">
            {NAV.map((item) => (
              <a key={item.href} href={item.href} className="hover:underline">
                {item.label}
              </a>
            ))}
          </nav>
          <AccessDialog />
        </header>
        <main id="contenido" tabIndex={-1} className="focus-visible:outline-none">
          <div className={`${CONTAINER} pt-[58px] pb-[87px]`}>
            <div className="flex flex-col items-center gap-[18px]">
              <p className="text-center">RELACIONES REALES. UN ESPACIO COMPARTIDO.</p>
              <h1 className="text-center text-[clamp(52px,10.42vw,150px)] leading-[1.15] font-bold tracking-[-0.01em] whitespace-nowrap">
                GOOD DOGGY
              </h1>
              <p className="w-full max-w-[780px] text-[18px]">
                Cuida cada conversación. Haz crecer cada relación.
                <br />
                Un CRM para tu equipo, tus clientes y tu próximo paso.
              </p>
              <div className="flex flex-wrap justify-center gap-4">
                <Button asChild variant="ink" size="ink" className={`w-[196px] ${ACTION}`}>
                  <Link href={WORKSPACE_HOME}>
                    Explorar el CRM <span aria-hidden>↗</span>
                  </Link>
                </Button>
                <Button asChild variant="ink" size="ink" className={`w-[178px] ${ACTION}`}>
                  <Link href={moduleHref("inbox")}>
                    Abrir Inbox <span aria-hidden>→</span>
                  </Link>
                </Button>
              </div>
              <p className="text-center">DEMO INTERACTIVA · DATOS FICTICIOS · SIN REGISTRO</p>
            </div>
            <div className="mt-[42px] grid gap-10 lg:grid-cols-[520fr_620fr] lg:pr-5">
              <Image
                src={heroTeam}
                alt="Tres personas de un equipo conversan alrededor de una mesa con una laptop."
                width={520}
                height={354}
                sizes="(min-width: 1024px) 520px, 100vw"
                priority
                unoptimized
                className="h-[354px] w-full rounded-[24px] object-cover"
              />
              <div>
                <LivePreview />
                <p className="mt-[26px]">EXPLORA LAS PESTAÑAS · INBOX / PIPELINE / IA</p>
              </div>
            </div>
          </div>
        </main>
      </div>

      <Section
        id="funcionalidades"
        eyebrow="01 / TODO CONECTADO"
        title="Cada relación tiene su propio ritmo."
        description="Seis herramientas que comparten contexto, para que tu equipo avance con claridad."
      >
        <ul className="grid w-full grid-cols-2 gap-8 sm:grid-cols-3 lg:grid-cols-6">
          {FEATURES.map((feature, index) => (
            <li key={feature.slug}>
              <Link href={moduleHref(feature.slug)} className="flex flex-col items-center gap-4">
                <span
                  aria-hidden
                  className={`${CARD} flex size-16 items-center justify-center rounded-[24px] text-[16px]`}
                >
                  {String(index + 1).padStart(2, "0")}
                </span>
                {feature.label}
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="equipo"
        eyebrow="02 / TU EQUIPO, EN SINCRONÍA"
        title="El contexto hace la diferencia."
        description="De la primera conversación al próximo paso. Sin perder la historia por el camino."
      >
        <ul className="grid w-full gap-6 lg:grid-cols-3">
          {BENTO.map((card) => (
            <li
              key={card.slug}
              className={`${CARD} flex flex-col items-start gap-3.5 rounded-[24px] p-6`}
            >
              <p>{card.eyebrow}</p>
              <h3 className="text-[24px] leading-[1.15]">{card.title}</h3>
              {card.rows.map(([rowTitle, detail]) => (
                <div key={rowTitle} className="flex flex-col gap-1">
                  <p>{rowTitle}</p>
                  <p>{detail}</p>
                </div>
              ))}
              <Button asChild variant="ink" size="ink" className={`w-[220px] ${ACTION}`}>
                <Link href={moduleHref(card.slug)} aria-label={`Explorar módulo: ${card.eyebrow}`}>
                  Explorar módulo <span aria-hidden>→</span>
                </Link>
              </Button>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        honey
        eyebrow="03 / HAZ ESPACIO PARA LO QUE IMPORTA"
        title={
          <>
            Tu equipo. Tus clientes.
            <br />
            Una mejor relación.
          </>
        }
        description="GOOD DOGGY es un CRM independiente para equipos y organizaciones."
      >
        <Button asChild variant="ink" size="ink" className={`w-[244px] ${ACTION}`}>
          <Link href={WORKSPACE_HOME}>
            Entrar a la demostración <span aria-hidden>↗</span>
          </Link>
        </Button>
        <p>Prototipo de producto. No envía mensajes ni procesa pagos.</p>
      </Section>

      <footer className={`${CONTAINER} flex flex-wrap items-start justify-between gap-4 py-10`}>
        <p className="text-[18px] leading-[1.15]">GOOD DOGGY</p>
        <p>Hecho para cuidar relaciones.</p>
      </footer>
    </div>
  );
}
