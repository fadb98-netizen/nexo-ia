"use client";

import * as React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FindingListMini } from "./finding-list-mini";
import { ChatPanel } from "./chat-panel";
import type { ContextoSeleccionado, Hallazgo } from "@/types";

export function CopilotSidebar({
  runId,
  hallazgos,
  contexto,
  onLimpiarContexto,
  onSeleccionarHallazgo,
  preguntaInicial,
  tabRequest,
}: {
  runId: string;
  hallazgos: Hallazgo[];
  contexto: ContextoSeleccionado | null;
  onLimpiarContexto: () => void;
  onSeleccionarHallazgo: (h: Hallazgo) => void;
  preguntaInicial?: { texto: string; nonce: number } | null;
  tabRequest?: { tab: "hallazgos" | "preguntar"; nonce: number } | null;
}) {
  const [tab, setTab] = React.useState<string>("hallazgos");

  React.useEffect(() => {
    if (tabRequest) setTab(tabRequest.tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabRequest?.nonce]);

  return (
    <aside className="flex h-full w-[340px] shrink-0 flex-col border-l border-border bg-bg-subtle/40">
      <div className="border-b border-border-subtle px-3 py-2">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="hallazgos">Hallazgos</TabsTrigger>
            <TabsTrigger value="preguntar">Preguntar</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="min-h-0 flex-1">
        {tab === "hallazgos" && <FindingListMini hallazgos={hallazgos} onSeleccionar={onSeleccionarHallazgo} />}
        {tab === "preguntar" && (
          <ChatPanel runId={runId} contexto={contexto} onLimpiarContexto={onLimpiarContexto} preguntaInicial={preguntaInicial} />
        )}
      </div>
    </aside>
  );
}
