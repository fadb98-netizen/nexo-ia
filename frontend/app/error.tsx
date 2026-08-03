"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  React.useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3 bg-bg px-4 text-center">
      <p className="text-sm font-medium text-fg">Algo se rompió en la aplicación.</p>
      <p className="max-w-md text-xs text-fg-subtle">
        Fue un error inesperado en la interfaz, no se perdió ningún dato. Podés intentar de nuevo.
      </p>
      <Button size="sm" onClick={() => reset()}>
        Reintentar
      </Button>
    </div>
  );
}
