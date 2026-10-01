import Link from "next/link";

import { Button } from "@/components/ui/button";

import { CONTACTS, KPIS, moduleHref, usd, WEEK_SALES } from "./data";
import { Avatar } from "./sidebar";
import { DemoTable } from "./table";

const BAR_SCALE = 0.02; // px por USD: 7100 → 142 px, como en el Figma
const CARD = "border-gd-edge/8 border";

// Resumen y Reportes comparten composición en el Figma (5:212 y 10:160); móvil en 5:2183.
export function Dashboard() {
  const recent = CONTACTS[0]!;
  return (
    <>
      <ul className="mt-[19px] grid grid-cols-2 gap-4 xl:grid-cols-4">
        {KPIS.map((kpi) => (
          <li key={kpi.label} className={`${CARD} rounded-[9px] p-[15px] pb-3.5 md:p-[18px]`}>
            <p>
              <span className="md:hidden">{kpi.short}</span>
              <span className="hidden md:inline">{kpi.label}</span>
            </p>
            <p className="mt-[15px] text-[25px] leading-[1.3] md:mt-[14px] md:text-[31px] md:font-bold">
              {kpi.value}
            </p>
            <p className="mt-[13px] flex items-baseline md:mt-[6px]">
              <span className="bg-gd-surface min-w-16 rounded-[4px] pl-2.5">{kpi.delta}</span>
              <span className="ml-2.5 hidden md:inline">vs. mes anterior</span>
            </p>
          </li>
        ))}
      </ul>

      <div className="mt-[29px] grid gap-[22px] md:mt-6 xl:grid-cols-[742fr_382fr]">
        <section
          aria-labelledby="gd-sales-title"
          className={`${CARD} rounded-[10px] px-[18px] pt-[17px] pb-[19px] md:px-[22px] md:pb-6`}
        >
          <div className="flex justify-between gap-4">
            <div>
              <h2 id="gd-sales-title" className="text-[17px] md:text-[18px]">
                El ritmo de tus ventas
              </h2>
              <p className="mt-2 hidden md:block">Ingresos de demostración · últimos 7 días</p>
            </div>
            <p className="mt-[11px] mr-[26px] hidden md:block">Esta semana</p>
          </div>
          <ul className="mt-3 flex h-[207px] items-end gap-[21px] overflow-x-auto md:h-[194px] md:gap-[39px] md:pl-[18px]">
            {WEEK_SALES.map((entry) => (
              <li key={entry.day} className="flex w-[25px] shrink-0 flex-col md:w-14">
                <span className="hidden whitespace-nowrap md:block">USD {entry.value}</span>
                <span className="sr-only md:hidden">USD {entry.value}</span>
                <span
                  aria-hidden
                  className="bg-gd-honey block rounded-[3px] md:rounded-[4px]"
                  style={{ height: entry.value * BAR_SCALE }}
                />
                <span className="mt-3 md:mt-[14px] md:text-center">
                  <span className="md:hidden">{entry.day.charAt(0)}</span>
                  <span className="hidden md:inline">{entry.day}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section
          aria-labelledby="gd-next-title"
          className={`${CARD} rounded-[10px] px-6 pt-[27px] pb-[18px]`}
        >
          <p className="bg-gd-surface inline-block rounded-[4px] px-2.5 py-[3px]">
            TU PRÓXIMO PASO
          </p>
          <h2 id="gd-next-title" className="mt-[11px] text-[26px] leading-[36px]">
            Las buenas ventas
            <br />
            empiezan con atención.
          </h2>
          <p className="mt-[18px]">Hay 3 clientes esperando un seguimiento.</p>
          <Button asChild variant="honey" size="honey" className="mt-[19px] w-[224px]">
            <Link href={moduleHref("tareas")}>
              Revisar seguimientos <span aria-hidden>↗</span>
            </Link>
          </Button>
          <div className="mt-[21px] flex items-center">
            <Avatar>AL</Avatar>
            <Avatar className="-ml-[9px]">MR</Avatar>
            <p className="ml-[22px]">Tu equipo está en movimiento</p>
          </div>
        </section>
      </div>

      <h2 className="mt-[27px] pl-[22px] text-[17px]">Oportunidades recientes</h2>
      <div className="mt-[17px]">
        <DemoTable
          caption="Oportunidades recientes"
          data={{
            columns: ["Contacto", "Producto", "Valor", "Etapa"],
            rows: [[recent.name, recent.interest, usd(recent.value), recent.stage]],
          }}
        />
      </div>
    </>
  );
}
