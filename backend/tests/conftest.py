from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

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

SEMANA_RECIENTE = date(2024, 3, 4)
SEMANA_COMPARATIVA = date(2024, 2, 26)


def _fila(pedido, cliente, sucursal, familia, sector, asesor, abc, usd, kg, posiciones, semana):
    return {
        COL_FECHA_PEDIDO: semana,
        COL_SEMANA: semana,
        COL_PEDIDO_ID: pedido,
        COL_CLIENTE_ID: cliente,
        COL_SUCURSAL: sucursal,
        COL_ASESOR: asesor,
        COL_SECTOR_INDUSTRIAL: sector,
        COL_FAMILIA: familia,
        COL_ABC_CLIENTE: abc,
        COL_USD: float(usd),
        COL_KG: float(kg),
        COL_POSICIONES: float(posiciones),
    }


@pytest.fixture
def df_reciente() -> pl.DataFrame:
    filas = [
        _fila("P1", "C1", "CAPITAL", "CH304", "CONSTRUCCION", "A1", "A", 1000, 500, 2, SEMANA_RECIENTE),
        _fila("P1", "C1", "CAPITAL", "PERFILES", "CONSTRUCCION", "A1", "A", 500, 200, 1, SEMANA_RECIENTE),
        _fila("P2", "C2", "ROSARIO", "CH304", "AGRO", "A2", "B", 2000, 800, 4, SEMANA_RECIENTE),
    ]
    return pl.DataFrame(filas, schema_overrides={COL_FECHA_PEDIDO: pl.Date, COL_SEMANA: pl.Date})


@pytest.fixture
def df_comparativo() -> pl.DataFrame:
    filas = [
        _fila("P3", "C1", "CAPITAL", "CH304", "CONSTRUCCION", "A1", "A", 800, 400, 2, SEMANA_COMPARATIVA),
        _fila("P4", "C3", "ROSARIO", "CH304", "AGRO", "A2", "B", 1800, 700, 3, SEMANA_COMPARATIVA),
    ]
    return pl.DataFrame(filas, schema_overrides={COL_FECHA_PEDIDO: pl.Date, COL_SEMANA: pl.Date})


@pytest.fixture
def df_historico() -> pl.DataFrame:
    return pl.DataFrame(
        [],
        schema={
            COL_FECHA_PEDIDO: pl.Date,
            COL_SEMANA: pl.Date,
            COL_PEDIDO_ID: pl.Utf8,
            COL_CLIENTE_ID: pl.Utf8,
            COL_SUCURSAL: pl.Utf8,
            COL_ASESOR: pl.Utf8,
            COL_SECTOR_INDUSTRIAL: pl.Utf8,
            COL_FAMILIA: pl.Utf8,
            COL_ABC_CLIENTE: pl.Utf8,
            COL_USD: pl.Float64,
            COL_KG: pl.Float64,
            COL_POSICIONES: pl.Float64,
        },
    )
