"""Nexo IA - backend analítico (FastAPI).

Flujo: POST /api/upload valida y calcula todo con Python (31 cruces,
hallazgos determinísticos); el resto de los endpoints leen esos resultados ya
calculados. La IA (si está configurada) sólo entra a interpretar vía
/api/chat, nunca a calcular.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import store
import supabase_client
from ai import assistant, tools as ai_tools
from config import DIMENSIONES, MAX_HALLAZGOS, MIN_HALLAZGOS
from core import charts, combinations, loader, metrics, patterns, periods, validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexo_ia")

app = FastAPI(title="Nexo IA", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP académico: sin cookies/credenciales, sin datos sensibles en el cliente
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_CSV_PATH = Path(__file__).parent.parent / "sample-data" / "pedidos_demo.csv"


class HistorialItem(BaseModel):
    pregunta: str
    respuesta_resumen: str


class ChatRequest(BaseModel):
    run_id: str
    pregunta: str
    contexto_seleccionado: dict | None = None
    historial: list[HistorialItem] = []


class ChartRequestBody(BaseModel):
    run_id: str
    chart_type: str
    metric: str
    group_by: str = ""
    filters: dict[str, str] = {}
    comparison: str = "ninguna"


class AnotacionRequest(BaseModel):
    run_id: str
    texto: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "ia_configurada": assistant.ia_disponible(), "supabase_configurado": supabase_client.disponible()}


@app.get("/api/demo-csv")
def demo_csv() -> FileResponse:
    if not SAMPLE_CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="No se encontró el CSV de demo en el servidor.")
    return FileResponse(SAMPLE_CSV_PATH, media_type="text/csv", filename="pedidos_demo.csv")


@app.post("/api/upload")
async def upload(archivo: UploadFile = File(...)) -> dict:
    contenido = await archivo.read()

    try:
        loader.validar_archivo_subido(archivo.filename or "archivo.csv", contenido)
        df_raw = loader.cargar_csv(contenido)
    except loader.ArchivoInvalidoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    df, reporte = validator.validar_y_limpiar(df_raw)
    reporte_dict = reporte.to_dict()

    if not reporte.es_valido:
        raise HTTPException(status_code=422, detail={"mensaje": "El archivo no pasó la validación.", "validacion": reporte_dict})

    p = periods.calcular_periodos(df)
    df_reciente = periods.filtrar_por_semanas(df, p.reciente)
    df_comparativo = periods.filtrar_por_semanas(df, p.comparativo)
    df_historico = periods.filtrar_por_semanas(df, p.historico)

    run_id = store.nuevo_run_id()

    cruces = combinations.calcular_todas_las_combinaciones_cacheado(
        run_id, df_reciente, df_comparativo, df_historico, p.grafico, p.historico
    )
    cruces_materiales = combinations.filtrar_material(cruces)

    total_actual = metrics.calcular_metricas_periodo(df_reciente)
    total_anterior = metrics.calcular_metricas_periodo(df_comparativo)
    comp_usd = metrics.comparar(total_actual, total_anterior, "usd")
    comp_pedidos = metrics.comparar(total_actual, total_anterior, "pedidos")
    comp_clientes = metrics.comparar(total_actual, total_anterior, "clientes")
    comp_pos_pp = metrics.comparar(total_actual, total_anterior, "posiciones_por_pedido")

    resumen_periodo = {
        "usd": comp_usd,
        "pedidos": comp_pedidos,
        "clientes": comp_clientes,
        "posiciones_por_pedido": comp_pos_pp,
    }

    hallazgos = patterns.generar_hallazgos(
        cruces_materiales, comp_usd["variacion_pct"], [s.isoformat() for s in p.grafico], MIN_HALLAZGOS, MAX_HALLAZGOS
    )

    run = store.Run(
        run_id=run_id,
        nombre_archivo=archivo.filename or "archivo.csv",
        creado_en=time.time(),
        df_reciente=df_reciente,
        df_comparativo=df_comparativo,
        df_historico=df_historico,
        semanas_grafico=[s.isoformat() for s in p.grafico],
        semanas_historico=[s.isoformat() for s in p.historico],
        cruces=cruces,
        cruces_materiales=cruces_materiales,
        hallazgos=hallazgos,
        resumen_periodo=resumen_periodo,
        validacion=reporte_dict,
        periodos=p.to_dict(),
    )
    store.guardar(run)

    supabase_client.guardar_run(run_id, run.nombre_archivo, reporte_dict, resumen_periodo, hallazgos)
    supabase_client.subir_csv(run_id, contenido, run.nombre_archivo)

    grafico_linea = charts.calcular_datos_grafico(
        {"chart_type": "line", "metric": "usd", "group_by": "semana", "filters": {}, "comparison": "ninguna"},
        df_reciente, df_comparativo, p.grafico,
    )
    grafico_contribuciones = charts.calcular_datos_grafico(
        {"chart_type": "diverging_bar", "metric": "usd", "group_by": "sucursal", "filters": {}, "comparison": "ninguna"},
        df_reciente, df_comparativo, p.grafico,
    )

    return {
        "run_id": run_id,
        "nombre_archivo": run.nombre_archivo,
        "validacion": reporte_dict,
        "periodos": p.to_dict(),
        "resumen_periodo": resumen_periodo,
        "hallazgos": hallazgos,
        "dimensiones": DIMENSIONES,
        "grafico_linea_usd": grafico_linea,
        "grafico_contribuciones_sucursal": grafico_contribuciones,
        "ia_configurada": assistant.ia_disponible(),
    }


@app.get("/api/runs")
def listar_runs() -> dict:
    en_memoria = store.listar_ids()
    return {"runs_en_memoria": en_memoria, "runs_supabase": supabase_client.listar_runs()}


@app.get("/api/runs/{run_id}")
def obtener_run(run_id: str) -> dict:
    run = store.obtener(run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Esa corrida ya no está en memoria (el servidor se reinició o expiró el cache). Volvé a subir el archivo.",
        )
    return {
        "run_id": run.run_id,
        "nombre_archivo": run.nombre_archivo,
        "validacion": run.validacion,
        "periodos": run.periodos,
        "resumen_periodo": run.resumen_periodo,
        "hallazgos": run.hallazgos,
        "anotaciones": run.anotaciones,
    }


@app.post("/api/charts")
def calcular_grafico(body: ChartRequestBody) -> dict:
    run = store.obtener(body.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Corrida no encontrada. Volvé a subir el archivo.")

    req = {
        "chart_type": body.chart_type,
        "metric": body.metric,
        "group_by": body.group_by,
        "filters": body.filters,
        "comparison": body.comparison,
    }
    valido, motivo = charts.validar_chart_request(req)
    if not valido:
        raise HTTPException(status_code=400, detail=motivo)

    return charts.calcular_datos_grafico(req, run.df_reciente, run.df_comparativo, [s for s in run.semanas_grafico])


@app.post("/api/anotaciones")
def agregar_anotacion(body: AnotacionRequest) -> dict:
    ok = store.agregar_anotacion(body.run_id, body.texto)
    if not ok:
        raise HTTPException(status_code=404, detail="Corrida no encontrada.")
    run = store.obtener(body.run_id)
    return {"anotaciones": run.anotaciones if run else []}


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    run = store.obtener(body.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Corrida no encontrada. Volvé a subir el archivo.")

    ctx = ai_tools.ContextoHerramientas(
        cruces=run.cruces,
        df_reciente=run.df_reciente,
        df_comparativo=run.df_comparativo,
        semanas_grafico=run.semanas_grafico,
        semanas_historico=run.semanas_historico,
        resumen_total=run.resumen_periodo,
    )
    logger.info("chat: run_id=%s pregunta=%r historial=%d contexto=%s", body.run_id, body.pregunta, len(body.historial), bool(body.contexto_seleccionado))
    historial = [{"pregunta": h.pregunta, "respuesta_resumen": h.respuesta_resumen} for h in body.historial]
    respuesta = assistant.responder(body.pregunta, ctx, run.hallazgos, body.contexto_seleccionado, run.anotaciones, historial)
    supabase_client.guardar_conversacion(body.run_id, body.pregunta, respuesta)
    return respuesta
