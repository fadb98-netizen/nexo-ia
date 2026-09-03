"""Orquestación del asistente: tool-calling + respuesta estructurada + validación.

Si no hay OPENAI_API_KEY configurada, o la IA no logra producir una respuesta
que pase el validador después de reintentar, se cae al modo determinístico:
se muestra el mejor hallazgo que Python ya calculó, sin ningún texto generado
por IA. La aplicación nunca falla por falta de IA (criterio de aceptación).
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os

from config import DIMENSIONES
from ai import prompts, scope, tools, validator
from core import charts, combinations, patterns
from core.evidence import describir_segmento

logger = logging.getLogger("nexo_ia.assistant")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_RONDAS_HERRAMIENTAS = 6
MAX_REINTENTOS_VALIDACION = 2
MAX_TURNOS_HISTORIAL = 4  # cuántos intercambios previos se le pasan a la IA como memoria real

# Campos numéricos de un cruce que el ranking (y metricas_respaldo, cuando la
# respuesta cita un cruce puntual) puede citar. Es una lista cerrada a
# propósito: así el validador puede leer cruce_citado[campo] directamente y
# comparar contra el valor citado, sin parsers de texto libre — y, al ser un
# `enum` del schema, el modelo no puede inventar un nombre de métrica que no
# exista en los datos (p. ej. "margen bruto").
CAMPOS_RANKING_VALIDOS = [
    "usd_actual", "usd_anterior", "diferencia_absoluta", "variacion_pct",
    "pedidos_actual", "pedidos_anterior", "clientes_actual", "clientes_anterior",
    "ticket_actual", "ticket_anterior", "participacion_pct", "participacion_anterior_pct",
    "contribucion_pct", "posiciones_por_pedido_actual", "posiciones_por_pedido_anterior",
    "persistencia", "volatilidad", "n_semanas_observadas",
]

# Campos que existen en `resumen_total` (comparación agregada de TODO el
# negocio, aplanada por _aplanar_resumen_total) — se usan como nombres válidos
# de `metricas_respaldo` cuando la respuesta describe el TOTAL (`segmento`
# vacío) en vez de un cruce puntual. Los nombres de "diferencia" y "variación"
# llevan el prefijo de la métrica acá (p. ej. `pedidos_variacion_pct`) porque
# el total compara 4 métricas distintas, a diferencia de un cruce (que sólo
# trae la diferencia/variación de usd).
CAMPOS_TOTAL_VALIDOS = [
    "usd_actual", "usd_anterior", "usd_diferencia_absoluta", "usd_variacion_pct",
    "pedidos_actual", "pedidos_anterior", "pedidos_diferencia_absoluta", "pedidos_variacion_pct",
    "clientes_actual", "clientes_anterior", "clientes_diferencia_absoluta", "clientes_variacion_pct",
    "posiciones_por_pedido_actual", "posiciones_por_pedido_anterior",
    "posiciones_por_pedido_diferencia_absoluta", "posiciones_por_pedido_variacion_pct",
]

# Universo completo de nombres de campo que `metricas_respaldo` puede citar
# (cruce puntual O total, según tenga o no `segmento`). Es un `enum` del
# schema: el modelo elige `campo` de esta lista cerrada, así el validador
# siempre puede contrastarlo contra un valor real — nunca queda un nombre
# libre sin ninguna forma de verificarlo.
CAMPOS_METRICA_RESPALDO_VALIDOS = sorted(set(CAMPOS_RANKING_VALIDOS) | set(CAMPOS_TOTAL_VALIDOS))

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
                    "description": (
                        "Evidencia numérica de respaldo. `campo` es el nombre TÉCNICO exacto "
                        "del dato tal como lo devolvió la herramienta (de una lista cerrada: no "
                        "podés inventar un campo que no exista, como 'margen' o 'rentabilidad' "
                        "— esos datos no existen en el dataset). `nombre` es sólo la etiqueta en "
                        "lenguaje humano que se muestra al usuario (ej. 'USD actual')."
                    ),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["nombre", "campo", "valor"],
                        "properties": {
                            "nombre": {"type": "string"},
                            "campo": {"type": "string", "enum": CAMPOS_METRICA_RESPALDO_VALIDOS},
                            "valor": {"type": "string"},
                        },
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


def _scope_anterior_de(historial: list[dict]) -> dict:
    if not historial:
        return {}
    segmento_previo = historial[-1].get("segmento") or []
    return {s["dimension"]: s["valor"] for s in segmento_previo if s.get("dimension")}


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
    scope_anterior = _scope_anterior_de(historial)

    if client is None:
        scope_propuesto = scope.resolver_scope_determinista(pregunta, ctx.cruces, scope_anterior)
        scope_final = scope.validar_scope_contra_cruces(scope_propuesto, ctx.cruces)
        cruces_scope = scope.filtrar_cruces_por_scope(ctx.cruces, scope_final)
        return _respuesta_determinista(
            pregunta,
            hallazgos,
            "No hay una clave de OpenAI configurada: se muestra el mejor hallazgo calculado por Python.",
            scope_activo=scope_final,
            cruces_scope=cruces_scope,
            semanas_grafico=ctx.semanas_grafico,
        )

    # El scope se resuelve UNA vez, antes de tocar ninguna herramienta, y se
    # usa para filtrar los cruces que el resto del turno (tools + validador +
    # fallback) puede ver — así deja de depender de que el modelo se acuerde
    # de repetir el mismo filtro en cada llamada (ver ai/scope.py).
    scope_propuesto = scope.resolver_scope(client, MODEL, pregunta, scope_anterior, contexto_seleccionado)
    scope_final = scope.validar_scope_contra_cruces(scope_propuesto, ctx.cruces)
    cruces_scope = scope.filtrar_cruces_por_scope(ctx.cruces, scope_final)
    ctx_scope = dataclasses.replace(ctx, cruces=cruces_scope, scope_activo=scope_final)

    logger.info(
        "responder: scope_anterior=%s scope_propuesto=%s scope_final=%s cruces_visibles=%d/%d",
        scope_anterior, scope_propuesto, scope_final, len(cruces_scope), len(ctx.cruces),
    )

    mensajes = [{"role": "system", "content": prompts.SYSTEM_ASISTENTE}]
    for turno in historial[-MAX_TURNOS_HISTORIAL:]:
        mensajes.append({"role": "user", "content": turno["pregunta"]})
        mensajes.append({"role": "assistant", "content": turno["respuesta_resumen"]})
    mensajes.append(
        {"role": "user", "content": prompts.prompt_pregunta(pregunta, contexto_seleccionado, anotaciones, scope_final)}
    )

    logger.info(
        "responder: pregunta=%r turnos_historial=%d contexto=%s",
        pregunta, min(len(historial), MAX_TURNOS_HISTORIAL), contexto_seleccionado.get("titulo") if contexto_seleccionado else None,
    )

    def _fallback(nota: str) -> dict:
        return _respuesta_determinista(
            pregunta, hallazgos, nota, scope_activo=scope_final, cruces_scope=cruces_scope, semanas_grafico=ctx.semanas_grafico
        )

    try:
        _correr_rondas_de_herramientas(client, mensajes, ctx_scope)
        respuesta = _forzar_respuesta_estructurada(client, mensajes)

        valido, problemas = validator.validar_respuesta(respuesta, ctx_scope.cruces, ctx_scope.resumen_total)
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
            _correr_rondas_de_herramientas(client, mensajes, ctx_scope)
            respuesta = _forzar_respuesta_estructurada(client, mensajes)
            valido, problemas = validator.validar_respuesta(respuesta, ctx_scope.cruces, ctx_scope.resumen_total)
            intentos += 1

        if not valido:
            logger.info("responder: fallback determinista tras %d reintentos. problemas=%s", intentos, "; ".join(problemas))
            return _fallback(
                "La IA no logró producir una respuesta con evidencia suficiente después de "
                "reintentar; se muestra el mejor hallazgo calculado por Python. Detalle: "
                + "; ".join(problemas)
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
        return _fallback(f"Error consultando la IA ({exc}); se muestra el mejor hallazgo calculado por Python.")


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


def _hallazgos_dentro_del_scope(
    hallazgos: list[dict], scope_activo: dict, cruces_scope: list[dict] | None, semanas_grafico: list[str] | None
) -> list[dict]:
    """Restringe los hallazgos priorizados (de TODO el negocio) al scope
    activo. Si ninguno de esos hallazgos globales cae dentro del scope, se
    sintetiza uno nuevo con el mismo motor determinístico (`core/patterns.py`)
    pero usando SÓLO los cruces que ya vienen filtrados a ese scope — nunca
    se cae de vuelta al hallazgo global más alto sin relación con lo pedido
    (ese era, en la auditoría, el bug más serio de pérdida de scope: el
    'modo seguro' terminaba siendo el que menos lo respetaba)."""
    candidatos = [h for h in hallazgos if scope.objeto_en_scope(h, scope_activo)]
    if candidatos or not cruces_scope:
        return candidatos

    materiales_scope = combinations.filtrar_material(cruces_scope)
    cruce_propio = next((c for c in cruces_scope if c["segmento"] == scope_activo), None)
    variacion_pct_scope = cruce_propio["variacion_pct"] if cruce_propio else None
    return patterns.generar_hallazgos(materiales_scope, variacion_pct_scope, semanas_grafico or [], min_n=1, max_n=1)


def _respuesta_determinista(
    pregunta: str,
    hallazgos: list[dict],
    nota: str,
    scope_activo: dict | None = None,
    cruces_scope: list[dict] | None = None,
    semanas_grafico: list[str] | None = None,
) -> dict:
    scope_activo = scope_activo or {}
    candidatos = (
        _hallazgos_dentro_del_scope(hallazgos, scope_activo, cruces_scope, semanas_grafico) if scope_activo else hallazgos
    )

    if not candidatos:
        if scope_activo:
            etiqueta_scope = ", ".join(f"{d}={v}" for d, v in scope_activo.items())
            que_ocurrio = f"No encontramos un patrón con volumen o impacto suficiente dentro de {etiqueta_scope} para este período."
        else:
            que_ocurrio = "No hay hallazgos materiales para este período."
        return {
            "origen": "determinista",
            "que_ocurrio": que_ocurrio,
            "segmento": [{"dimension": d, "valor": v} for d, v in scope_activo.items()],
            "cuanto_explica": "0%",
            "metricas_respaldo": [],
            "evolucion_semanal": "Sin datos suficientes.",
            "nivel_evidencia": "baja",
            "limitaciones": nota,
            "hay_causa_dominante": False,
            "graficos": [],
            "ranking": [],
        }

    elegido = _elegir_hallazgo_por_palabras_clave(pregunta, candidatos)
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
            {"nombre": k, "campo": k, "valor": str(v)} for k, v in list(elegido["metricas_respaldo"].items())[:8]
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
