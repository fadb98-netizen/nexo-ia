from __future__ import annotations

from core import charts
from tests.conftest import SEMANA_COMPARATIVA, SEMANA_RECIENTE


def test_validar_chart_request_tipo_invalido():
    ok, motivo = charts.validar_chart_request({"chart_type": "scatter3d", "metric": "usd"})
    assert not ok
    assert "chart_type" in motivo


def test_validar_chart_request_metric_invalida():
    ok, motivo = charts.validar_chart_request({"chart_type": "line", "metric": "profit"})
    assert not ok


def test_validar_chart_request_filtro_dimension_desconocida():
    ok, motivo = charts.validar_chart_request(
        {"chart_type": "pie", "metric": "usd", "group_by": "sucursal", "filters": {"pais": "AR"}}
    )
    assert not ok


def test_validar_chart_request_heatmap_necesita_2_dimensiones():
    ok, motivo = charts.validar_chart_request({"chart_type": "heatmap", "metric": "usd", "group_by": "sucursal"})
    assert not ok
    ok2, _ = charts.validar_chart_request({"chart_type": "heatmap", "metric": "usd", "group_by": "sucursal,familia"})
    assert ok2


def test_validar_chart_request_normaliza_mayusculas():
    ok, motivo = charts.validar_chart_request({"chart_type": "LINE", "metric": "USD", "group_by": "Semana"})
    assert ok, motivo


def test_calcular_datos_grafico_line_usa_filtros(df_reciente, df_comparativo):
    req = {"chart_type": "line", "metric": "usd", "group_by": "semana", "filters": {"sucursal": "CAPITAL"}, "comparison": "ninguna"}
    datos = charts.calcular_datos_grafico(req, df_reciente, df_comparativo, [SEMANA_COMPARATIVA, SEMANA_RECIENTE])
    serie = datos["series"][0]["datos"]
    assert len(serie) == 2
    valor_reciente = next(d["valor"] for d in serie if d["semana"] == SEMANA_RECIENTE.isoformat())
    assert valor_reciente == 1500.0  # CAPITAL en reciente: 1000 + 500


def test_calcular_datos_grafico_acepta_semanas_como_strings(df_reciente, df_comparativo):
    req = {"chart_type": "line", "metric": "usd", "group_by": "semana", "filters": {}, "comparison": "ninguna"}
    semanas_str = [SEMANA_COMPARATIVA.isoformat(), SEMANA_RECIENTE.isoformat()]
    datos = charts.calcular_datos_grafico(req, df_reciente, df_comparativo, semanas_str)
    assert len(datos["series"][0]["datos"]) == 2


def test_calcular_datos_grafico_diverging_bar(df_reciente, df_comparativo):
    req = {"chart_type": "diverging_bar", "metric": "usd", "group_by": "sucursal", "filters": {}, "comparison": "ninguna"}
    datos = charts.calcular_datos_grafico(req, df_reciente, df_comparativo, [SEMANA_COMPARATIVA, SEMANA_RECIENTE])
    por_categoria = {c["categoria"]: c["diferencia"] for c in datos["categorias"]}
    assert por_categoria["CAPITAL"] == 700.0
    assert por_categoria["ROSARIO"] == 200.0
