import Link from "next/link";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

// Página 404 propia: la de serie de Next inserta un <style> sin nonce, que la CSP bloquea.
export default function NotFound() {
  const t = useTranslations("errors");
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">{t("notFoundTitle")}</h1>
      <p className="text-muted">{t("notFoundBody")}</p>
      <Button asChild variant="primary" className="self-start">
        <Link href="/">{t("backHome")}</Link>
      </Button>
    </main>
  );
}
