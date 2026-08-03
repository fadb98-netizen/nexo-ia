"use client";

import * as React from "react";
import { Header } from "@/components/dashboard/header";
import { KpiRow } from "@/components/dashboard/kpi-row";
import { FindingsCenter } from "@/components/dashboard/findings-center";
import { HeatmapConfigurable } from "@/components/dashboard/heatmap-configurable";
import { UploadScreen } from "@/components/dashboard/upload-screen";
import { CopilotSidebar } from "@/components/copilot/copilot-sidebar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { ApiError, cargarDemo, subirCsv } from "@/lib/api";
import type { ContextoSeleccionado, Hallazgo, UploadResponse } from "@/types";

export default function Home() {
  const [run, setRun] = React.useState<UploadResponse | null>(null);
  const [cargando, setCargando] = React.useState(false);
  const [errorUpload, setErrorUpload] = React.useState<string | null>(null);

  const [contexto, setContexto] = React.useState<ContextoSeleccionado | null>(null);
  const [preguntaInicial, setPreguntaInicial] = React.useState<{ texto: string; nonce: number } | null>(null);
  const [tabRequest, setTabRequest] = React.useState<{ tab: "hallazgos" | "preguntar"; nonce: number } | null>(null);

  async function manejarArchivo(f: File) {
    setCargando(true);
    setErrorUpload(null);
    try {
      const res = await subirCsv(f);
      setRun(res);
    } catch (err) {
      console.error("Error al procesar el archivo:", err);
      setErrorUpload(err instanceof ApiError ? err.message : "No se pudo procesar el archivo.");
    } finally {
      setCargando(false);
    }
  }

  async function manejarDemo() {
    setCargando(true);
    setErrorUpload(null);
    try {
      const res = await cargarDemo();
      setRun(res);
    } catch (err) {
      console.error("Error al cargar el demo:", err);
      setErrorUpload(err instanceof ApiError ? err.message : "No se pudo cargar el demo.");
    } finally {
      setCargando(false);
    }
  }

  function investigar(h: Hallazgo) {
    setContexto({ tipo: "hallazgo", titulo: h.titulo, detalle: h as unknown as Record<string, unknown> });
    setPreguntaInicial({ texto: `Investigá en profundidad este hallazgo y traé evidencia adicional: "${h.titulo}". ${h.que_ocurrio}`, nonce: Date.now() });
    setTabRequest({ tab: "preguntar", nonce: Date.now() });
  }

  function usarGraficoComoContexto(titulo: string, detalle: Record<string, unknown>) {
    setContexto({ tipo: "grafico", titulo, detalle });
    setTabRequest({ tab: "preguntar", nonce: Date.now() });
  }

  if (!run) {
    return <UploadScreen onArchivo={manejarArchivo} onDemo={manejarDemo} cargando={cargando} error={errorUpload} />;
  }

  return (
    <div className="flex h-screen flex-col bg-bg">
      <Header
        nombreArchivo={run.nombre_archivo}
        periodos={run.periodos}
        validacion={run.validacion}
        iaConfigurada={run.ia_configurada}
        onReset={() => {
          setRun(null);
          setContexto(null);
        }}
      />
      <div className="flex min-h-0 flex-1">
        <main className="min-w-0 flex-1 space-y-5 overflow-y-auto px-4 py-4">
          <KpiRow resumen={run.resumen_periodo} />

          <div className="grid grid-cols-1 gap-2.5 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Evolución semanal — USD</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => usarGraficoComoContexto("Evolución semanal de USD", { chart: "line", data: run.grafico_linea_usd })}>
                  Usar como contexto
                </Button>
              </CardHeader>
              <CardContent>
                <ChartRenderer data={run.grafico_linea_usd} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Contribuciones por sucursal</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => usarGraficoComoContexto("Contribuciones por sucursal", { chart: "diverging_bar", data: run.grafico_contribuciones_sucursal })}
                >
                  Usar como contexto
                </Button>
              </CardHeader>
              <CardContent>
                <ChartRenderer data={run.grafico_contribuciones_sucursal} />
              </CardContent>
            </Card>
          </div>

          <HeatmapConfigurable runId={run.run_id} />

          <FindingsCenter hallazgos={run.hallazgos} onInvestigar={investigar} />
        </main>

        <CopilotSidebar
          runId={run.run_id}
          hallazgos={run.hallazgos}
          contexto={contexto}
          onLimpiarContexto={() => setContexto(null)}
          onSeleccionarHallazgo={investigar}
          preguntaInicial={preguntaInicial}
          tabRequest={tabRequest}
        />
      </div>
    </div>
  );
}
