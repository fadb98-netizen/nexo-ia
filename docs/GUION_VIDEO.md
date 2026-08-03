# Guion del video explicativo

Duración objetivo: **3:30 - 5:00 min**. Grabar en pantalla completa del navegador, con el
proyecto ya corriendo (local o el link de producción).

---

**0:00 – 0:30 | El problema**
Hablar a cámara o en voz en off, sin pantalla del producto todavía (o con el dashboard vacío de
fondo).
> "Cuando las ventas caen, el total no dice por qué. La causa real suele estar escondida en un
> cruce puntual — una sucursal, con una familia de producto, en un sector específico — invisible
> si sólo se mira el agregado. Cruzar eso a mano en una planilla es lento y depende de quién
> pregunte."

**0:30 – 1:00 | Para qué sirve Nexo IA**
Pantalla: landing de carga de CSV.
> "Nexo IA es un asistente que sube un CSV de pedidos, calcula todas las combinaciones posibles
> entre 5 dimensiones comerciales, y permite preguntarle en lenguaje natural qué pasó — con
> evidencia real detrás de cada respuesta, nunca inventada."

**1:00 – 1:40 | Recorrido rápido de la interfaz**
Acción: click en "Cargar datos de demo" (o subir `data/datos_demo.csv`). Mostrar el dashboard
resultante.
- Señalar los 4 KPIs superiores (USD, pedidos, clientes, posiciones por pedido).
- Señalar el Centro de Hallazgos (3-5 patrones priorizados automáticamente).
- Señalar el heatmap configurable.
> "Todo esto lo calculó Python al momento de subir el archivo — sin ninguna IA todavía."

**1:40 – 3:10 | 3-4 preguntas representativas**
Abrir la pestaña "Preguntar" del copiloto. Escribir y esperar la respuesta de cada una (dejar
que se vea el badge "Investigado por IA" y las métricas citadas):

1. *"¿Qué explica la caída del último mes?"* — mostrar que cita un segmento y cifras concretas.
2. *"Compará ventas entre sucursales"* — mostrar el ranking con varias sucursales.
3. *"Mostrame la evolución semanal de ventas"* — mostrar que dispara un gráfico de línea.

**3:10 – 3:40 | Pregunta de seguimiento**
Sin cambiar de tema, escribir algo que dependa de la respuesta anterior, por ejemplo:
*"¿Y esa sucursal en qué familia cayó más?"*
> "El asistente recuerda de qué se venía hablando — no hay que repetir el contexto."

**3:40 – 4:00 | Ejemplo de gráfico**
Hacer zoom o señalar el gráfico generado en la respuesta anterior (línea o barras).
> "El gráfico no lo genera la IA: sólo pide el tipo y el filtro, y Python calcula los valores
> reales — así el gráfico y el texto nunca se contradicen."

**4:00 – 4:30 | Arquitectura, muy breve**
Se puede mostrar el diagrama del README o simplemente hablar en voz en off.
> "Frontend en Next.js, backend en FastAPI con Polars para todo el cálculo. La IA sólo entra al
> final, con herramientas de solo lectura, y cada respuesta se valida automáticamente contra los
> datos reales antes de mostrarse. Si algo falla, el sistema muestra el mejor hallazgo calculado
> por Python — nunca se rompe."

**4:30 – 5:00 | Cierre: beneficios y límites**
> "Con esto, cualquiera puede investigar una variación comercial sin saber SQL ni armar tablas
> dinámicas, con la garantía de que cada número que ve es real. Como limitación honesta: la
> calidad del análisis depende de la calidad del CSV cargado, y el modelo a veces necesita un
> reintento interno para citar un dato con el formato exacto — el sistema lo maneja solo, pero
> agrega algo de latencia."

---

### Notas de grabación
- Si una respuesta de la IA tarda (reintento interno), no cortar — es parte real del flujo y
  vale la pena mostrarlo funcionando.
- Usar `data/datos_demo.csv` o el botón de demo: tiene una caída marcada y una combinación sin
  datos en el período reciente, ideal para que las respuestas del punto 1:40 salgan concretas.
- No hace falta guion palabra por palabra: estas son ideas por bloque, con tiempos orientativos.
