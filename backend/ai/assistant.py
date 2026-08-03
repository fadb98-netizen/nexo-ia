"""Orquestación del asistente: tool-calling + respuesta estructurada + validación.

Si no hay OPENAI_API_KEY configurada, o la IA no logra producir una respuesta
que pase el validador después de reintentar, se cae al modo determinístico:
se muestra el mejor hallazgo que Python ya calculó, sin ningún texto generado
por IA. La aplicación nunca falla por falta de IA (criterio de aceptación).
"""
from __future__ import annotations

import json
import logging
import os

from config import DIMENSIONES
from ai import prompts, tools, validator
from core import charts
from core.evidence import describir_segmento

logger = logging.getLogger("nexo_ia.assistant")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_RONDAS_HERRAMIENTAS = 6
MAX_REINTENTOS_VALIDACION = 2
MAX_TURNOS_HISTORIAL = 4  # cuántos intercambios previos se le pasan a la IA como memoria real

# Campos numéricos de un cruce que el ranking puede citar. Es una lista
# cerrada a propósito: así el validador puede leer cruce_citado[metrica]
# directamente y comparar contra el valor citado, sin parsers de texto libre.
CAMPOS_RANKING_VALIDOS = [
    "usd_actual", "usd_anterior", "diferencia_absoluta", "variacion_pct",
    "pedidos_actual", "pedidos_anterior", "clientes_actual", "clientes_anterior",
    "ticket_actual", "ticket_anterior", "participacion_pct", "contribucion_pct",
    "posiciones_por_pedido_actual", "posiciones_por_pedido_anterior",
]

RESPUESTA_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "conclusion_nexo_ia",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "que_ocurrio",
                "segmento",
                "cuanto_explica",
                "metricas_respaldo",
                "evolucion_semanal",
                "nivel_evidencia",
                "limitaciones",
                "hay_causa_dominante",
                "graficos",
                "ranking",
            ],
            "properties": {
                "que_ocurrio": {"type": "string"},
                "segmento": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["dimension", "valor"],
                        "properties": {
                            "dimension": {"type": "string", "enum": DIMENSIONES},
                            "valor": {"type": "string"},
                        },
                    },
                },
                "cuanto_explica": {"type": "string"},
                "metricas_respaldo": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["nombre", "valor"],
                        "properties": {"nombre": {"type": "string"}, "valor": {"type": "string"}},
                    },
                },
                "evolucion_semanal": {"type": "string"},
                "nivel_evidencia": {"type": "string", "enum": ["alta", "media", "baja"]},
                "limitaciones": {"type": "string"},
                "hay_causa_dominante": {"type": "boolean"},
                "graficos": {
                    "type": "array",
                    "maxItems": 2,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["chart_type", "metric", "group_by", "filters", "comparison", "title"],
                        "properties": {
                            "chart_type": {
                                "type": "string",
                                "enum": ["line", "diverging_bar", "heatmap", "stacked_100", "pie", "table"],
                            },
                            "metric": {"type": "string"},
                            "group_by": {"type": "string"},
                            "filters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["dimension", "valor"],
                                    "properties": {
                                        "dimension": {"type": "string", "enum": DIMENSIONES},
                                        "valor": {"type": "string"},
                                    },
                                },
                            },
                            "comparison": {"type": "string"},
                            "title": {"type": "string"},
                        },
                    },
                },
                "ranking": {
                    "type": "array",
                    "maxItems": 10,
                    "description": (
                        "Para preguntas de tipo 'top N' o que comparan varios segmentos a la "
                        "vez: un item por segmento, cada uno con su propia combinación de "
                        "dimensiones. NO usar 'segmento' para esto — 'segmento' es sólo la "
                        "combinación principal que se explica en que_ocurrio."
                    ),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["segmento", "metrica", "valor"],
                        "properties": {
                            "segmento": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["dimension", "valor"],
                                    "properties": {
                                        "dimension": {"type": "string", "enum": DIMENSIONES},
                                        "valor": {"type": "string"},
                                    },
                                },
                            },
                            "metrica": {"type": "string", "enum": CAMPOS_RANKING_VALIDOS},
                            "valor": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def ia_disponible() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _cliente():
    if not ia_disponible():
        return None
    from openai import OpenAI

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def responder(
    pregunta: str,
    ctx: tools.ContextoHerramientas,
    hallazgos: list[dict],
    contexto_seleccionado: dict | None = None,
    anotaciones: list[str] | None = None,
    historial: list[dict] | None = None,
) -> dict:
    anotaciones = anotaciones or []
    historial = historial or []
    client = _cliente()
    if client is None:
        return _respuesta_determinista(
            pregunta, hallazgos, "No hay una clave de OpenAI configurada: se muestra el mejor hallazgo calculado por Python."
        )

    mensajes = [{"role": "system", "content": prompts.SYSTEM_ASISTENTE}]
    for turno in historial[-MAX_TURNOS_HISTORIAL:]:
        mensajes.append({"role": "user", "content": turno["pregunta"]})
        mensajes.append({"role": "assistant", "content": turno["respuesta_resumen"]})
    mensajes.append({"role": "user", "content": prompts.prompt_pregunta(pregunta, contexto_seleccionado, anotaciones)})

    logger.info(
        "responder: pregunta=%r turnos_historial=%d contexto=%s",
        pregunta, min(len(historial), MAX_TURNOS_HISTORIAL), contexto_seleccionado.get("titulo") if contexto_seleccionado else None,
    )

    try:
        _correr_rondas_de_herramientas(client, mensajes, ctx)
        respuesta = _forzar_respuesta_estructurada(client, mensajes)

        valido, problemas = validator.validar_respuesta(respuesta, ctx.cruces, ctx.resumen_total)
        intentos = 0
        while not valido and intentos < MAX_REINTENTOS_VALIDACION:
            logger.info("responder: validacion fallida (intento %d): %s", intentos, "; ".join(problemas))
            mensajes.append({"role": "assistant", "content": json.dumps(respuesta, ensure_ascii=False)})
            mensajes.append(
                {
                    "role": "user",
                    "content": (
                        "Tu respuesta anterior tiene estos problemas, corregilos usando más "
                        "herramientas si hace falta y volvé a responder: " + "; ".join(problemas)
                    ),
                }
            )
            _correr_rondas_de_herramientas(client, mensajes, ctx)
            respuesta = _forzar_respuesta_estructurada(client, mensajes)
            valido, problemas = validator.validar_respuesta(respuesta, ctx.cruces, ctx.resumen_total)
            intentos += 1

        if not valido:
            logger.info("responder: fallback determinista tras %d reintentos. problemas=%s", intentos, "; ".join(problemas))
            return _respuesta_determinista(
                pregunta,
                hallazgos,
                "La IA no logró producir una respuesta con evidencia suficiente después de "
                "reintentar; se muestra el mejor hallazgo calculado por Python. Detalle: "
                + "; ".join(problemas),
            )

        respuesta["origen"] = "ia"
        graficos_solicitados = respuesta.get("graficos", [])
        respuesta["graficos"] = _resolver_graficos(graficos_solicitados, ctx, respuesta.get("segmento") or [])
        logger.info(
            "responder: OK nivel_evidencia=%s graficos_solicitados=%s ranking_items=%d",
            respuesta.get("nivel_evidencia"),
            [g.get("chart_type") for g in graficos_solicitados],
            len(respuesta.get("ranking") or []),
        )
        return respuesta

    except Exception as exc:  # noqa: BLE001 - cualquier falla de la API de OpenAI no debe tumbar la app
        logger.exception("responder: error consultando la IA")
        return _respuesta_determinista(pregunta, hallazgos, f"Error consultando la IA ({exc}); se muestra el mejor hallazgo calculado por Python.")


