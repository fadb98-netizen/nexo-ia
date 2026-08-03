"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "outline" | "ghost" | "subtle";
type Size = "sm" | "md" | "icon";

const variantClasses: Record<Variant, string> = {
  default: "bg-accent text-accent-fg hover:brightness-110",
  outline: "border border-border bg-transparent text-fg hover:bg-bg-subtle",
  ghost: "bg-transparent text-fg-muted hover:bg-bg-subtle hover:text-fg",
  subtle: "bg-bg-subtle text-fg hover:bg-bg-inset border border-border-subtle",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-8 px-3 text-sm gap-1.5",
  icon: "h-7 w-7 p-0",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium transition-colors duration-100 disabled:opacity-40 disabled:pointer-events-none whitespace-nowrap",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";
