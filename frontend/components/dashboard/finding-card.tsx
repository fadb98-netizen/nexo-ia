import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ETIQUETAS_DIMENSION, type Hallazgo } from "@/types";
import { formatPct } from "@/lib/utils";

const ETIQUETA_TIPO: Record<string, string> = {
  anomalia: "Anomalía",
  tendencia_persistente: "Tendencia persistente",
  segmento_atipico: "Segmento atípico",
  concentrado: "Concentrado",
  generalizado: "Generalizado",
  interaccion_profunda: "Cruce profundo",
  cambio_relevante: "Cambio relevante",
};

const TONO_EVIDENCIA: Record<string, "positive" | "warning" | "neutral"> = {
  alta: "positive",
  media: "warning",
  baja: "neutral",
};

export function FindingCard({ hallazgo, onInvestigar }: { hallazgo: Hallazgo; onInvestigar: (h: Hallazgo) => void }) {
  const contribucion = hallazgo.metricas_respaldo["contribucion_pct"];
  return (
    <div className="animate-slide-up rounded-lg border border-border bg-bg-subtle p-3 hover:border-border-subtle transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone="accent">{ETIQUETA_TIPO[hallazgo.tipo] ?? hallazgo.tipo}</Badge>
          <Badge tone={TONO_EVIDENCIA[hallazgo.nivel_evidencia] ?? "neutral"}>Evidencia {hallazgo.nivel_evidencia}</Badge>
        </div>
        {typeof contribucion === "number" && (
          <span className="whitespace-nowrap text-xs font-medium tabular text-fg-muted">{formatPct(contribucion)} de la variación</span>
        )}
      </div>
      <h4 className="mt-2 text-sm font-medium leading-snug text-fg">{hallazgo.titulo}</h4>
      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-fg-muted">{hallazgo.resumen}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {hallazgo.dimensiones.map((d) => (
          <span key={d} className="rounded-sm bg-bg-inset px-1.5 py-0.5 text-[10px] text-fg-subtle">
            {ETIQUETAS_DIMENSION[d]}
          </span>
        ))}
      </div>
      <div className="mt-2.5 flex justify-end">
        <Button size="sm" variant="subtle" onClick={() => onInvestigar(hallazgo)}>
          Investigar
        </Button>
      </div>
    </div>
  );
}