def _contar_registros(resultado: dict) -> int:
    for clave in ("filas", "series"):
        if isinstance(resultado.get(clave), list):
            return len(resultado[clave])
    return 1 if resultado.get("encontrado") else 0


def _correr_rondas_de_herramientas(client, mensajes: list[dict], ctx: tools.ContextoHerramientas) -> None:
    for ronda in range(MAX_RONDAS_HERRAMIENTAS):
        resp = client.chat.completions.create(model=MODEL, messages=mensajes, tools=tools.TOOLS_SCHEMA, tool_choice="auto")
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return
        mensajes.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            }
        )
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            resultado = tools.ejecutar_tool(tc.function.name, args, ctx)
            logger.info(
                "tool_call[ronda %d]: %s(%s) -> %d registros%s",
                ronda, tc.function.name, args, _contar_registros(resultado),
                " [nota: " + resultado["nota"] + "]" if resultado.get("nota") else "",
            )
            mensajes.append(
                {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(resultado, ensure_ascii=False, default=str)}
            )


def _forzar_respuesta_estructurada(client, mensajes: list[dict]) -> dict:
    mensajes_finales = mensajes + [
        {
            "role": "user",
            "content": "Devolvé ahora tu conclusión final en el formato JSON estructurado pedido, sin llamar más herramientas.",
        }
    ]
    resp = client.chat.completions.create(model=MODEL, messages=mensajes_finales, response_format=RESPUESTA_JSON_SCHEMA)
    return json.loads(resp.choices[0].message.content)


def _datos_vacios(datos: dict) -> bool:
    """Detecta si un gráfico ya calculado no tiene ningún valor real que
    mostrar (todo cero o listas vacías), para no mandarle al frontend un
    gráfico en blanco sin explicación."""
    tipo = datos.get("tipo")
    if tipo == "line":
        return not any(p["valor"] for s in datos.get("series", []) for p in s.get("datos", []))
    if tipo == "diverging_bar":
        return not any(c["diferencia"] for c in datos.get("categorias", []))
    if tipo == "heatmap":
        return not any(c["valor"] for c in datos.get("celdas", []))
    if tipo == "stacked_100":
        return not any(f.get("categorias") for f in datos.get("filas", []))
    if tipo == "pie":
        return not any(p["valor"] for p in datos.get("porciones", []))
    if tipo == "table":
        return not datos.get("filas")
    return False


