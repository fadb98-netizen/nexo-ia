"""Clasificación de patrones y scoring de hallazgos.

Este módulo NO calcula métricas nuevas: sólo lee los cruces ya calculados por
`combinations.py` (que a su vez usa `metrics.py`), los clasifica según el tipo
de patrón que representan y les asigna un score para poder priorizar entre 3 y
5 hallazgos. Ningún número se inventa acá — todo viene de los cruces.
"""
from __future__ import annotations

from config import (
    MAX_HALLAZGOS,
    MIN_HALLAZGOS,
    MIN_PEDIDOS_COMBINADOS,
    MIN_SEMANAS_OBSERVADAS,
)
from core import evidence
from core.metrics import safe_div

PESOS_SCORE = {
    "impacto": 0.25,
    "contribucion": 0.20,
    "persistencia": 0.15,
    "volumen": 0.10,
    "profundidad": 0.10,
    "desviacion": 0.10,
    "anomalia": 0.10,
}


def calcular_score(cruce: dict, max_impacto_abs: float, variacion_pct_total: float | None) -> tuple[float, dict]:
    impacto_norm = safe_div(abs(cruce["diferencia_absoluta"]), max_impacto_abs) if max_impacto_abs else 0.0
    contribucion_norm = min(abs(cruce["contribucion_pct"]) / 100, 1.0)
    persistencia_norm = cruce["persistencia"]
    volumen_norm = min((cruce["pedidos_actual"] + cruce["pedidos_anterior"]) / 50, 1.0)
    profundidad_norm = cruce["nivel"] / 5

    if cruce["variacion_pct"] is not None and variacion_pct_total is not None:
        desviacion_norm = min(abs(cruce["variacion_pct"] - variacion_pct_total) / 50, 1.0)
    else:
        desviacion_norm = 0.0

    anomalia_norm = 1.0 if cruce["anomalia"]["es_anomalia"] else 0.0

    positivos = (
        PESOS_SCORE["impacto"] * impacto_norm
        + PESOS_SCORE["contribucion"] * contribucion_norm
        + PESOS_SCORE["persistencia"] * persistencia_norm
        + PESOS_SCORE["volumen"] * volumen_norm
        + PESOS_SCORE["profundidad"] * profundidad_norm
        + PESOS_SCORE["desviacion"] * desviacion_norm
        + PESOS_SCORE["anomalia"] * anomalia_norm
    )

    penal_volatilidad = min(cruce["volatilidad"] / 2, 1.0)
    penal_pocos_datos = 1.0 if cruce["n_semanas_observadas"] < MIN_SEMANAS_OBSERVADAS else 0.0

    score = 100 * positivos - 15 * penal_volatilidad - 20 * penal_pocos_datos
    score = max(0.0, min(100.0, score))

    desglose = {
        "impacto_norm": round(impacto_norm, 2),
        "contribucion_norm": round(contribucion_norm, 2),
        "persistencia_norm": round(persistencia_norm, 2),
        "volumen_norm": round(volumen_norm, 2),
        "profundidad_norm": round(profundidad_norm, 2),
        "desviacion_norm": round(desviacion_norm, 2),
        "anomalia_norm": anomalia_norm,
        "penalizacion_volatilidad": round(penal_volatilidad, 2),
        "penalizacion_pocos_datos": penal_pocos_datos,
    }
    return score, desglose


def nivel_de_evidencia(cruce: dict, score: float) -> str:
    volumen = cruce["pedidos_actual"] + cruce["pedidos_anterior"]
    if score >= 65 and volumen >= 15 and cruce["n_semanas_observadas"] >= 4:
        return "alta"
    if score >= 35 and volumen >= MIN_PEDIDOS_COMBINADOS:
        return "media"
    return "baja"


def clasificar_patron(
    cruce: dict,
    variacion_pct_total: float | None,
    es_dominante_en_su_dimension: bool | None,
) -> str:
    if cruce["anomalia"]["es_anomalia"]:
        return "anomalia"

    if cruce["persistencia"] >= 0.75 and cruce["n_semanas_observadas"] >= 4:
        return "tendencia_persistente"

    if (
        cruce["variacion_pct"] is not None
        and variacion_pct_total is not None
        and abs(cruce["variacion_pct"]) > 5
        and abs(variacion_pct_total) > 0.5
        and (cruce["variacion_pct"] > 0) != (variacion_pct_total > 0)
    ):
        return "segmento_atipico"

    if cruce["nivel"] == 1 and es_dominante_en_su_dimension:
        return "concentrado"

    if cruce["nivel"] == 1 and es_dominante_en_su_dimension is False:
        return "generalizado"

    if cruce["nivel"] >= 3:
        return "interaccion_profunda"

    return "cambio_relevante"


