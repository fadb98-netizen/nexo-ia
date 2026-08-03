export type Dimension = "sucursal" | "familia" | "sector_industrial" | "asesor" | "abc_cliente";

export const DIMENSIONES: Dimension[] = ["sucursal", "familia", "sector_industrial", "asesor", "abc_cliente"];

export const ETIQUETAS_DIMENSION: Record<Dimension, string> = {
  sucursal: "Sucursal",
  familia: "Familia",
  sector_industrial: "Sector industrial",
  asesor: "Asesor",
  abc_cliente: "Clase ABC",
};

export interface ValidacionReporte {
  es_valido: boolean;
  filas_originales: number;
  filas_validas: number;
  filas_descartadas: number;
  duplicados_eliminados: number;
  valores_faltantes: number;
  valores_invalidos: number;
  semanas_disponibles: number;
  semana_derivada_de_fecha: boolean;
  errores: string[];
  advertencias: string[];
}

export interface Periodos {
  reciente: string[];
  comparativo: string[];
  historico: string[];
  grafico: string[];
  semanas_incompletas_descartadas: string[];
  semanas_totales_usadas: number;
}

export interface ComparacionMetrica {
  actual: number;
  anterior: number;
  diferencia_absoluta: number;
  variacion_pct: number | null;
}

export interface ResumenPeriodo {
  usd: ComparacionMetrica;
  pedidos: ComparacionMetrica;
  clientes: ComparacionMetrica;
  posiciones_por_pedido: ComparacionMetrica;
}

export type TipoHallazgo =
  | "anomalia"
  | "tendencia_persistente"
  | "segmento_atipico"
  | "concentrado"
  | "generalizado"
  | "interaccion_profunda"
  | "cambio_relevante";

export type NivelEvidencia = "alta" | "media" | "baja";

export interface Hallazgo {
  id: string;
  tipo: TipoHallazgo;
  titulo: string;
  resumen: string;
  segmento: Partial<Record<Dimension, string>>;
  dimensiones: Dimension[];
  nivel: number;
  que_ocurrio: string;
  cuanto_explica: string;
  metricas_respaldo: Record<string, number | string | null>;
  evolucion_semanal: number[];
  semanas_grafico: string[];
  nivel_evidencia: NivelEvidencia;
  limitaciones: string[];
  driver_principal: string;
  score: number;
  score_desglose: Record<string, number>;
}

export interface UploadResponse {
  run_id: string;
  nombre_archivo: string;
  validacion: ValidacionReporte;
  periodos: Periodos;
  resumen_periodo: ResumenPeriodo;
  hallazgos: Hallazgo[];
  dimensiones: Dimension[];
  grafico_linea_usd: ChartLineData;
  grafico_contribuciones_sucursal: ChartDivergingBarData;
  ia_configurada: boolean;
}

export interface ChartLineSerie {
  nombre: string;
  datos: { semana: string; valor: number }[];
}
export interface ChartLineData {
  tipo: "line";
  series: ChartLineSerie[];
}

export interface ChartDivergingBarData {
  tipo: "diverging_bar";
  categorias: { categoria: string; diferencia: number }[];
}

export interface ChartHeatmapData {
  tipo: "heatmap";
  eje_x: string;
  eje_y: string;
  celdas: { x: string; y: string; valor: number }[];
}

export interface ChartStacked100Data {
  tipo: "stacked_100";
  dimension: string;
  filas: { semana: string; categorias: Record<string, number> }[];
}

export interface ChartPieData {
  tipo: "pie";
  porciones: { categoria: string; valor: number }[];
}

export interface ChartTableData {
  tipo: "table";
  filas: { categoria: string; actual: number; anterior: number }[];
}

export type ChartData =
  | ChartLineData
  | ChartDivergingBarData
  | ChartHeatmapData
  | ChartStacked100Data
  | ChartPieData
  | ChartTableData;

export interface SegmentoDim {
  dimension: Dimension;
  valor: string;
}

export interface ChatGrafico {
  titulo: string;
  solicitud?: Record<string, unknown>;
  datos?: ChartData;
  error?: string;
}

export interface RankingItem {
  segmento: SegmentoDim[];
  metrica: string;
  valor: string;
}

export interface ChatResponse {
  origen: "ia" | "determinista";
  que_ocurrio: string;
  segmento: SegmentoDim[];
  cuanto_explica: string;
  metricas_respaldo: { nombre: string; valor: string }[];
  evolucion_semanal: string;
  nivel_evidencia: NivelEvidencia;
  limitaciones: string;
  hay_causa_dominante: boolean;
  graficos: ChatGrafico[];
  ranking: RankingItem[];
}

export interface ContextoSeleccionado {
  tipo: "hallazgo" | "grafico";
  titulo: string;
  detalle: Record<string, unknown>;
}
