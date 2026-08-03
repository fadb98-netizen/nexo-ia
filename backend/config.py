"""Configuración central: columnas, dimensiones, tipos y umbrales.

Ningún otro módulo debe usar strings de columna hardcodeados: todo pasa por
las constantes COL_* definidas acá.
"""
from __future__ import annotations

# --- Columnas del CSV ---
COL_FECHA_PEDIDO = "fecha_pedido"
COL_SEMANA = "semana"
COL_PEDIDO_ID = "pedido_id"
COL_CLIENTE_ID = "cliente_id"
COL_SUCURSAL = "sucursal"
COL_ASESOR = "asesor"
COL_SECTOR_INDUSTRIAL = "sector_industrial"
COL_FAMILIA = "familia"
COL_ABC_CLIENTE = "abc_cliente"
COL_USD = "usd"
COL_KG = "kg"
COL_POSICIONES = "posiciones"

COLUMNAS_OBLIGATORIAS = [
    COL_FECHA_PEDIDO,
    COL_SEMANA,
    COL_PEDIDO_ID,
    COL_CLIENTE_ID,
    COL_SUCURSAL,
    COL_ASESOR,
    COL_SECTOR_INDUSTRIAL,
    COL_FAMILIA,
    COL_ABC_CLIENTE,
    COL_USD,
    COL_KG,
    COL_POSICIONES,
]

COLUMNAS_NUMERICAS = [COL_USD, COL_KG, COL_POSICIONES]
COLUMNAS_TEXTO_OBLIGATORIAS = [
    COL_PEDIDO_ID,
    COL_CLIENTE_ID,
    COL_SUCURSAL,
    COL_ASESOR,
    COL_SECTOR_INDUSTRIAL,
    COL_FAMILIA,
    COL_ABC_CLIENTE,
]

# --- Dimensiones habilitadas para el motor de 31 cruces ---
DIMENSIONES = [
    COL_SUCURSAL,
    COL_FAMILIA,
    COL_SECTOR_INDUSTRIAL,
    COL_ASESOR,
    COL_ABC_CLIENTE,
]

# --- Períodos (en semanas) ---
SEMANAS_TOTAL_ESPERADAS = 16
SEMANAS_RECIENTE = 4
SEMANAS_COMPARATIVO = 4
SEMANAS_HISTORICO = 8  # las 8 más antiguas de las 16, usadas como contexto
SEMANAS_GRAFICO = 8  # reciente + comparativo, lo que se muestra en pantalla
SEMANAS_MINIMO_ACEPTABLE = 9  # menos que esto: no alcanza para reciente+comparativo+algo de histórico

# --- Umbrales de materialidad para el filtro post-cálculo de los 31 cruces ---
MIN_PEDIDOS_COMBINADOS = 5  # pedidos_actual + pedidos_anterior por debajo de esto: no hay volumen
MIN_CONTRIBUCION_ABS_PCT = 3.0  # contribución absoluta a la variación total, en puntos porcentuales
MIN_SEMANAS_OBSERVADAS = 2  # cuántas semanas con datos como mínimo dentro del período reciente+comparativo

# --- Hallazgos ---
MIN_HALLAZGOS = 3
MAX_HALLAZGOS = 5

# --- Validación de archivo subido ---
MAX_FILE_SIZE_MB = 25
ALLOWED_EXTENSIONS = {".csv"}

# --- Valores válidos de ABC (si aparece un valor fuera de esta lista, se marca como inválido) ---
ABC_VALIDOS = {"A", "B", "C"}
