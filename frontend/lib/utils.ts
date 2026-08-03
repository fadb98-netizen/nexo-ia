import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatUsd(valor: number): string {
  const signo = valor < 0 ? "-" : "";
  return `${signo}US$ ${Math.abs(valor).toLocaleString("es-AR", { maximumFractionDigits: 0 })}`;
}

export function formatPct(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "s/d";
  const signo = valor > 0 ? "+" : "";
  return `${signo}${valor.toFixed(1)}%`;
}

export function formatNumero(valor: number, decimales = 0): string {
  return valor.toLocaleString("es-AR", { maximumFractionDigits: decimales, minimumFractionDigits: decimales });
}
