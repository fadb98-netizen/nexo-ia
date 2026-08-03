from __future__ import annotations

from datetime import date, timedelta

import polars as pl
import pytest

from config import COL_SEMANA
from core import periods


def _df_con_semanas(semanas: list[date]) -> pl.DataFrame:
    return pl.DataFrame({COL_SEMANA: semanas}, schema={COL_SEMANA: pl.Date})


def test_division_16_semanas_en_reciente_comparativo_historico():
    hoy = date(2024, 6, 1)
    lunes_base = hoy - timedelta(days=hoy.weekday())
    semanas = [lunes_base - timedelta(weeks=(16 - i)) for i in range(16)]  # 16 semanas ya cerradas
    df = _df_con_semanas(semanas)

    p = periods.calcular_periodos(df, hoy=hoy)

    assert len(p.reciente) == 4
    assert len(p.comparativo) == 4
    assert len(p.historico) == 8
    assert p.reciente == semanas[-4:]
    assert p.comparativo == semanas[-8:-4]
    assert p.historico == semanas[-16:-8]
    assert len(p.grafico) == 8
    assert p.semanas_totales_usadas == 16


def test_semana_incompleta_se_descarta():
    hoy = date(2024, 6, 5)  # miércoles
    lunes_actual = hoy - timedelta(days=hoy.weekday())  # semana en curso, incompleta
    semanas_cerradas = [lunes_actual - timedelta(weeks=w) for w in range(1, 10)]
    todas = semanas_cerradas + [lunes_actual]
    df = _df_con_semanas(todas)

    p = periods.calcular_periodos(df, hoy=hoy)

    assert lunes_actual not in p.reciente
    assert lunes_actual not in p.comparativo
    assert lunes_actual not in p.historico
    assert lunes_actual in p.semanas_incompletas_descartadas


def test_filtrar_por_semanas(df_reciente):
    from tests.conftest import SEMANA_RECIENTE

    filtrado = periods.filtrar_por_semanas(df_reciente, [SEMANA_RECIENTE])
    assert filtrado.height == df_reciente.height

    vacio = periods.filtrar_por_semanas(df_reciente, [])
    assert vacio.height == 0
