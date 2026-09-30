import { getTranslations } from "next-intl/server";

import { HealthStatus } from "@/components/health-status";
import { backendHealth } from "@/lib/health";

export const dynamic = "force-dynamic"; // se consulta en cada petición, nunca en el build

export default async function HomePage() {
  const t = await getTranslations("health");
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
      <HealthStatus label={t("backend")} status={await backendHealth()} />
    </main>
  );
}
