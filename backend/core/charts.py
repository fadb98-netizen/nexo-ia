"""Valida las solicitudes de gráfico que devuelve la IA y calcula los datos.

La IA nunca genera valores ni código de gráfico: devuelve una solicitud
estructurada (chart_type, metric, group_by, filters, comparison, title).
Este módulo la valida y, si es válida, calcula los datos reales desde los
DataFrames ya filtrados por período — el frontend sólo dibuja lo que llega acá.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _datetime

import polars as pl

from config import (
    COL_CLIENTE_ID,
    COL_KG,
    COL_PEDIDO_ID,
    COL_POSICIONES,
    COL_SEMANA,
    COL_USD,
    DIMENSIONES,
)

TIPOS_PERMITIDOS = {"line", "diverging_bar", "heatmap", "stacked_100", "pie", "table"}
METRICAS_PERMITIDAS = {"usd", "kg", "posiciones", "pedidos", "clientes", "ticket"}
COMPARACIONES_PERMITIDAS = {"segmento_vs_total", "actual_vs_anterior", "ninguna"}
GRUPOS_VALIDOS = set(DIMENSIONES) | {COL_SEMANA}


def normalizar_chart_request(req: dict) -> dict:
    """La IA a veces manda mayúsculas ('USD', 'Semana') donde se espera el
    literal exacto en minúsculas. Se normaliza acá (una sola vez, para todo
    caller) en vez de rechazar una solicitud por lo demás válida.
    """
    return {
        "chart_type": str(req.get("chart_type", "")).strip().lower(),
        "metric": str(req.get("metric", "")).strip().lower(),
        "group_by": ",".join(p.strip().lower() for p in str(req.get("group_by", "")).split(",")),
        "filters": dict(req.get("filters") or {}),
        "comparison": _normalizar_comparison(req.get("comparison", "ninguna")),
    }


def _normalizar_comparison(valor: str) -> str:
    v = str(valor or "ninguna").strip().lower()
    if v in COMPARACIONES_PERMITIDAS:
        return v
    if "total" in v:
        return "segmento_vs_total"
    if "anterior" in v or "vs" in v:
        return "actual_vs_anterior"
    return "ninguna"


def validar_chart_request(req: dict) -> tuple[bool, str]:
    req = normalizar_chart_request(req)
    chart_type = req.get("chart_type")
    metric = req.get("metric")
    group_by = req.get("group_by", "")
    filters = req.get("filters") or {}
    comparison = req.get("comparison", "ninguna")

    if chart_type not in TIPOS_PERMITIDOS:
        return False, f"chart_type inválido: {chart_type}"
    if metric not in METRICAS_PERMITIDAS:
        return False, f"metric inválida: {metric}"
    if comparison not in COMPARACIONES_PERMITIDAS:
        return False, f"comparison inválida: {comparison}"
    for dim in filters:
        if dim not in DIMENSIONES:
            return False, f"filtro sobre dimensión desconocida: {dim}"

    if chart_type == "heatmap":
        dims = [d.strip() for d in group_by.split(",") if d.strip()]
        if len(dims) != 2 or any(d not in DIMENSIONES for d in dims):
            return False, "heatmap necesita group_by con exactamente 2 dimensiones separadas por coma."
    elif chart_type == "line":
        if group_by not in (COL_SEMANA, ""):
            return False, "line sólo soporta group_by='semana'."
    else:
        if group_by not in GRUPOS_VALIDOS:
            return False, f"group_by inválido para {chart_type}: {group_by}"

    return True, ""


def _a_date(valor) -> _date:
    if isinstance(valor, _date):
        return valor
    return _datetime.strptime(str(valor), "%Y-%m-%d").date()


def _aplicar_filtros(df: pl.DataFrame, filters: dict) -> pl.DataFrame:
    for dim, valor in filters.items():
        df = df.filter(pl.col(dim) == valor)
    return df


def _agregado(df: pl.DataFrame, group_cols: list[str], metric: str) -> pl.DataFrame:
    if df.height == 0:
        return pl.DataFrame(schema={**{c: pl.Utf8 for c in group_cols}, "valor": pl.Float64})

    if metric == "pedidos":
        base = df.group_by(group_cols).agg(pl.col(COL_PEDIDO_ID).n_unique().alias("valor"))
    elif metric == "clientes":
        base = df.group_by(group_cols).agg(pl.col(COL_CLIENTE_ID).n_unique().alias("valor"))
    elif metric == "ticket":
        agg = df.group_by(group_cols).agg(
            [pl.col(COL_USD).sum().alias("_usd"), pl.col(COL_PEDIDO_ID).n_unique().alias("_pedidos")]
        )
        base = agg.with_columns(
            (pl.col("_usd") / pl.when(pl.col("_pedidos") > 0).then(pl.col("_pedidos")).otherwise(1)).alias("valor")
        ).select(group_cols + ["valor"])
    else:
        col = {"usd": COL_USD, "kg": COL_KG, "posiciones": COL_POSICIONES}[metric]
        base = df.group_by(group_cols).agg(pl.col(col).sum().alias("valor"))
    return base


def calcular_datos_grafico(
    req: dict,
    df_reciente: pl.DataFrame,
    df_comparativo: pl.DataFrame,
    semanas_grafico: list,
) -> dict:
    req = normalizar_chart_request(req)
    chart_type = req["chart_type"]
    metric = req["metric"]
    group_by = req.get("group_by", "")
    filters = req.get("filters") or {}
    comparison = req.get("comparison", "ninguna")
    semanas_grafico = [_a_date(s) for s in semanas_grafico]

    df_periodo = pl.concat([df_comparativo, df_reciente]) if df_comparativo.height or df_reciente.height else df_reciente
    df_filtrado = _aplicar_filtros(df_periodo, filters)

    if chart_type == "line":
        agg = _agregado(df_filtrado, [COL_SEMANA], metric)
        mapa = dict(zip(agg[COL_SEMANA].to_list(), agg["valor"].to_list()))
        serie = [{"semana": s.isoformat(), "valor": float(mapa.get(s, 0.0))} for s in semanas_grafico]
        resultado = {"tipo": "line", "series": [{"nombre": "Segmento", "datos": serie}]}
        if comparison == "segmento_vs_total":
            agg_total = _agregado(df_periodo, [COL_SEMANA], metric)
            mapa_total = dict(zip(agg_total[COL_SEMANA].to_list(), agg_total["valor"].to_list()))
            serie_total = [{"semana": s.isoformat(), "valor": float(mapa_total.get(s, 0.0))} for s in semanas_grafico]
            resultado["series"].append({"nombre": "Total", "datos": serie_total})
        return resultado

    if chart_type == "diverging_bar":
        actual = _agregado(_aplicar_filtros(df_reciente, filters), [group_by], metric)
        anterior = _agregado(_aplicar_filtros(df_comparativo, filters), [group_by], metric)
        mapa_ant = dict(zip(anterior[group_by].to_list(), anterior["valor"].to_list()))
        filas = []
        for cat, val_actual in zip(actual[group_by].to_list(), actual["valor"].to_list()):
            val_anterior = mapa_ant.pop(cat, 0.0)
            filas.append({"categoria": cat, "diferencia": float(val_actual - val_anterior)})
        for cat, val_anterior in mapa_ant.items():
            filas.append({"categoria": cat, "diferencia": float(-val_anterior)})
        filas.sort(key=lambda f: f["diferencia"])
        return {"tipo": "diverging_bar", "categorias": filas}

    if chart_type == "heatmap":
        dims = [d.strip() for d in group_by.split(",")]
        agg = _agregado(df_filtrado, dims, metric)
        celdas = [
            {"x": row[dims[0]], "y": row[dims[1]], "valor": float(row["valor"])}
            for row in agg.iter_rows(named=True)
        ]
        return {"tipo": "heatmap", "eje_x": dims[0], "eje_y": dims[1], "celdas": celdas}

    if chart_type == "stacked_100":
        agg = _agregado(df_filtrado, [COL_SEMANA, group_by], metric)
        por_semana: dict = {}
        for row in agg.iter_rows(named=True):
            por_semana.setdefault(row[COL_SEMANA], {})[row[group_by]] = row["valor"]
        filas = []
        for s in semanas_grafico:
            valores = por_semana.get(s, {})
            total = sum(valores.values()) or 1.0
            filas.append(
                {
                    "semana": s.isoformat(),
                    "categorias": {cat: round(v / total * 100, 2) for cat, v in valores.items()},
                }
            )
        return {"tipo": "stacked_100", "dimension": group_by, "filas": filas}

    if chart_type == "pie":
        agg = _agregado(df_filtrado, [group_by], metric)
        return {
            "tipo": "pie",
            "porciones": [
                {"categoria": row[group_by], "valor": float(row["valor"])} for row in agg.iter_rows(named=True)
            ],
        }

    if chart_type == "table":
        group_cols = [group_by] if group_by in DIMENSIONES else DIMENSIONES[:1]
        actual = _agregado(df_reciente.pipe(_aplicar_filtros, filters), group_cols, metric)
        anterior = _agregado(df_comparativo.pipe(_aplicar_filtros, filters), group_cols, metric)
        mapa_ant = dict(zip(anterior[group_cols[0]].to_list(), anterior["valor"].to_list()))
        filas = [
            {
                "categoria": row[group_cols[0]],
                "actual": float(row["valor"]),
                "anterior": float(mapa_ant.get(row[group_cols[0]], 0.0)),
            }
            for row in actual.iter_rows(named=True)
        ]
        return {"tipo": "table", "filas": filas}

    return {"tipo": chart_type, "error": "tipo no implementado"}
