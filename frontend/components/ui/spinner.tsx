import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn("inline-block h-3.5 w-3.5 animate-spin rounded-full border-[1.5px] border-fg-subtle border-t-accent", className)}
    />
  );
}
