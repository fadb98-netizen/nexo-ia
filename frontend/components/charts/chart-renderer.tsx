"use client";

import * as React from "react";
import type * as echarts from "echarts";
import { EChart } from "./echart";
import { CHART_COLORS, baseAxisStyle, baseGrid, CHART_FONT } from "@/lib/chart-theme";
import { formatNumero, formatUsd } from "@/lib/utils";
import type { ChartData } from "@/types";

const tooltipBase = {
  backgroundColor: "#1c1c1c",
  borderColor: CHART_COLORS.border,
  textStyle: { color: CHART_COLORS.fg, fontSize: 12, fontFamily: CHART_FONT },
};

function fmtSemana(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" });
}

export function ChartRenderer({ data, height = 220 }: { data: ChartData; height?: number }) {
  if (data.tipo === "line") {
    const option: echarts.EChartsOption = {
      grid: baseGrid(),
      tooltip: { trigger: "axis", ...tooltipBase },
      legend: data.series.length > 1 ? { top: 0, right: 0, textStyle: { color: CHART_COLORS.fgMuted, fontSize: 11 }, itemWidth: 10, itemHeight: 10 } : undefined,
      xAxis: {
        type: "category",
        data: data.series[0]?.datos.map((d) => fmtSemana(d.semana)) ?? [],
        ...baseAxisStyle(),
        splitLine: { show: false },
      },
      yAxis: { type: "value", ...baseAxisStyle(), axisLabel: { ...baseAxisStyle().axisLabel, formatter: (v: number) => formatNumero(v) } },
      series: data.series.map((s, i) => ({
        name: s.nombre,
        type: "line",
        smooth: false,
        symbolSize: 5,
        showSymbol: true,
        lineStyle: { width: 2, color: i === 0 ? CHART_COLORS.accent : CHART_COLORS.fgSubtle },
        itemStyle: { color: i === 0 ? CHART_COLORS.accent : CHART_COLORS.fgSubtle },
        areaStyle: i === 0 ? { color: CHART_COLORS.accent, opacity: 0.08 } : undefined,
        data: s.datos.map((d) => d.valor),
      })),
    };
    return <EChart option={option} height={height} />;
  }

  if (data.tipo === "diverging_bar") {
    const ordenado = [...data.categorias];
    const option: echarts.EChartsOption = {
      grid: baseGrid(),
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...tooltipBase, valueFormatter: (v) => formatUsd(v as number) },
      xAxis: { type: "value", ...baseAxisStyle(), axisLabel: { ...baseAxisStyle().axisLabel, formatter: (v: number) => formatNumero(v) } },
      yAxis: { type: "category", data: ordenado.map((c) => c.categoria), ...baseAxisStyle(), splitLine: { show: false } },
      series: [
        {
          type: "bar",
          data: ordenado.map((c) => ({
            value: c.diferencia,
            itemStyle: { color: c.diferencia >= 0 ? CHART_COLORS.positive : CHART_COLORS.negative, borderRadius: 2 },
          })),
          barMaxWidth: 16,
        },
      ],
    };
    return <EChart option={option} height={Math.max(height, ordenado.length * 26)} />;
  }

  if (data.tipo === "heatmap") {
    const xs = Array.from(new Set(data.celdas.map((c) => c.x)));
    const ys = Array.from(new Set(data.celdas.map((c) => c.y)));
    const max = Math.max(1, ...data.celdas.map((c) => c.valor));
    const option: echarts.EChartsOption = {
      grid: { ...baseGrid(), top: 10 },
      tooltip: { ...tooltipBase, position: "top", formatter: (p: any) => `${xs[p.value[0]]} × ${ys[p.value[1]]}<br/>${formatUsd(p.value[2])}` },
      xAxis: { type: "category", data: xs, ...baseAxisStyle(), splitArea: { show: true } },
      yAxis: { type: "category", data: ys, ...baseAxisStyle(), splitArea: { show: true } },
      visualMap: {
        min: 0,
        max,
        show: false,
        inRange: { color: ["#1c1c1c", CHART_COLORS.accent] },
      },
      series: [
        {
          type: "heatmap",
          data: data.celdas.map((c) => [xs.indexOf(c.x), ys.indexOf(c.y), c.valor]),
          itemStyle: { borderColor: CHART_COLORS.bg === "transparent" ? "#121212" : CHART_COLORS.bg, borderWidth: 2 },
        },
      ],
    };
    return <EChart option={option} height={Math.max(height, ys.length * 28)} />;
  }

  if (data.tipo === "stacked_100") {
    const categorias = Array.from(new Set(data.filas.flatMap((f) => Object.keys(f.categorias))));
    const option: echarts.EChartsOption = {
      grid: baseGrid(),
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...tooltipBase, valueFormatter: (v) => `${v}%` },
      legend: { top: 0, right: 0, textStyle: { color: CHART_COLORS.fgMuted, fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
      xAxis: { type: "category", data: data.filas.map((f) => fmtSemana(f.semana)), ...baseAxisStyle(), splitLine: { show: false } },
      yAxis: { type: "value", max: 100, ...baseAxisStyle() },
      series: categorias.map((cat, i) => ({
        name: cat,
        type: "bar",
        stack: "total",
        barMaxWidth: 28,
        itemStyle: { color: CHART_COLORS.categorical[i % CHART_COLORS.categorical.length] },
        data: data.filas.map((f) => f.categorias[cat] ?? 0),
      })),
    };
    return <EChart option={option} height={height} />;
  }

  if (data.tipo === "pie") {
    const option: echarts.EChartsOption = {
      tooltip: { trigger: "item", ...tooltipBase, valueFormatter: (v) => formatUsd(v as number) },
      legend: { orient: "vertical", right: 4, top: "middle", textStyle: { color: CHART_COLORS.fgMuted, fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
      series: [
        {
          type: "pie",
          radius: ["45%", "72%"],
          center: ["38%", "50%"],
          label: { show: false },
          itemStyle: { borderColor: "#121212", borderWidth: 2 },
          data: data.porciones.map((p, i) => ({
            name: p.categoria,
            value: p.valor,
            itemStyle: { color: CHART_COLORS.categorical[i % CHART_COLORS.categorical.length] },
          })),
        },
      ],
    };
    return <EChart option={option} height={height} />;
  }

  if (data.tipo === "table") {
    return (
      <div className="max-h-56 overflow-auto rounded-md border border-border-subtle">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-bg-inset text-fg-subtle">
            <tr>
              <th className="px-2.5 py-1.5 text-left font-medium">Categoría</th>
              <th className="px-2.5 py-1.5 text-right font-medium">Actual</th>
              <th className="px-2.5 py-1.5 text-right font-medium">Anterior</th>
            </tr>
          </thead>
          <tbody>
            {data.filas.map((f) => (
              <tr key={f.categoria} className="border-t border-border-subtle">
                <td className="px-2.5 py-1.5 text-fg">{f.categoria}</td>
                <td className="px-2.5 py-1.5 text-right tabular text-fg-muted">{formatUsd(f.actual)}</td>
                <td className="px-2.5 py-1.5 text-right tabular text-fg-subtle">{formatUsd(f.anterior)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return null;
}
