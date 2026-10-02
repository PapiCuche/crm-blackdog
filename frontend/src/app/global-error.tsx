"use client";

import "./globals.css";

import messages from "../../messages/es-PE.json";
import { dmSans } from "./fonts";

// Error en el propio layout raíz: sustituye a <html>. La pantalla de serie de Next inserta un
// <style> sin nonce, que la CSP bloquea. Sin proveedor de i18n: lee el catálogo directamente.
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  const t = messages.errors;
  return (
    <html lang="es-PE" className={dmSans.variable}>
      <body>
        <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-4 p-8">
          <h1 className="text-2xl font-semibold tracking-tight">{t.errorTitle}</h1>
          <p role="alert" className="text-muted">
            {t.errorBody}
          </p>
          <button
            type="button"
            onClick={reset}
            className="bg-foreground text-surface hover:bg-foreground/85 h-9 self-start rounded-[12px] px-4 text-sm font-medium transition-colors"
          >
            {t.retry}
          </button>
        </main>
      </body>
    </html>
  );
}
