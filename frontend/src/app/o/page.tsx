import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { AuthCard } from "@/components/auth/auth-card";
import { OrganizationList } from "@/components/auth/organization-list";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations();
  return { title: `${t("organizations.pageTitle")} · ${t("app.name")}` };
}

// `?elegir` muestra la lista aunque haya una sola organización (para cambiar de una a otra).
export default async function OrganizationsPage({
  searchParams,
}: {
  searchParams: Promise<{ elegir?: string }>;
}) {
  const t = await getTranslations("organizations");
  const { elegir } = await searchParams;
  return (
    <AuthCard eyebrow={t("eyebrow")} title={t("title")}>
      <OrganizationList choose={elegir !== undefined} />
    </AuthCard>
  );
}
