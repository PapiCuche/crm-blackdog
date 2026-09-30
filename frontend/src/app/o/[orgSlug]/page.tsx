import { getTranslations } from "next-intl/server";

export default async function WorkspacePage() {
  const t = await getTranslations("shell");
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-xl font-semibold tracking-tight">{t("workspaceTitle")}</h1>
      <p className="text-muted">{t("workspaceEmpty")}</p>
    </section>
  );
}