def _resolver_graficos(graficos: list[dict], ctx: tools.ContextoHerramientas, segmento_principal: list[dict]) -> list[dict]:
    resueltos = []
    for g in graficos:
        filters = {f["dimension"]: f["valor"] for f in g.get("filters", [])}
        group_by = g.get("group_by") or ""
        # Si la respuesta cita un segmento específico, el/los gráficos tienen que
        # mostrar ESE segmento, no el total — si la IA pidió el gráfico sin
        # filtrar (o filtrando sólo una parte), se completa con el resto del
        # segmento citado para que el gráfico y el texto no se contradigan.
        for s in segmento_principal:
            dim, val = s.get("dimension"), s.get("valor")
            if dim and dim not in filters and dim not in group_by.split(","):
                filters[dim] = val
        req = {
            "chart_type": g.get("chart_type"),
            "metric": g.get("metric"),
            "group_by": group_by,
            "filters": filters,
            "comparison": g.get("comparison", "ninguna"),
        }
        valido, motivo = charts.validar_chart_request(req)
        if not valido:
            logger.info("grafico rechazado: %s (%s)", req, motivo)
            resueltos.append({"titulo": g.get("title", ""), "error": motivo})
            continue
        datos = charts.calcular_datos_grafico(req, ctx.df_reciente, ctx.df_comparativo, ctx.semanas_grafico)
        if _datos_vacios(datos):
            logger.info("grafico sin datos: %s", req)
            resueltos.append(
                {
                    "titulo": g.get("title", ""),
                    "error": "No hay datos para esta combinación en el período analizado.",
                }
            )
            continue
        resueltos.append({"titulo": g.get("title", ""), "solicitud": req, "datos": datos})
    return resueltos


def _respuesta_determinista(pregunta: str, hallazgos: list[dict], nota: str) -> dict:
    if not hallazgos:
        return {
            "origen": "determinista",
            "que_ocurrio": "No hay hallazgos materiales para este período.",
            "segmento": [],
            "cuanto_explica": "0%",
            "metricas_respaldo": [],
            "evolucion_semanal": "Sin datos suficientes.",
            "nivel_evidencia": "baja",
            "limitaciones": nota,
            "hay_causa_dominante": False,
            "graficos": [],
            "ranking": [],
        }

    elegido = _elegir_hallazgo_por_palabras_clave(pregunta, hallazgos)
    serie_str = ", ".join(f"{v:,.0f}".replace(",", ".") for v in elegido["evolucion_semanal"])

    grafico_linea = {
        "titulo": "Evolución semanal — usd",
        "solicitud": {"chart_type": "line", "metric": "usd", "group_by": "semana", "filters": {}, "comparison": "ninguna"},
        "datos": {
            "tipo": "line",
            "series": [
                {
                    "nombre": describir_segmento(elegido["segmento"]),
                    "datos": [
                        {"semana": s, "valor": float(v)}
                        for s, v in zip(elegido["semanas_grafico"], elegido["evolucion_semanal"])
                    ],
                }
            ],
        },
    }

    return {
        "origen": "determinista",
        "que_ocurrio": elegido["que_ocurrio"],
        "segmento": [{"dimension": d, "valor": str(elegido["segmento"][d])} for d in elegido["dimensiones"]],
        "cuanto_explica": elegido["cuanto_explica"],
        "metricas_respaldo": [
            {"nombre": k, "valor": str(v)} for k, v in list(elegido["metricas_respaldo"].items())[:8]
        ],
        "evolucion_semanal": f"Serie semanal (usd), {elegido['semanas_grafico'][0]} a {elegido['semanas_grafico'][-1]}: {serie_str}",
        "nivel_evidencia": elegido["nivel_evidencia"],
        "limitaciones": (nota + " " + "; ".join(elegido["limitaciones"])).strip(),
        "hay_causa_dominante": elegido["tipo"] in ("concentrado", "tendencia_persistente", "anomalia"),
        "graficos": [grafico_linea],
        "ranking": [],
    }


def _elegir_hallazgo_por_palabras_clave(pregunta: str, hallazgos: list[dict]) -> dict:
    p = pregunta.lower()
    if "concentrad" in p or "generaliz" in p:
        for h in hallazgos:
            if h["tipo"] in ("concentrado", "generalizado"):
                return h
    if "compens" in p:
        for h in hallazgos:
            if h["tipo"] == "generalizado":
                return h
    if "persistent" in p or "reciente" in p:
        for h in hallazgos:
            if h["tipo"] == "tendencia_persistente":
                return h
    if "anóma" in p or "anoma" in p:
        for h in hallazgos:
            if h["tipo"] == "anomalia":
                return h
    return hallazgos[0]
