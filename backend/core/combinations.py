"""Motor de los 31 cruces: todas las combinaciones de 1 a 5 dimensiones.

Genera, sin excepción, las 31 combinaciones posibles de
sucursal / familia / sector_industrial / asesor / abc_cliente (2^5 - 1), calcula
el set completo de métricas para cada una (período reciente vs. comparativo)
y recién al final aplica el filtro de materialidad. Los resultados de una
misma corrida (mismo `run_id`) se cachean en memoria para no repetir el
cálculo de los 31 cruces en cada request.
"""
from __future__ import annotations

import itertools
from datetime import date

import polars as pl

from config import (
    COL_CLIENTE_ID,
    COL_KG,
    COL_PEDIDO_ID,
    COL_POSICIONES,
    COL_SEMANA,
    COL_USD,
    DIMENSIONES,
    MIN_CONTRIBUCION_ABS_PCT,
    MIN_PEDIDOS_COMBINADOS,
    SEMANAS_RECIENTE,
)
from core import metrics

_CACHE: dict[str, list[dict]] = {}

_COLS_NUMERICAS_ACTUAL = ["usd", "kg", "posiciones", "pedidos", "clientes"]
_COLS_NUMERICAS_ANTERIOR = [f"{c}_ant" for c in _COLS_NUMERICAS_ACTUAL]


def generar_combinaciones_de_dimensiones() -> list[tuple[str, ...]]:
    """Las 31 combinaciones: 5 de 1 nivel, 10 de 2, 10 de 3, 5 de 4, 1 de 5."""
    combos: list[tuple[str, ...]] = []
    for r in range(1, len(DIMENSIONES) + 1):
        combos.extend(itertools.combinations(DIMENSIONES, r))
    return combos


def calcular_todas_las_combinaciones(
    df_reciente: pl.DataFrame,
    df_comparativo: pl.DataFrame,
    df_historico: pl.DataFrame,
    semanas_grafico: list[date],
    semanas_historico: list[date],
) -> list[dict]:
    """Calcula las 31 combinaciones completas, SIN aplicar todavía el filtro
    de materialidad (eso es responsabilidad de `filtrar_material`).

    `semanas_grafico` = comparativo + reciente (hasta 8, para persistencia,
    volatilidad y tendencia). `semanas_historico` = hasta 8 semanas más
    antiguas, usadas sólo como línea de base para detectar anomalías.
    """
    total_actual = metrics.calcular_metricas_periodo(df_reciente)
    total_anterior = metrics.calcular_metricas_periodo(df_comparativo)
    total_diferencia_usd = total_actual["usd"] - total_anterior["usd"]

    df_grafico = pl.concat([df_comparativo, df_reciente]) if df_comparativo.height or df_reciente.height else df_reciente

    resultados: list[dict] = []
    for combo in generar_combinaciones_de_dimensiones():
        resultados.extend(
            _calcular_cruce(
                df_reciente,
                df_comparativo,
                df_grafico,
                df_historico,
                semanas_grafico,
                semanas_historico,
                combo,
                total_actual["usd"],
                total_anterior["usd"],
                total_diferencia_usd,
            )
        )
    return resultados


def calcular_todas_las_combinaciones_cacheado(
    run_id: str,
    df_reciente: pl.DataFrame,
    df_comparativo: pl.DataFrame,
    df_historico: pl.DataFrame,
    semanas_grafico: list[date],
    semanas_historico: list[date],
) -> list[dict]:
    if run_id in _CACHE:
        return _CACHE[run_id]
    resultado = calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, semanas_grafico, semanas_historico
    )
    _CACHE[run_id] = resultado
    return resultado


def limpiar_cache(run_id: str | None = None) -> None:
    if run_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(run_id, None)


def filtrar_material(cruces: list[dict]) -> list[dict]:
    """Único filtro permitido: volumen insuficiente o irrelevancia material.

    Un cruce pasa si tiene volumen suficiente de pedidos Y (explica una
    porción relevante de la variación total O representa por sí mismo una
    porción relevante del negocio actual — este segundo criterio evita que,
    cuando la variación total es ~0, todos los segmentos queden filtrados por
    "no explicar nada" pese a moverse fuerte en direcciones opuestas).
    """
    resultado = []
    for c in cruces:
        volumen_ok = (c["pedidos_actual"] + c["pedidos_anterior"]) >= MIN_PEDIDOS_COMBINADOS
        relevante_ok = (
            abs(c["contribucion_pct"]) >= MIN_CONTRIBUCION_ABS_PCT
            or abs(c["impacto_relativo_pct"]) >= MIN_CONTRIBUCION_ABS_PCT
        )
        if volumen_ok and relevante_ok:
            resultado.append(c)
    return resultado


def _agregar(df: pl.DataFrame, combo: tuple[str, ...], sufijo: str = "") -> pl.DataFrame:
    if df.height == 0:
        return pl.DataFrame(schema={**{d: pl.Utf8 for d in combo}, **{f"{c}{sufijo}": pl.Float64 for c in _COLS_NUMERICAS_ACTUAL}})
    return df.group_by(list(combo)).agg(
        [
            pl.col(COL_USD).sum().alias(f"usd{sufijo}"),
            pl.col(COL_KG).sum().alias(f"kg{sufijo}"),
            pl.col(COL_POSICIONES).sum().alias(f"posiciones{sufijo}"),
            pl.col(COL_PEDIDO_ID).n_unique().alias(f"pedidos{sufijo}"),
            pl.col(COL_CLIENTE_ID).n_unique().alias(f"clientes{sufijo}"),
        ]
    )


