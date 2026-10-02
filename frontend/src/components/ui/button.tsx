import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

// shadcn/ui (new-york) con el lenguaje del Figma GOOD DOGGY. `primary` (tinta), `accent`
// (miel) y `ghost` son los de las pantallas oficiales: responden a la pulsación con una escala
// breve. `ink` y `honey` son los de la demo congelada y no cambian.
const PRESS =
  "transition-[color,background-color,border-color,scale] duration-150 ease-(--ease-out) active:scale-[0.97]";
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: `bg-foreground text-surface hover:bg-foreground/85 rounded-[12px] ${PRESS}`,
        accent: `border-foreground/10 bg-accent text-accent-foreground hover:border-foreground/40 border ${PRESS}`,
        ghost: `text-muted hover:bg-surface-raised hover:text-foreground ${PRESS}`,
        // Demo visual (Figma GOOD DOGGY): "Honey Button" oscuro; el hover invierte el color.
        ink: "border-gd-edge bg-gd-foreground text-gd-paper hover:bg-gd-paper hover:text-gd-foreground rounded-[16px] border text-[16px] drop-shadow-[0_1px_4px_rgba(32,32,32,0.12)]",
        // Acción del workspace de la demo: etiqueta a la izquierda y flecha a la derecha.
        honey:
          "border-gd-edge/8 bg-gd-honey text-gd-foreground hover:border-gd-edge/40 justify-between rounded-[6px] border text-[15px] font-normal",
      },
      size: {
        default: "h-9 px-4",
        lg: "h-11 rounded-[14px] px-5 text-[15px]",
        icon: "size-9",
        ink: "h-11 px-5",
        honey: "h-10 px-4",
      },
    },
    defaultVariants: { variant: "ghost", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "button";
  return <Component className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
