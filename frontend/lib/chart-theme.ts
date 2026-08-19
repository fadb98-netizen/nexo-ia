export const CHART_COLORS = {
  bg: "transparent",
  fg: "#e5e5e5",
  fgMuted: "#8a8a8a",
  fgSubtle: "#5c5c5c",
  border: "#2a2a2a",
  accent: "#60a5fa",
  positive: "#34d399",
  negative: "#f87171",
  warning: "#fbbf24",
  categorical: ["#60a5fa", "#34d399", "#fbbf24", "#c084fc", "#f87171", "#22d3ee", "#a3a3a3", "#fb923c"],
  // Baldes de un solo tono (azul, el mismo del accent) para heatmaps: los
  // valores típicos quedan casi indistinguibles del fondo (no llaman la
  // atención) y el salto se concentra en lo atípico, en vez de un degradé
  // parejo de 0 a máximo que un solo outlier aplasta.
  heatmap: {
    cero: "#161b24",
    bajo: "#20304a",
    medio: "#2f4870",
    alto: "#4d76b8",
    atipico: "#60a5fa",
  },
};

export const CHART_FONT = "ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif";

export function baseGrid() {
  return { left: 8, right: 12, top: 20, bottom: 8, containLabel: true as const };
}

export function baseAxisStyle() {
  return {
    axisLine: { lineStyle: { color: CHART_COLORS.border } },
    axisTick: { show: false },
    axisLabel: { color: CHART_COLORS.fgMuted, fontSize: 11, fontFamily: CHART_FONT },
    splitLine: { lineStyle: { color: CHART_COLORS.border, type: "dashed" as const } },
  };
}
