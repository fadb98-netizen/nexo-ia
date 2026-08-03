from __future__ import annotations

import polars as pl

from core import validator


def _csv_valido_con(filas_extra: str = "") -> bytes:
    # Dos semanas distintas: lo mínimo para que el dataset sea "válido" a
    # nivel período (una sola semana no alcanza para ninguna comparación).
    header = "fecha_pedido,semana,pedido_id,cliente_id,sucursal,asesor,sector_industrial,familia,abc_cliente,usd,kg,posiciones\n"
    base = (
        "2024-03-04,2024-03-04,P1,C1,CAPITAL,A1,CONSTRUCCION,CH304,A,1000,500,2\n"
        "2024-02-26,2024-02-26,P0,C0,CAPITAL,A1,CONSTRUCCION,CH304,A,900,450,2\n"
    )
    return (header + base + filas_extra).encode("utf-8")


def _cargar(contenido: bytes) -> pl.DataFrame:
    from core import loader

    return loader.cargar_csv(contenido)


def test_fila_valida_pasa():
    df, reporte = validator.validar_y_limpiar(_cargar(_csv_valido_con()))
    assert reporte.es_valido
    assert reporte.filas_validas == 2
    assert reporte.valores_invalidos == 0


def test_usd_negativo_se_descarta():
    extra = "2024-03-04,2024-03-04,P2,C2,CAPITAL,A1,CONSTRUCCION,CH304,A,-100,500,2\n"
    df, reporte = validator.validar_y_limpiar(_cargar(_csv_valido_con(extra)))
    assert reporte.filas_validas == 2
    assert reporte.valores_invalidos == 1


def test_abc_con_esquema_rico_no_se_descarta():
    """Regresión: la clasificación ABC real de Famiq usa códigos como A0-A3,
    AN, P0-P3, PN, N, R, X — no sólo A/B/C. Un validador que sólo aceptara
    A/B/C descartaba en producción el 79% de las filas de un CSV real."""
    extra = (
        "2024-03-04,2024-03-04,P2,C2,CAPITAL,ASESOR1,CONSTRUCCION,CH304,A2,100,500,2\n"
        "2024-03-04,2024-03-04,P3,C3,CAPITAL,ASESOR1,CONSTRUCCION,CH304,PN,100,500,2\n"
    )
    df, reporte = validator.validar_y_limpiar(_cargar(_csv_valido_con(extra)))
    assert reporte.filas_validas == 4
    assert reporte.valores_invalidos == 0
    assert set(df["abc_cliente"].to_list()) >= {"A", "A2", "PN"}


def test_abc_se_normaliza_a_mayuscula():
    extra = "2024-03-04,2024-03-04,P2,C2,CAPITAL,ASESOR1,CONSTRUCCION,CH304,a2,100,500,2\n"
    df, reporte = validator.validar_y_limpiar(_cargar(_csv_valido_con(extra)))
    fila = df.filter(df["pedido_id"] == "P2")
    assert fila["abc_cliente"].to_list() == ["A2"]


def test_fila_con_columna_obligatoria_vacia_se_descarta():
    extra = "2024-03-04,2024-03-04,,C2,CAPITAL,A1,CONSTRUCCION,CH304,A,100,500,2\n"
    df, reporte = validator.validar_y_limpiar(_cargar(_csv_valido_con(extra)))
    assert reporte.filas_validas == 2
    assert reporte.valores_faltantes == 1


def test_fila_duplicada_exacta_se_elimina():
    extra = "2024-03-04,2024-03-04,P1,C1,CAPITAL,A1,CONSTRUCCION,CH304,A,1000,500,2\n"
    df, reporte = validator.validar_y_limpiar(_cargar(_csv_valido_con(extra)))
    assert reporte.filas_validas == 2
    assert reporte.duplicados_eliminados == 1


def test_menos_de_2_semanas_es_invalido():
    df, reporte = validator.validar_y_limpiar(_cargar(_csv_valido_con()))
    assert not reporte.es_valido or reporte.semanas_disponibles < 9
    # con una sola semana el dataset es técnicamente "válido" para limpiar,
    # pero no alcanza para ningún período: se marca inválido específicamente
    # cuando hay menos de 2 semanas distintas.
    header = "fecha_pedido,semana,pedido_id,cliente_id,sucursal,asesor,sector_industrial,familia,abc_cliente,usd,kg,posiciones\n"
    una_fila = header + "2024-03-04,2024-03-04,P1,C1,CAPITAL,A1,CONSTRUCCION,CH304,A,1000,500,2\n"
    from core import loader

    _, reporte_una_semana = validator.validar_y_limpiar(loader.cargar_csv(una_fila.encode("utf-8")))
    assert not reporte_una_semana.es_valido
    assert reporte_una_semana.semanas_disponibles == 1


def test_pocas_semanas_genera_advertencia_no_bloqueante():
    header = "fecha_pedido,semana,pedido_id,cliente_id,sucursal,asesor,sector_industrial,familia,abc_cliente,usd,kg,posiciones\n"
    filas = header
    for i, semana in enumerate(["2024-03-04", "2024-03-11", "2024-03-18"]):
        filas += f"{semana},{semana},P{i},C{i},CAPITAL,A1,CONSTRUCCION,CH304,A,1000,500,2\n"
    from core import loader

    df, reporte = validator.validar_y_limpiar(loader.cargar_csv(filas.encode("utf-8")))
    assert reporte.es_valido
    assert reporte.semanas_disponibles == 3
    assert any("Sólo hay" in a for a in reporte.advertencias)
