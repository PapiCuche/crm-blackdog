import { DM_Sans } from "next/font/google";

// Fuente del Figma GOOD DOGGY (D-F2-7). `next/font` la descarga en el build y la sirve desde
// el propio origen: la CSP no necesita ningún dominio de fuentes.
export const dmSans = DM_Sans({ subsets: ["latin"], axes: ["opsz"], variable: "--font-dm-sans" });
