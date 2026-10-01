import { useTranslations } from "next-intl";

import type { BackendHealth } from "@/lib/health";
import { cn } from "@/lib/utils";

export function HealthStatus({ label, status }: { label: string; status: BackendHealth }) {
  const t = useTranslations("health");
  return (
    <div className="bg-surface border-border flex items-center justify-between rounded-lg border p-4">
      <span className="font-medium">{label}</span>
      <span role="status" className="flex items-center gap-2 text-sm">
        <span
          aria-hidden
          className={cn("size-2 rounded-full", status === "ok" ? "bg-success" : "bg-danger")}
        />
        {t(status)}
      </span>
    </div>
  );
}
