"""Genera sample-data/pedidos_demo.csv: 16 semanas de pedidos sintéticos.

Script standalone (sólo usa la librería estándar) para que pueda correrse sin
el entorno virtual del backend. Reproducible vía semilla fija.

Uso:
    python generar_datos_sinteticos.py

Embebe a propósito un patrón concentrado y persistente en las últimas 4
semanas (CAPITAL x CAÑOS Y TUBOS x CONSTRUCCION x ASESOR_3 x clase A) para que
el motor de 31 cruces y la IA tengan algo real que encontrar en el modo demo,
más una compensación parcial en otro segmento (ROSARIO x PERFILES) para que el
patrón no sea trivialmente "la variación total = la variación del segmento".
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 42
N_SEMANAS = 16
SALIDA = Path(__file__).parent / "pedidos_demo.csv"

SUCURSALES = ["CAPITAL", "ROSARIO", "CORDOBA", "MENDOZA"]
FAMILIAS = ["CH304", "CH316", "CH430", "CAÑOS Y TUBOS", "PERFILES", "BULONERIA"]
SECTORES = ["CONSTRUCCION", "AUTOPARTES", "AGRO", "METALMECANICA", "ENERGIA"]
ASESORES = [f"ASESOR_{i}" for i in range(1, 7)]
ABC = ["A", "B", "C"]

SEGMENTO_BASE = {"sucursal": "CAPITAL", "familia": "CAÑOS Y TUBOS", "sector_industrial": "CONSTRUCCION"}
SEGMENTO_PROFUNDO = {"asesor": "ASESOR_3", "abc_cliente": "A"}  # dentro del segmento base, la caída se concentra acá
SEGMENTO_COMPENSA = {"sucursal": "ROSARIO", "familia": "PERFILES"}

N_CLIENTES = 160


def _lunes_de_esta_semana(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _clientes_para(sucursal: str, sector: str, abc: str, rng: random.Random) -> str:
    # Determinístico por combinación para que un mismo tipo de cliente
    # aparezca reiteradas veces (necesario para métricas de concentración).
    base = hash((sucursal, sector, abc)) % 40
    idx = base + rng.randint(0, 8)
    return f"CLI_{idx % N_CLIENTES:04d}"


def _ticket_medio(sucursal: str, familia: str) -> float:
    # Media estable por combinación sucursal x familia (no una tirada libre por
    # línea): así el ruido semana a semana es acotado y el efecto embebido en
    # el período reciente queda como la señal dominante, no ruido de muestreo.
    return 800 + (abs(hash((sucursal, familia))) % 2500)


def generar() -> None:
    rng = random.Random(SEMILLA)

    lunes_actual = _lunes_de_esta_semana(date.today()) - timedelta(weeks=1)  # última semana completa
    semanas = [lunes_actual - timedelta(weeks=(N_SEMANAS - 1 - i)) for i in range(N_SEMANAS)]

    filas = []
    pedido_seq = 1

    for idx_semana, lunes in enumerate(semanas):
        es_reciente = idx_semana >= N_SEMANAS - 4  # últimas 4 semanas = período afectado
        n_pedidos_semana = rng.randint(170, 220)

        for _ in range(n_pedidos_semana):
            sucursal = rng.choice(SUCURSALES)
            asesor = rng.choice(ASESORES)
            sector = rng.choice(SECTORES)
            abc = rng.choices(ABC, weights=[0.2, 0.35, 0.45])[0]
            cliente_id = _clientes_para(sucursal, sector, abc, rng)
            fecha_pedido = lunes + timedelta(days=rng.randint(0, 4))  # días hábiles L-V
            pedido_id = f"PED{pedido_seq:07d}"
            pedido_seq += 1

            n_lineas = rng.choices([1, 2, 3], weights=[0.55, 0.3, 0.15])[0]
            familias_pedido = rng.sample(FAMILIAS, k=n_lineas)

            for familia in familias_pedido:
                es_base_afectado = (
                    es_reciente
                    and sucursal == SEGMENTO_BASE["sucursal"]
                    and familia == SEGMENTO_BASE["familia"]
                    and sector == SEGMENTO_BASE["sector_industrial"]
                )
                es_profundo_afectado = (
                    es_base_afectado
                    and asesor == SEGMENTO_PROFUNDO["asesor"]
                    and abc == SEGMENTO_PROFUNDO["abc_cliente"]
                )
                es_segmento_compensa = (
                    es_reciente
                    and sucursal == SEGMENTO_COMPENSA["sucursal"]
                    and familia == SEGMENTO_COMPENSA["familia"]
                )

                usd_base = _ticket_medio(sucursal, familia) * rng.uniform(0.75, 1.25)
                kg_base = usd_base * rng.uniform(0.8, 1.6)
                posiciones = rng.randint(1, 6)

                if es_profundo_afectado:
                    usd_base *= 0.35  # caída muy fuerte y persistente, concentrada acá
                    kg_base *= 0.4
                    if rng.random() < 0.35:
                        continue
                elif es_base_afectado:
                    usd_base *= 0.8  # caída moderada en el resto del segmento base
                    kg_base *= 0.85
                elif es_segmento_compensa:
                    usd_base *= 1.35  # compensación parcial

                filas.append(
                    {
                        "fecha_pedido": fecha_pedido.isoformat(),
                        "semana": lunes.isoformat(),
                        "pedido_id": pedido_id,
                        "cliente_id": cliente_id,
                        "sucursal": sucursal,
                        "asesor": asesor,
                        "sector_industrial": sector,
                        "familia": familia,
                        "abc_cliente": abc,
                        "usd": round(usd_base, 2),
                        "kg": round(kg_base, 1),
                        "posiciones": posiciones,
                    }
                )

    columnas = [
        "fecha_pedido", "semana", "pedido_id", "cliente_id", "sucursal",
        "asesor", "sector_industrial", "familia", "abc_cliente", "usd", "kg", "posiciones",
    ]
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)

    print(f"Generadas {len(filas)} filas ({pedido_seq - 1} pedidos únicos) en {SALIDA}")


if __name__ == "__main__":
    generar()
