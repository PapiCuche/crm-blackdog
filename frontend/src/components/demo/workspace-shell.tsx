import type { ReactNode } from "react";

import type { DemoModule } from "./data";
import { MobileNav } from "./mobile-nav";
import { Avatar, Sidebar } from "./sidebar";

// Workspace del Figma GOOD DOGGY: barra lateral de 224, barra superior de 70 y contenido.
export function WorkspaceShell({ active, children }: { active: DemoModule; children: ReactNode }) {
  return (
    <div className="bg-gd-surface flex min-h-dvh leading-[1.34]">
      <a
        href="#workspace"
        className="bg-gd-foreground text-gd-paper sr-only z-50 rounded-[16px] px-4 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Saltar al contenido
      </a>
      <aside className="sticky top-0 hidden h-dvh shrink-0 lg:block">
        <Sidebar active={active} />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-gd-edge/8 flex h-[60px] shrink-0 items-center justify-between border-b px-4 pt-2 lg:h-[70px] lg:border-l lg:pr-7 lg:pl-[34px]">
          <div className="flex items-center gap-1.5">
            <MobileNav active={active} />
            <p>Workspace › {active.label}</p>
          </div>
          <div className="flex items-center gap-6">
            <p className="hidden lg:block">Demo interactiva</p>
            <Avatar>AL</Avatar>
          </div>
        </header>
        <main
          id="workspace"
          tabIndex={-1}
          className="flex-1 px-4 pt-[31px] pb-6 focus-visible:outline-none lg:pt-[34px] lg:pr-9 lg:pl-[34px]"
        >
          {children}
        </main>
        <footer className="flex flex-wrap justify-between gap-x-6 gap-y-1 px-4 pb-[22px] lg:pr-[116px] lg:pl-[34px]">
          <p>GOOD DOGGY · Diseñado para conversaciones que importan.</p>
          <p>Prototipo visual / USD / UTC-5</p>
        </footer>
      </div>
    </div>
  );
}
