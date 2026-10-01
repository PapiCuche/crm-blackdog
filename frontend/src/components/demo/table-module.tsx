"use client";

import { useState } from "react";

import type { TableData } from "./data";
import { DemoTable } from "./table";

function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

// Módulos de listado: búsqueda local sobre los datos ficticios, con estado vacío.
export function TableModule({ label, data }: { label: string; data: TableData }) {
  const [query, setQuery] = useState("");
  const needle = normalize(query.trim());
  const rows = needle
    ? data.rows.filter((row) => row.some((cell) => normalize(cell).includes(needle)))
    : data.rows;
  const scope = label.toLowerCase();
  return (
    <>
      <div className="mt-[18px] flex flex-wrap items-center justify-between gap-3">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label={`Buscar en ${scope}`}
          placeholder={`⌕ Buscar en ${scope}…`}
          className="border-gd-edge/8 bg-gd-surface placeholder:text-gd-foreground h-10 w-full max-w-[360px] rounded-[6px] border px-[15px]"
        />
        <p className="bg-gd-surface rounded-[4px] pl-2.5 lg:-mr-1.5">Vista de demostración</p>
      </div>
      <p role="status" className="sr-only">
        {needle ? `${rows.length} resultados` : ""}
      </p>
      <div className="mt-[23px]">
        <DemoTable
          caption={label}
          data={{ columns: data.columns, rows }}
          empty={`Sin resultados para «${query.trim()}» en ${scope}.`}
        />
      </div>
    </>
  );
}
