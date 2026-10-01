import { House } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

// App Shell (Sidebar + Topbar + Workspace), desktop-first y responsive. Solo estructura: los
// módulos de negocio (Inbox, Clientes, …) llegan con sus fases desde el diseño de Figma.
export function AppShell({ orgSlug, children }: { orgSlug: string; children: ReactNode }) {
  const t = useTranslations();
  const home = `/o/${orgSlug}`; // slug ya validado por el layout (sin re-codificar)
  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <a
        href="#workspace"
        className="bg-accent text-accent-foreground sr-only z-50 rounded-md px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("app.skipToContent")}
      </a>
      <aside className="border-border bg-surface flex shrink-0 flex-col gap-4 border-b p-3 md:w-60 md:border-r md:border-b-0">
        <span className="text-accent px-2 text-sm font-semibold tracking-wide">
          {t("app.name")}
        </span>
        <nav aria-label={t("shell.navigation")}>
          <Button asChild className="w-full justify-start">
            <Link href={home} aria-current="page">
              <House aria-hidden /> {t("shell.home")}
            </Link>
          </Button>
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border flex h-14 items-center gap-2 border-b px-6">
          <span className="text-muted text-sm">{t("shell.organization")}:</span>
          <span className="truncate font-mono text-sm">{orgSlug}</span>
        </header>
        <main id="workspace" tabIndex={-1} className="flex-1 p-6 focus-visible:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}
