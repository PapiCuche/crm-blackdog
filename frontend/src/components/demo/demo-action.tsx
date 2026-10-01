"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

// "Nueva acción ↗": el Figma no define destino. En la demo solo informa; no crea registros.
export function DemoAction() {
  const [used, setUsed] = useState(false);
  return (
    <div className="relative">
      <Button variant="honey" size="honey" className="w-[164px]" onClick={() => setUsed(true)}>
        Nueva acción <span aria-hidden>↗</span>
      </Button>
      <p role="status" className="top-full right-0 mt-1 md:absolute md:whitespace-nowrap">
        {used ? "Acción de demostración: no crea registros." : ""}
      </p>
    </div>
  );
}
