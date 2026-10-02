import { getTranslations } from "next-intl/server";

export default async function WorkspacePage() {
  const t = await getTranslations("shell");
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-[28px] leading-tight font-bold tracking-[0.02em]">
        {t("workspaceTitle")}
      </h1>
      <p className="text-muted">{t("workspaceEmpty")}</p>
    </section>
  );
}
