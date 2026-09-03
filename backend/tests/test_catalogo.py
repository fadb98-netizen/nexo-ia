from __future__ import annotations

from core import catalogo, combinations
from tests.conftest import SEMANA_COMPARATIVA, SEMANA_RECIENTE


def test_construir_catalogo_lista_los_valores_reales_por_dimension(df_reciente, df_comparativo, df_historico):
    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    cat = catalogo.construir_catalogo(cruces)

    valores_sucursal = {v["valor"] for v in cat["sucursal"]}
    assert valores_sucursal == {"CAPITAL", "ROSARIO"}
    # sólo nivel 1 (uno por categoría), nunca cruces combinados
    assert all(isinstance(v["volumen_pedidos"], int) for v in cat["sucursal"])


def test_construir_catalogo_ordena_por_volumen_descendente(df_reciente, df_comparativo, df_historico):
    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    cat = catalogo.construir_catalogo(cruces)
    volumenes = [v["volumen_pedidos"] for v in cat["sucursal"]]
    assert volumenes == sorted(volumenes, reverse=True)


def test_valor_existe():
    cat = {"sucursal": [{"valor": "CAPITAL", "volumen_pedidos": 10}]}
    assert catalogo.valor_existe(cat, "sucursal", "CAPITAL") is True
    assert catalogo.valor_existe(cat, "sucursal", "ROSARIO") is False
    assert catalogo.valor_existe(cat, "asesor", "CAPITAL") is False
