"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

const COLUMNAS = [
  { nombre: "fecha_pedido", tipo: "fecha", ejemplo: "2026-04-29", descripcion: "Fecha del pedido (acepta AAAA-MM-DD, DD/MM/AAAA, AAAA/MM/DD o DD-MM-AAAA)." },
  { nombre: "semana", tipo: "fecha", ejemplo: "2026-04-27", descripcion: "Lunes ISO de esa semana. Si no se puede leer, se calcula sola a partir de fecha_pedido." },
  { nombre: "pedido_id", tipo: "texto", ejemplo: "PED0000001", descripcion: "Identificador del pedido. No necesita ser único por fila si un pedido tiene varias familias." },
  { nombre: "cliente_id", tipo: "texto", ejemplo: "CLI_0003", descripcion: "Identificador del cliente." },
  { nombre: "sucursal", tipo: "texto", ejemplo: "CAPITAL", descripcion: "Sucursal u oficina de ventas que generó el pedido." },
  { nombre: "asesor", tipo: "texto", ejemplo: "ASESOR_1", descripcion: "Asesor o vendedor a cargo del pedido." },
  { nombre: "sector_industrial", tipo: "texto", ejemplo: "AGRO", descripcion: "Sector industrial del cliente." },
  { nombre: "familia", tipo: "texto", ejemplo: "PERFILES", descripcion: "Familia de producto de esa línea del pedido." },
  { nombre: "abc_cliente", tipo: "texto", ejemplo: "B", descripcion: "Clasificación ABC del cliente. No hay una lista fija de valores válidos." },
  { nombre: "usd", tipo: "número ≥ 0", ejemplo: "1699.57", descripcion: "Monto vendido en dólares para esa fila." },
  { nombre: "kg", tipo: "número ≥ 0", ejemplo: "1402.9", descripcion: "Kilos vendidos para esa fila." },
  { nombre: "posiciones", tipo: "número > 0", ejemplo: "1", descripcion: "Cantidad de posiciones (líneas) del pedido en esa combinación." },
];

const QUERY_SUPERSET = `SELECT
    fecha_documento AS fecha_pedido,
    toMonday(fecha_documento) AS semana,
    toString(numero_documento_ventas) AS pedido_id,
    toString(cliente_id) AS cliente_id,
    oficina_ventas_descripcion AS sucursal,
    asesor_z1_descripcion AS asesor,
    sector_industrial_descripcion_dm AS sector_industrial,
    familia_descripcion_dm AS familia,
    clase_abc_cliente AS abc_cliente,
    round(SUM(valor_neto_posicion_usd), 2) AS usd,
    round(SUM(peso_neto_posicion), 2) AS kg,
    COUNT(DISTINCT posicion) AS posiciones
FROM mart.mart_base_ventas
WHERE tipo_documento_venta_id = 'P'   -- solo Pedidos (no Ofertas ni Facturas)
  AND posicion_anulada = ''            -- excluye posiciones anuladas
  AND documento_borrado = ''           -- excluye documentos borrados
  AND motivo_rechazo = ''              -- excluye posiciones rechazadas
  AND fecha_documento >= today() - INTERVAL 16 WEEK
GROUP BY
    fecha_documento, numero_documento_ventas, cliente_id, oficina_ventas_descripcion,
    asesor_z1_descripcion, sector_industrial_descripcion_dm, clase_abc_cliente, familia_descripcion_dm
ORDER BY fecha_documento`;

function BotonCopiar({ texto }: { texto: string }) {
  const [copiado, setCopiado] = React.useState(false);
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={async () => {
        await navigator.clipboard.writeText(texto);
        setCopiado(true);
        setTimeout(() => setCopiado(false), 1500);
      }}
    >
      {copiado ? "¡Copiado!" : "Copiar query"}
    </Button>
  );
}

