# Estructura de la presentación

Referencia rápida de las 10 diapositivas. El archivo real, con diseño y notas para el
expositor, es [`presentacion_nexo_ia.pptx`](presentacion_nexo_ia.pptx) /
[`.pdf`](presentacion_nexo_ia.pdf). Audiencia: profesores de Ingeniería.

---

### 1. Portada
Nexo IA — Asistente inteligente para análisis comercial. *"Python calcula. La inteligencia
artificial interpreta."* Datos de alumno/padrón/materia/año (completar antes de exponer) y
stack principal.

### 2. Problema que resuelve
Un dashboard tradicional muestra que un indicador cambió; encontrar qué combinación de
dimensiones lo explica requiere consultas manuales. Contraste: *"Los pedidos disminuyeron"*
(dashboard tradicional) vs. una conclusión con el segmento exacto (Nexo IA).

### 3. Solución propuesta
Flujo de 6 pasos: CSV → Validación → Motor Python → Detección de patrones → IA → Conclusión y
gráficos. La IA no recibe la base completa ni calcula valores por su cuenta.

### 4. Lógica del motor Python — *prioritaria*
16 semanas divididas en 3 ventanas (8 histórico / 4 comparativo / 4 reciente). 12 métricas
calculadas por cruce. Los pedidos se cuentan por `pedido_id` único, no por fila del CSV.

### 5. Análisis multivariable — *prioritaria*
5 dimensiones × 31 combinaciones (5+10+10+5+1). Se calculan todas antes de filtrar; sólo se
muestran las que tienen impacto, volumen, persistencia, contribución y evidencia suficientes.

### 6. Rol de la inteligencia artificial — *prioritaria*
Dos columnas: qué hace Python (calcula, agrupa, compara, filtra, puntúa, prepara gráficos) vs.
qué hace la IA (investiga, compara explicaciones, redacta, explica evidencia, elige
visualización). Reglas de seguridad: no inventa cifras, no calcula sobre texto, no accede al
CSV completo, no afirma causalidad sin evidencia, indica cuando no hay causa dominante.

### 7. Respuestas verificables mediante gráficos — *prioritaria*
Ejemplo real (verificado contra el motor, dataset de demo): Sucursal Norte × Familia Alfa,
USD 27.161 → 10.600 (-61%). La IA pide tipo de gráfico y filtros; Python recalcula los valores
representados — texto y gráfico nunca se contradicen.

### 8. Aplicación y experiencia de usuario
Captura real de la interfaz (insertar antes de exponer). Señalar: carga de CSV, validación,
indicadores, evolución semanal, hallazgos priorizados, copiloto, gráficos contextuales.

### 9. Arquitectura y herramientas
Frontend (Next.js, TypeScript, Tailwind, componentes propios estilo shadcn/ui, ECharts) ·
Backend (Python, FastAPI, Polars) · Datos opcionales (Supabase) · IA (OpenAI, tool calling,
JSON Schema) · Infraestructura (Vercel, Render, GitHub). Por qué cada una, no sólo qué es.

### 10. Resultado, limitaciones y conclusión
Resultado (aplicación funcional, 59 tests en verde, desplegada) · Limitaciones honestas
(depende de la calidad del CSV, identifica relaciones matemáticas no causas comerciales,
requiere validación humana) · Conclusión: combina la exactitud de Python con la capacidad
interpretativa de la IA, con trazabilidad sobre cada conclusión.
