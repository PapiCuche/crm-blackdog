"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

// Error de render dentro del layout raíz. Sin detalle técnico: va al log del servidor.
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  const t = useTranslations("errors");
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">{t("errorTitle")}</h1>
      <p role="alert" className="text-muted">
        {t("errorBody")}
      </p>
      <Button variant="primary" className="self-start" onClick={reset}>
        {t("retry")}
      </Button>
    </main>
  );
}
