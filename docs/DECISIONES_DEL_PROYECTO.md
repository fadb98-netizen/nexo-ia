# Decisiones del proyecto

*Lectura estimada: 4 minutos.*

## Problema

Las herramientas de BI tradicionales muestran totales y permiten filtrar, pero no investigan
por sí solas: alguien tiene que saber de antemano qué cruce de dimensiones mirar. En una base
de pedidos con 5 dimensiones comerciales (sucursal, familia, sector, asesor, clase de cliente),
la causa real de una variación puede estar escondida en cualquiera de las 31 combinaciones
posibles entre ellas — y mirar sólo el total, o sólo una dimensión a la vez, deja pasar
patrones que sólo aparecen al cruzar varias.

## Solución

**Cómo funciona:** se sube un CSV de pedidos; Python calcula las 31 combinaciones completas
(nunca filtra antes de calcular) y prioriza entre 3 y 5 hallazgos con un score determinístico.
La IA entra recién ahí, para *interpretar* esos resultados en lenguaje natural.

- **Interpreta la pregunta** distinguiendo si es descriptiva (evolución del total), explicativa
  (qué causó una variación) o de comparación/ranking entre categorías — cada tipo dispara una
  estrategia de investigación distinta.
- **Consulta los datos** exclusivamente a través de 5 herramientas de solo lectura
  (`ai/tools.py`) sobre los cruces ya calculados: ranking por dimensión, desglose de una
  combinación, resumen del total, detalle de un cliente y tendencia histórica de un cruce
  puntual. Nunca recibe el CSV completo.
- **Decide qué gráfico mostrar** según la intención: evolución/tendencia → línea; comparación
  entre categorías → barras o ranking; composición → participación; cruce de dos dimensiones →
  heatmap. Un valor puntual no genera gráfico, se cita como número.
- **Mantiene contexto** de conversación (últimos 4 intercambios reales, no resúmenes) para que
  preguntas de seguimiento ("¿y esa sucursal, en qué familia cayó más?") se entiendan sin
  repetir todo. El contexto de un hallazgo o gráfico seleccionado con "Investigar" se usa una
  sola vez y se limpia solo, para no contaminar la siguiente pregunta si no tiene relación.
- **Evita inventar** de dos formas: nunca puede pasar como filtro un valor de dimensión que no
  haya visto antes en el resultado de una herramienta (si no lo conoce, tiene que consultarlo
  primero); y toda cifra que cite en la respuesta final se contrasta automáticamente contra el
  cruce real correspondiente antes de mostrarse — si no coincide, se rechaza y se reintenta.
- **Cuando no hay datos suficientes** (una combinación sin filas en el período, una sucursal que
  no existe) lo dice explícitamente en vez de aproximar o inventar, y baja el nivel de evidencia
  declarado en la respuesta.

## Decisiones tomadas

- **Python calcula, la IA interpreta** — regla no negociable. Evita el riesgo central de un
  asistente de datos con LLM: que un número "suene bien" sin ser real.
- **Modelo de IA:** OpenAI con tool-calling y `response_format` de JSON Schema estricto, para
  forzar una respuesta con una forma exacta y verificable, no texto libre.
- **Tool calls en vez de mandarle todo el dataset al prompt:** con 5 dimensiones y miles de
  filas no entra en contexto, y tampoco es necesario — el modelo sólo necesita pedir lo que va
  a usar, de forma trazable (queda registrado qué consultó).
- **Validación determinística después de la IA:** un LLM puede parafrasear mal un número aunque
  haya usado la herramienta correcta; un validador de código (no otro LLM) es la única forma de
  garantizar que lo que se muestra es exactamente lo que Python calculó.
- **Separación frontend / backend / prompts / herramientas / validador:** cada capa se puede
  auditar y testear sola. En particular, las reglas de "qué puede y no puede hacer la IA" viven
  todas en `ai/prompts.py`, en un solo lugar.
- **Elección de gráfico por intención, no por default:** mostrar siempre el mismo tipo de
  gráfico (o dejar que el modelo elija sin guía) llevaba a usar barras o tablas para preguntas
  de evolución temporal, que se entienden mejor con una línea.
- **Historial acotado a 4 intercambios:** suficiente para preguntas de seguimiento naturales,
  sin inflar cada consulta a la IA con toda la conversación (costo y latencia).
- **Fallback determinístico ante cualquier falla:** si no hay clave de OpenAI, si la IA no logra
  una respuesta válida tras reintentar, o si la API falla, se muestra el mejor hallazgo ya
  calculado por Python, en el mismo formato — la aplicación nunca se rompe ni queda en blanco
  por un problema de la IA.

## Herramientas utilizadas

| Tecnología | Para qué se usa | Por qué se eligió | Ventaja principal acá |
|---|---|---|---|
| **Polars** | Todo el cómputo tabular (validación, 31 cruces, métricas) | DataFrame moderno, más rápido que pandas en agregaciones repetidas | Calcular 31 combinaciones sobre miles de filas sin que sea el cuello de botella |
| **FastAPI** | API del backend | Tipado con Pydantic, async nativo, documentación automática | Contratos claros entre frontend y backend, validación de requests gratis |
| **OpenAI (tool-calling + JSON Schema)** | Interpretación en lenguaje natural | Soporte maduro de `response_format` estricto, necesario para forzar la forma de la respuesta | La salida de la IA es siempre parseable y verificable, nunca texto libre |
| **Next.js + TypeScript** | Frontend | App Router, tipado compartido con el backend vía contratos TS | Menos bugs de "el backend cambió un campo y el frontend no se enteró" |
| **Apache ECharts** | Gráficos | Soporta todos los tipos que necesita el copiloto (línea, barras divergentes, heatmap, participación) con un único componente | Un solo renderer para toda la variedad de gráficos que pide la IA |
| **Supabase (opcional)** | Persistir historial de corridas | Postgres + Storage gestionado, con modo "no-op" fácil de dejar sin configurar | El proyecto funciona igual sin él — no es una dependencia dura |

## Limitaciones

- El modelo (LLM) puede necesitar 1-2 reintentos para citar un cruce o formato de número
  correctamente; el validador lo detecta y fuerza la corrección, a costa de latencia extra.
- La calidad del análisis depende directamente de la calidad del CSV cargado — columnas mal
  tipadas o con pocas semanas de datos producen hallazgos de evidencia "baja".
- El historial de conversación está acotado a 4 intercambios: una pregunta que dependa de algo
  dicho mucho antes en una conversación larga puede perder ese contexto.
- El store de una corrida vive en memoria del proceso backend; si se reinicia, hay que volver a
  subir el CSV para seguir conversando sobre él (Supabase guarda un espejo agregado, no los
  DataFrames completos).
- Sin autenticación de usuarios — aceptable para una entrega académica, no para producción con
  datos reales de clientes.
