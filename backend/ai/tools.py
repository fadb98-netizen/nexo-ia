"""Herramientas que la IA puede invocar. Todas son de sólo lectura sobre
resultados YA CALCULADOS por `core/` — ninguna hace un cálculo nuevo desde el
CSV crudo, y ninguna le da a la IA acceso a filas individuales (salvo el
agregado por `cliente_id`, que es la única columna de identidad presente en
el dataset — no hay nombre de cliente en el schema).
"""
from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from config import COL_CLIENTE_ID, COL_PEDIDO_ID, DIMENSIONES, MIN_PEDIDOS_COMBINADOS
from core import metrics


@dataclass
class ContextoHerramientas:
    cruces: list[dict]  # las 31 combinaciones completas, SIN filtrar por materialidad
    df_reciente: pl.DataFrame
    df_comparativo: pl.DataFrame
    semanas_grafico: list[str]
    semanas_historico: list[str]
    resumen_total: dict | None = None  # comparación actual vs. anterior agregada de TODO el dataset (sin filtrar)


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "obtener_tabla_dimension",
            "description": (
                "Ranking de una sola dimensión (nivel 1) ordenado por impacto. "
                "Punto de partida para ver qué categorías mueven más el resultado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dimension": {"type": "string", "enum": DIMENSIONES},
                    "top_n": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                },
                "required": ["dimension"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "desglosar_variacion",
            "description": (
                "Devuelve TODOS los cruces (materiales y no materiales, marcados) para una "
                "combinación específica de dimensiones (1 a 5), opcionalmente restringida a "
                "valores fijos de algunas de esas dimensiones. Usar esto para profundizar: "
                "primero 1 dimensión, después 2, 3... hasta encontrar el cruce más profundo "
                "que siga siendo material."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dimensiones": {
                        "type": "array",
                        "items": {"type": "string", "enum": DIMENSIONES},
                        "minItems": 1,
                        "maxItems": 5,
                        "description": "Qué dimensiones componen el cruce a consultar.",
                    },
                    "filtro": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dimension": {"type": "string", "enum": DIMENSIONES},
                                "valor": {"type": "string"},
                            },
                            "required": ["dimension", "valor"],
                        },
                        "description": "Restringe el resultado a filas donde esa dimensión tenga ese valor exacto.",
                    },
                },
                "required": ["dimensiones"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_resumen_total",
            "description": (
                "Comparación actual vs. período anterior de usd, pedidos, clientes y "
                "posiciones_por_pedido, agregando TODO el dataset sin filtrar a ningún "
                "segmento. Usar esto (y sólo esto) cuando la pregunta sea sobre la evolución, "
                "el total o el resultado GENERAL del negocio, sin pedir explicación de un "
                "segmento en particular — nunca inventes estos totales, siempre pedí esta "
                "herramienta."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detalle_cliente",
            "description": (
                "Métricas agregadas (nunca filas crudas) de un cliente puntual por cliente_id: "
                "usd, pedidos, kg, posiciones, período reciente vs. comparativo."
            ),
            "parameters": {
                "type": "object",
                "properties": {"cliente_id": {"type": "string"}},
                "required": ["cliente_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_tendencia_historica",
            "description": (
                "Evolución semanal (últimas 8 semanas) y comparación contra las 8 semanas "
                "históricas previas de un cruce exacto. Usar para responder '¿es reciente o "
                "persistente?' o '¿es una anomalía respecto de lo habitual?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dimensiones": {
                        "type": "array",
                        "items": {"type": "string", "enum": DIMENSIONES},
                        "minItems": 1,
                        "maxItems": 5,
                    },
                    "filtro": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dimension": {"type": "string", "enum": DIMENSIONES},
                                "valor": {"type": "string"},
                            },
                            "required": ["dimension", "valor"],
                        },
                        "description": "Debe traer exactamente un valor por cada dimensión listada arriba.",
                    },
                },
                "required": ["dimensiones", "filtro"],
            },
        },
    },
]


def _filtro_a_dict(filtro: list[dict] | None) -> dict:
    return {f["dimension"]: f["valor"] for f in (filtro or [])}


def _cruce_publico(c: dict) -> dict:
    """Recorta el cruce interno a lo que tiene sentido mandarle al modelo
    (saca la serie completa cruda del histórico, que no aporta como texto)."""
    return {
        "dimensiones": c["dimensiones"],
        "segmento": c["segmento"],
        "nivel": c["nivel"],
        "usd_actual": c["usd_actual"],
        "usd_anterior": c["usd_anterior"],
        "diferencia_absoluta": c["diferencia_absoluta"],
        "variacion_pct": c["variacion_pct"],
        "pedidos_actual": c["pedidos_actual"],
        "pedidos_anterior": c["pedidos_anterior"],
        "clientes_actual": c["clientes_actual"],
        "clientes_anterior": c["clientes_anterior"],
        "ticket_actual": round(c["ticket_actual"], 2),
        "ticket_anterior": round(c["ticket_anterior"], 2),
        "posiciones_por_pedido_actual": round(c["posiciones_por_pedido_actual"], 2),
        "posiciones_por_pedido_anterior": round(c["posiciones_por_pedido_anterior"], 2),
        "participacion_pct": round(c["participacion_pct"], 2),
        "participacion_anterior_pct": round(c["participacion_anterior_pct"], 2),
        "contribucion_pct": round(c["contribucion_pct"], 2),
        "persistencia": round(c["persistencia"], 2),
        "volatilidad": round(c["volatilidad"], 2),
        "tendencia": c["tendencia"],
        "driver": c["driver"],
        "n_semanas_observadas": c["n_semanas_observadas"],
        "material": (c["pedidos_actual"] + c["pedidos_anterior"]) >= MIN_PEDIDOS_COMBINADOS,
    }


