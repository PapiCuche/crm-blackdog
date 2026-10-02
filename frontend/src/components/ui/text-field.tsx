import { type ComponentProps, useId } from "react";

import { cn } from "@/lib/utils";

type Props = ComponentProps<"input"> & { label: string; error?: string; hint?: string };

// Campo de texto con su etiqueta. El error sustituye a la ayuda y se anuncia al aparecer.
// 16 px en el control: por debajo, Safari en iOS amplía la página al enfocarlo.
export function TextField({
  label,
  error,
  hint,
  id,
  className,
  "aria-describedby": describedBy,
  ...props
}: Props) {
  const generated = useId();
  const field = id ?? generated;
  const note = error || hint; // un error vacío no es un error
  const described = [describedBy, note ? `${field}-note` : null].filter(Boolean).join(" ");
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={field} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={field}
        aria-invalid={error ? true : undefined}
        aria-describedby={described || undefined}
        className={cn(
          "bg-surface border-foreground/50 placeholder:text-muted h-11 rounded-[10px] border px-3 text-[16px]",
          "focus-visible:border-foreground aria-invalid:border-danger disabled:opacity-60",
          className,
        )}
        {...props}
      />
      {note ? (
        <p
          id={`${field}-note`}
          role={error ? "alert" : undefined}
          className={cn("text-sm", error ? "text-danger" : "text-muted")}
        >
          {note}
        </p>
      ) : null}
    </div>
  );
}
