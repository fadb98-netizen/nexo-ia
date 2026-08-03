from __future__ import annotations

from datetime import date

import polars as pl

from ai import assistant, tools
from config import COL_FAMILIA, COL_SEMANA, COL_SUCURSAL, COL_USD, COL_KG, COL_PEDIDO_ID, COL_POSICIONES, COL_CLIENTE_ID


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


def test_resolver_graficos_sin_segmento_no_inyecta_nada():
    """Pregunta sobre el TOTAL (segmento vacío): el gráfico se deja tal cual
    lo pidió la IA, sin forzar ningún filtro."""
    ctx = _ctx()
    graficos = [{"chart_type": "line", "metric": "usd", "group_by": "semana", "filters": [], "title": "Evolución total"}]

    resueltos = assistant._resolver_graficos(graficos, ctx, [])

    serie = resueltos[0]["datos"]["series"][0]["datos"]
    valores = {d["semana"]: d["valor"] for d in serie}
    assert valores["2026-06-01"] == 1050.0  # 100 + 900 + 50: total real, sin filtrar
