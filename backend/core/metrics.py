"""Cálculo de métricas sobre un DataFrame ya filtrado a un período/segmento.

Nada acá sabe de IA ni de la interfaz: son funciones puras Polars -> dict/float
que se reutilizan tanto para los KPIs generales como para cada uno de los 31
cruces. Los pedidos siempre se cuentan con `n_unique(pedido_id)`, nunca con la
cantidad de filas (una misma fila puede repetirse por familia/posición dentro
de un mismo pedido).
"""
from __future__ import annotations

from datetime import date

import polars as pl

from config import (
    COL_CLIENTE_ID,
    COL_KG,
    COL_PEDIDO_ID,
    COL_POSICIONES,
    COL_SEMANA,
    COL_USD,
)


def calcular_metricas_periodo(df_periodo: pl.DataFrame) -> dict:
    """Métricas base de un DataFrame ya recortado a un período (y, opcionalmente, un segmento)."""
    if df_periodo.height == 0:
        return {
            "usd": 0.0,
            "pedidos": 0,
            "clientes": 0,
            "kg": 0.0,
            "posiciones": 0.0,
            "ticket_promedio": 0.0,
            "posiciones_por_pedido": 0.0,
            "usd_por_posicion": 0.0,
            "kg_por_pedido": 0.0,
            "pedidos_por_cliente": 0.0,
            "n_semanas_con_datos": 0,
            "concentracion_clientes": 0.0,
            "n_filas": 0,
        }

    usd = float(df_periodo[COL_USD].sum())
    kg = float(df_periodo[COL_KG].sum())
    posiciones = float(df_periodo[COL_POSICIONES].sum())
    pedidos = int(df_periodo[COL_PEDIDO_ID].n_unique())
    clientes = int(df_periodo[COL_CLIENTE_ID].n_unique())
    n_semanas = int(df_periodo[COL_SEMANA].n_unique())

    return {
        "usd": usd,
        "pedidos": pedidos,
        "clientes": clientes,
        "kg": kg,
        "posiciones": posiciones,
        "ticket_promedio": safe_div(usd, pedidos),
        "posiciones_por_pedido": safe_div(posiciones, pedidos),
        "usd_por_posicion": safe_div(usd, posiciones),
        "kg_por_pedido": safe_div(kg, pedidos),
        "pedidos_por_cliente": safe_div(pedidos, clientes),
        "n_semanas_con_datos": n_semanas,
        "concentracion_clientes": _concentracion_clientes(df_periodo),
        "n_filas": df_periodo.height,
    }


def comparar(actual: dict, anterior: dict, metrica: str = "usd") -> dict:
    """Variación absoluta y porcentual de una métrica entre dos períodos."""
    v_actual = actual.get(metrica, 0.0)
    v_anterior = anterior.get(metrica, 0.0)
    diferencia = v_actual - v_anterior
    variacion_pct = safe_div(diferencia, v_anterior) * 100 if v_anterior else None
    return {
        "actual": v_actual,
        "anterior": v_anterior,
        "diferencia_absoluta": diferencia,
        "variacion_pct": variacion_pct,
    }


def participacion(valor_segmento: float, valor_total: float) -> float:
    """Qué porcentaje del total representa el segmento (período actual)."""
    return safe_div(valor_segmento, valor_total) * 100


def contribucion_variacion(diferencia_segmento: float, diferencia_total: float) -> float:
    """Qué porcentaje de la variación total explica la variación de este segmento.

    Si el total no varió (o varió 0), no hay variación que contribuir.
    """
    if diferencia_total == 0:
        return 0.0
    return safe_div(diferencia_segmento, diferencia_total) * 100


def serie_semanal(df: pl.DataFrame, semanas: list[date], metrica_col: str = COL_USD) -> list[dict]:
    """Serie ordenada semana -> valor agregado, incluyendo semanas sin datos (0)."""
    if df.height == 0:
        agregado = {}
    else:
        agg = df.group_by(COL_SEMANA).agg(pl.col(metrica_col).sum().alias("valor"))
        agregado = dict(zip(agg[COL_SEMANA].to_list(), agg["valor"].to_list()))

    return [{"semana": s.isoformat(), "valor": float(agregado.get(s, 0.0))} for s in semanas]


def tendencia_semanal(serie: list[float]) -> dict:
    """Pendiente de una regresión lineal simple sobre la serie (x = índice de semana).

    Devuelve la pendiente normalizada por el promedio de la serie (para que sea
    comparable entre segmentos de distinta magnitud) y una clasificación.
    """
    n = len(serie)
    if n < 2 or all(v == 0 for v in serie):
        return {"pendiente": 0.0, "pendiente_normalizada": 0.0, "direccion": "sin_datos"}

    xs = list(range(n))
    x_bar = sum(xs) / n
    y_bar = sum(serie) / n
    num = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, serie))
    den = sum((x - x_bar) ** 2 for x in xs)
    pendiente = safe_div(num, den)
    pendiente_norm = safe_div(pendiente, y_bar) if y_bar else 0.0

    if pendiente_norm > 0.03:
        direccion = "creciente"
    elif pendiente_norm < -0.03:
        direccion = "decreciente"
    else:
        direccion = "estable"

    return {"pendiente": pendiente, "pendiente_normalizada": pendiente_norm, "direccion": direccion}


