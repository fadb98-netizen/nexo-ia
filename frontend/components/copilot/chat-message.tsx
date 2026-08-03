import { Badge } from "@/components/ui/badge";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { ETIQUETAS_DIMENSION, type ChatResponse, type Dimension } from "@/types";

const TONO_EVIDENCIA: Record<string, "positive" | "warning" | "neutral"> = {
  alta: "positive",
  media: "warning",
  baja: "neutral",
};

export function UserBubble({ texto }: { texto: string }) {
  return (
    <div className="ml-6 rounded-lg rounded-tr-sm bg-accent/15 px-3 py-2 text-sm text-fg">{texto}</div>
  );
}

export function AssistantResponse({ respuesta }: { respuesta: ChatResponse }) {
  return (
    <div className="mr-2 space-y-2.5 rounded-lg rounded-tl-sm border border-border bg-bg-subtle p-3 text-sm">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge tone={TONO_EVIDENCIA[respuesta.nivel_evidencia] ?? "neutral"}>Evidencia {respuesta.nivel_evidencia}</Badge>
        <Badge tone={respuesta.origen === "ia" ? "accent" : "neutral"}>{respuesta.origen === "ia" ? "Investigado por IA" : "Determinístico (Python)"}</Badge>
        {respuesta.hay_causa_dominante ? (
          <Badge tone="positive">Causa dominante</Badge>
        ) : (
          <Badge tone="neutral">Sin causa única dominante</Badge>
        )}
      </div>

      {respuesta.segmento.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {respuesta.segmento.map((s, i) => (
            <span key={i} className="rounded-sm bg-bg-inset px-1.5 py-0.5 text-[10px] text-fg-subtle">
              {ETIQUETAS_DIMENSION[s.dimension as Dimension] ?? s.dimension}: <span className="text-fg-muted">{s.valor}</span>
            </span>
          ))}
        </div>
      )}

      <p className="leading-relaxed text-fg">{respuesta.que_ocurrio}</p>
      <p className="leading-relaxed text-fg-muted">{respuesta.cuanto_explica}</p>

      {respuesta.metricas_respaldo.length > 0 && (
        <div className="grid grid-cols-2 gap-1 rounded-md bg-bg-inset p-2">
          {respuesta.metricas_respaldo.map((m, i) => (
            <div key={i} className="text-[11px]">
              <span className="text-fg-subtle">{m.nombre}: </span>
              <span className="tabular text-fg-muted">{m.valor}</span>
            </div>
          ))}
        </div>
      )}

      {respuesta.ranking.length > 0 && (
        <table className="w-full border-collapse text-[11px]">
          <tbody>
            {respuesta.ranking.map((item, i) => (
              <tr key={i} className="border-b border-border-subtle last:border-0">
                <td className="py-1 pr-2 text-fg-subtle">{i + 1}.</td>
                <td className="py-1 pr-2 text-fg">
                  {item.segmento.map((s) => s.valor).join(" × ")}
                </td>
                <td className="py-1 text-right tabular text-fg-muted">
                  {item.metrica}: {item.valor}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="text-xs leading-relaxed text-fg-subtle">{respuesta.evolucion_semanal}</p>

      {respuesta.limitaciones && (
        <p className="rounded-md border border-warning/20 bg-warning/5 px-2 py-1.5 text-xs leading-relaxed text-warning">
          {respuesta.limitaciones}
        </p>
      )}

      {respuesta.graficos.map((g, i) => (
        <div key={i} className="rounded-md border border-border-subtle p-2">
          <div className="mb-1 text-[11px] font-medium text-fg-muted">{g.titulo}</div>
          {g.datos ? <ChartRenderer data={g.datos} height={160} /> : <p className="text-[11px] text-fg-subtle">{g.error}</p>}
        </div>
      ))}
    </div>
  );
}