def obtener_tabla_dimension(ctx: ContextoHerramientas, dimension: str, top_n: int = 10) -> dict:
    candidatos = [c for c in ctx.cruces if c["nivel"] == 1 and c["dimensiones"] == [dimension]]
    candidatos.sort(key=lambda c: abs(c["diferencia_absoluta"]), reverse=True)
    return {"dimension": dimension, "filas": [_cruce_publico(c) for c in candidatos[:top_n]]}


def desglosar_variacion(ctx: ContextoHerramientas, dimensiones: list[str], filtro: list[dict] | None = None) -> dict:
    dims_set = list(dict.fromkeys(dimensiones))
    filtro_dict = _filtro_a_dict(filtro)

    candidatos = [c for c in ctx.cruces if c["nivel"] == len(dims_set) and set(c["dimensiones"]) == set(dims_set)]
    if filtro_dict:
        candidatos = [
            c for c in candidatos
            if all(c["segmento"].get(k) == v for k, v in filtro_dict.items())
        ]
    candidatos.sort(key=lambda c: abs(c["contribucion_pct"]), reverse=True)

    if not candidatos:
        return {
            "dimensiones": dims_set,
            "filtro": filtro_dict,
            "filas": [],
            "nota": (
                "No hay datos para esa combinación de dimensiones/filtro. Si adivinaste el "
                "valor del filtro, llamá obtener_tabla_dimension para esa dimensión primero y "
                "usá un valor real de ahí — no reintentes con otro valor inventado."
            ),
        }

    return {"dimensiones": dims_set, "filtro": filtro_dict, "filas": [_cruce_publico(c) for c in candidatos[:15]]}


def obtener_resumen_total(ctx: ContextoHerramientas) -> dict:
    if not ctx.resumen_total:
        return {"error": "No hay resumen total disponible para esta corrida."}
    return ctx.resumen_total


def detalle_cliente(ctx: ContextoHerramientas, cliente_id: str) -> dict:
    def _agregar(df: pl.DataFrame) -> dict:
        sub = df.filter(pl.col(COL_CLIENTE_ID) == cliente_id)
        return metrics.calcular_metricas_periodo(sub)

    actual = _agregar(ctx.df_reciente)
    anterior = _agregar(ctx.df_comparativo)
    if actual["n_filas"] == 0 and anterior["n_filas"] == 0:
        return {"cliente_id": cliente_id, "encontrado": False}

    comparacion = metrics.comparar(actual, anterior, "usd")
    return {
        "cliente_id": cliente_id,
        "encontrado": True,
        "usd_actual": actual["usd"],
        "usd_anterior": anterior["usd"],
        "diferencia_absoluta": comparacion["diferencia_absoluta"],
        "variacion_pct": comparacion["variacion_pct"],
        "pedidos_actual": actual["pedidos"],
        "pedidos_anterior": anterior["pedidos"],
        "ticket_actual": round(actual["ticket_promedio"], 2),
        "ticket_anterior": round(anterior["ticket_promedio"], 2),
    }


def consultar_tendencia_historica(ctx: ContextoHerramientas, dimensiones: list[str], filtro: list[dict]) -> dict:
    dims_set = list(dict.fromkeys(dimensiones))
    filtro_dict = _filtro_a_dict(filtro)

    if set(filtro_dict.keys()) != set(dims_set):
        return {"error": "El filtro debe traer exactamente un valor por cada dimensión listada."}

    candidatos = [c for c in ctx.cruces if c["nivel"] == len(dims_set) and set(c["dimensiones"]) == set(dims_set)]
    match = next((c for c in candidatos if all(c["segmento"].get(k) == v for k, v in filtro_dict.items())), None)
    if match is None:
        return {
            "error": (
                "No se encontró ese cruce exacto entre los datos calculados. Si adivinaste "
                "el valor del filtro, llamá obtener_tabla_dimension para esa dimensión primero "
                "y usá un valor real de ahí. Si preguntan por la evolución TOTAL sin filtrar a "
                "un segmento, no uses esta herramienta: pedí directamente un gráfico line con "
                "filters vacío en tu respuesta final."
            )
        }

    return {
        "segmento": match["segmento"],
        "semanas_grafico": ctx.semanas_grafico,
        "serie_semanal_usd": match["serie_semanal_usd"],
        "persistencia": round(match["persistencia"], 2),
        "volatilidad": round(match["volatilidad"], 2),
        "tendencia": match["tendencia"],
        "anomalia": match["anomalia"],
    }


DISPATCH = {
    "obtener_tabla_dimension": obtener_tabla_dimension,
    "desglosar_variacion": desglosar_variacion,
    "obtener_resumen_total": obtener_resumen_total,
    "detalle_cliente": detalle_cliente,
    "consultar_tendencia_historica": consultar_tendencia_historica,
}


def ejecutar_tool(nombre: str, argumentos: dict, ctx: ContextoHerramientas) -> dict:
    fn = DISPATCH.get(nombre)
    if fn is None:
        return {"error": f"Herramienta desconocida: {nombre}"}
    try:
        return fn(ctx, **argumentos)
    except TypeError as exc:
        return {"error": f"Argumentos inválidos para {nombre}: {exc}"}
