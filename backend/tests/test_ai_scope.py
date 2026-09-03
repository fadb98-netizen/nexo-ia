from __future__ import annotations

import json
import types

from ai import scope
from core import combinations
from tests.conftest import SEMANA_COMPARATIVA, SEMANA_RECIENTE


class _ClienteFalso:
    """Simula la forma mínima del cliente de OpenAI que usa `scope.py`
    (`client.chat.completions.create(...).choices[0].message.content`),
    para poder probar el filtrado de opciones sin llamar a la API real."""

    def __init__(self, contenido: dict):
        self._contenido = contenido
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        mensaje = types.SimpleNamespace(content=json.dumps(self._contenido))
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=mensaje)])


def _cruces(df_reciente, df_comparativo, df_historico):
    return combinations.calcular_todas_las_combinaciones(
        df_reciente, df_comparativo, df_historico, [SEMANA_COMPARATIVA, SEMANA_RECIENTE], []
    )


def test_validar_scope_contra_cruces_descarta_valor_inventado(df_reciente, df_comparativo, df_historico):
    cruces = _cruces(df_reciente, df_comparativo, df_historico)
    valido = scope.validar_scope_contra_cruces({"sucursal": "TUCUMAN_INVENTADA"}, cruces)
    assert valido == {}


def test_validar_scope_contra_cruces_conserva_valor_real(df_reciente, df_comparativo, df_historico):
    cruces = _cruces(df_reciente, df_comparativo, df_historico)
    valido = scope.validar_scope_contra_cruces({"sucursal": "CAPITAL"}, cruces)
    assert valido == {"sucursal": "CAPITAL"}


def test_validar_scope_contra_cruces_matchea_valor_sin_prefijo_organizacional(
    df_reciente, df_comparativo, df_historico
):
    """Regresión real: el resolver de scope extrajo 'VT MENDOZA' de una
    pregunta sobre 'OF VT MENDOZA' (le comió el prefijo 'OF'). En vez de
    perder el scope entero por esa diferencia de redacción, si hay
    EXACTAMENTE un valor real que lo contiene, se usa ese."""
    cruces = _cruces(df_reciente, df_comparativo, df_historico)
    valido = scope.validar_scope_contra_cruces({"sucursal": "APITAL"}, cruces)  # subset de "CAPITAL"
    assert valido == {"sucursal": "CAPITAL"}


def test_filtrar_cruces_por_scope_excluye_cruces_de_otro_valor_y_sin_esa_dimension(
    df_reciente, df_comparativo, df_historico
):
    """El corazón del scope-lock: al fijar sucursal=CAPITAL, un cruce de
    ROSARIO queda afuera (valor distinto) y también un cruce nivel-1 de
    'asesor' solo (no incluye la dimensión 'sucursal' en absoluto, así que no
    hay forma de garantizar que sea consistente con el scope: mezclaría
    datos de todo el negocio, no sólo de CAPITAL)."""
    cruces = _cruces(df_reciente, df_comparativo, df_historico)
    filtrados = scope.filtrar_cruces_por_scope(cruces, {"sucursal": "CAPITAL"})

    assert all(c["segmento"].get("sucursal") == "CAPITAL" for c in filtrados)
    assert not any(c["dimensiones"] == ["asesor"] for c in filtrados)  # A1 y A2 solos, sin filtrar por sucursal
    assert any(c["nivel"] == 1 and c["dimensiones"] == ["sucursal"] for c in filtrados)  # el total de CAPITAL sí queda
    assert any(set(c["dimensiones"]) == {"sucursal", "asesor"} for c in filtrados)  # el cruce de 2 dims sí queda


def test_filtrar_cruces_por_scope_sin_scope_no_cambia_nada(df_reciente, df_comparativo, df_historico):
    cruces = _cruces(df_reciente, df_comparativo, df_historico)
    assert scope.filtrar_cruces_por_scope(cruces, {}) == cruces


def test_resolver_scope_sin_cliente_hereda_el_anterior():
    assert scope.resolver_scope(None, "modelo-x", "cualquier pregunta", {"sucursal": "CAPITAL"}) == {"sucursal": "CAPITAL"}


