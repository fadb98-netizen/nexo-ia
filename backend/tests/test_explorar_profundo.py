from __future__ import annotations

from core.combinations import explorar_cruces_profundo


def _cruce(nivel: int, contribucion_pct: float, pedidos: int = 20) -> dict:
    return {
        "nivel": nivel,
        "dimensiones": ["sucursal"] * nivel,  # no importa el contenido real para estos tests
        "segmento": {},
        "pedidos_actual": pedidos,
        "pedidos_anterior": 0,
        "contribucion_pct": contribucion_pct,
        "impacto_relativo_pct": contribucion_pct,
    }


def test_filtra_por_nivel_min_y_max():
    cruces = [_cruce(1, 50), _cruce(2, 40), _cruce(3, 30), _cruce(4, 20), _cruce(5, 10)]
    seleccionados, total = explorar_cruces_profundo(cruces, nivel_min=2, nivel_max=4)
    niveles = {c["nivel"] for c in seleccionados}
    assert niveles == {2, 3, 4}
    assert total == 3


def test_ordena_por_contribucion_absoluta_descendente():
    cruces = [_cruce(2, -80), _cruce(2, 10), _cruce(3, 50)]
    seleccionados, _ = explorar_cruces_profundo(cruces, nivel_min=2, nivel_max=4)
    contribuciones = [c["contribucion_pct"] for c in seleccionados]
    assert contribuciones == [-80, 50, 10]  # por |valor|, no por valor con signo


def test_excluye_no_materiales():
    material = _cruce(2, 50, pedidos=20)
    poco_volumen = _cruce(2, 50, pedidos=1)  # por debajo de MIN_PEDIDOS_COMBINADOS
    seleccionados, total = explorar_cruces_profundo([material, poco_volumen], nivel_min=2, nivel_max=4)
    assert total == 1
    assert seleccionados == [material]


def test_trunca_a_top_n_y_reporta_el_total_real():
    cruces = [_cruce(2, 5 + i) for i in range(10)]  # 10 cruces de nivel 2, todos por encima del umbral de materialidad
    seleccionados, total = explorar_cruces_profundo(cruces, nivel_min=2, nivel_max=4, top_n=3)
    assert len(seleccionados) == 3
    assert total == 10  # el caller puede saber que se truncó (10 > 3) y avisarlo, nunca en silencio


def test_nivel_1_queda_afuera_por_default():
    """Nivel 1 ya lo cubre obtener_tabla_dimension -- "profundo" es sobre
    cruces combinados, no sobre el ranking de una sola dimensión."""
    cruces = [_cruce(1, 90)]
    seleccionados, total = explorar_cruces_profundo(cruces)
    assert seleccionados == []
    assert total == 0
