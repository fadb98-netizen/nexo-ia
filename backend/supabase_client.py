"""Integración con Supabase: guardar runs, hallazgos y conversaciones.

Todo acá es best-effort: si no hay SUPABASE_URL/SUPABASE_KEY configuradas, o
la llamada falla por cualquier motivo (red, esquema no creado todavía, etc.),
se loguea y la app sigue funcionando con el store en memoria. Nunca debe
tumbar un request.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("nexo_ia.supabase")

_client = None
_intentado = False


def _get_client():
    global _client, _intentado
    if _intentado:
        return _client
    _intentado = True
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.info("Supabase no configurado (SUPABASE_URL/SUPABASE_KEY ausentes); se sigue sólo con memoria.")
        return None
    try:
        from supabase import create_client

        _client = create_client(url, key)
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo inicializar el cliente de Supabase.")
        _client = None
    return _client


def disponible() -> bool:
    return _get_client() is not None


def guardar_run(run_id: str, nombre_archivo: str, validacion: dict, resumen: dict, hallazgos: list[dict]) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.table("runs").insert(
            {
                "run_id": run_id,
                "nombre_archivo": nombre_archivo,
                "validacion": validacion,
                "resumen": resumen,
                "hallazgos": hallazgos,
            }
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo guardar el run %s en Supabase.", run_id)


def guardar_conversacion(run_id: str, pregunta: str, respuesta: dict) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.table("conversaciones").insert(
            {"run_id": run_id, "pregunta": pregunta, "respuesta": respuesta}
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo guardar la conversación del run %s en Supabase.", run_id)


def listar_runs(limite: int = 20) -> list[dict]:
    client = _get_client()
    if client is None:
        return []
    try:
        res = client.table("runs").select("run_id,nombre_archivo,creado_en,resumen").order("creado_en", desc=True).limit(limite).execute()
        return res.data or []
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo listar runs desde Supabase.")
        return []


def subir_csv(run_id: str, contenido: bytes, nombre_archivo: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        ruta = f"{run_id}/{nombre_archivo}"
        client.storage.from_("csv-uploads").upload(ruta, contenido, {"content-type": "text/csv"})
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo subir el CSV del run %s a Supabase Storage.", run_id)
