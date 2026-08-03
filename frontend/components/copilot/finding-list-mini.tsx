import { Badge } from "@/components/ui/badge";
import type { Hallazgo } from "@/types";

const TONO_EVIDENCIA: Record<string, "positive" | "warning" | "neutral"> = {
  alta: "positive",
  media: "warning",
  baja: "neutral",
};

export function FindingListMini({ hallazgos, onSeleccionar }: { hallazgos: Hallazgo[]; onSeleccionar: (h: Hallazgo) => void }) {
  return (
    <div className="space-y-1.5 p-3">
      {hallazgos.map((h) => (
        <button
          key={h.id}
          onClick={() => onSeleccionar(h)}
          className="block w-full rounded-md border border-border-subtle bg-bg-inset p-2.5 text-left transition-colors hover:border-accent/40"
        >
          <div className="mb-1 flex items-center gap-1.5">
            <Badge tone={TONO_EVIDENCIA[h.nivel_evidencia] ?? "neutral"}>{h.nivel_evidencia}</Badge>
            <span className="text-[10px] text-fg-subtle">score {h.score}</span>
          </div>
          <div className="text-xs font-medium leading-snug text-fg">{h.titulo}</div>
        </button>
      ))}
      {hallazgos.length === 0 && <p className="text-xs text-fg-subtle">No hay hallazgos para este período.</p>}
    </div>
  );
}
