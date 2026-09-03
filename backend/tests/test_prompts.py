from __future__ import annotations

from ai import prompts


def test_prompt_pregunta_sin_exploracion_profunda_no_menciona_el_modo():
    texto = prompts.prompt_pregunta("¿Cómo viene Capital?", None, [])
    assert "MODO ANÁLISIS PROFUNDO" not in texto


def test_prompt_pregunta_con_exploracion_profunda_la_incluye_completa():
    cruces = [{"segmento": {"sucursal": "CAPITAL"}, "contribucion_pct": 42.0}]
    texto = prompts.prompt_pregunta("Análisis profundo de Capital", None, [], scope_activo={"sucursal": "CAPITAL"}, exploracion_profunda=cruces)
    assert "MODO ANÁLISIS PROFUNDO" in texto
    assert "CAPITAL" in texto
    assert "42.0" in texto


def test_prompt_pregunta_con_exploracion_vacia_igual_marca_el_modo():
    """Una lista vacía (no encontró nada material dentro del scope) sigue
    siendo "modo profundo activado" -- distinto de None (modo normal)."""
    texto = prompts.prompt_pregunta("Análisis profundo", None, [], exploracion_profunda=[])
    assert "MODO ANÁLISIS PROFUNDO" in texto