def test_resolver_scope_determinista_detecta_valor_mencionado_en_la_pregunta(df_reciente, df_comparativo, df_historico):
    cruces = _cruces(df_reciente, df_comparativo, df_historico)
    resultado = scope.resolver_scope_determinista("Analizá ROSARIO por favor", cruces)
    assert resultado == {"sucursal": "ROSARIO"}


def test_resolver_scope_determinista_sin_mencion_hereda_el_anterior(df_reciente, df_comparativo, df_historico):
    cruces = _cruces(df_reciente, df_comparativo, df_historico)
    resultado = scope.resolver_scope_determinista("¿cuál explica más esa variación?", cruces, {"sucursal": "CAPITAL"})
    assert resultado == {"sucursal": "CAPITAL"}


def test_detectar_ambiguedad_sin_cliente_no_marca_nada():
    assert scope.detectar_ambiguedad(None, "modelo-x", "¿cómo viene la clase A?", {"abc_cliente": []}) == {
        "es_ambigua": False,
        "motivo": "",
        "opciones": [],
    }


def test_detectar_ambiguedad_descarta_opciones_inventadas_y_valida_las_reales():
    """Aunque el modelo diga es_ambigua=true, cada opción se contrasta contra
    el catálogo real -- una opción con un valor que no existe en los datos
    nunca llega al usuario."""
    catalogo = {"abc_cliente": [{"valor": "A", "volumen_pedidos": 10}, {"valor": "A1", "volumen_pedidos": 20}]}
    cliente = _ClienteFalso(
        {
            "es_ambigua": True,
            "motivo": "Clase A puede ser el código exacto o la familia A1-A3.",
            "opciones": [
                {"dimension": "abc_cliente", "valor": "A", "etiqueta": "Clase A (código exacto)"},
                {"dimension": "abc_cliente", "valor": "A1", "etiqueta": "Clase A1"},
                {"dimension": "abc_cliente", "valor": "A99_INVENTADO", "etiqueta": "Opción inventada"},
            ],
        }
    )
    resultado = scope.detectar_ambiguedad(cliente, "modelo-x", "¿cómo viene la clase A?", catalogo)
    assert resultado["es_ambigua"] is True
    assert {o["valor"] for o in resultado["opciones"]} == {"A", "A1"}


def test_detectar_ambiguedad_con_menos_de_2_opciones_validas_no_marca_ambiguedad():
    """Si al descartar las opciones inventadas queda una sola (o ninguna)
    opción real, preguntar no tiene sentido -- no hay entre qué elegir."""
    catalogo = {"abc_cliente": [{"valor": "A", "volumen_pedidos": 10}]}
    cliente = _ClienteFalso(
        {
            "es_ambigua": True,
            "motivo": "...",
            "opciones": [
                {"dimension": "abc_cliente", "valor": "A", "etiqueta": "Clase A"},
                {"dimension": "abc_cliente", "valor": "INVENTADO", "etiqueta": "..."},
            ],
        }
    )
    resultado = scope.detectar_ambiguedad(cliente, "modelo-x", "¿cómo viene la clase A?", catalogo)
    assert resultado["es_ambigua"] is False


def test_objeto_en_scope_requiere_la_dimension_y_el_valor():
    cruce_capital = {"dimensiones": ["sucursal", "asesor"], "segmento": {"sucursal": "CAPITAL", "asesor": "A1"}}
    cruce_rosario = {"dimensiones": ["sucursal", "asesor"], "segmento": {"sucursal": "ROSARIO", "asesor": "A2"}}
    cruce_sin_sucursal = {"dimensiones": ["asesor"], "segmento": {"asesor": "A1"}}

    scope_activo = {"sucursal": "CAPITAL"}
    assert scope.objeto_en_scope(cruce_capital, scope_activo) is True
    assert scope.objeto_en_scope(cruce_rosario, scope_activo) is False
    assert scope.objeto_en_scope(cruce_sin_sucursal, scope_activo) is False
