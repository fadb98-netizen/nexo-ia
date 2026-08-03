import { FindingCard } from "./finding-card";
import type { Hallazgo } from "@/types";

export function FindingsCenter({ hallazgos, onInvestigar }: { hallazgos: Hallazgo[]; onInvestigar: (h: Hallazgo) => void }) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Centro de hallazgos</h2>
        <span className="text-[11px] text-fg-subtle">{hallazgos.length} priorizados</span>
      </div>
      {hallazgos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border-subtle p-6 text-center text-xs text-fg-subtle">
          No se encontraron hallazgos con volumen o relevancia suficiente en este período.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 xl:grid-cols-3">
          {hallazgos.map((h) => (
            <FindingCard key={h.id} hallazgo={h} onInvestigar={onInvestigar} />
          ))}
        </div>
      )}
    </section>
  );
}
