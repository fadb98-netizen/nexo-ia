from __future__ import annotations

import pytest

from core import loader


def test_archivo_vacio_es_invalido():
    with pytest.raises(loader.ArchivoInvalidoError):
        loader.validar_archivo_subido("vacio.csv", b"")


def test_extension_invalida():
    with pytest.raises(loader.ArchivoInvalidoError):
        loader.validar_archivo_subido("datos.txt", b"a,b,c\n1,2,3")


def test_archivo_demasiado_grande():
    contenido = b"x" * (30 * 1024 * 1024)
    with pytest.raises(loader.ArchivoInvalidoError):
        loader.validar_archivo_subido("grande.csv", contenido)


def test_csv_sin_columnas_obligatorias_falla_al_cargar():
    contenido = b"col_a,col_b\n1,2\n"
    with pytest.raises(loader.ArchivoInvalidoError):
        loader.cargar_csv(contenido)


def test_csv_valido_carga_ok():
    header = "fecha_pedido,semana,pedido_id,cliente_id,sucursal,asesor,sector_industrial,familia,abc_cliente,usd,kg,posiciones\n"
    fila = "2024-03-04,2024-03-04,P1,C1,CAPITAL,A1,CONSTRUCCION,CH304,A,1000,500,2\n"
    df = loader.cargar_csv((header + fila).encode("utf-8"))
    assert df.height == 1
    assert "usd" in df.columns
