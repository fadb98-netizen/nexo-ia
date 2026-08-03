"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { calcularGrafico } from "@/lib/api";
import { DIMENSIONES, ETIQUETAS_DIMENSION, type ChartHeatmapData, type Dimension } from "@/types";

const METRICAS: { value: string; label: string }[] = [
  { value: "usd", label: "USD" },
  { value: "kg", label: "Kg" },
  { value: "posiciones", label: "Posiciones" },
  { value: "pedidos", label: "Pedidos" },
];

export function HeatmapConfigurable({ runId }: { runId: string }) {
  const [ejeX, setEjeX] = React.useState<Dimension>("sucursal");
  const [ejeY, setEjeY] = React.useState<Dimension>("familia");
  const [metric, setMetric] = React.useState("usd");
  const [datos, setDatos] = React.useState<ChartHeatmapData | null>(null);
  const [cargando, setCargando] = React.useState(false);

  React.useEffect(() => {
    let cancelado = false;
    setCargando(true);
    calcularGrafico(runId, { chart_type: "heatmap", metric, group_by: `${ejeX},${ejeY}` })
      .then((d) => {
        if (!cancelado) setDatos(d as ChartHeatmapData);
      })
      .catch(() => !cancelado && setDatos(null))
      .finally(() => !cancelado && setCargando(false));
    return () => {
      cancelado = true;
    };
  }, [runId, ejeX, ejeY, metric]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Heatmap configurable</CardTitle>
        <div className="flex items-center gap-1.5">
          <Select value={ejeX} onChange={(e) => setEjeX(e.target.value as Dimension)}>
            {DIMENSIONES.map((d) => (
              <option key={d} value={d}>
                {ETIQUETAS_DIMENSION[d]}
              </option>
            ))}
          </Select>
          <span className="text-fg-subtle text-xs">×</span>
          <Select value={ejeY} onChange={(e) => setEjeY(e.target.value as Dimension)}>
            {DIMENSIONES.map((d) => (
              <option key={d} value={d}>
                {ETIQUETAS_DIMENSION[d]}
              </option>
            ))}
          </Select>
          <Select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {METRICAS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {cargando && (
          <div className="flex h-40 items-center justify-center">
            <Spinner />
          </div>
        )}
        {!cargando && datos && <ChartRenderer data={datos} height={Math.min(280, 40 + datos.celdas.length * 6)} />}
        {!cargando && !datos && <p className="text-xs text-fg-subtle">No se pudo calcular este cruce.</p>}
      </CardContent>
    </Card>
  );
}