def _serie_semanal_por_segmento(
    df_grafico: pl.DataFrame, combo: tuple[str, ...], semanas_grafico: list[date]
) -> dict[tuple, list[float]]:
    if df_grafico.height == 0:
        return {}
    agg = df_grafico.group_by(list(combo) + [COL_SEMANA]).agg(pl.col(COL_USD).sum().alias("usd"))
    mapa: dict[tuple, dict] = {}
    for row in agg.iter_rows(named=True):
        key = tuple(row[d] for d in combo)
        mapa.setdefault(key, {})[row[COL_SEMANA]] = row["usd"]
    return {key: [float(valores.get(s, 0.0)) for s in semanas_grafico] for key, valores in mapa.items()}


def _calcular_cruce(
    df_reciente: pl.DataFrame,
    df_comparativo: pl.DataFrame,
    df_grafico: pl.DataFrame,
    df_historico: pl.DataFrame,
    semanas_grafico: list[date],
    semanas_historico: list[date],
    combo: tuple[str, ...],
    total_actual_usd: float,
    total_anterior_usd: float,
    total_diferencia_usd: float,
) -> list[dict]:
    actual_agg = _agregar(df_reciente, combo, "")
    anterior_agg = _agregar(df_comparativo, combo, "_ant")

    merged = actual_agg.join(anterior_agg, on=list(combo), how="full", coalesce=True)
    todas_num = [c for c in _COLS_NUMERICAS_ACTUAL + _COLS_NUMERICAS_ANTERIOR if c in merged.columns]
    merged = merged.with_columns([pl.col(c).fill_null(0.0) for c in todas_num])

    series_por_segmento = _serie_semanal_por_segmento(df_grafico, combo, semanas_grafico)
    series_historico_por_segmento = _serie_semanal_por_segmento(df_historico, combo, semanas_historico)

    resultados = []
    for row in merged.iter_rows(named=True):
        dims = {d: row[d] for d in combo}
        segmento_key = tuple(row[d] for d in combo)

        usd_actual, usd_anterior = row["usd"], row["usd_ant"]
        pedidos_actual, pedidos_anterior = int(row["pedidos"]), int(row["pedidos_ant"])
        posiciones_actual, posiciones_anterior = row["posiciones"], row["posiciones_ant"]
        kg_actual, kg_anterior = row["kg"], row["kg_ant"]
        clientes_actual, clientes_anterior = int(row["clientes"]), int(row["clientes_ant"])

        diferencia_usd = usd_actual - usd_anterior
        variacion_pct = metrics.safe_div(diferencia_usd, usd_anterior) * 100 if usd_anterior else None

        pos_pp_actual = metrics.safe_div(posiciones_actual, pedidos_actual)
        pos_pp_anterior = metrics.safe_div(posiciones_anterior, pedidos_anterior)
        usd_pp_actual = metrics.safe_div(usd_actual, posiciones_actual)
        usd_pp_anterior = metrics.safe_div(usd_anterior, posiciones_anterior)

        serie = series_por_segmento.get(segmento_key, [0.0] * len(semanas_grafico))
        serie_reciente = serie[-SEMANAS_RECIENTE:]
        serie_historico = series_historico_por_segmento.get(segmento_key, [0.0] * len(semanas_historico))

        resultados.append(
            {
                "nivel": len(combo),
                "dimensiones": list(combo),
                "segmento": dims,
                "usd_actual": usd_actual,
                "usd_anterior": usd_anterior,
                "diferencia_absoluta": diferencia_usd,
                "variacion_pct": variacion_pct,
                "pedidos_actual": pedidos_actual,
                "pedidos_anterior": pedidos_anterior,
                "posiciones_actual": posiciones_actual,
                "posiciones_anterior": posiciones_anterior,
                "kg_actual": kg_actual,
                "kg_anterior": kg_anterior,
                "clientes_actual": clientes_actual,
                "clientes_anterior": clientes_anterior,
                "ticket_actual": metrics.safe_div(usd_actual, pedidos_actual),
                "ticket_anterior": metrics.safe_div(usd_anterior, pedidos_anterior),
                "posiciones_por_pedido_actual": pos_pp_actual,
                "posiciones_por_pedido_anterior": pos_pp_anterior,
                "usd_por_posicion_actual": usd_pp_actual,
                "usd_por_posicion_anterior": usd_pp_anterior,
                "participacion_pct": metrics.participacion(usd_actual, total_actual_usd),
                "participacion_anterior_pct": metrics.participacion(usd_anterior, total_anterior_usd),
                "contribucion_pct": metrics.contribucion_variacion(diferencia_usd, total_diferencia_usd),
                "impacto_relativo_pct": metrics.safe_div(abs(diferencia_usd), total_actual_usd) * 100,
                "serie_semanal_usd": serie,
                "persistencia": metrics.persistencia(serie),
                "volatilidad": metrics.volatilidad(serie),
                "tendencia": metrics.tendencia_semanal(serie),
                "anomalia": metrics.anomalia_vs_historico(serie_historico, serie_reciente),
                "driver": metrics.decomponer_driver(
                    pedidos_actual, pedidos_anterior, pos_pp_actual, pos_pp_anterior, usd_pp_actual, usd_pp_anterior
                ),
                "n_semanas_observadas": sum(1 for v in serie if v != 0),
            }
        )
    return resultados
