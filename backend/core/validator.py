"""Validación y normalización de tipos del CSV cargado.

Filosofía: nunca abortar toda la carga por filas puntuales rotas. Cada regla
de validación limpia (dropea) las filas que la violan y deja constancia en el
`ValidationReport`. Sólo se considera el dataset inválido (`es_valido=False`)
cuando, después de limpiar, no queda suficiente información para operar.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from config import (
    ABC_VALIDOS,
    COL_ABC_CLIENTE,
    COL_CLIENTE_ID,
    COL_FECHA_PEDIDO,
    COL_KG,
    COL_PEDIDO_ID,
    COL_POSICIONES,
    COL_SEMANA,
    COL_USD,
    COLUMNAS_TEXTO_OBLIGATORIAS,
    SEMANAS_MINIMO_ACEPTABLE,
)

FORMATOS_FECHA = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]


@dataclass
class ValidationReport:
    filas_originales: int = 0
    filas_validas: int = 0
    filas_descartadas: int = 0
    duplicados_eliminados: int = 0
    valores_faltantes: int = 0
    valores_invalidos: int = 0
    semanas_disponibles: int = 0
    semana_derivada_de_fecha: bool = False
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def es_valido(self) -> bool:
        return not self.errores and self.filas_validas > 0

    def to_dict(self) -> dict:
        return {
            "es_valido": self.es_valido,
            "filas_originales": self.filas_originales,
            "filas_validas": self.filas_validas,
            "filas_descartadas": self.filas_descartadas,
            "duplicados_eliminados": self.duplicados_eliminados,
            "valores_faltantes": self.valores_faltantes,
            "valores_invalidos": self.valores_invalidos,
            "semanas_disponibles": self.semanas_disponibles,
            "semana_derivada_de_fecha": self.semana_derivada_de_fecha,
            "errores": self.errores,
            "advertencias": self.advertencias,
        }


def _parse_fecha_col(df: pl.DataFrame, col: str) -> pl.Series:
    """Intenta parsear una columna de string a Date probando varios formatos."""
    resultado = pl.Series([None] * df.height, dtype=pl.Date)
    for fmt in FORMATOS_FECHA:
        candidato = df[col].str.strip_chars().str.to_date(fmt, strict=False)
        resultado = resultado.zip_with(resultado.is_not_null(), candidato)
    return resultado


def validar_y_limpiar(df_raw: pl.DataFrame) -> tuple[pl.DataFrame, ValidationReport]:
    report = ValidationReport(filas_originales=df_raw.height)
    df = df_raw.clone()

    # 1) Normalizar strings: trim en todas las columnas de texto obligatorias.
    for col in COLUMNAS_TEXTO_OBLIGATORIAS:
        df = df.with_columns(pl.col(col).cast(pl.Utf8).str.strip_chars().alias(col))

    # 2) Faltantes en columnas de texto obligatorias (vacío o null).
    mask_texto_ok = pl.lit(True)
    for col in COLUMNAS_TEXTO_OBLIGATORIAS:
        mask_texto_ok = mask_texto_ok & df[col].is_not_null() & (df[col] != "")
    faltantes_texto = df.height - df.filter(mask_texto_ok).height
    report.valores_faltantes += faltantes_texto
    df = df.filter(mask_texto_ok)

    # 3) Tipar numéricos: usd, kg, posiciones -> Float64. Lo que no castea, null.
    for col in [COL_USD, COL_KG, COL_POSICIONES]:
        df = df.with_columns(
            pl.col(col).str.strip_chars().str.replace_all(",", ".").cast(pl.Float64, strict=False).alias(col)
        )
    mask_numeric_ok = (
        df[COL_USD].is_not_null()
        & df[COL_KG].is_not_null()
        & df[COL_POSICIONES].is_not_null()
        & (df[COL_USD] >= 0)
        & (df[COL_KG] >= 0)
        & (df[COL_POSICIONES] > 0)
    )
    invalidos_numericos = df.height - df.filter(mask_numeric_ok).height
    report.valores_invalidos += invalidos_numericos
    df = df.filter(mask_numeric_ok)

    # 4) Fecha de pedido -> Date.
    df = df.with_columns(_parse_fecha_col(df, COL_FECHA_PEDIDO).alias(COL_FECHA_PEDIDO))
    fechas_invalidas = df.height - df.filter(pl.col(COL_FECHA_PEDIDO).is_not_null()).height
    report.valores_invalidos += fechas_invalidas
    df = df.filter(pl.col(COL_FECHA_PEDIDO).is_not_null())

    # 5) Semana -> Date. Si la columna no es interpretable como fecha en ningún
    #    caso, se deriva del lunes ISO de fecha_pedido (convención habitual de
    #    mart: `semana` = inicio de semana ISO).
    semana_parseada = _parse_fecha_col(df, COL_SEMANA)
    if semana_parseada.is_not_null().sum() == 0 and df.height > 0:
        report.semana_derivada_de_fecha = True
        report.advertencias.append(
            "La columna 'semana' no pudo interpretarse como fecha; se derivó "
            "automáticamente desde 'fecha_pedido' (lunes ISO de cada pedido)."
        )
        semana_derivada = pl.col(COL_FECHA_PEDIDO) - pl.duration(
            days=(pl.col(COL_FECHA_PEDIDO).dt.weekday() - 1)
        )
        df = df.with_columns(semana_derivada.alias(COL_SEMANA))
    else:
        df = df.with_columns(semana_parseada.alias(COL_SEMANA))
        semanas_invalidas = df.height - df.filter(pl.col(COL_SEMANA).is_not_null()).height
        report.valores_invalidos += semanas_invalidas
        df = df.filter(pl.col(COL_SEMANA).is_not_null())

    # 6) ABC de cliente: normalizar a mayúscula y validar contra el set permitido.
    df = df.with_columns(pl.col(COL_ABC_CLIENTE).str.to_uppercase().alias(COL_ABC_CLIENTE))
    mask_abc_ok = df[COL_ABC_CLIENTE].is_in(list(ABC_VALIDOS))
    abc_invalidos = df.height - df.filter(mask_abc_ok).height
    report.valores_invalidos += abc_invalidos
    df = df.filter(mask_abc_ok)

    # 7) Duplicados: fila 100% idéntica en todas las columnas.
    antes = df.height
    df = df.unique()
    report.duplicados_eliminados = antes - df.height

    report.filas_validas = df.height
    report.filas_descartadas = report.filas_originales - report.filas_validas

    # 8) Semanas disponibles.
    if df.height > 0:
        report.semanas_disponibles = df[COL_SEMANA].n_unique()

    # --- Errores bloqueantes ---
    if df.height == 0:
        report.errores.append(
            "No quedaron filas válidas después de limpiar el archivo. Revisá "
            "el formato de fechas, valores numéricos y columnas obligatorias."
        )
    elif report.semanas_disponibles < 2:
        report.errores.append(
            "El archivo tiene menos de 2 semanas de datos; no alcanza para "
            "calcular ninguna comparación de período."
        )

    # --- Advertencias no bloqueantes ---
    if 2 <= report.semanas_disponibles < SEMANAS_MINIMO_ACEPTABLE:
        report.advertencias.append(
            f"Sólo hay {report.semanas_disponibles} semanas disponibles (se "
            f"esperan {SEMANAS_MINIMO_ACEPTABLE} o más para período reciente + "
            "comparativo + contexto histórico). El análisis va a ser parcial."
        )
    if report.duplicados_eliminados > 0:
        report.advertencias.append(
            f"Se eliminaron {report.duplicados_eliminados} filas duplicadas."
        )
    if report.valores_faltantes > 0:
        report.advertencias.append(
            f"Se descartaron {report.valores_faltantes} filas con columnas "
            "obligatorias vacías."
        )
    if report.valores_invalidos > 0:
        report.advertencias.append(
            f"Se descartaron {report.valores_invalidos} filas con valores "
            "numéricos, fechas o ABC inválidos."
        )

    return df, report
