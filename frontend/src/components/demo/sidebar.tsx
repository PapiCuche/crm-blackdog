import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { DEMO_HOME, type DemoModule, moduleHref, MODULES } from "./data";

export function Avatar({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "bg-gd-surface flex size-8 shrink-0 items-center justify-center rounded-full",
        className,
      )}
    >
      {children}
    </span>
  );
}

// Barra lateral del workspace (Figma 5:212): se usa fija en escritorio y dentro del menú móvil.
export function Sidebar({ active }: { active: DemoModule }) {
  return (
    <div className="bg-gd-canvas flex h-full w-56 flex-col overflow-y-auto">
      <Link href={DEMO_HOME} className="flex gap-1 px-6 pt-[26px]" aria-label="GOOD DOGGY: inicio">
        <span className="text-[27px] leading-[35px]">GD</span>
        <span className="flex flex-col gap-[5px]">
          <span className="text-[16px]">GOOD DOGGY</span>
          <span className="pl-0.5">WORKSPACE</span>
        </span>
      </Link>
      <div className="border-gd-edge/8 mx-4 mt-[21px] flex h-[62px] shrink-0 items-center gap-2.5 rounded-[8px] border px-2">
        <Avatar>GD</Avatar>
        <p className="min-w-0 leading-[21px]">
          <span className="block truncate">Mi organización</span>
          <span className="block truncate">Espacio de demostración</span>
        </p>
      </div>
      <p id="gd-nav-label" className="mt-5 px-7">
        ESPACIO DE TRABAJO
      </p>
      <nav aria-labelledby="gd-nav-label" className="mx-4 mt-3">
        <ul className="flex flex-col gap-[5px]">
          {MODULES.map((module) => {
            const current = module.slug === active.slug;
            return (
              <li key={module.slug}>
                <Link
                  href={moduleHref(module.slug)}
                  aria-current={current ? "page" : undefined}
                  className={cn(
                    "flex h-[37px] items-center gap-[11px] rounded-[8px] border border-transparent px-[11px]",
                    current ? "border-gd-edge/8 bg-gd-honey" : "hover:bg-gd-surface",
                  )}
                >
                  <span
                    aria-hidden
                    className={cn(
                      "size-3 rounded-[3px]",
                      current ? "bg-gd-paper" : "bg-gd-foreground",
                    )}
                  />
                  {module.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="mt-auto flex items-center gap-2.5 px-[26px] pt-6 pb-[21px]">
        <Avatar>AL</Avatar>
        <p className="min-w-0 leading-[21px]">
          <span className="block truncate">Andrea López</span>
          <span className="block truncate">Equipo comercial · Demo</span>
        </p>
      </div>
    </div>
  );
}
