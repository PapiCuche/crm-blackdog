import Link from "next/link";

import { Button } from "@/components/ui/button";

import { Dashboard } from "./dashboard";
import { findModule, type ModuleSlug, moduleHref, TABLES } from "./data";
import { DemoAction } from "./demo-action";
import { Inbox } from "./inbox";
import { Pipeline } from "./pipeline";
import { TableModule } from "./table-module";
import { WorkspaceShell } from "./workspace-shell";

function Content({ slug, label }: { slug: ModuleSlug; label: string }) {
  if (slug === "resumen" || slug === "reportes") return <Dashboard />;
  if (slug === "inbox") return <Inbox />;
  if (slug === "pipeline") return <Pipeline />;
  const table = TABLES[slug];
  return table ? <TableModule label={label} data={table} /> : null;
}

// Una pantalla del workspace: cabecera común del Figma + el contenido del módulo.
export function ModuleView({ slug }: { slug: ModuleSlug }) {
  const active = findModule(slug)!;
  const [head, tail] = active.title.split(", "); // en móvil el Figma parte el título tras la coma
  return (
    <WorkspaceShell active={active}>
      <div className="flex flex-col gap-[18px] md:flex-row md:items-start md:justify-between">
        <div>
          <p>GOOD DOGGY / {active.label.toUpperCase()}</p>
          <h1 className="mt-[5px] text-[28px] leading-[33px] md:mt-0.5 md:text-[34px] md:leading-[44px] md:font-bold md:tracking-[0.02em]">
            {head}
            {tail && (
              <>
                , <br className="md:hidden" />
                {tail}
              </>
            )}
          </h1>
          <p className="mt-[14px] md:mt-[5px]">{active.subtitle}</p>
        </div>
        <div className="md:mt-[22px]">
          {slug === "resumen" ? (
            <Button asChild variant="honey" size="honey" className="w-[160px] md:w-[164px]">
              <Link href={moduleHref("pipeline")}>
                Ver pipeline <span aria-hidden>↗</span>
              </Link>
            </Button>
          ) : (
            <DemoAction />
          )}
        </div>
      </div>
      <p className="mt-3.5 md:hidden">Datos ficticios · sin operaciones reales</p>
      <p className="mt-3.5 hidden md:block">
        <span aria-hidden className="inline-block align-[-1px] text-[19px] leading-none">
          ◇
        </span>{" "}
        Prototipo interactivo · Datos ficticios
      </p>
      <Content slug={slug} label={active.label} />
    </WorkspaceShell>
  );
}
