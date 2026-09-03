from __future__ import annotations

from ai.correcciones import construir_mensaje_correccion


def test_incluye_la_lista_cruda_de_problemas():
    mensaje = construir_mensaje_correccion(["Un problema cualquiera sin patrón reconocido."])
    assert "Un problema cualquiera sin patrón reconocido." in mensaje


def test_reconoce_patron_de_segmento_inventado_y_agrega_instruccion():
    mensaje = construir_mensaje_correccion(
        ["El segmento citado no corresponde a ningún cruce calculado por Python: posible invención."]
    )
    assert "Cómo corregirlo:" in mensaje
    assert "EXCLUSIVAMENTE" in mensaje


def test_reconoce_patron_de_metrica_invalida():
    mensaje = construir_mensaje_correccion(
        ["La métrica 'Margen bruto' (campo 'margen_bruto') no corresponde a ningún dato real calculado..."]
    )
    assert "margen, rentabilidad, costo o precio" in mensaje


def test_no_duplica_la_misma_instruccion_para_problemas_repetidos():
    problemas = [
        "La métrica 'usd_actual' citada (1) no coincide con el valor real calculado (2).",
        "La métrica 'pedidos_actual' citada (3) no coincide con el valor real calculado (4).",
    ]
    mensaje = construir_mensaje_correccion(problemas)
    assert mensaje.count("Revisá que estés copiando la cifra EXACTA") == 1


def test_sin_patrones_reconocidos_no_agrega_seccion_como_corregirlo():
    mensaje = construir_mensaje_correccion(["Trae menos de 2 métricas de respaldo: no hay evidencia numérica suficiente."])
    assert "Cómo corregirlo:" not in mensaje
