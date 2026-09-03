from __future__ import annotations

from core import combinations
from ai import tools
from tests.conftest import SEMANA_COMPARATIVA, SEMANA_RECIENTE


def _ctx(df_reciente, df_comparativo, df_historico) -> tools.ContextoHerramientas:
    cruces = combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )
    return tools.ContextoHerramientas(
        cruces=cruces,
        df_reciente=df_reciente,
        df_comparativo=df_comparativo,
        semanas_grafico=[SEMANA_COMPARATIVA.isoformat(), SEMANA_RECIENTE.isoformat()],
        semanas_historico=[],
    )


def test_obtener_tabla_dimension_sin_filtro_es_global(df_reciente, df_comparativo, df_historico):
    """Comportamiento previo, sin tocar: sin filtro, devuelve todos los
    asesores del negocio (A1 de CAPITAL y A2 de ROSARIO)."""
    ctx = _ctx(df_reciente, df_comparativo, df_historico)
    resultado = tools.obtener_tabla_dimension(ctx, "asesor")
    asesores = {f["segmento"]["asesor"] for f in resultado["filas"]}
    assert asesores == {"A1", "A2"}


def test_obtener_tabla_dimension_con_filtro_queda_scopeada(df_reciente, df_comparativo, df_historico):
    """Bug de la auditoría (Fase 1): pedir el ranking de una dimensión
    restringido a un scope ya establecido (p. ej. 'asesor' dentro de
    'sucursal'=CAPITAL) tiene que devolver sólo A1 -- nunca A2 (de ROSARIO),
    y sin necesidad de caer a la versión sin filtro."""
    ctx = _ctx(df_reciente, df_comparativo, df_historico)
    resultado = tools.obtener_tabla_dimension(ctx, "asesor", filtro=[{"dimension": "sucursal", "valor": "CAPITAL"}])
    asesores = {f["segmento"]["asesor"] for f in resultado["filas"]}
    assert asesores == {"A1"}
    assert all(f["segmento"]["sucursal"] == "CAPITAL" for f in resultado["filas"])


def test_desglosar_variacion_con_filtro_fuera_de_dimensiones_no_devuelve_vacio(df_reciente, df_comparativo, df_historico):
    """Antes de la Fase 1: pedir 'asesor' filtrado por 'sucursal' (una
    dimensión que no está en `dimensiones`) devolvía 0 filas siempre, porque
    un cruce de nivel 1 de 'asesor' no tiene la clave 'sucursal' en su
    segmento. Ahora tiene que ampliar la búsqueda a ambas dimensiones y
    devolver el resultado ya restringido, con una nota explicando por qué
    las filas tienen más dimensiones de las pedidas."""
    ctx = _ctx(df_reciente, df_comparativo, df_historico)
    resultado = tools.desglosar_variacion(
        ctx, dimensiones=["asesor"], filtro=[{"dimension": "sucursal", "valor": "CAPITAL"}]
    )
    assert resultado["filas"], "no debería devolver vacío"
    assert all(f["segmento"]["sucursal"] == "CAPITAL" for f in resultado["filas"])
    assert {f["segmento"]["asesor"] for f in resultado["filas"]} == {"A1"}
    assert "nota" in resultado  # avisa que el agrupamiento real incluye 'sucursal'


def test_desglosar_variacion_con_filtro_dentro_de_dimensiones_no_cambia(df_reciente, df_comparativo, df_historico):
    """Cuando el filtro ya está incluido en `dimensiones` (uso normal, sin el
    bug), el comportamiento es exactamente el de antes: sin nota extra."""
    ctx = _ctx(df_reciente, df_comparativo, df_historico)
    resultado = tools.desglosar_variacion(
        ctx, dimensiones=["sucursal", "asesor"], filtro=[{"dimension": "sucursal", "valor": "CAPITAL"}]
    )
    assert resultado["filas"]
    assert "nota" not in resultado


def test_obtener_resumen_total_bloqueado_con_scope_activo(df_reciente, df_comparativo, df_historico):
    """Fase 2: con un scope activo, obtener_resumen_total ya no devuelve el
    total SIN FILTRAR de todo el negocio (esa era una vía directa para que
    el modelo citara números nacionales dentro de una respuesta scopeada)."""
    ctx = _ctx(df_reciente, df_comparativo, df_historico)
    ctx.scope_activo = {"sucursal": "CAPITAL"}
    resultado = tools.obtener_resumen_total(ctx)
    assert "error" in resultado
