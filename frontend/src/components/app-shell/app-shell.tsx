import Link from "next/link";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { MobileMenu } from "./mobile-menu";

// Barra lateral del workspace (Figma GOOD DOGGY, 5:212): fija en escritorio y dentro del
// menú en móvil. `label` distingue las dos copias de la navegación para los lectores de pantalla.
function Sidebar({ orgSlug, label }: { orgSlug: string; label: string }) {
  const t = useTranslations();
  return (
    <div className="bg-surface flex h-full w-56 flex-col overflow-y-auto">
      <p className="flex items-center gap-2 px-6 pt-6">
        <span aria-hidden className="text-[27px] leading-none">
          GD
        </span>
        <span className="flex flex-col text-[13px] leading-tight tracking-wide uppercase">
          <span className="text-[15px] font-medium">{t("app.brand")}</span>
          {t("shell.workspace")}
        </span>
      </p>
      <p className="border-border mx-4 mt-5 flex flex-col rounded-lg border px-3 py-2.5 leading-snug">
        <span className="text-muted text-[13px]">{t("shell.organization")}</span>
        <span className="truncate font-mono text-sm">{orgSlug}</span>
      </p>
      <nav aria-label={label} className="mx-4 mt-5">
        <ul className="flex flex-col gap-1">
          <li>
            <Link
              href={`/o/${orgSlug}`} // slug ya validado por el layout (sin re-codificar)
              aria-current="page"
              className="border-foreground/10 bg-accent text-accent-foreground flex h-[37px] items-center gap-3 rounded-lg border px-3"
            >
              <span aria-hidden className="bg-surface size-3 rounded-[3px]" />
              {t("shell.home")}
            </Link>
          </li>
        </ul>
      </nav>
    </div>
  );
}

// App Shell (barra lateral + barra superior + workspace). Solo estructura: los módulos de
// negocio llegan con sus fases, y la navegación por permisos con F2-08.
export function AppShell({ orgSlug, children }: { orgSlug: string; children: ReactNode }) {
  const t = useTranslations();
  return (
    <div className="flex min-h-dvh">
      <a
        href="#workspace"
        className="bg-foreground text-surface sr-only z-50 rounded-[12px] focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:px-4 focus:py-2"
      >
        {t("app.skipToContent")}
      </a>
      <aside className="sticky top-0 hidden h-dvh shrink-0 lg:block">
        <Sidebar orgSlug={orgSlug} label={t("shell.navigation")} />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border flex h-[60px] shrink-0 items-center gap-2 border-b px-4 lg:h-[70px] lg:border-l lg:px-8">
          <MobileMenu
            label={t("shell.menu")}
            title={t("shell.menuTitle")}
            closeLabel={t("shell.closeMenu")}
          >
            <Sidebar orgSlug={orgSlug} label={t("shell.menuNavigation")} />
          </MobileMenu>
          <p className="shrink-0">
            {t("shell.workspace")} › {t("shell.home")}
          </p>
          <span className="text-muted ml-auto min-w-0 truncate font-mono text-sm lg:hidden">
            {orgSlug}
          </span>
        </header>
        <main
          id="workspace"
          tabIndex={-1}
          className="flex-1 px-4 py-8 focus-visible:outline-none lg:px-8"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