def persistencia(serie: list[float]) -> float:
    """Fracción de cambios semana-a-semana que van en la misma dirección que el
    cambio neto del período (primer vs. último valor). 0 = errático, 1 = persistente.
    """
    if len(serie) < 2:
        return 0.0

    cambio_neto = serie[-1] - serie[0]
    if cambio_neto == 0:
        return 0.0
    signo_neto = 1 if cambio_neto > 0 else -1

    deltas = [serie[i] - serie[i - 1] for i in range(1, len(serie))]
    deltas_no_nulos = [d for d in deltas if d != 0]
    if not deltas_no_nulos:
        return 0.0

    alineados = sum(1 for d in deltas_no_nulos if (1 if d > 0 else -1) == signo_neto)
    return alineados / len(deltas_no_nulos)


def volatilidad(serie: list[float]) -> float:
    """Coeficiente de variación (desvío estándar / promedio) de la serie."""
    n = len(serie)
    if n < 2:
        return 0.0
    promedio = sum(serie) / n
    if promedio == 0:
        return 0.0
    varianza = sum((v - promedio) ** 2 for v in serie) / n
    desvio = varianza ** 0.5
    return desvio / promedio


def anomalia_vs_historico(serie_historico: list[float], serie_reciente: list[float]) -> dict:
    """Compara el promedio del período reciente contra la media/desvío histórico
    (z-score). |z| > 2 se considera una anomalía respecto del comportamiento
    habitual del segmento en las semanas de contexto (histórico).
    """
    if len(serie_historico) < 2 or not serie_reciente:
        return {"z_score": 0.0, "es_anomalia": False, "promedio_historico": 0.0, "promedio_reciente": 0.0}

    media_hist = sum(serie_historico) / len(serie_historico)
    varianza_hist = sum((v - media_hist) ** 2 for v in serie_historico) / len(serie_historico)
    desvio_hist = varianza_hist ** 0.5
    media_reciente = sum(serie_reciente) / len(serie_reciente)

    if desvio_hist == 0:
        z = 0.0 if media_reciente == media_hist else (10.0 if media_reciente > media_hist else -10.0)
    else:
        z = (media_reciente - media_hist) / desvio_hist

    return {
        "z_score": z,
        "es_anomalia": abs(z) > 2.0,
        "promedio_historico": media_hist,
        "promedio_reciente": media_reciente,
    }


def decomponer_driver(
    pedidos_actual: int,
    pedidos_anterior: int,
    posiciones_por_pedido_actual: float,
    posiciones_por_pedido_anterior: float,
    usd_por_posicion_actual: float,
    usd_por_posicion_anterior: float,
) -> dict:
    """Descomposición exacta de Δusd en 3 factores multiplicativos:
    usd = pedidos × posiciones_por_pedido × usd_por_posicion.

    Usa sustitución en cadena (cada factor se evalúa con los dos anteriores ya
    "actualizados" y el resto en su valor anterior), de forma que la suma de
    las 3 contribuciones da exactamente la diferencia total de usd. Así se
    responde de forma verificable "¿el cambio se explica por pedidos, ticket o
    posiciones por pedido?" sin que la IA tenga que estimarlo.
    """
    d_pedidos = pedidos_actual - pedidos_anterior
    d_pos_pp = posiciones_por_pedido_actual - posiciones_por_pedido_anterior
    d_usd_pp = usd_por_posicion_actual - usd_por_posicion_anterior

    contrib_pedidos = d_pedidos * posiciones_por_pedido_anterior * usd_por_posicion_anterior
    contrib_posiciones_por_pedido = pedidos_actual * d_pos_pp * usd_por_posicion_anterior
    contrib_usd_por_posicion = pedidos_actual * posiciones_por_pedido_actual * d_usd_pp

    contribuciones = {
        "pedidos": contrib_pedidos,
        "posiciones_por_pedido": contrib_posiciones_por_pedido,
        "usd_por_posicion": contrib_usd_por_posicion,
    }
    driver_principal = max(contribuciones, key=lambda k: abs(contribuciones[k]))
    total_abs = sum(abs(v) for v in contribuciones.values())
    peso_principal = safe_div(abs(contribuciones[driver_principal]), total_abs)

    return {
        "contribucion_pedidos": contrib_pedidos,
        "contribucion_posiciones_por_pedido": contrib_posiciones_por_pedido,
        "contribucion_usd_por_posicion": contrib_usd_por_posicion,
        "driver_principal": driver_principal if peso_principal >= 0.5 else "mixto",
        "peso_driver_principal_pct": peso_principal * 100,
    }


def _concentracion_clientes(df_periodo: pl.DataFrame) -> float:
    """Índice de Herfindahl-Hirschman (0-1) sobre la participación de usd por cliente.

    Cerca de 0: usd repartido entre muchos clientes. Cerca de 1: concentrado en pocos.
    """
    if df_periodo.height == 0:
        return 0.0
    por_cliente = df_periodo.group_by(COL_CLIENTE_ID).agg(pl.col(COL_USD).sum().alias("usd"))
    total = float(por_cliente["usd"].sum())
    if total <= 0:
        return 0.0
    shares = (por_cliente["usd"] / total).to_list()
    return sum(s ** 2 for s in shares)


def safe_div(numerador: float, denominador: float) -> float:
    if not denominador:
        return 0.0
    return numerador / denominador
