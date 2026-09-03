from __future__ import annotations

from datetime import date

import polars as pl

from ai import assistant, tools
from config import COL_FAMILIA, COL_SEMANA, COL_SUCURSAL, COL_USD, COL_KG, COL_PEDIDO_ID, COL_POSICIONES, COL_CLIENTE_ID
from tests.conftest import SEMANA_COMPARATIVA, SEMANA_RECIENTE


def _df(filas: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(filas)


def _ctx() -> tools.ContextoHerramientas:
    semanas = [date(2026, 6, 1), date(2026, 6, 8)]
    filas = [
        {COL_SEMANA: semanas[0], COL_SUCURSAL: "CAPITAL", COL_FAMILIA: "CH304", COL_USD: 100.0, COL_KG: 1.0, COL_PEDIDO_ID: "P1", COL_POSICIONES: 1, COL_CLIENTE_ID: "C1"},
        {COL_SEMANA: semanas[0], COL_SUCURSAL: "MENDOZA", COL_FAMILIA: "CH316", COL_USD: 900.0, COL_KG: 1.0, COL_PEDIDO_ID: "P2", COL_POSICIONES: 1, COL_CLIENTE_ID: "C2"},
        {COL_SEMANA: semanas[1], COL_SUCURSAL: "CAPITAL", COL_FAMILIA: "CH304", COL_USD: 120.0, COL_KG: 1.0, COL_PEDIDO_ID: "P3", COL_POSICIONES: 1, COL_CLIENTE_ID: "C1"},
        {COL_SEMANA: semanas[1], COL_SUCURSAL: "MENDOZA", COL_FAMILIA: "CH316", COL_USD: 950.0, COL_KG: 1.0, COL_PEDIDO_ID: "P4", COL_POSICIONES: 1, COL_CLIENTE_ID: "C2"},
        {COL_SEMANA: semanas[0], COL_SUCURSAL: "MENDOZA", COL_FAMILIA: "CH304", COL_USD: 50.0, COL_KG: 1.0, COL_PEDIDO_ID: "P5", COL_POSICIONES: 1, COL_CLIENTE_ID: "C3"},
    ]
    df = _df(filas)
    df_vacio = df.clear()
    return tools.ContextoHerramientas(
        cruces=[], df_reciente=df, df_comparativo=df_vacio, semanas_grafico=[s.isoformat() for s in semanas], semanas_historico=[]
    )


def test_resolver_graficos_inyecta_filtro_del_segmento_citado():
    """Si la respuesta cita un segmento (CAPITAL x CH304) y el gráfico de
    línea pide filters vacío, el gráfico tiene que filtrarse a ESE segmento
    -- si no, mostraría el total (CAPITAL+MENDOZA) y contradiría el texto."""
    ctx = _ctx()
    graficos = [{"chart_type": "line", "metric": "usd", "group_by": "semana", "filters": [], "title": "Evolución"}]
    segmento = [{"dimension": "sucursal", "valor": "CAPITAL"}, {"dimension": "familia", "valor": "CH304"}]

    resueltos = assistant._resolver_graficos(graficos, ctx, segmento)

    assert len(resueltos) == 1
    serie = resueltos[0]["datos"]["series"][0]["datos"]
    valores = {d["semana"]: d["valor"] for d in serie}
    # sólo CAPITAL x CH304 (100, 120), nunca el total con MENDOZA incluido (1000, 1070)
    assert valores["2026-06-01"] == 100.0
    assert valores["2026-06-08"] == 120.0


def test_resolver_graficos_no_inyecta_filtro_de_la_dimension_agrupada():
    """Si el gráfico agrupa POR sucursal, no hay que forzarle un filtro de
    sucursal (eso lo dejaría en una sola barra) aunque el segmento la mencione."""
    ctx = _ctx()
    graficos = [{"chart_type": "diverging_bar", "metric": "usd", "group_by": "sucursal", "filters": [], "title": "Comparación"}]
    segmento = [{"dimension": "sucursal", "valor": "CAPITAL"}, {"dimension": "familia", "valor": "CH304"}]

    resueltos = assistant._resolver_graficos(graficos, ctx, segmento)

    categorias = {c["categoria"] for c in resueltos[0]["datos"]["categorias"]}
    assert "MENDOZA" in categorias  # familia sí se filtró a CH304, pero sucursal quedó libre para comparar


def _hallazgo_falso(sucursal: str, tipo: str = "cambio_relevante") -> dict:
    return {
        "id": f"h-{sucursal}",
        "tipo": tipo,
        "segmento": {"sucursal": sucursal},
        "dimensiones": ["sucursal"],
        "que_ocurrio": f"En {sucursal} pasó algo.",
        "cuanto_explica": "Explica 40.0% de la variación total.",
        "metricas_respaldo": {"usd_actual": 100.0, "usd_anterior": 80.0},
        "evolucion_semanal": [10.0, 20.0, 30.0, 40.0],
        "semanas_grafico": ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"],
        "nivel_evidencia": "media",
        "limitaciones": [],
    }


def test_respuesta_determinista_con_scope_nunca_muestra_otro_segmento():
    """El fallback determinístico (Fase 2) tiene que filtrar los hallazgos
    globales por el scope activo -- nunca devolver el hallazgo #1 de OTRO
    segmento sólo porque es el de mayor score a nivel de todo el negocio
    (ese fue el bug más serio encontrado en la auditoría)."""
    hallazgos_globales = [_hallazgo_falso("ROSARIO"), _hallazgo_falso("CAPITAL")]

    resp = assistant._respuesta_determinista(
        "¿cuál asesor explica más esa variación?",
        hallazgos_globales,
        "nota de prueba",
        scope_activo={"sucursal": "CAPITAL"},
    )

    assert resp["segmento"] == [{"dimension": "sucursal", "valor": "CAPITAL"}]


def test_respuesta_determinista_con_scope_sintetiza_hallazgo_si_ninguno_global_matchea(
    df_reciente, df_comparativo, df_historico
):
    """Si ningún hallazgo PRIORIZADO (de todo el negocio) cae dentro del
    scope, se sintetiza uno nuevo a partir de los cruces YA FILTRADOS a ese
    scope -- nunca se muestra un hallazgo de otro segmento como si fuera la
    respuesta."""
    from ai import scope as ai_scope
    from core import combinations

    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    cruces_capital = ai_scope.filtrar_cruces_por_scope(cruces, {"sucursal": "CAPITAL"})

    hallazgos_globales = [_hallazgo_falso("ROSARIO")]  # ninguno menciona CAPITAL

    resp = assistant._respuesta_determinista(
        "¿qué pasó en CAPITAL?",
        hallazgos_globales,
        "nota de prueba",
        scope_activo={"sucursal": "CAPITAL"},
        cruces_scope=cruces_capital,
        semanas_grafico=[SEMANA_COMPARATIVA.isoformat(), SEMANA_RECIENTE.isoformat()],
    )

    assert all(s["dimension"] != "sucursal" or s["valor"] == "CAPITAL" for s in resp["segmento"])
    assert "ROSARIO" not in resp["que_ocurrio"]


def test_resolver_graficos_sin_segmento_no_inyecta_nada():
    """Pregunta sobre el TOTAL (segmento vacío): el gráfico se deja tal cual
    lo pidió la IA, sin forzar ningún filtro."""
    ctx = _ctx()
    graficos = [{"chart_type": "line", "metric": "usd", "group_by": "semana", "filters": [], "title": "Evolución total"}]

    resueltos = assistant._resolver_graficos(graficos, ctx, [])

    serie = resueltos[0]["datos"]["series"][0]["datos"]
    valores = {d["semana"]: d["valor"] for d in serie}
    assert valores["2026-06-01"] == 1050.0  # 100 + 900 + 50: total real, sin filtrar
