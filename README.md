# Nexo IA

Asistente de análisis comercial conversacional. Se sube un CSV de pedidos y la aplicación
detecta, explica y visualiza los patrones detrás de una variación — sin que la IA invente ni
calcule ninguna cifra por su cuenta.

## 1. Problema que resuelve

Cuando una métrica agregada (ventas, pedidos) cae o sube, esa variación casi nunca está
repartida de forma uniforme: suele estar concentrada en un cruce específico de sucursal ×
familia de producto × sector × asesor × clase de cliente, invisible al mirar el total. Detectar
eso a mano cruzando planillas es lento y depende de quién pregunte.

## 2. Para qué sirve el asistente

Responde en lenguaje natural preguntas sobre esos datos ("¿qué explica la caída del último
mes?", "compará ventas entre oficinas") investigando con herramientas sobre números que
**Python ya calculó**, nunca inventados por el modelo. Si la evidencia no alcanza, lo dice en
vez de arriesgar una respuesta.

## 3. Principales funcionalidades

- Carga de CSV con validación completa (columnas, tipos, fechas, duplicados, semanas).
- Cálculo exhaustivo de las 31 combinaciones posibles entre 5 dimensiones comerciales.
- Centro de hallazgos: 3-5 patrones priorizados automáticamente, sin intervención de la IA.
- Copiloto conversacional con memoria de la conversación y gráficos generados a demanda
  (línea, barras, heatmap, participación, tabla, ranking) según lo que se pregunte.
- Modo 100% determinístico si no hay una clave de OpenAI configurada — la app nunca falla por
  falta de IA.

## 4. Arquitectura general

```
Frontend (Next.js)  ──HTTP──▶  Backend (FastAPI)
  dashboard, copiloto              ├─ core/  → validación, 31 cruces, patrones (determinístico)
                                    ├─ ai/    → tool-calling + OpenAI + validador anti-invención
                                    └─ Supabase (opcional) → historial de corridas
```

La IA nunca ve el CSV ni calcula nada: sólo interpreta resultados ya calculados por Python a
través de herramientas de solo lectura, y su respuesta final se valida automáticamente contra
esos mismos datos antes de mostrarse. Detalle completo en
[`docs/DECISIONES_DEL_PROYECTO.md`](docs/DECISIONES_DEL_PROYECTO.md).

Material de entrega: [`docs/presentacion_nexo_ia.pptx`](docs/presentacion_nexo_ia.pptx) /
[`.pdf`](docs/presentacion_nexo_ia.pdf) (10 diapositivas, con notas para el expositor) y
[`docs/ESTRUCTURA_PRESENTACION.md`](docs/ESTRUCTURA_PRESENTACION.md).

## 5. Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Frontend | Next.js (TypeScript) + Tailwind CSS + Apache ECharts |
| Backend | FastAPI + Polars |
| IA | OpenAI (tool-calling + salida estructurada) |
| Persistencia opcional | Supabase |
| Tests | Pytest |

## 6. Instrucciones para ejecutar el proyecto

Requisitos: Python 3.11+, Node.js 20+.

```bash
git clone <url-del-repo>
cd nexo-ia
```

**Backend:**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend** (en otra terminal):

```bash
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:3000`.

## 7. Variables de entorno

Copiar [`.env.example`](.env.example) a `backend/.env` y a `frontend/.env.local`. Ninguna es
obligatoria salvo la del frontend en local.

| Variable | Dónde | Obligatoria | Qué pasa si falta |
|---|---|---|---|
| `OPENAI_API_KEY` | backend | No | La app funciona en modo determinístico (sin interpretación de IA). |
| `OPENAI_MODEL` | backend | No | Usa `gpt-4o-mini` por defecto. |
| `SUPABASE_URL` / `SUPABASE_KEY` | backend | No | No se persiste historial entre reinicios del backend. |
| `NEXT_PUBLIC_API_URL` | frontend | Sí | Debe apuntar al backend (`http://localhost:8000` en local). |

Ninguna variable lleva un valor real en este repo.

## 8. Cómo correr los tests

```bash
cd backend
pytest -q
```

## 9. Web desplegada

**Frontend:** [nexo-ia-eta.vercel.app](https://nexo-ia-eta.vercel.app) (Vercel)
**Backend:** Render, capa gratuita — la primera request tras un período de inactividad puede
tardar hasta ~50s en responder mientras el servicio arranca de nuevo.

## 10. Cómo probar el asistente con el CSV de ejemplo

[`data/datos_demo.csv`](data/datos_demo.csv) es un dataset 100% ficticio (16 semanas, ~670
filas) pensado para probar el flujo completo: subirlo en pantalla principal (o usar el botón
"Cargar datos de demo", que carga un dataset sintético equivalente generado en el servidor).

Columnas: `fecha_pedido`, `semana` (lunes ISO de esa semana), `pedido_id`, `cliente_id`,
`sucursal`, `asesor`, `sector_industrial`, `familia`, `abc_cliente`, `usd`, `kg`, `posiciones`.

Incluye a propósito una caída marcada en `SUCURSAL NORTE × FAMILIA ALFA` en las últimas 4
semanas, y una combinación (`SUCURSAL OESTE × FAMILIA DELTA`) que tenía datos y desaparece en
el período reciente — útil para probar cómo responde el asistente cuando no hay información.
Preguntas sugeridas: *"¿qué explica la caída del último mes?"*, *"compará ventas entre
sucursales"*, *"¿cómo viene FAMILIA DELTA en SUCURSAL OESTE?"*.
