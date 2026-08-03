# Nexo IA

Asistente de análisis comercial. Se sube un CSV de pedidos (16 semanas), **Python calcula
todo** — validación, KPIs, y las 31 combinaciones posibles de 5 dimensiones comerciales — y
**la IA interpreta esa evidencia** para redactar conclusiones verificables, nunca cifras
propias.

> Trabajo final de Ingeniería. Repo pensado para clonarse y correr siguiendo este README de
> punta a punta, sin credenciales: la app funciona en modo determinístico (sin OpenAI) y sin
> Supabase configurado.

---

## 1. Objetivo

Detectar, en una base de pedidos comerciales, patrones multivariables que no son evidentes
mirando el dato de forma agregada — por ejemplo, que una caída total esté en realidad
concentrada en un cruce muy específico de sucursal × familia × sector × asesor × clase de
cliente, mientras el resto del negocio está estable o incluso creciendo.

La regla de diseño central, no negociable:

> **Python calcula todos los números y genera la evidencia. La IA interpreta, investiga con
> herramientas y redacta conclusiones. La IA nunca inventa ni calcula cifras por su cuenta.**

Ver sección 9 (["Cómo se controla a la IA"](#9-cómo-se-controla-a-la-ia)) para el detalle de
cómo se hace cumplir esto en código, no sólo en el prompt.

---

## 2. Arquitectura

```
Usuario → sube CSV
   │
   ▼
Frontend (Next.js/TS, Vercel)  ──HTTP──▶  Backend (FastAPI, Python)
   │  Dashboard, gráficos ECharts,            │
   │  centro de hallazgos, copiloto           ├─ core/  → validación, 31 cruces, patrones,
   │                                          │           scoring (TODO determinístico)
   │                                          ├─ ai/    → tool-calling + OpenAI + validador
   │                                          └─ Supabase (opcional) → historial de corridas
   ▼                                                       y conversaciones
Browser (ECharts, estado de la corrida en memoria del cliente)
```

- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind CSS + componentes propios
  estilo shadcn/ui (escritos a mano, ver sección 8). Gráficos con Apache ECharts.
- **Backend**: FastAPI + Polars para todo el cómputo tabular. Sin base de datos obligatoria:
  el resultado de una corrida vive en memoria del proceso (`store.py`), con un espejo
  best-effort en Supabase si está configurado.
- **IA**: OpenAI, tool-calling + `response_format` JSON Schema estricto para forzar una
  respuesta estructurada. Ver sección 9.
- **Supabase**: opcional. Guarda runs, hallazgos y conversaciones para poder listarlos
  después. Si no está configurado, todo sigue funcionando con el store en memoria del backend.

---

## 3. Instalación

Requisitos: Python 3.11+, Node.js 20+, git.

```bash
git clone <url-del-repo>
cd nexo-ia
```

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate       |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

---

## 4. Variables de entorno

Copiar `.env.example` a `.env` (backend) y a `frontend/.env.local` (frontend), o setearlas
en el entorno / en el dashboard de Vercel.

| Variable | Dónde | Obligatoria | Descripción |
|---|---|---|---|
| `OPENAI_API_KEY` | backend | No | Si falta, la app cae a modo determinístico (ver criterio de aceptación #10). |
| `OPENAI_MODEL` | backend | No | Default `gpt-4o-mini`. |
| `SUPABASE_URL` / `SUPABASE_KEY` | backend | No | Service Role key. Si faltan, no se persiste historial entre reinicios del backend. |
| `NEXT_PUBLIC_API_URL` | frontend | Sí | URL del backend. Local: `http://localhost:8000`. |

**Nunca** poner la Supabase *anon key* ni la OpenAI key en el frontend — ambas son
exclusivamente del backend.

---

## 5. Ejecución local

**Backend** (desde `backend/`, con el venv activado):

```bash
uvicorn main:app --reload --port 8000
```

**Frontend** (desde `frontend/`, en otra terminal):

```bash
npm run dev
```

Abrir `http://localhost:3000`. Si no tenés un CSV a mano, el botón **"Cargar datos de demo"**
sube el dataset sintético de `sample-data/` automáticamente.

**Tests del backend:**

```bash
cd backend
pytest -q
```

---

## 6. Deploy

### Frontend → Vercel

1. Importar el repo en Vercel, con **Root Directory = `frontend`**.
2. Variable de entorno `NEXT_PUBLIC_API_URL` apuntando al backend ya desplegado.
3. Vercel detecta Next.js automáticamente (hay un `vercel.json` mínimo por explicitud).

### Backend → cualquier host de Python (Railway, Render, Fly.io, un VPS con Docker, etc.)

Vercel no corre procesos Python de larga duración con estado en memoria como este backend
necesita — por eso el backend se despliega aparte. Comando de arranque:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Configurar ahí las variables de entorno de la sección 4 (`OPENAI_API_KEY`, `SUPABASE_URL`,
`SUPABASE_KEY` si se usan) y habilitar CORS ya está resuelto en `main.py` (abierto, sin
credenciales — ver sección 10 de seguridad).

---

## 7. Supabase (opcional)

1. Crear un proyecto en [supabase.com](https://supabase.com).
2. Pegar el contenido de [`supabase/schema.sql`](supabase/schema.sql) en el SQL Editor y
   ejecutarlo. Crea las tablas `runs`, `conversaciones`, `anotaciones` con RLS restringido a
   la Service Role key.
3. Crear un bucket de Storage llamado `csv-uploads` (privado) desde el dashboard, para que
   `subir_csv()` pueda guardar una copia del archivo original de cada corrida.
4. Copiar la **Service Role key** (no la anon key) a `SUPABASE_KEY` en el backend.

Sin este paso, la app funciona igual: `supabase_client.py` detecta la ausencia de
credenciales y todas sus funciones se vuelven no-ops silenciosos.

---

## 8. El motor de 31 cruces

Sobre 5 dimensiones (`sucursal`, `familia`, `sector_industrial`, `asesor`, `abc_cliente`) hay
exactamente 2⁵ − 1 = **31** combinaciones posibles (5 de un nivel + 10 de dos + 10 de tres +
5 de cuatro + 1 de cinco). `core/combinations.py` las genera **todas**, sin excepción
(`generar_combinaciones_de_dimensiones`, testeado en `tests/test_combinations.py`), y para
cada una calcula el set completo de métricas — período reciente vs. comparativo, ticket,
posiciones por pedido, participación, contribución a la variación total, persistencia
semanal, volatilidad y una detección de anomalía contra las 8 semanas históricas.

Reglas duras del motor:

- **Los pedidos se cuentan siempre con `n_unique(pedido_id)`**, nunca contando filas — una
  misma orden puede tener varias filas si tiene líneas de distinta familia.
- **Se calculan las 31 combinaciones completas antes de filtrar nada.** El filtro de
  materialidad (`filtrar_material`) es el único filtro permitido, y se aplica *después*:
  descarta un cruce sólo si no tiene volumen de pedidos suficiente o no representa una
  porción relevante del negocio/de la variación — nunca antes de haberlo calculado.
- **Cache por corrida** (`calcular_todas_las_combinaciones_cacheado`, keyed por `run_id`) para
  no repetir el cómputo de los 31 cruces en cada request del copiloto.
- Sobre esos cruces, `core/patterns.py` clasifica el tipo de patrón (concentrado,
  generalizado, tendencia persistente, anomalía, segmento atípico, interacción profunda que
  sólo aparece al cruzar varias dimensiones) y calcula un **score** ponderando impacto
  absoluto, contribución, persistencia, volumen, profundidad del cruce, desvío respecto del
  comportamiento general, y penalizando volatilidad alta o pocos datos — así se eligen entre
  3 y 5 hallazgos para el Centro de hallazgos sin intervención de la IA.
- `core/metrics.decomponer_driver` hace una **descomposición exacta** (no aproximada) de
  cuánto de un cambio en USD se explica por cantidad de pedidos vs. posiciones por pedido vs.
  USD por posición, vía sustitución en cadena — la suma de los 3 términos da exactamente la
  diferencia total.

---

## 9. Cómo se controla a la IA

La IA (`ai/assistant.py`) nunca ve el CSV ni calcula nada. Recibe únicamente:

1. Un resumen del período ya calculado por Python.
2. Los 3-5 hallazgos de nivel 1-2 como punto de partida (no como conclusión final).
3. Cuatro **herramientas de sólo lectura** (`ai/tools.py`) sobre los 31 cruces ya calculados:
   `obtener_tabla_dimension`, `desglosar_variacion` (con filtros, para profundizar cruces),
   `detalle_cliente` (agregado por `cliente_id` — el dataset no tiene nombres de cliente) y
   `consultar_tendencia_historica` (serie semanal + comparación contra el histórico).

Su respuesta final es forzada a un **JSON Schema estricto** (`RESPUESTA_JSON_SCHEMA`, con
`response_format` de OpenAI) que exige los 7 componentes pedidos: qué ocurrió, qué
combinación de dimensiones lo explica, cuánto explica, qué métricas lo respaldan, cómo
evolucionó semana a semana, nivel de evidencia, y limitaciones.

Esa respuesta pasa por un **validador automático** (`ai/validator.py`) antes de mostrarse:

- Rechaza si el segmento citado **no corresponde a ningún cruce real** calculado por Python
  (la defensa central contra números inventados).
- Cruza cada métrica citada contra el valor real del cruce (con tolerancia del 5%) y rechaza
  si no coincide.
- Rechaza si `cuanto_explica` no trae ningún número verificable, o si la evolución semanal es
  demasiado corta para ser evidencia real.
- **Rechaza por profundidad insuficiente**: si existe un cruce más específico (una dimensión
  más) que contiene el mismo segmento citado, con contribución claramente mayor y volumen
  suficiente, y la IA no lo investigó, se pide que reintente.

Si la respuesta no pasa el validador, se reintenta una vez con el detalle de qué falló; si
sigue sin pasar, **o si no hay `OPENAI_API_KEY` configurada**, la app muestra el mejor
hallazgo calculado por Python en el mismo formato (sin ningún texto generado por IA) — la app
nunca falla por falta de IA.

Los gráficos siguen la misma lógica: la IA sólo devuelve una *solicitud* estructurada
(`chart_type`, `metric`, `group_by`, `filters`, `comparison`, `title`, máximo 2 por
respuesta). `core/charts.py` la valida y calcula los datos reales desde los DataFrames — la
IA nunca genera un valor de gráfico.

---

## 10. Seguridad y privacidad

- No hay claves en el repo; `.env.example` documenta lo que hace falta.
- El backend valida tipo y tamaño de archivo antes de procesar cualquier CSV
  (`core/loader.py`, límite 25 MB, sólo `.csv`).
- **A la IA nunca se le manda el CSV completo** — sólo resúmenes agregados y los resultados
  de sus propias tool calls (ver sección 9).
- El dataset no tiene nombres de cliente en su esquema (sólo `cliente_id`); ese id sólo se
  usa para métricas agregadas, nunca para identificar a nadie.
- CORS del backend está abierto (`allow_origins=["*"]`) a propósito: es un MVP académico sin
  autenticación ni cookies de sesión, así que no hay credenciales cruzando origen que proteger.
  Si esto se pone en producción real con datos sensibles, restringir `allow_origins` al
  dominio del frontend.
- Sin autenticación de usuarios en este MVP (a propósito, ver sección 11).

---

## 11. Limitaciones conocidas

- **Sin autenticación.** Cualquiera con la URL puede subir un archivo o leer runs.
  Aceptable para una entrega académica; no para producción con datos reales de clientes.
- **Store de corridas en memoria de un solo proceso** (`store.py`). Si el backend se
  reinicia, el copiloto de una corrida vieja deja de poder responder preguntas nuevas
  (hay que volver a subir el archivo) — Supabase guarda un espejo de los resultados
  agregados y hallazgos, pero no los DataFrames completos.
- **La IA es no determinística.** Dos corridas de la misma pregunta sobre el mismo dataset
  pueden citar segmentos distintos (ambos válidos y respaldados) porque el modelo elige qué
  investigar primero. El validador garantiza que lo que sea que responda esté respaldado por
  datos reales, no que siempre sea *la misma* respuesta.
- **Validación cruzada de cifras con tolerancia del 5%**, no exacta — deja pasar redondeos de
  la IA al parafrasear un número, no cualquier invención.
- **Pedidos/Ofertas vs. Facturas**: este proyecto asume que el CSV ya viene con una sola
  granularidad de documento (pedidos). No mezcla tipos de documento como sí hace el mart de
  origen — si se reutiliza este motor sobre datos reales de un mart más amplio, hay que
  filtrar antes a un tipo de documento consistente.
- **Sin capturas de pantalla incluidas en este repo.** El flujo completo (demo → dashboard →
  hallazgos → copiloto con gráficos) se verificó funcionando de punta a punta en un browser
  real durante el desarrollo, pero no se generó un archivo de imagen para adjuntar acá —
  correr la app localmente (sección 5) para verla.

---

## 12. Datos sintéticos

`sample-data/generar_datos_sinteticos.py` genera `sample-data/pedidos_demo.csv`: 16 semanas,
~3.200 pedidos, con un patrón embebido a propósito para que el motor tenga algo real que
encontrar en el modo demo — una caída jerárquica y persistente en
`CAPITAL × CAÑOS Y TUBOS × CONSTRUCCION` (más fuerte todavía dentro de `ASESOR_3 × clase A`),
más una compensación parcial en `ROSARIO × PERFILES`. El resto de los datos tiene ruido
aleatorio realista (con semilla fija, reproducible), así que no todos los hallazgos que
aparecen van a ser ese patrón embebido — es a propósito: el motor tiene que priorizar entre
señal real y ruido, no mostrar un único caso de laboratorio perfecto.

Para regenerarlo: `python sample-data/generar_datos_sinteticos.py`.

---

## 13. Estructura del repo

```
nexo-ia/
├── frontend/            Next.js + TypeScript + Tailwind + ECharts
│   ├── app/              layout, page principal, estilos globales
│   ├── components/       ui/ (primitivos), dashboard/, copilot/, charts/
│   ├── lib/               cliente de API, utils de formato, tema de gráficos
│   └── types/             contratos TS espejo de los modelos del backend
├── backend/
│   ├── main.py            endpoints FastAPI
│   ├── config.py           columnas, dimensiones, umbrales — nada hardcodeado en otro lado
│   ├── store.py             estado en memoria por corrida
│   ├── supabase_client.py    persistencia best-effort
│   ├── core/                loader, validator, periods, metrics, combinations, patterns,
│   │                         evidence, charts
│   ├── ai/                   assistant, tools, prompts, validator
│   └── tests/                 53 tests, pytest
├── supabase/schema.sql
├── sample-data/
├── .env.example
└── README.md
```

---

## 14. Criterios de aceptación — estado

- [x] Cargar un CSV real y uno sintético (demo).
- [x] Validación completa (columnas, tipos, fechas, faltantes, duplicados, semanas, ABC).
- [x] Las 31 combinaciones se calculan siempre, sin excepción, antes de filtrar.
- [x] Hallazgos priorizados (3-5) con score, tipo de patrón y nivel de evidencia.
- [x] La IA responde con evidencia verificable o cae a modo determinístico — nunca inventa.
- [x] Cada conclusión de la IA puede traer hasta 2 gráficos, calculados por Python.
- [x] Dashboard compacto, denso, oscuro, verificado en un browser real.
- [x] Modo demo con datos sintéticos.
- [x] `pytest -q` → 53/53 verde.
- [x] La app no falla sin `OPENAI_API_KEY` configurada (modo determinístico probado).
