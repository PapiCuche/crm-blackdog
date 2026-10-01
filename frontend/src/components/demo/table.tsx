import type { ReactNode } from "react";

import type { TableData } from "./data";
import { Avatar } from "./sidebar";

// Tabla del workspace (Figma: Contactos, Catálogo, …). Primera celda con avatar de dos letras,
// última celda como etiqueta. Columnas iguales dentro del margen de 18/14 px del diseño; la
// línea bajo la cabecera ocupa todo el ancho de la tarjeta.
export function DemoTable({
  caption,
  data,
  empty,
}: {
  caption: string;
  data: TableData;
  empty?: ReactNode;
}) {
  const count = data.columns.length;
  return (
    <div className="border-gd-edge/8 after:border-gd-edge/8 relative overflow-x-auto rounded-[8px] border pr-3.5 pl-[18px] after:pointer-events-none after:absolute after:inset-x-0 after:top-[45px] after:border-b">
      <table className="w-full min-w-[720px] table-fixed text-left">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="h-[45px]">
            {data.columns.map((column) => (
              <th key={column} scope="col" className="pt-2 font-normal">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.join("|")} className="h-[66px]">
              {row.map((cell, index) =>
                index === 0 ? (
                  <th key={index} scope="row" className="pt-1.5 pr-2 font-normal">
                    <span className="flex items-center gap-2.5">
                      <Avatar>{cell.slice(0, 2).toUpperCase()}</Avatar>
                      {cell}
                    </span>
                  </th>
                ) : (
                  <td key={index} className="pt-1.5 pr-2">
                    {index === count - 1 ? (
                      <span className="bg-gd-surface inline-block rounded-[4px] px-2.5 py-[3px]">
                        {cell}
                      </span>
                    ) : (
                      cell
                    )}
                  </td>
                ),
              )}
            </tr>
          ))}
          {data.rows.length === 0 && (
            <tr className="h-[66px]">
              <td colSpan={count}>{empty}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
