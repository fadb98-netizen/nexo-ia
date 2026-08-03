from __future__ import annotations

from ai import validator

CRUCE_REAL = {
    "nivel": 2,
    "dimensiones": ["sucursal", "familia"],
    "segmento": {"sucursal": "CAPITAL", "familia": "CH304"},
    "usd_actual": 115756.29,
    "usd_anterior": 217919.89,
    "diferencia_absoluta": -102163.6,
    "variacion_pct": -46.9,
    "pedidos_actual": 20,
    "pedidos_anterior": 30,
    "contribucion_pct": 45.0,
}

CRUCE_MAS_PROFUNDO = {
    "nivel": 3,
    "dimensiones": ["sucursal", "familia", "sector_industrial"],
    "segmento": {"sucursal": "CAPITAL", "familia": "CH304", "sector_industrial": "CONSTRUCCION"},
    "usd_actual": 90000.0,
    "usd_anterior": 190000.0,
    "diferencia_absoluta": -100000.0,
    "variacion_pct": -52.6,
    "pedidos_actual": 15,
    "pedidos_anterior": 22,
    "contribucion_pct": 80.0,
}

CRUCES_DISPONIBLES = [CRUCE_REAL, CRUCE_MAS_PROFUNDO]


def _respuesta_base(**overrides) -> dict:
    base = {
        "que_ocurrio": "Cayó fuerte en CAPITAL x CH304.",
        "segmento": [{"dimension": "sucursal", "valor": "CAPITAL"}, {"dimension": "familia", "valor": "CH304"}],
        "cuanto_explica": "Explica 45.0% de la variación total.",
        "metricas_respaldo": [
            {"nombre": "usd_actual", "valor": "115756.29"},
            {"nombre": "pedidos_actual", "valor": "20"},
        ],
        "evolucion_semanal": "Cayó de forma sostenida en las últimas 4 semanas, semana a semana.",
        "nivel_evidencia": "media",
        "limitaciones": "",
        "hay_causa_dominante": True,
        "graficos": [],
    }
    base.update(overrides)
    return base


def test_respuesta_bien_formada_pasa():
    valido, problemas = validator.validar_respuesta(_respuesta_base(), [CRUCE_REAL])
    assert valido, problemas


def test_segmento_vacio_falla():
    valido, problemas = validator.validar_respuesta(_respuesta_base(segmento=[]), CRUCES_DISPONIBLES)
    assert not valido
    assert any("segmento" in p.lower() for p in problemas)


def test_segmento_inventado_falla():
    resp = _respuesta_base(segmento=[{"dimension": "sucursal", "valor": "MENDOZA"}])
    valido, problemas = validator.validar_respuesta(resp, CRUCES_DISPONIBLES)
    assert not valido
    assert any("no corresponde" in p for p in problemas)


def test_pocas_metricas_falla():
    resp = _respuesta_base(metricas_respaldo=[{"nombre": "usd_actual", "valor": "115756.29"}])
    valido, problemas = validator.validar_respuesta(resp, CRUCES_DISPONIBLES)
    assert not valido


def test_cuanto_explica_sin_numero_falla():
    resp = _respuesta_base(cuanto_explica="Explica una porción relevante.")
    valido, problemas = validator.validar_respuesta(resp, CRUCES_DISPONIBLES)
    assert not valido


def test_cifra_citada_no_coincide_con_la_real_falla():
    resp = _respuesta_base(
        metricas_respaldo=[
            {"nombre": "usd_actual", "valor": "999999.00"},
            {"nombre": "pedidos_actual", "valor": "20"},
        ]
    )
    valido, problemas = validator.validar_respuesta(resp, [CRUCE_REAL])
    assert not valido
    assert any("no coincide" in p for p in problemas)


def test_cifra_citada_en_formato_es_ar_se_reconoce_igual():
    """115.756,29 (es-AR) y 115756.29 (estándar) tienen que validar igual:
    regresión del bug donde el parser rompía cifras en notación estándar."""
    resp_estandar = _respuesta_base(metricas_respaldo=[
        {"nombre": "usd_actual", "valor": "115756.29"},
        {"nombre": "pedidos_actual", "valor": "20"},
    ])
    resp_es_ar = _respuesta_base(metricas_respaldo=[
        {"nombre": "usd_actual", "valor": "115.756,29"},
        {"nombre": "pedidos_actual", "valor": "20"},
    ])
    valido1, problemas1 = validator.validar_respuesta(resp_estandar, [CRUCE_REAL])
    valido2, problemas2 = validator.validar_respuesta(resp_es_ar, [CRUCE_REAL])
    assert valido1, problemas1
    assert valido2, problemas2


def test_profundidad_insuficiente_si_existe_cruce_mas_profundo_no_citado():
    resp = _respuesta_base(
        segmento=[{"dimension": "sucursal", "valor": "CAPITAL"}, {"dimension": "familia", "valor": "CH304"}]
    )
    valido, problemas = validator.validar_respuesta(resp, CRUCES_DISPONIBLES)
    assert not valido
    assert any("profundidad" in p.lower() for p in problemas)


def test_extraer_numero_maneja_ambos_formatos():
    assert validator._extraer_numero("115756.29") == 115756.29
    assert validator._extraer_numero("115.756,29") == 115756.29
    assert validator._extraer_numero("US$ 1.500,50") == 1500.50
    assert validator._extraer_numero("-32.7%") == -32.7
