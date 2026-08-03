"""Validador automático de la respuesta estructurada de la IA.

Si la respuesta no trae evidencia numérica verificable, no investigó lo
suficientemente profundo, o cita una cifra que no coincide con el cruce real,
se marca como inválida para que `assistant.py` la reintente (o caiga al modo
determinístico). Esto es lo que impide que la IA "invente" — cada número
citado se contrasta contra los cruces que Python ya calculó.
"""
from __future__ import annotations

import re

from config import DIMENSIONES, MIN_CONTRIBUCION_ABS_PCT
from ai.prompts import TIPOS_GRAFICO_PERMITIDOS

_NUMERO_RE = re.compile(r"-?\d[\d.,]*")


def _extraer_numero(texto: str) -> float | None:
    """Extrae el primer número de un string que puede venir en notación
    estándar (115756.29) o en notación es-AR (115.756,29) — ambas aparecen
    en las respuestas de la IA según cite un valor "en crudo" de una tool o
    lo redacte en prosa.
    """
    m = _NUMERO_RE.search(texto)
    if not m:
        return None
    crudo = m.group()
    if "," in crudo and "." in crudo:
        crudo = crudo.replace(".", "").replace(",", ".")  # es-AR: punto miles, coma decimal
    elif "," in crudo:
        crudo = crudo.replace(",", ".")  # sólo coma: es decimal
    # sólo con puntos (o sin separadores): ya es notación estándar, no tocar
    try:
        return float(crudo)
    except ValueError:
        return None


def _buscar_cruce(segmento: list[dict], cruces: list[dict]) -> dict | None:
    if not segmento:
        return None
    valores = {s["dimension"]: s["valor"] for s in segmento}
    for c in cruces:
        if set(c["dimensiones"]) == set(valores.keys()) and all(
            c["segmento"].get(k) == v for k, v in valores.items()
        ):
            return c
    return None


def _hay_cruce_mas_profundo_no_mencionado(cruce: dict, cruces: list[dict]) -> bool:
    """¿Existe un cruce que contiene los mismos valores + al menos una
    dimensión más, con mayor |contribución|, y sigue siendo material?
    """
    if cruce["nivel"] >= len(DIMENSIONES):
        return False
    valores = cruce["segmento"]
    contribucion_base = abs(cruce["contribucion_pct"])
    for c in cruces:
        if c["nivel"] <= cruce["nivel"]:
            continue
        if not set(cruce["dimensiones"]).issubset(set(c["dimensiones"])):
            continue
        if not all(c["segmento"].get(k) == v for k, v in valores.items()):
            continue
        volumen_ok = (c["pedidos_actual"] + c["pedidos_anterior"]) >= 5
        if volumen_ok and abs(c["contribucion_pct"]) > contribucion_base * 1.3:
            return True
    return False


def _validar_ranking(ranking: list[dict], cruces_disponibles: list[dict]) -> list[str]:
    problemas: list[str] = []
    for item in ranking:
        segmento_item = item.get("segmento") or []
        metrica = item.get("metrica")
        valor_citado = _extraer_numero(str(item.get("valor", "")))
        cruce = _buscar_cruce(segmento_item, cruces_disponibles)
        if cruce is None:
            problemas.append(
                f"Un ítem del ranking cita una combinación ({segmento_item}) que no corresponde a "
                "ningún cruce calculado por Python: posible invención."
            )
            continue
        if valor_citado is None or metrica not in cruce or not isinstance(cruce[metrica], (int, float)):
            problemas.append(
                f"Un ítem del ranking para {segmento_item} no trae un valor numérico verificable "
                f"para la métrica '{metrica}'."
            )
            continue
        real = float(cruce[metrica])
        tolerancia = max(abs(real) * 0.05, 1.0)
        if abs(abs(valor_citado) - abs(real)) > tolerancia:
            problemas.append(
                f"El ranking cita '{metrica}'={valor_citado} para {segmento_item}, pero el valor "
                f"real calculado es {real}."
            )
    return problemas


def _aplanar_resumen_total(resumen_total: dict | None) -> dict:
    """Convierte {"usd": {"actual": .., "anterior": .., ...}, "pedidos": {...}, ...}
    en un dict plano {"usd_actual": .., "usd_anterior": .., ...} para poder
    contrastar contra `metricas_respaldo` con el mismo mecanismo que un cruce."""
    if not resumen_total:
        return {}
    plano = {}
    for metrica, comparacion in resumen_total.items():
        if not isinstance(comparacion, dict):
            continue
        for campo, valor in comparacion.items():
            if isinstance(valor, (int, float)):
                plano[f"{metrica}_{campo}"] = valor
    return plano


