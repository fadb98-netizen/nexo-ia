"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Periodos, ValidacionReporte } from "@/types";

function rango(semanas: string[]): string {
  if (semanas.length === 0) return "s/d";
  const fmt = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" });
  return `${fmt(semanas[0])} – ${fmt(semanas[semanas.length - 1])}`;
}

export function Header({
  nombreArchivo,
  periodos,
  validacion,
  iaConfigurada,
  onReset,
}: {
  nombreArchivo: string;
  periodos: Periodos;
  validacion: ValidacionReporte;
  iaConfigurada: boolean;
  onReset: () => void;
}) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-bg-subtle/60 px-4 py-2.5 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div className="h-5 w-5 rounded-[5px] bg-accent" />
          <span className="text-sm font-semibold tracking-tight">Nexo IA</span>
        </div>
        <div className="h-4 w-px bg-border" />
        <span className="text-xs text-fg-muted">{nombreArchivo}</span>
        <div className="h-4 w-px bg-border" />
        <span className="text-xs text-fg-subtle">
          Reciente <span className="text-fg-muted tabular">{rango(periodos.reciente)}</span> vs. comparativo{" "}
          <span className="text-fg-muted tabular">{rango(periodos.comparativo)}</span>
        </span>
      </div>
      <div className="flex items-center gap-2">
        {validacion.advertencias.length > 0 && (
          <Badge tone="warning" title={validacion.advertencias.join(" | ")}>
            {validacion.advertencias.length} advertencia{validacion.advertencias.length > 1 ? "s" : ""}
          </Badge>
        )}
        <Badge tone={validacion.es_valido ? "positive" : "negative"}>{validacion.es_valido ? "Datos válidos" : "Datos inválidos"}</Badge>
        <Badge tone={iaConfigurada ? "accent" : "neutral"}>{iaConfigurada ? "IA activa" : "Modo determinístico"}</Badge>
        <Button variant="outline" size="sm" onClick={onReset}>
          Nuevo análisis
        </Button>
      </div>
    </header>
  );
}
