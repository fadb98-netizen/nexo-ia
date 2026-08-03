"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export function UploadScreen({
  onArchivo,
  onDemo,
  cargando,
  error,
}: {
  onArchivo: (f: File) => void;
  onDemo: () => void;
  cargando: boolean;
  error: string | null;
}) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [arrastrando, setArrastrando] = React.useState(false);

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-bg px-4">
      <div className="mb-6 flex items-center gap-2">
        <div className="h-7 w-7 rounded-md bg-accent" />
        <span className="text-lg font-semibold tracking-tight">Nexo IA</span>
      </div>
      <p className="mb-6 max-w-md text-center text-sm text-fg-muted">
        Asistente de análisis comercial. Subí un CSV de pedidos (16 semanas) y Python va a validar,
        calcular 31 cruces de dimensiones y detectar los patrones más relevantes.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onArchivo(f);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex w-full max-w-md cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center transition-colors ${
          arrastrando ? "border-accent bg-accent/5" : "border-border-subtle bg-bg-subtle hover:border-border"
        }`}
      >
        {cargando ? (
          <>
            <Spinner className="h-5 w-5" />
            <span className="text-sm text-fg-muted">Validando y calculando…</span>
          </>
        ) : (
          <>
            <span className="text-sm text-fg">Arrastrá tu CSV acá o hacé click para elegirlo</span>
            <span className="text-xs text-fg-subtle">fecha_pedido, semana, pedido_id, cliente_id, sucursal, asesor, sector_industrial, familia, abc_cliente, usd, kg, posiciones</span>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onArchivo(f);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="mt-4 w-full max-w-md rounded-md border border-negative/30 bg-negative/5 px-3 py-2 text-xs text-negative">
          {error}
        </div>
      )}

      <div className="mt-5 flex items-center gap-2 text-xs text-fg-subtle">
        <span>¿No tenés un archivo a mano?</span>
        <Button variant="outline" size="sm" onClick={onDemo} disabled={cargando}>
          Cargar datos de demo
        </Button>
      </div>
    </div>
  );
}
