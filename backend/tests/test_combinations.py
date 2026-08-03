from __future__ import annotations

from core import combinations
from tests.conftest import SEMANA_COMPARATIVA, SEMANA_RECIENTE


def test_genera_las_31_combinaciones():
    combos = combinations.generar_combinaciones_de_dimensiones()
    assert len(combos) == 31
    por_nivel = {}
    for c in combos:
        por_nivel[len(c)] = por_nivel.get(len(c), 0) + 1
    assert por_nivel == {1: 5, 2: 10, 3: 10, 4: 5, 5: 1}
    assert len(set(combos)) == 31  # ninguna combinación repetida


def test_nivel1_sucursal_capital_valores_correctos(df_reciente, df_comparativo, df_historico):
    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    capital = next(c for c in cruces if c["nivel"] == 1 and c["segmento"].get("sucursal") == "CAPITAL")

    # CAPITAL en reciente: P1 (dos líneas, usd 1000+500=1500), 1 pedido único.
    assert capital["usd_actual"] == 1500.0
    assert capital["pedidos_actual"] == 1
    # CAPITAL en comparativo: P3, usd 800, 1 pedido.
    assert capital["usd_anterior"] == 800.0
    assert capital["pedidos_anterior"] == 1
    assert capital["diferencia_absoluta"] == 700.0


def test_contribucion_de_los_dos_niveles1_de_sucursal_suma_100(df_reciente, df_comparativo, df_historico):
    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    sucursales = [c for c in cruces if c["nivel"] == 1 and c["dimensiones"] == ["sucursal"]]
    assert len(sucursales) == 2  # CAPITAL y ROSARIO son las únicas presentes
    total_contribucion = sum(c["contribucion_pct"] for c in sucursales)
    assert round(total_contribucion, 4) == 100.0


def test_nunique_pedido_no_se_infla_al_cruzar_con_familia(df_reciente, df_comparativo, df_historico):
    """P1 tiene 2 líneas (CH304 y PERFILES). Cruzado por sucursal+familia da
    2 filas de resultado (una por familia), pero cada una debe seguir
    contando 1 pedido, no 2 — nunca sumar pedidos de sub-grupos para inferir
    el total de un grupo más amplio."""
    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    detalle = [
        c for c in cruces
        if c["nivel"] == 2 and set(c["dimensiones"]) == {"sucursal", "familia"} and c["segmento"].get("sucursal") == "CAPITAL"
    ]
    assert len(detalle) == 2
    for c in detalle:
        assert c["pedidos_actual"] == 1  # P1 en cada una de sus 2 familias


def test_filtrar_material_excluye_bajo_volumen(df_reciente, df_comparativo, df_historico):
    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    # con sólo 1-2 pedidos por segmento en esta fixture, ningún cruce nivel 5
    # (el más específico, que reparte aún más el volumen) debería sobrevivir
    # al filtro de materialidad si MIN_PEDIDOS_COMBINADOS > 2.
    from config import MIN_PEDIDOS_COMBINADOS

    materiales = combinations.filtrar_material(cruces)
    if MIN_PEDIDOS_COMBINADOS > 2:
        assert all(c["nivel"] < 5 or (c["pedidos_actual"] + c["pedidos_anterior"]) >= MIN_PEDIDOS_COMBINADOS for c in materiales)
    for c in materiales:
        assert (c["pedidos_actual"] + c["pedidos_anterior"]) >= MIN_PEDIDOS_COMBINADOS


def test_cache_devuelve_mismo_objeto(df_reciente, df_comparativo, df_historico):
    combinations.limpiar_cache("run-test")
    r1 = combinations.calcular_todas_las_combinaciones_cacheado(
        "run-test", df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    r2 = combinations.calcular_todas_las_combinaciones_cacheado(
        "run-test", df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    assert r1 is r2
    combinations.limpiar_cache("run-test")