export function UploadScreen({
  onArchivo,
  onDemo,
  cargando,
  error,
}: {
  onArchivo: (f: File) => void;
  onDemo: () => void;
  cargando: boolean;
  error: string | null;
}) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [arrastrando, setArrastrando] = React.useState(false);

  return (
    <div className="flex h-screen w-full flex-col items-center overflow-y-auto bg-bg px-4 py-10">
      <div className="mb-6 flex items-center gap-2">
        <div className="h-7 w-7 rounded-md bg-accent" />
        <span className="text-lg font-semibold tracking-tight">Nexo IA</span>
      </div>
      <p className="mb-6 max-w-md text-center text-sm text-fg-muted">
        Asistente de análisis comercial. Subí un CSV de pedidos (16 semanas) y Python va a validar,
        calcular 31 cruces de dimensiones y detectar los patrones más relevantes.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onArchivo(f);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex w-full max-w-md cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center transition-colors ${
          arrastrando ? "border-accent bg-accent/5" : "border-border-subtle bg-bg-subtle hover:border-border"
        }`}
      >
        {cargando ? (
          <>
            <Spinner className="h-5 w-5" />
            <span className="text-sm text-fg-muted">Validando y calculando…</span>
          </>
        ) : (
          <>
            <span className="text-sm text-fg">Arrastrá tu CSV acá o hacé click para elegirlo</span>
            <span className="text-xs text-fg-subtle">
              12 columnas obligatorias — ver el detalle abajo
            </span>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onArchivo(f);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="mt-4 w-full max-w-md rounded-md border border-negative/30 bg-negative/5 px-3 py-2 text-xs text-negative">
          {error}
        </div>
      )}

      <div className="mt-5 flex items-center gap-2 text-xs text-fg-subtle">
        <span>¿No tenés un archivo a mano?</span>
        <Button variant="outline" size="sm" onClick={onDemo} disabled={cargando}>
          Cargar datos de demo
        </Button>
      </div>

      <details className="mt-8 w-full max-w-2xl rounded-lg border border-border-subtle bg-bg-subtle px-4 py-3 text-sm">
        <summary className="cursor-pointer select-none font-medium text-fg">
          ¿Qué dataset espera Nexo IA?
        </summary>
        <div className="mt-3 space-y-3 text-fg-muted">
          <p>
            Un CSV a nivel de <strong>pedido × familia de producto</strong>: una fila por cada
            combinación de pedido y familia que ese pedido incluyó, con 16 semanas de historia
            (8 de contexto + 4 de comparación + 4 recientes). Cada fila necesita estas 12 columnas,
            con estos nombres exactos:
          </p>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-border-subtle text-left text-fg-subtle">
                  <th className="py-1 pr-3 font-medium">Columna</th>
                  <th className="py-1 pr-3 font-medium">Tipo</th>
                  <th className="py-1 pr-3 font-medium">Ejemplo</th>
                  <th className="py-1 font-medium">Descripción</th>
                </tr>
              </thead>
              <tbody>
                {COLUMNAS.map((c) => (
                  <tr key={c.nombre} className="border-b border-border-subtle/50 align-top">
                    <td className="py-1.5 pr-3 font-mono text-fg">{c.nombre}</td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">{c.tipo}</td>
                    <td className="py-1.5 pr-3 font-mono whitespace-nowrap">{c.ejemplo}</td>
                    <td className="py-1.5">{c.descripcion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>Ejemplo de fila completa:</p>
          <pre className="overflow-x-auto rounded-md bg-bg px-3 py-2 text-xs">
            <code>
              fecha_pedido,semana,pedido_id,cliente_id,sucursal,asesor,sector_industrial,familia,abc_cliente,usd,kg,posiciones{"\n"}
              2026-04-29,2026-04-27,PED0000001,CLI_0003,CAPITAL,ASESOR_1,AGRO,PERFILES,B,1699.57,1402.9,1
            </code>
          </pre>

          <details className="rounded-md border border-border-subtle bg-bg px-3 py-2">
            <summary className="cursor-pointer select-none text-xs font-medium text-fg">
              ¿Tenés acceso al Superset de Famiq? Generá el CSV directo desde ahí
            </summary>
            <div className="mt-2 space-y-2">
              <p className="text-xs text-fg-muted">
                Pegá esta query en SQL Lab (base ClickHouse PRD) y exportá el resultado como CSV —
                ya viene con las 12 columnas en el formato que Nexo IA espera.
              </p>
              <pre className="overflow-x-auto rounded-md bg-bg-subtle px-3 py-2 text-xs">
                <code>{QUERY_SUPERSET}</code>
              </pre>
              <BotonCopiar texto={QUERY_SUPERSET} />
            </div>
          </details>
        </div>
      </details>
    </div>
  );
}
