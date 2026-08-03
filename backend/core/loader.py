"""Carga del CSV subido a un DataFrame de Polars.

Sólo se encarga de leer bytes -> DataFrame con los tipos "crudos" (todo como
string salvo lo que Polars infiera solo). La normalización de tipos y la
validación de reglas de negocio viven en validator.py — este módulo no debe
lanzar excepciones de negocio, sólo errores de parseo de archivo.
"""
from __future__ import annotations

import io

import polars as pl

from config import ALLOWED_EXTENSIONS, COLUMNAS_OBLIGATORIAS, MAX_FILE_SIZE_MB


class ArchivoInvalidoError(Exception):
    """Error de estructura de archivo (no de contenido/negocio)."""


def validar_archivo_subido(nombre_archivo: str, contenido: bytes) -> None:
    ext = "." + nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ArchivoInvalidoError(
            f"Extensión '{ext}' no permitida. Se espera un archivo .csv."
        )

    tamano_mb = len(contenido) / (1024 * 1024)
    if tamano_mb > MAX_FILE_SIZE_MB:
        raise ArchivoInvalidoError(
            f"El archivo pesa {tamano_mb:.1f} MB, supera el límite de {MAX_FILE_SIZE_MB} MB."
        )

    if len(contenido) == 0:
        raise ArchivoInvalidoError("El archivo está vacío.")


def cargar_csv(contenido: bytes) -> pl.DataFrame:
    """Lee el CSV como strings crudos (sin inferencia de tipos).

    La conversión de tipos numéricos/fecha se hace en validator.py, donde
    además se registran las filas que no pudieron convertirse en vez de que
    Polars falle en silencio o aborte la carga completa.
    """
    try:
        df = pl.read_csv(
            io.BytesIO(contenido),
            infer_schema_length=0,  # todo como string; validator.py tipa a mano
            truncate_ragged_lines=True,
        )
    except Exception as exc:  # noqa: BLE001 - superficie única de error de parseo
        raise ArchivoInvalidoError(f"No se pudo leer el CSV: {exc}") from exc

    if df.height == 0:
        raise ArchivoInvalidoError("El CSV no contiene filas de datos.")

    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]
    if faltantes:
        raise ArchivoInvalidoError(
            "Faltan columnas obligatorias: " + ", ".join(faltantes)
        )

    return df
