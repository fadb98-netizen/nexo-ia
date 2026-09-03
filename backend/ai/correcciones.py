"""Mensajes de corrección para el loop de reintento del validador.

Antes, cuando la respuesta de la IA no pasaba `validator.validar_respuesta`,
`assistant.py` le devolvía al modelo la lista cruda de problemas como único
contexto para reintentar ("La métrica 'X' citada (123) no coincide con...").
Son mensajes precisos, pero exigen que el modelo mismo deduzca qué acción
concreta lo va a arreglar — y en la práctica, varias veces repetía el mismo
error en el reintento (ver auditoría, sección 08: "reintentos ante error").

Acá se reconocen los patrones de error MÁS comunes (son los mensajes que el
propio `validator.py` genera, así que el matching es estable) y se les agrega
una instrucción específica y accionable, sin dejar de mostrar también el
error crudo para que quede trazable.
"""
from __future__ import annotations

# (substring del mensaje de validator.py, instrucción concreta de corrección)
# El orden importa: se evalúan en orden y sólo se agrega cada instrucción una
# vez, aunque varios problemas del mismo tipo la disparen.
_PATRONES_CORRECCION: list[tuple[str, str]] = [
    (
        "no corresponde a ningún cruce calculado por Python",
        "Estás citando un segmento o un ítem de 'ranking' que no existe entre los datos "
        "calculados. Nunca inventes una combinación: usá EXCLUSIVAMENTE una que hayas visto "
        "literalmente en el campo 'segmento' de una fila que te devolvió desglosar_variacion "
        "u obtener_tabla_dimension en esta misma conversación.",
    ),
    (
        "no corresponde a ningún dato real",
        "Estás citando un 'campo' de metricas_respaldo que no existe para este segmento o "
        "total. Copiá 'campo' EXACTO de una de las claves numéricas que te devolvió la "
        "herramienta — no traduzcas el nombre ni inventes uno parecido (recordá: métricas "
        "como margen, rentabilidad, costo o precio no existen en los datos).",
    ),
    (
        "profundidad insuficiente",
        "Existe un cruce más profundo y con más contribución que el que citaste. Volvé a "
        "llamar desglosar_variacion agregando UNA dimensión más al mismo segmento (con el "
        "filtro de los valores que ya identificaste) antes de responder.",
    ),
    (
        "'cuanto_explica' cita",
        "El número en 'cuanto_explica' no coincide con la contribución real del segmento "
        "citado. Copiá literalmente 'contribucion_pct' o 'participacion_pct' del MISMO cruce "
        "que usaste para 'segmento' (no el de otro cruce), en notación estándar.",
    ),
    (
        "repite la misma dimensión",
        "Tenés varios valores de la misma dimensión mezclados en 'segmento'. Elegí uno solo "
        "para 'segmento' (el de mayor impacto) y movés el resto de las categorías al array "
        "'ranking'.",
    ),
    (
        "no coincide con el valor real calculado",
        "Un número que citaste no coincide con el valor real que te devolvió la herramienta. "
        "Revisá que estés copiando la cifra EXACTA (sin redondear, sin coma decimal ni punto "
        "de miles) del mismo cruce que estás citando — no la de un cruce parecido.",
    ),
    (
        "no coincide con el total real calculado",
        "Estás citando un número que no coincide con lo que obtener_resumen_total te "
        "devolvió. Volvé a llamarla (si hay un scope activo, está bloqueada: usá "
        "desglosar_variacion en su lugar) y copiá el valor EXACTO.",
    ),
]


def construir_mensaje_correccion(problemas: list[str]) -> str:
    """Arma el mensaje de reintento: la lista cruda de problemas (para que
    quede trazable) más, cuando el patrón es reconocible, una instrucción
    concreta de cómo corregirlo — en vez de dejar que el modelo deduzca la
    acción a partir del error crudo."""
    instrucciones: list[str] = []
    for problema in problemas:
        for patron, instruccion in _PATRONES_CORRECCION:
            if patron in problema and instruccion not in instrucciones:
                instrucciones.append(instruccion)
                break

    partes = ["Tu respuesta anterior no pasó la validación. Problemas detectados:"]
    partes.extend(f"- {p}" for p in problemas)
    if instrucciones:
        partes.append("Cómo corregirlo:")
        partes.extend(f"- {i}" for i in instrucciones)
    partes.append("Usá más herramientas si hace falta y volvé a responder.")
    return "\n".join(partes)
