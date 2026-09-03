import type { ChartData, ChatResponse, ContextoSeleccionado, HistorialItem, UploadResponse } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (data.detail?.mensaje) return data.detail.mensaje;
    return JSON.stringify(data.detail ?? data);
  } catch {
    return res.statusText;
  }
}

export async function subirCsv(archivo: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("archivo", archivo);
  const res = await fetch(`${API_URL}/api/upload`, { method: "POST", body: form });
  if (!res.ok) throw new ApiError(await parseErrorDetail(res), res.status);
  return res.json();
}

export async function cargarDemo(): Promise<UploadResponse> {
  const resCsv = await fetch(`${API_URL}/api/demo-csv`);
  if (!resCsv.ok) throw new ApiError("No se pudo obtener el CSV de demo.", resCsv.status);
  const blob = await resCsv.blob();
  const archivo = new File([blob], "pedidos_demo.csv", { type: "text/csv" });
  return subirCsv(archivo);
}

export async function preguntar(
  runId: string,
  pregunta: string,
  contextoSeleccionado?: ContextoSeleccionado | null,
  historial?: HistorialItem[],
  aclaracionElegida?: { dimension: string; valor: string } | null
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      run_id: runId,
      pregunta,
      contexto_seleccionado: contextoSeleccionado ?? null,
      historial: historial ?? [],
      aclaracion_elegida: aclaracionElegida ?? null,
    }),
  });
  if (!res.ok) throw new ApiError(await parseErrorDetail(res), res.status);
  return res.json();
}

export async function calcularGrafico(
  runId: string,
  req: { chart_type: string; metric: string; group_by: string; filters?: Record<string, string>; comparison?: string }
): Promise<ChartData> {
  const res = await fetch(`${API_URL}/api/charts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, filters: {}, comparison: "ninguna", ...req }),
  });
  if (!res.ok) throw new ApiError(await parseErrorDetail(res), res.status);
  return res.json();
}

export async function agregarAnotacion(runId: string, texto: string): Promise<string[]> {
  const res = await fetch(`${API_URL}/api/anotaciones`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, texto }),
  });
  if (!res.ok) throw new ApiError(await parseErrorDetail(res), res.status);
  const data = await res.json();
  return data.anotaciones;
}

export async function chequearSalud(): Promise<{ status: string; ia_configurada: boolean; supabase_configurado: boolean }> {
  const res = await fetch(`${API_URL}/api/health`);
  if (!res.ok) throw new ApiError("El backend no responde.", res.status);
  return res.json();
}

export { ApiError };
