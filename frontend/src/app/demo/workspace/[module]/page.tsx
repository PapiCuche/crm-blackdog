import { notFound } from "next/navigation";

import { findModule, MODULES } from "@/components/demo/data";
import { ModuleView } from "@/components/demo/module-view";

export const dynamicParams = false; // solo los módulos del Figma; el resto responde 404

export function generateStaticParams() {
  return MODULES.filter((m) => m.slug !== "resumen").map((m) => ({ module: m.slug }));
}

export default async function DemoModulePage({ params }: { params: Promise<{ module: string }> }) {
  const found = findModule((await params).module);
  if (!found || found.slug === "resumen") notFound(); // el resumen vive en /demo/workspace
  return <ModuleView slug={found.slug} />;
}
