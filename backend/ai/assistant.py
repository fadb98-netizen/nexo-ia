"""Orquestación del asistente: tool-calling + respuesta estructurada + validación.

Si no hay OPENAI_API_KEY configurada, o la IA no logra producir una respuesta
que pase el validador después de reintentar, se cae al modo determinístico:
se muestra el mejor hallazgo que Python ya calculó, sin ningún texto generado
por IA. La aplicación nunca falla por falta de IA (criterio de aceptación).
"""
from __future__ import annotations

import json
import os

from config import DIMENSIONES
from ai import prompts, tools, validator
from core import charts

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_RONDAS_HERRAMIENTAS = 6
MAX_REINTENTOS_VALIDACION = 1

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
) -> dict:
    anotaciones = anotaciones or []
    client = _cliente()
    if client is None:
        return _respuesta_determinista(
            pregunta, hallazgos, "No hay una clave de OpenAI configurada: se muestra el mejor hallazgo calculado por Python."
        )

    mensajes = [
        {"role": "system", "content": prompts.SYSTEM_ASISTENTE},
        {"role": "user", "content": prompts.prompt_pregunta(pregunta, contexto_seleccionado, anotaciones)},
    ]

    try:
        _correr_rondas_de_herramientas(client, mensajes, ctx)
        respuesta = _forzar_respuesta_estructurada(client, mensajes)

        valido, problemas = validator.validar_respuesta(respuesta, ctx.cruces)
        intentos = 0
        while not valido and intentos < MAX_REINTENTOS_VALIDACION:
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
            valido, problemas = validator.validar_respuesta(respuesta, ctx.cruces)
            intentos += 1

        if not valido:
            return _respuesta_determinista(
                pregunta,
                hallazgos,
                "La IA no logró producir una respuesta con evidencia suficiente después de "
                "reintentar; se muestra el mejor hallazgo calculado por Python. Detalle: "
                + "; ".join(problemas),
            )

        respuesta["origen"] = "ia"
        respuesta["graficos"] = _resolver_graficos(respuesta.get("graficos", []), ctx)
        return respuesta

    except Exception as exc:  # noqa: BLE001 - cualquier falla de la API de OpenAI no debe tumbar la app
        return _respuesta_determinista(pregunta, hallazgos, f"Error consultando la IA ({exc}); se muestra el mejor hallazgo calculado por Python.")


def _correr_rondas_de_herramientas(client, mensajes: list[dict], ctx: tools.ContextoHerramientas) -> None:
    for _ in range(MAX_RONDAS_HERRAMIENTAS):
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


def _resolver_graficos(graficos: list[dict], ctx: tools.ContextoHerramientas) -> list[dict]:
    resueltos = []
    for g in graficos:
        req = {
            "chart_type": g.get("chart_type"),
            "metric": g.get("metric"),
            "group_by": g.get("group_by"),
            "filters": {f["dimension"]: f["valor"] for f in g.get("filters", [])},
            "comparison": g.get("comparison", "ninguna"),
        }
        valido, motivo = charts.validar_chart_request(req)
        if not valido:
            resueltos.append({"titulo": g.get("title", ""), "error": motivo})
            continue
        datos = charts.calcular_datos_grafico(req, ctx.df_reciente, ctx.df_comparativo, ctx.semanas_grafico)
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
        }

    elegido = _elegir_hallazgo_por_palabras_clave(pregunta, hallazgos)
    serie_str = ", ".join(f"{v:,.0f}".replace(",", ".") for v in elegido["evolucion_semanal"])

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
        "graficos": [],
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
