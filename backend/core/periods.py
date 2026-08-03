"""División del histórico en período reciente / comparativo / contexto.

Regla central: nunca comparar semanas completas contra una semana incompleta.
Se asume que la columna `semana` (ya normalizada a Date en validator.py)
representa el lunes de inicio de cada semana ISO. Una semana se considera
completa cuando su domingo (lunes + 6 días) ya pasó respecto de la fecha de
corte (`hoy`, por defecto la fecha actual del sistema).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import polars as pl

from config import (
    COL_SEMANA,
    SEMANAS_COMPARATIVO,
    SEMANAS_HISTORICO,
    SEMANAS_RECIENTE,
    SEMANAS_TOTAL_ESPERADAS,
)


@dataclass
class Periodos:
    reciente: list[date] = field(default_factory=list)
    comparativo: list[date] = field(default_factory=list)
    historico: list[date] = field(default_factory=list)
    semanas_incompletas_descartadas: list[date] = field(default_factory=list)

    @property
    def grafico(self) -> list[date]:
        """Últimas hasta-8 semanas (comparativo + reciente), para mostrar en pantalla."""
        return sorted(self.comparativo + self.reciente)

    @property
    def tendencia(self) -> list[date]:
        """Hasta 16 semanas, para detectar tendencia/persistencia/anomalías."""
        return sorted(self.historico + self.comparativo + self.reciente)

    @property
    def semanas_totales_usadas(self) -> int:
        return len(self.tendencia)

    def to_dict(self) -> dict:
        return {
            "reciente": [d.isoformat() for d in self.reciente],
            "comparativo": [d.isoformat() for d in self.comparativo],
            "historico": [d.isoformat() for d in self.historico],
            "grafico": [d.isoformat() for d in self.grafico],
            "semanas_incompletas_descartadas": [
                d.isoformat() for d in self.semanas_incompletas_descartadas
            ],
            "semanas_totales_usadas": self.semanas_totales_usadas,
        }


def calcular_periodos(df: pl.DataFrame, hoy: date | None = None) -> Periodos:
    hoy = hoy or date.today()

    semanas: list[date] = sorted(df[COL_SEMANA].unique().to_list())

    completas: list[date] = []
    incompletas: list[date] = []
    for inicio in semanas:
        fin_semana = inicio + timedelta(days=6)
        if fin_semana < hoy:
            completas.append(inicio)
        else:
            incompletas.append(inicio)

    # Nos quedamos como máximo con las 16 semanas completas más recientes.
    usadas = completas[-SEMANAS_TOTAL_ESPERADAS:]

    reciente = usadas[-SEMANAS_RECIENTE:]
    resto = usadas[: -SEMANAS_RECIENTE] if len(usadas) > SEMANAS_RECIENTE else []
    comparativo = resto[-SEMANAS_COMPARATIVO:]
    resto2 = resto[: -SEMANAS_COMPARATIVO] if len(resto) > SEMANAS_COMPARATIVO else []
    historico = resto2[-SEMANAS_HISTORICO:]

    return Periodos(
        reciente=reciente,
        comparativo=comparativo,
        historico=historico,
        semanas_incompletas_descartadas=incompletas,
    )


def filtrar_por_semanas(df: pl.DataFrame, semanas: list[date]) -> pl.DataFrame:
    if not semanas:
        return df.clear()
    return df.filter(pl.col(COL_SEMANA).is_in(semanas))
