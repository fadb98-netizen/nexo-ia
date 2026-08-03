import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nexo IA — Asistente de análisis comercial",
  description: "Detección de patrones multivariables en pedidos comerciales, con evidencia calculada por Python e interpretada por IA.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
