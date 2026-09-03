"""Resolución y aplicación del "scope activo" de una pregunta del copiloto.

Antes de este módulo, el scope (p. ej. "estamos hablando de OF VT MENDOZA")
vivía únicamente como texto libre dentro del prompt: el modelo tenía que
"acordarse" de repetirlo en cada llamada a una herramienta, y nada impedía
que una llamada sin filtro devolviera datos de todo el negocio mezclados con
los del segmento que se estaba analizando (ver auditoría, sección 02/03).

Acá el scope se resuelve UNA vez, antes de tocar ninguna herramienta, y se
usa para filtrar de verdad la lista de cruces que `ai/tools.py` puede ver:
una vez fijado, ninguna herramienta —ni el validador, ni el fallback
determinístico— puede devolver ni aceptar datos que no lo respeten, sin
importar qué pida el modelo. El scope deja de ser una convención de prompt
y pasa a ser un límite que impone Python.
"""
from __future__ import annotations

import json
import logging

from config import DIMENSIONES

logger = logging.getLogger("nexo_ia.assistant")

SCOPE_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "scope_pregunta",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["mantiene_scope_anterior", "scope"],
            "properties": {
                "mantiene_scope_anterior": {
                    "type": "boolean",
                    "description": (
                        "true si la pregunta actual continúa analizando el mismo scope que "
                        "la respuesta anterior (ej. 'separalo por asesor', 'profundizá ahí', "
                        "'¿cuál explica más esa variación?'). false si cambia de tema, "
                        "pregunta por el total general del negocio, o establece un scope "
                        "nuevo y distinto del anterior."
                    ),
                },
                "scope": {
                    "type": "array",
                    "description": (
                        "Filtros de scope mencionados EXPLÍCITAMENTE en la pregunta actual "
                        "(nombre de sucursal, sector, familia, asesor o clase ABC). Vacío si "
                        "la pregunta es sobre el total general o no menciona ningún filtro "
                        "nuevo. Nunca inventes un valor que no esté mencionado en el texto."
                    ),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["dimension", "valor"],
                        "properties": {
                            "dimension": {"type": "string", "enum": DIMENSIONES},
                            "valor": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}

PROMPT_SISTEMA_SCOPE = f"""Tu única tarea es detectar el SCOPE (el universo de análisis)
de una pregunta sobre datos comerciales, para que el sistema filtre los datos
ANTES de investigar. No analizás nada, no calculás nada, no redactás ninguna
conclusión: sólo identificás a qué segmento se refiere la pregunta.

Dimensiones posibles: {DIMENSIONES}.

Reglas:
1. `scope`: la lista de (dimension, valor) que la pregunta ACTUAL menciona
   como filtro. Vacío si es sobre el total general del negocio, o si no
   menciona ningún filtro nuevo.
2. `mantiene_scope_anterior`: si es true y la pregunta también menciona un
   scope nuevo, ese nuevo scope se COMBINA con el anterior (no lo
   reemplaza) — salvo que mencione otro valor para la MISMA dimensión, en
   cuyo caso el valor nuevo gana. Si la pregunta cambia claramente de tema o
   pregunta por el total general, `mantiene_scope_anterior` tiene que ser
   false aunque haya un scope anterior.
3. Copiá los valores tal como aparecen mencionados en la pregunta (no los
   normalices a mayúsculas ni les agregues prefijos que no estén en el
   texto) — el sistema los va a contrastar por separado contra los valores
   reales del dataset, y descarta cualquier valor que no exista.
4. "Separalo/desglosalo/dividilo POR asesor" (o por cualquier otra dimensión,
   SIN nombrar un valor puntual de esa dimensión) es un pedido de desglose,
   NO un filtro de scope — no pongas el nombre de la dimensión como si fuera
   su propio valor (p. ej. dimension=asesor, valor=asesor) en `scope` para
   eso. Sólo agregás algo a
   `scope` cuando la pregunta nombra un VALOR concreto de una dimensión
   (un nombre real de sucursal, sector, familia, asesor o clase ABC), nunca
   el nombre de la dimensión en sí.
"""


def _prompt_usuario_scope(
    pregunta: str, scope_anterior: dict | None, contexto_seleccionado: dict | None
) -> str:
    partes = [f"Pregunta actual: {pregunta}"]
    if scope_anterior:
        partes.append(
            "Scope de la respuesta INMEDIATAMENTE anterior en esta conversación: "
            + json.dumps(scope_anterior, ensure_ascii=False)
        )
    else:
        partes.append("No hay scope anterior (primera pregunta, o la anterior era sobre el total general).")
    if contexto_seleccionado:
        partes.append(
            "Contexto que el usuario tenía seleccionado al escribir esta pregunta puntual "
            "(puede sugerir un scope, pero si la pregunta de arriba habla de otra cosa, no lo "
            "uses): " + json.dumps(contexto_seleccionado, ensure_ascii=False)
        )
    return "\n\n".join(partes)


def resolver_scope(
    client,
    model: str,
    pregunta: str,
    scope_anterior: dict | None = None,
    contexto_seleccionado: dict | None = None,
) -> dict:
    """Devuelve el scope activo para esta pregunta puntual: un dict
    `{dimension: valor}` (sin validar todavía contra los datos reales — eso
    lo hace `validar_scope_contra_cruces`, que necesita conocer los cruces
    de esta corrida y por eso vive separado).
    """
    if client is None:
        return dict(scope_anterior or {})

    mensajes = [
        {"role": "system", "content": PROMPT_SISTEMA_SCOPE},
        {"role": "user", "content": _prompt_usuario_scope(pregunta, scope_anterior, contexto_seleccionado)},
    ]
    try:
        resp = client.chat.completions.create(model=model, messages=mensajes, response_format=SCOPE_JSON_SCHEMA)
        data = json.loads(resp.choices[0].message.content)
    except Exception:
        logger.exception("resolver_scope: fallo consultando la IA, se hereda el scope anterior tal cual")
        return dict(scope_anterior or {})

    scope_mencionado = {s["dimension"]: s["valor"] for s in (data.get("scope") or [])}
    if data.get("mantiene_scope_anterior") and scope_anterior:
        return {**scope_anterior, **scope_mencionado}
    return scope_mencionado


def resolver_scope_determinista(pregunta: str, cruces: list[dict], scope_anterior: dict | None = None) -> dict:
    """Variante sin IA (usada cuando no hay OPENAI_API_KEY configurada):
    busca si alguno de los valores reales de una dimensión (nivel 1) está
    mencionado literalmente en la pregunta. Es mucho más limitada que
    `resolver_scope` (no entiende "hablame del total" ni cambios de tema:
    si no encuentra ninguna mención nueva, siempre hereda el scope
    anterior), pero es mejor que no tener ningún scope en absoluto.

    Sólo considera valores de 4+ caracteres: hay clases ABC reales de una
    sola letra ("A", "B", "X") que matchearían como substring de casi
    cualquier pregunta y bloquearían el scope con un falso positivo.
    """
    pregunta_norm = pregunta.lower()
    palabras_pregunta = set(pregunta_norm.split())
    encontrado: dict[str, str] = {}
    for c in cruces:
        if c["nivel"] != 1:
            continue
        dim = c["dimensiones"][0]
        valor = c["segmento"].get(dim)
        if not valor or len(str(valor)) < 4:
            continue
        valor_norm = str(valor).lower()
        if valor_norm in pregunta_norm or any(
            palabra in palabras_pregunta for palabra in valor_norm.split() if len(palabra) > 3
        ):
            encontrado[dim] = valor
    if encontrado:
        return {**(scope_anterior or {}), **encontrado}
    return dict(scope_anterior or {})


def validar_scope_contra_cruces(scope_propuesto: dict, cruces: list[dict]) -> dict:
    """Descarta cualquier dimension:valor del scope propuesto que no
    corresponda a ningún valor real de un cruce de nivel 1 — nunca bloquear
    toda la conversación (dejando 0 cruces visibles) por un valor mal escrito,
    inventado, o levemente distinto del real.

    Antes de descartarlo del todo, intenta una coincidencia flexible: el
    modelo a veces extrae el valor sin un prefijo/sufijo organizacional (por
    ejemplo "VT MENDOZA" en vez de "OF VT MENDOZA") — si hay EXACTAMENTE un
    valor real que lo contiene (o que está contenido en él), se usa ese en
    vez de perder el scope entero por una diferencia de redacción.
    """
    valido: dict[str, str] = {}
    for dim, valor in scope_propuesto.items():
        valores_reales = {c["segmento"].get(dim) for c in cruces if c["nivel"] == 1 and c["dimensiones"] == [dim]}
        valores_reales.discard(None)

        if valor in valores_reales:
            valido[dim] = valor
            continue

        valor_norm = str(valor).strip().lower()
        candidatos = [
            v for v in valores_reales if valor_norm and (valor_norm in str(v).lower() or str(v).lower() in valor_norm)
        ]
        if len(candidatos) == 1:
            logger.info("scope: %s=%r no matcheaba exacto, se usa el valor real más cercano %r", dim, valor, candidatos[0])
            valido[dim] = candidatos[0]
        else:
            logger.info("scope: descartado %s=%r (no corresponde a ningún valor real de esa dimensión)", dim, valor)
    return valido


def objeto_en_scope(obj: dict, scope_activo: dict) -> bool:
    """¿Este cruce (o hallazgo, misma forma: `dimensiones` + `segmento`) es
    consistente con el scope activo? Tiene que incluir CADA dimensión del
    scope entre las suyas propias, con el mismo valor — un cruce que no
    desglosa por esa dimensión en absoluto (p. ej. el ranking global de
    'asesor' cuando el scope es sucursal=X) NO es válido dentro del scope,
    porque mezclaría datos de fuera de él.
    """
    return all(dim in obj["dimensiones"] and obj["segmento"].get(dim) == valor for dim, valor in scope_activo.items())


def filtrar_cruces_por_scope(cruces: list[dict], scope_activo: dict) -> list[dict]:
    if not scope_activo:
        return cruces
    return [c for c in cruces if objeto_en_scope(c, scope_activo)]
