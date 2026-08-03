"""Empaquetado de evidencia: convierte un cruce calculado en algo citable.

Un `Hallazgo` es la unidad que ve tanto el usuario (Centro de hallazgos) como
la IA (a través de las tools). Nunca contiene un número que no venga
directamente de `core/combinations.py` o `core/metrics.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Hallazgo:
    id: str
    tipo: str
    titulo: str
    resumen: str
    segmento: dict
    dimensiones: list[str]
    nivel: int
    que_ocurrio: str
    cuanto_explica: str
    metricas_respaldo: dict
    evolucion_semanal: list[float]
    semanas_grafico: list[str]
    nivel_evidencia: str
    limitaciones: list[str]
    driver_principal: str
    score: float
    score_desglose: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "resumen": self.resumen,
            "segmento": self.segmento,
            "dimensiones": self.dimensiones,
            "nivel": self.nivel,
            "que_ocurrio": self.que_ocurrio,
            "cuanto_explica": self.cuanto_explica,
            "metricas_respaldo": self.metricas_respaldo,
            "evolucion_semanal": self.evolucion_semanal,
            "semanas_grafico": self.semanas_grafico,
            "nivel_evidencia": self.nivel_evidencia,
            "limitaciones": self.limitaciones,
            "driver_principal": self.driver_principal,
            "score": round(self.score, 1),
            "score_desglose": self.score_desglose,
        }


def formatear_usd(valor: float) -> str:
    signo = "-" if valor < 0 else ""
    return f"{signo}US$ {abs(valor):,.0f}".replace(",", ".")


def formatear_pct(valor: float | None) -> str:
    if valor is None:
        return "s/d"
    return f"{valor:+.1f}%"


def describir_segmento(segmento: dict) -> str:
    return " × ".join(str(v) for v in segmento.values())


def evidencia_suficiente(cruce: dict, min_pedidos: int) -> tuple[bool, str]:
    """Chequeo binario reutilizado por el validador de IA: ¿hay evidencia
    numérica mínima detrás de este cruce como para sostener una conclusión?
    """
    volumen = cruce["pedidos_actual"] + cruce["pedidos_anterior"]
    if volumen < min_pedidos:
        return False, f"Sólo {volumen} pedidos combinados (mínimo {min_pedidos})."
    if cruce["n_semanas_observadas"] < 2:
        return False, "Menos de 2 semanas con datos en el período reciente+comparativo."
    return True, ""


def construir_metricas_respaldo(cruce: dict) -> dict:
    """Subconjunto de campos numéricos que se muestra como evidencia dura."""
    return {
        "usd_actual": cruce["usd_actual"],
        "usd_anterior": cruce["usd_anterior"],
        "diferencia_absoluta": cruce["diferencia_absoluta"],
        "variacion_pct": cruce["variacion_pct"],
        "pedidos_actual": cruce["pedidos_actual"],
        "pedidos_anterior": cruce["pedidos_anterior"],
        "clientes_actual": cruce["clientes_actual"],
        "clientes_anterior": cruce["clientes_anterior"],
        "ticket_actual": cruce["ticket_actual"],
        "ticket_anterior": cruce["ticket_anterior"],
        "posiciones_por_pedido_actual": cruce["posiciones_por_pedido_actual"],
        "posiciones_por_pedido_anterior": cruce["posiciones_por_pedido_anterior"],
        "participacion_pct": cruce["participacion_pct"],
        "contribucion_pct": cruce["contribucion_pct"],
        "persistencia": cruce["persistencia"],
        "volatilidad": cruce["volatilidad"],
        "n_semanas_observadas": cruce["n_semanas_observadas"],
    }