_LIMITACIONES_POR_TIPO = {
    "anomalia": "El comportamiento se desvía fuerte de su propio histórico; igual puede deberse a un evento puntual (un pedido grande, un feriado) y no a un cambio estructural.",
}


def _limitaciones(cruce: dict, tipo: str) -> list[str]:
    limitaciones = []
    volumen = cruce["pedidos_actual"] + cruce["pedidos_anterior"]
    if volumen < 15:
        limitaciones.append(f"Volumen relativamente bajo ({volumen} pedidos combinados): tomar la magnitud con cautela.")
    if cruce["volatilidad"] > 1.0:
        limitaciones.append("La serie semanal es volátil; el patrón podría no repetirse la semana próxima.")
    if cruce["n_semanas_observadas"] < 4:
        limitaciones.append("Menos de 4 semanas con datos en el segmento: la tendencia es preliminar.")
    if tipo in _LIMITACIONES_POR_TIPO:
        limitaciones.append(_LIMITACIONES_POR_TIPO[tipo])
    return limitaciones


def _titulo(cruce: dict, tipo: str) -> str:
    seg = evidence.describir_segmento(cruce["segmento"])
    direccion = "cayó" if (cruce["diferencia_absoluta"] or 0) < 0 else "subió"
    etiquetas = {
        "anomalia": f"{seg}: comportamiento anómalo respecto de su histórico",
        "tendencia_persistente": f"{seg}: caída persistente semana a semana" if cruce["diferencia_absoluta"] < 0 else f"{seg}: crecimiento persistente semana a semana",
        "segmento_atipico": f"{seg} se mueve al revés del resultado general",
        "concentrado": f"La variación de {list(cruce['segmento'].keys())[0]} está concentrada en {seg}",
        "generalizado": f"La variación de {list(cruce['segmento'].keys())[0]} está repartida entre varias categorías (incluye {seg}), sin un responsable único",
        "interaccion_profunda": f"{seg}: patrón que sólo aparece al cruzar {cruce['nivel']} dimensiones",
        "cambio_relevante": f"{seg} {direccion} de forma relevante",
    }
    return etiquetas.get(tipo, f"{seg} {direccion}")


def _que_ocurrio(cruce: dict) -> str:
    seg = evidence.describir_segmento(cruce["segmento"])
    return (
        f"En {seg}, usd pasó de {evidence.formatear_usd(cruce['usd_anterior'])} a "
        f"{evidence.formatear_usd(cruce['usd_actual'])} ({evidence.formatear_pct(cruce['variacion_pct'])}), "
        f"con {cruce['pedidos_actual']} pedidos en el período reciente vs. {cruce['pedidos_anterior']} en el comparativo."
    )


def _cuanto_explica(cruce: dict) -> str:
    return (
        f"Explica {cruce['contribucion_pct']:.1f}% de la variación total de usd y representa "
        f"{cruce['participacion_pct']:.1f}% del usd actual (vs. {cruce['participacion_anterior_pct']:.1f}% en el período anterior)."
    )


