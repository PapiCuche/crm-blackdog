import type { Metadata } from "next";
import { DM_Sans } from "next/font/google";
import type { ReactNode } from "react";

// Demo visual (UI-01): prototipo navegable del Figma GOOD DOGGY con datos ficticios. Vive solo
// bajo /demo: no llama a la API ni sustituye las rutas de tenant (/o/[orgSlug]).
const dmSans = DM_Sans({ subsets: ["latin"], axes: ["opsz"], variable: "--font-dm-sans" });

export const metadata: Metadata = {
  title: "GOOD DOGGY · Demo",
  robots: { index: false, follow: false },
};

export default function DemoLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`${dmSans.variable} bg-gd-canvas text-gd-foreground font-gd min-h-dvh scroll-smooth text-[15px] tracking-[0.007em] scheme-light [--ring:var(--gd-foreground)]`}
    >
      {children}
    </div>
  );
}
