"""Estado en memoria de cada corrida (run) del análisis.

Guarda, por `run_id`, todo lo que hace falta para responder preguntas del
copiloto sin volver a subir el CSV: los DataFrames ya filtrados por período,
los 31 cruces, los hallazgos y las anotaciones. Es un cache de proceso único
(no distribuido) — documentado como limitación conocida del MVP en el README.
Supabase (ver `supabase_client.py`) guarda una copia best-effort de los
resultados agregados para poder listar corridas anteriores incluso si este
proceso se reinicia, pero el chat interactivo después de un reinicio requiere
volver a subir el archivo.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

import polars as pl


@dataclass
class Run:
    run_id: str
    nombre_archivo: str
    creado_en: float
    df_reciente: pl.DataFrame
    df_comparativo: pl.DataFrame
    df_historico: pl.DataFrame
    semanas_grafico: list[str]
    semanas_historico: list[str]
    cruces: list[dict]
    cruces_materiales: list[dict]
    hallazgos: list[dict]
    resumen_periodo: dict
    validacion: dict
    periodos: dict
    catalogo: dict = field(default_factory=dict)  # valores reales por dimensión, para detectar ambigüedad (ai/scope.py)
    anotaciones: list[str] = field(default_factory=list)


_RUNS: dict[str, Run] = {}
_MAX_RUNS_EN_MEMORIA = 20


def nuevo_run_id() -> str:
    return uuid.uuid4().hex[:12]


def guardar(run: Run) -> None:
    _RUNS[run.run_id] = run
    if len(_RUNS) > _MAX_RUNS_EN_MEMORIA:
        mas_viejo = min(_RUNS.values(), key=lambda r: r.creado_en)
        _RUNS.pop(mas_viejo.run_id, None)


def obtener(run_id: str) -> Run | None:
    return _RUNS.get(run_id)


def agregar_anotacion(run_id: str, texto: str) -> bool:
    run = _RUNS.get(run_id)
    if run is None:
        return False
    run.anotaciones.append(texto)
    return True


def listar_ids() -> list[str]:
    return sorted(_RUNS.keys(), key=lambda rid: _RUNS[rid].creado_en, reverse=True)
