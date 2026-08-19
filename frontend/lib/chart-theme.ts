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
  // Rampa secuencial de un solo tono (azul), oscuro→claro: en dark mode el
  // extremo oscuro se "hunde" en el fondo (valor bajo) y el extremo claro
  // resalta (valor alto) — el orden se invierte respecto a una rampa pensada
  // para fondo claro.
  sequential: ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"],
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
