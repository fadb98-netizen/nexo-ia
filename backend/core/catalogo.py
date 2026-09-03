"""Catálogo semántico del dataset: qué valores reales existen para cada
dimensión y con cuánto volumen, para que la capa de interpretación (ver
`ai/scope.py`) pueda detectar cuándo una pregunta es ambigua ANTES de
investigar, en vez de que el modelo elija arbitrariamente una lectura.

No es un archivo estático: se genera una vez por corrida, a partir de los
mismos cruces de nivel 1 que ya calculó `combinations.py` — los valores
reales de asesor, familia, sector o clase ABC cambian con cada dataset que
suba cada usuario.
"""
from __future__ import annotations

from config import DIMENSIONES

# Términos de negocio para los que el dataset NO tiene ningún dato real —
# la IA no puede sustituirlos en silencio por una métrica parecida (ver
# ai/prompts.py, regla 16). Lista abierta a propósito: cualquier término que
# no sea exactamente usd/kg/posiciones/pedidos/clientes/ticket (ni un campo
# derivado de esos) cae acá conceptualmente, esto es sólo para los casos más
# comunes que se preguntan en la práctica.
METRICAS_INEXISTENTES = ["margen", "margen bruto", "rentabilidad", "costo", "costos", "precio", "utilidad", "ganancia"]


def construir_catalogo(cruces: list[dict]) -> dict[str, list[dict]]:
    """`{dimension: [{"valor": str, "volumen_pedidos": int}, ...]}`, uno por
    cada valor real que aparece en los cruces de nivel 1, ordenado por
    volumen descendente."""
    catalogo: dict[str, list[dict]] = {dim: [] for dim in DIMENSIONES}
    for c in cruces:
        if c["nivel"] != 1:
            continue
        dim = c["dimensiones"][0]
        valor = c["segmento"].get(dim)
        if not valor:
            continue
        volumen = c["pedidos_actual"] + c["pedidos_anterior"]
        catalogo[dim].append({"valor": valor, "volumen_pedidos": volumen})
    for valores in catalogo.values():
        valores.sort(key=lambda v: v["volumen_pedidos"], reverse=True)
    return catalogo


def valor_existe(catalogo: dict[str, list[dict]], dimension: str, valor: str) -> bool:
    return any(v["valor"] == valor for v in catalogo.get(dimension, []))
