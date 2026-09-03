"""Dataset sintético de alta cardinalidad para el motor de cruces y el
scope-lock -- el gap que señaló la auditoría (sección 03): todos los tests
existentes corren sobre datasets chicos (2-3 sucursales, un puñado de
categorías por dimensión), muy distintos de la escala real de producción
(9 oficinas, 37 asesores, 134 familias, 28 sectores). Con pocas categorías
hay pocas formas de "elegir mal"; achicar esa brecha ayuda a que el motor
de cruces y el scope-lock se sigan probando en un escenario donde SÍ hay
margen para confundir un valor con otro parecido.

No sube ningún CSV real: genera un DataFrame sintético (semilla fija, así el
test es reproducible) con una cardinalidad comparable a producción.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import polars as pl
import pytest

from ai import scope as ai_scope
from config import (
    COL_ABC_CLIENTE,
    COL_ASESOR,
    COL_CLIENTE_ID,
    COL_FAMILIA,
    COL_FECHA_PEDIDO,
    COL_KG,
    COL_PEDIDO_ID,
    COL_POSICIONES,
    COL_SECTOR_INDUSTRIAL,
    COL_SEMANA,
    COL_SUCURSAL,
    COL_USD,
)
from core import catalogo, combinations

N_SUCURSALES = 9
N_ASESORES = 37
N_FAMILIAS = 60  # 134 en producción real; se achica acá sólo para que el test corra rápido
N_SECTORES = 28
N_ABC = 12
N_FILAS = 6000


def _generar_dataset(seed: int = 42) -> tuple[pl.DataFrame, pl.DataFrame, list[date]]:
    rnd = random.Random(seed)
    sucursales = [f"OF VT {i:02d}" for i in range(1, N_SUCURSALES + 1)]
    asesores = [f"ASESOR {i:03d}" for i in range(1, N_ASESORES + 1)]
    familias = [f"FAMILIA {i:03d}" for i in range(1, N_FAMILIAS + 1)]
    sectores = [f"SECTOR {i:02d}" for i in range(1, N_SECTORES + 1)]
    abc = [f"ABC{i}" for i in range(1, N_ABC + 1)]

    lunes_inicial = date(2026, 1, 5)
    semanas = [lunes_inicial + timedelta(weeks=w) for w in range(8)]  # 4 comparativo + 4 reciente

    filas = []
    for i in range(N_FILAS):
        semana = rnd.choice(semanas)
        filas.append(
            {
                COL_FECHA_PEDIDO: semana,
                COL_SEMANA: semana,
                COL_PEDIDO_ID: f"P{i // 3}",  # ~3 líneas (familias) por pedido en promedio
                COL_CLIENTE_ID: f"C{i % 500}",
                COL_SUCURSAL: rnd.choice(sucursales),
                COL_ASESOR: rnd.choice(asesores),
                COL_SECTOR_INDUSTRIAL: rnd.choice(sectores),
                COL_FAMILIA: rnd.choice(familias),
                COL_ABC_CLIENTE: rnd.choice(abc),
                COL_USD: round(rnd.uniform(50, 5000), 2),
                COL_KG: round(rnd.uniform(1, 500), 2),
                COL_POSICIONES: float(rnd.randint(1, 5)),
            }
        )
    df = pl.DataFrame(filas, schema_overrides={COL_FECHA_PEDIDO: pl.Date, COL_SEMANA: pl.Date})
    df_reciente = df.filter(pl.col(COL_SEMANA).is_in(semanas[4:]))
    df_comparativo = df.filter(pl.col(COL_SEMANA).is_in(semanas[:4]))
    return df_reciente, df_comparativo, semanas


@pytest.fixture(scope="module")
def dataset_alta_cardinalidad():
    """Cruces calculados UNA sola vez para todo el archivo -- es la parte
    cara (miles de combinaciones posibles); recalcularla en cada test
    multiplicaría el tiempo de la suite sin agregar cobertura real."""
    df_reciente, df_comparativo, semanas = _generar_dataset()
    df_historico = df_reciente.clear()
    cruces = combinations.calcular_todas_las_combinaciones(df_reciente, df_comparativo, df_historico, semanas, [])
    return {
        "df_reciente": df_reciente,
        "df_comparativo": df_comparativo,
        "semanas": semanas,
        "cruces": cruces,
    }


def test_totales_de_nivel1_coinciden_con_el_total_real_a_escala(dataset_alta_cardinalidad):
    """La suma de usd_actual de todos los valores de nivel 1 de una dimensión
    tiene que dar exactamente el total real -- ninguna fila se pierde ni se
    duplica aunque haya miles de combinaciones posibles."""
    cruces = dataset_alta_cardinalidad["cruces"]
    df_reciente = dataset_alta_cardinalidad["df_reciente"]

    nivel1_sucursal = [c for c in cruces if c["nivel"] == 1 and c["dimensiones"] == ["sucursal"]]
    assert len(nivel1_sucursal) == N_SUCURSALES
    assert round(sum(c["usd_actual"] for c in nivel1_sucursal), 2) == round(df_reciente[COL_USD].sum(), 2)

    nivel1_asesor = [c for c in cruces if c["nivel"] == 1 and c["dimensiones"] == ["asesor"]]
    assert round(sum(c["usd_actual"] for c in nivel1_asesor), 2) == round(df_reciente[COL_USD].sum(), 2)


def test_catalogo_lista_todas_las_categorias_reales_a_escala(dataset_alta_cardinalidad):
    cat = catalogo.construir_catalogo(dataset_alta_cardinalidad["cruces"])

    # con 6000 filas repartidas al azar entre 37 asesores, es prácticamente
    # seguro que los 37 aparezcan al menos una vez en reciente o comparativo
    assert len(cat["asesor"]) == N_ASESORES
    assert len(cat["sucursal"]) == N_SUCURSALES
    assert len(cat["abc_cliente"]) == N_ABC


def test_scope_lock_no_mezcla_oficinas_a_escala(dataset_alta_cardinalidad):
    """El corazón de la Fase 2, ahora con 9 oficinas y 37 asesores reales de
    por medio en vez de 2 y 2: fijar el scope a una oficina puntual no puede
    dejar pasar ni un asesor de otra oficina."""
    cruces = dataset_alta_cardinalidad["cruces"]

    scope_activo = {"sucursal": "OF VT 03"}
    filtrados = ai_scope.filtrar_cruces_por_scope(cruces, scope_activo)

    assert filtrados  # tiene que quedar algo (con 6000 filas y 9 oficinas, hay volumen de sobra)
    assert all(c["segmento"].get("sucursal") == "OF VT 03" for c in filtrados)
    # ningún cruce de nivel 1 de otra dimensión "sola" (sin la oficina) puede colarse
    assert not any(c["dimensiones"] == ["asesor"] for c in filtrados)
    assert not any(c["dimensiones"] == ["familia"] for c in filtrados)


def test_desglosar_variacion_con_filtro_fuera_de_dimensiones_a_escala(dataset_alta_cardinalidad):
    """El fix de la Fase 1 (desglosar_variacion ampliando la búsqueda cuando
    el filtro trae una dimensión fuera de la lista pedida) tiene que seguir
    funcionando con decenas de asesores y oficinas, no sólo con 2 de cada."""
    from ai import tools

    ctx = tools.ContextoHerramientas(
        cruces=dataset_alta_cardinalidad["cruces"],
        df_reciente=dataset_alta_cardinalidad["df_reciente"],
        df_comparativo=dataset_alta_cardinalidad["df_comparativo"],
        semanas_grafico=[s.isoformat() for s in dataset_alta_cardinalidad["semanas"]],
        semanas_historico=[],
    )

    resultado = tools.desglosar_variacion(
        ctx, dimensiones=["asesor"], filtro=[{"dimension": "sucursal", "valor": "OF VT 05"}]
    )

    assert resultado["filas"]
    assert all(f["segmento"]["sucursal"] == "OF VT 05" for f in resultado["filas"])
    assert "nota" in resultado
