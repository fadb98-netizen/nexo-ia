import { formatNumero, formatPct, formatUsd } from "@/lib/utils";
import type { ComparacionMetrica, ResumenPeriodo } from "@/types";

function KpiCard({ label, metrica, formato }: { label: string; metrica: ComparacionMetrica; formato: (v: number) => string }) {
  const positivo = (metrica.variacion_pct ?? 0) >= 0;
  return (
    <div className="flex-1 rounded-lg border border-border bg-bg-subtle px-3.5 py-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-fg-subtle">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-xl font-semibold tabular text-fg">{formato(metrica.actual)}</span>
        <span className={`text-xs font-medium tabular ${positivo ? "text-positive" : "text-negative"}`}>{formatPct(metrica.variacion_pct)}</span>
      </div>
      <div className="mt-0.5 text-[11px] text-fg-subtle tabular">vs. {formato(metrica.anterior)} período anterior</div>
    </div>
  );
}

export function KpiRow({ resumen }: { resumen: ResumenPeriodo }) {
  return (
    <div className="flex gap-2.5">
      <KpiCard label="USD de pedidos" metrica={resumen.usd} formato={formatUsd} />
      <KpiCard label="Pedidos" metrica={resumen.pedidos} formato={(v) => formatNumero(v)} />
      <KpiCard label="Clientes compradores" metrica={resumen.clientes} formato={(v) => formatNumero(v)} />
      <KpiCard label="Posiciones por pedido" metrica={resumen.posiciones_por_pedido} formato={(v) => formatNumero(v, 1)} />
    </div>
  );
}
