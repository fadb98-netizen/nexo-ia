from __future__ import annotations

from core import metrics


def test_pedidos_se_cuentan_con_nunique_no_por_filas(df_reciente):
    m = metrics.calcular_metricas_periodo(df_reciente)
    # df_reciente tiene 3 FILAS pero sólo 2 pedidos únicos (P1 aparece 2 veces
    # por tener 2 líneas de familia distinta).
    assert df_reciente.height == 3
    assert m["pedidos"] == 2


def test_posiciones_se_suman_no_se_cuentan_filas(df_reciente):
    m = metrics.calcular_metricas_periodo(df_reciente)
    # 2 + 1 + 4 = 7 posiciones, no 3 (la cantidad de filas).
    assert m["posiciones"] == 7


def test_usd_y_kg_totales(df_reciente):
    m = metrics.calcular_metricas_periodo(df_reciente)
    assert m["usd"] == 3500.0
    assert m["kg"] == 1500.0


def test_ticket_y_posiciones_por_pedido(df_reciente):
    m = metrics.calcular_metricas_periodo(df_reciente)
    assert m["ticket_promedio"] == 3500.0 / 2
    assert m["posiciones_por_pedido"] == 7 / 2


def test_metricas_df_vacio_no_explota():
    import polars as pl

    vacio = pl.DataFrame(
        schema={"usd": pl.Float64, "kg": pl.Float64, "posiciones": pl.Float64, "pedido_id": pl.Utf8, "cliente_id": pl.Utf8, "semana": pl.Date}
    )
    m = metrics.calcular_metricas_periodo(vacio)
    assert m["usd"] == 0.0
    assert m["pedidos"] == 0


def test_comparar_variacion_pct():
    actual = {"usd": 150.0}
    anterior = {"usd": 100.0}
    r = metrics.comparar(actual, anterior, "usd")
    assert r["diferencia_absoluta"] == 50.0
    assert r["variacion_pct"] == 50.0


def test_contribucion_variacion_suma_parcial():
    # dos segmentos que explican, entre los dos, toda la variación total
    c1 = metrics.contribucion_variacion(700.0, 900.0)
    c2 = metrics.contribucion_variacion(200.0, 900.0)
    assert round(c1 + c2, 6) == 100.0


def test_contribucion_variacion_total_cero_no_divide_por_cero():
    assert metrics.contribucion_variacion(500.0, 0.0) == 0.0


def test_persistencia_serie_monotona_es_1():
    assert metrics.persistencia([100, 90, 80, 70]) == 1.0


def test_persistencia_serie_erratica_es_menor_a_1():
    assert metrics.persistencia([100, 130, 80, 200]) < 1.0


def test_volatilidad_serie_constante_es_0():
    assert metrics.volatilidad([100, 100, 100]) == 0.0


def test_anomalia_detecta_desvio_fuerte():
    historico = [100, 105, 95, 102, 98, 101, 99, 103]
    reciente = [400, 420, 410, 405]
    r = metrics.anomalia_vs_historico(historico, reciente)
    assert r["es_anomalia"] is True


def test_anomalia_no_marca_variacion_normal():
    historico = [100, 105, 95, 102, 98, 101, 99, 103]
    reciente = [101, 99, 100, 102]
    r = metrics.anomalia_vs_historico(historico, reciente)
    assert r["es_anomalia"] is False


def test_decomponer_driver_pedidos_domina():
    r = metrics.decomponer_driver(
        pedidos_actual=20, pedidos_anterior=10,
        posiciones_por_pedido_actual=2.0, posiciones_por_pedido_anterior=2.0,
        usd_por_posicion_actual=100.0, usd_por_posicion_anterior=100.0,
    )
    assert r["driver_principal"] == "pedidos"


def test_decomponer_driver_suma_da_diferencia_total():
    pedidos_actual, pedidos_anterior = 12, 10
    pp_actual, pp_anterior = 3.0, 2.5
    upp_actual, upp_anterior = 50.0, 45.0
    r = metrics.decomponer_driver(pedidos_actual, pedidos_anterior, pp_actual, pp_anterior, upp_actual, upp_anterior)
    suma = r["contribucion_pedidos"] + r["contribucion_posiciones_por_pedido"] + r["contribucion_usd_por_posicion"]
    usd_actual = pedidos_actual * pp_actual * upp_actual
    usd_anterior = pedidos_anterior * pp_anterior * upp_anterior
    assert round(suma, 6) == round(usd_actual - usd_anterior, 6)
