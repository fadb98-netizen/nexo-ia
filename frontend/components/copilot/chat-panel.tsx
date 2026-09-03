"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { UserBubble, AssistantResponse } from "./chat-message";
import { preguntar } from "@/lib/api";
import type { ChatResponse, ContextoSeleccionado, HistorialItem } from "@/types";

const TURNOS_HISTORIAL_ENVIADOS = 4;

const PREGUNTAS_SUGERIDAS = [
  "¿Qué combinación explica mejor la caída?",
  "¿La variación está concentrada o generalizada?",
  "¿Qué segmento compensó parcialmente el resultado?",
  "¿Este patrón es reciente o persistente?",
  "¿El cambio se explica por pedidos, ticket o posiciones?",
  "¿Qué cruce presenta el comportamiento más anómalo?",
];

interface Mensaje {
  id: string;
  rol: "usuario" | "asistente";
  texto?: string;
  respuesta?: ChatResponse;
  cargando?: boolean;
}

export function ChatPanel({
  runId,
  contexto,
  onLimpiarContexto,
  preguntaInicial,
}: {
  runId: string;
  contexto: ContextoSeleccionado | null;
  onLimpiarContexto: () => void;
  preguntaInicial?: { texto: string; nonce: number } | null;
}) {
  const [mensajes, setMensajes] = React.useState<Mensaje[]>([]);
  const [input, setInput] = React.useState("");
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const ultimoNonce = React.useRef<number>(-1);

  const enviar = React.useCallback(
    async (texto: string) => {
      if (!texto.trim()) return;
      const idUsuario = `u-${Date.now()}`;
      const idAsistente = `a-${Date.now()}`;

      const historial: HistorialItem[] = [];
      for (let i = 0; i < mensajes.length - 1; i++) {
        const pregunta = mensajes[i];
        const respuesta = mensajes[i + 1];
        if (pregunta.rol === "usuario" && pregunta.texto && respuesta.rol === "asistente" && respuesta.respuesta) {
          historial.push({
            pregunta: pregunta.texto,
            respuesta_resumen: `${respuesta.respuesta.que_ocurrio} ${respuesta.respuesta.cuanto_explica}`.trim(),
            segmento: respuesta.respuesta.segmento,
          });
        }
      }
      const historialReciente = historial.slice(-TURNOS_HISTORIAL_ENVIADOS);

      // el contexto seleccionado (hallazgo/gráfico) sólo vale para esta pregunta puntual:
      // se limpia enseguida para que no siga aplicándose a las preguntas siguientes.
      const contextoDeEstaPregunta = contexto;
      if (contexto) onLimpiarContexto();

      setMensajes((prev) => [
        ...prev,
        { id: idUsuario, rol: "usuario", texto },
        { id: idAsistente, rol: "asistente", cargando: true },
      ]);
      setInput("");
      try {
        const respuesta = await preguntar(runId, texto, contextoDeEstaPregunta, historialReciente);
        setMensajes((prev) => prev.map((m) => (m.id === idAsistente ? { ...m, cargando: false, respuesta } : m)));
      } catch (err) {
        setMensajes((prev) =>
          prev.map((m) =>
            m.id === idAsistente
              ? {
                  ...m,
                  cargando: false,
                  respuesta: {
                    origen: "determinista",
                    que_ocurrio: "No se pudo consultar al copiloto (falló la conexión con el backend).",
                    segmento: [],
                    cuanto_explica: "",
                    metricas_respaldo: [],
                    evolucion_semanal: "",
                    nivel_evidencia: "baja",
                    limitaciones: err instanceof Error ? err.message : "Error desconocido.",
                    hay_causa_dominante: false,
                    graficos: [],
                    ranking: [],
                  },
                }
              : m
          )
        );
      }
    },
    [runId, contexto, mensajes, onLimpiarContexto]
  );

  React.useEffect(() => {
    if (preguntaInicial && preguntaInicial.nonce !== ultimoNonce.current) {
      ultimoNonce.current = preguntaInicial.nonce;
      enviar(preguntaInicial.texto);
    }
  }, [preguntaInicial, enviar]);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [mensajes]);

  return (
    <div className="flex h-full flex-col">
      {contexto && (
        <div className="flex items-center justify-between gap-2 border-b border-border-subtle bg-bg-inset px-3 py-1.5">
          <span className="truncate text-[11px] text-fg-muted">
            Contexto: <span className="text-fg">{contexto.titulo}</span>
          </span>
          <button onClick={onLimpiarContexto} className="text-[11px] text-fg-subtle hover:text-fg-muted">
            quitar
          </button>
        </div>
      )}

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
        {mensajes.length === 0 && (
          <div className="space-y-1.5">
            <p className="mb-2 text-xs text-fg-subtle">Preguntas sugeridas:</p>
            {PREGUNTAS_SUGERIDAS.map((p) => (
              <button
                key={p}
                onClick={() => enviar(p)}
                className="block w-full rounded-md border border-border-subtle bg-bg-inset px-2.5 py-1.5 text-left text-xs text-fg-muted transition-colors hover:border-accent/40 hover:text-fg"
              >
                {p}
              </button>
            ))}
          </div>
        )}
        {mensajes.map((m) =>
          m.rol === "usuario" ? (
            <UserBubble key={m.id} texto={m.texto ?? ""} />
          ) : m.cargando ? (
            <div key={m.id} className="mr-2 flex items-center gap-2 rounded-lg rounded-tl-sm border border-border bg-bg-subtle px-3 py-2.5 text-xs text-fg-subtle">
              <Spinner /> Investigando con evidencia…
            </div>
          ) : m.respuesta ? (
            <AssistantResponse key={m.id} respuesta={m.respuesta} />
          ) : null
        )}
      </div>

      <div className="flex items-end gap-2 border-t border-border-subtle p-2.5">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              enviar(input);
            }
          }}
          placeholder="Preguntale al copiloto..."
          rows={1}
          className="min-h-[32px]"
        />
        <Button size="sm" onClick={() => enviar(input)} disabled={!input.trim()}>
          Enviar
        </Button>
      </div>
    </div>
  );
}