def validar_respuesta(
    respuesta: dict, cruces_disponibles: list[dict], resumen_total: dict | None = None
) -> tuple[bool, list[str]]:
    problemas: list[str] = []

    segmento = respuesta.get("segmento") or []
    metricas = respuesta.get("metricas_respaldo") or []
    cuanto_explica = respuesta.get("cuanto_explica") or ""
    evolucion = respuesta.get("evolucion_semanal") or ""
    graficos = respuesta.get("graficos") or []
    ranking = respuesta.get("ranking") or []

    dimensiones_en_segmento = [s.get("dimension") for s in segmento]
    if len(dimensiones_en_segmento) != len(set(dimensiones_en_segmento)):
        problemas.append(
            "El 'segmento' de nivel superior repite la misma dimensión con más de un valor "
            "(eso corresponde a un ranking, no a un solo cruce): usá el campo 'ranking' para "
            "comparar varios valores de una misma dimensión, y dejá 'segmento' con un único "
            "valor por dimensión."
        )

    # segmento vacío es válido: es la respuesta a una pregunta sobre el TOTAL/
    # agregado general, no sobre un cruce específico. En ese caso se contrasta
    # metricas_respaldo contra el resumen total real en vez de contra un cruce.
    if not segmento and not ranking:
        totales_planos = _aplanar_resumen_total(resumen_total)
        for m in metricas:
            nombre_norm = re.sub(r"[^a-z_]", "", str(m.get("nombre", "")).lower().replace(" ", "_"))
            valor_citado = _extraer_numero(str(m.get("valor", "")))
            if nombre_norm in totales_planos and valor_citado is not None:
                real = float(totales_planos[nombre_norm])
                tolerancia = max(abs(real) * 0.05, 1.0)
                if abs(abs(valor_citado) - abs(real)) > tolerancia:
                    problemas.append(
                        f"La métrica '{m.get('nombre')}' citada ({valor_citado}) no coincide con el "
                        f"total real calculado ({real})."
                    )

    if len(metricas) < 2:
        problemas.append("Trae menos de 2 métricas de respaldo: no hay evidencia numérica suficiente.")

    if _extraer_numero(cuanto_explica) is None:
        problemas.append("'cuanto_explica' no contiene ningún número verificable.")

    if len(evolucion.strip()) < 15:
        problemas.append("La evolución semanal está vacía o es demasiado breve para ser evidencia real.")

    if len(graficos) > 2:
        problemas.append("Pide más de 2 gráficos.")
    for g in graficos:
        if g.get("chart_type") not in TIPOS_GRAFICO_PERMITIDOS:
            problemas.append(f"Tipo de gráfico no permitido: {g.get('chart_type')}.")

    cruce_citado = _buscar_cruce(segmento, cruces_disponibles)
    if segmento and cruce_citado is None:
        problemas.append(
            "El segmento citado no corresponde a ningún cruce calculado por Python: posible invención."
        )
    elif cruce_citado is not None:
        for m in metricas:
            nombre_norm = re.sub(r"[^a-z_]", "", str(m.get("nombre", "")).lower().replace(" ", "_"))
            valor_citado = _extraer_numero(str(m.get("valor", "")))
            if nombre_norm in cruce_citado and isinstance(cruce_citado[nombre_norm], (int, float)) and valor_citado is not None:
                real = float(cruce_citado[nombre_norm])
                tolerancia = max(abs(real) * 0.05, 1.0)
                if abs(abs(valor_citado) - abs(real)) > tolerancia:
                    problemas.append(
                        f"La métrica '{m.get('nombre')}' citada ({valor_citado}) no coincide con el "
                        f"valor real calculado ({real})."
                    )

        # Con ranking no vacío la pregunta es un "top N" dentro de una misma
        # dimensión (ej. top asesores) — profundizar más dimensiones sobre el
        # #1 del ranking no tiene sentido para ese tipo de pregunta.
        if not ranking and _hay_cruce_mas_profundo_no_mencionado(cruce_citado, cruces_disponibles):
            problemas.append(
                "Existe un cruce más profundo y con más contribución que el citado, y la respuesta "
                "no lo investigó: profundidad insuficiente."
            )

        contribucion_citada = abs(cruce_citado.get("contribucion_pct", 0))
        if respuesta.get("hay_causa_dominante") and contribucion_citada < MIN_CONTRIBUCION_ABS_PCT:
            problemas.append(
                "Afirma que hay una causa dominante pero la contribución del segmento citado es mínima."
            )

    if len(ranking) > 10:
        problemas.append("El ranking trae más de 10 ítems.")
    problemas.extend(_validar_ranking(ranking, cruces_disponibles))

    return (len(problemas) == 0), problemas
