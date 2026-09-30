import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell/app-shell";

const ORG_SLUG = /^[-a-zA-Z0-9_]{1,63}$/;

// Rutas de tenant (D3): el slug solo selecciona; la API autoriza (sin auth hasta la Fase 2).
export default async function TenantLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ orgSlug: string }>;
}) {
  const { orgSlug } = await params;
  if (!ORG_SLUG.test(orgSlug)) notFound(); // mismo patrón que el backend (TenantResolutionMiddleware)
  return <AppShell orgSlug={orgSlug}>{children}</AppShell>;
}