def generar_hallazgos(
    cruces_materiales: list[dict],
    variacion_pct_total: float | None,
    semanas_grafico: list[str],
    min_n: int = MIN_HALLAZGOS,
    max_n: int = MAX_HALLAZGOS,
) -> list[dict]:
    """Puntúa, clasifica y arma entre `min_n` y `max_n` hallazgos priorizados.

    Evita duplicar el mismo "relato": si un cruce de nivel 5 es un
    subconjunto casi idéntico (mismo score de contribución) de uno de nivel 3
    ya elegido, no aporta nada nuevo mostrarlo aparte — se prioriza el de
    mayor score y se deja el resto disponible para que la IA profundice bajo
    pedido, no para inflar el conteo de hallazgos.
    """
    if not cruces_materiales:
        return []

    max_impacto_abs = max(abs(c["diferencia_absoluta"]) for c in cruces_materiales)

    # Dominancia dentro de cada dimensión (para concentrado vs. generalizado):
    # comparamos, sólo entre los cruces de nivel 1 de una misma dimensión, si
    # el de mayor |contribución| se lleva la mayoría de la variación de esa
    # dimensión o si está repartida.
    dominancia_nivel1: dict[str, bool] = {}
    por_dimension: dict[str, list[dict]] = {}
    for c in cruces_materiales:
        if c["nivel"] == 1:
            por_dimension.setdefault(c["dimensiones"][0], []).append(c)
    for dim, grupo in por_dimension.items():
        total_abs = sum(abs(c["diferencia_absoluta"]) for c in grupo) or 1.0
        top = max(grupo, key=lambda c: abs(c["diferencia_absoluta"]))
        top_share = abs(top["diferencia_absoluta"]) / total_abs
        for c in grupo:
            es_top = c is top
            dominancia_nivel1[id(c)] = top_share >= 0.6 if es_top else False

    candidatos = []
    for c in cruces_materiales:
        score, desglose = calcular_score(c, max_impacto_abs, variacion_pct_total)
        tipo = clasificar_patron(c, variacion_pct_total, dominancia_nivel1.get(id(c)))
        candidatos.append((score, tipo, c, desglose))

    candidatos.sort(key=lambda x: x[0], reverse=True)

    elegidos: list[tuple[float, str, dict, dict]] = []
    segmentos_cubiertos: set[frozenset] = set()
    for score, tipo, c, desglose in candidatos:
        clave_valores = frozenset(c["segmento"].items())
        # Evita elegir dos cruces que son subconjunto exacto uno del otro con
        # score casi idéntico (mismo relato contado dos veces).
        es_redundante = any(clave_valores <= otra or otra <= clave_valores for otra in segmentos_cubiertos)
        if es_redundante and len(elegidos) >= min_n:
            continue
        elegidos.append((score, tipo, c, desglose))
        segmentos_cubiertos.add(clave_valores)
        if len(elegidos) >= max_n:
            break

    if len(elegidos) < min_n:
        ya = {id(c) for _, _, c, _ in elegidos}
        for score, tipo, c, desglose in candidatos:
            if id(c) in ya:
                continue
            elegidos.append((score, tipo, c, desglose))
            if len(elegidos) >= min_n:
                break

    hallazgos = []
    for i, (score, tipo, c, desglose) in enumerate(elegidos):
        hallazgo = evidence.Hallazgo(
            id=f"h{i + 1}",
            tipo=tipo,
            titulo=_titulo(c, tipo),
            resumen=_que_ocurrio(c) + " " + _cuanto_explica(c),
            segmento=c["segmento"],
            dimensiones=c["dimensiones"],
            nivel=c["nivel"],
            que_ocurrio=_que_ocurrio(c),
            cuanto_explica=_cuanto_explica(c),
            metricas_respaldo=evidence.construir_metricas_respaldo(c),
            evolucion_semanal=c["serie_semanal_usd"],
            semanas_grafico=semanas_grafico,
            nivel_evidencia=nivel_de_evidencia(c, score),
            limitaciones=_limitaciones(c, tipo),
            driver_principal=c["driver"]["driver_principal"],
            score=score,
            score_desglose=desglose,
        )
        hallazgos.append(hallazgo.to_dict())

    return hallazgos


def detectar_compensaciones(cruces_nivel1: list[dict], umbral_pct: float = 15.0) -> list[dict]:
    """Pares de categorías de UNA MISMA dimensión que se mueven en sentido
    contrario y cuyo efecto neto se cancela parcialmente (compensación oculta).
    """
    resultados = []
    por_dimension: dict[str, list[dict]] = {}
    for c in cruces_nivel1:
        por_dimension.setdefault(c["dimensiones"][0], []).append(c)

    for dim, grupo in por_dimension.items():
        positivos = [c for c in grupo if c["diferencia_absoluta"] > 0]
        negativos = [c for c in grupo if c["diferencia_absoluta"] < 0]
        for pos in positivos:
            for neg in negativos:
                suma_abs = abs(pos["diferencia_absoluta"]) + abs(neg["diferencia_absoluta"])
                neto = pos["diferencia_absoluta"] + neg["diferencia_absoluta"]
                if suma_abs == 0:
                    continue
                cancelacion_pct = (1 - abs(neto) / suma_abs) * 100
                if cancelacion_pct >= umbral_pct and min(abs(pos["diferencia_absoluta"]), abs(neg["diferencia_absoluta"])) > 0:
                    resultados.append(
                        {
                            "dimension": dim,
                            "sube": pos["segmento"],
                            "baja": neg["segmento"],
                            "sube_diferencia": pos["diferencia_absoluta"],
                            "baja_diferencia": neg["diferencia_absoluta"],
                            "cancelacion_pct": cancelacion_pct,
                        }
                    )
    resultados.sort(key=lambda r: r["cancelacion_pct"], reverse=True)
    return resultados
