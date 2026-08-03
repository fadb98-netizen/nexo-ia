# Estructura de la presentación

8 diapositivas, sin texto denso — cada una apoyada en una captura o diagrama.

---

### 1. Problema
- **Título:** Los totales esconden la causa real
- **Mensaje principal:** una variación agregada puede estar concentrada en un cruce muy
  específico de dimensiones, invisible al mirar el dato de forma agregada.
- **Contenido mínimo:** un ejemplo numérico corto (ej. "ventas -12%, pero -60% en una sola
  combinación sucursal × familia").
- **Visual sugerido:** captura del KPI de USD del dashboard junto a un hallazgo concentrado del
  Centro de Hallazgos.

### 2. Objetivo del proyecto
- **Título:** Investigar variaciones comerciales sin SQL
- **Mensaje principal:** construir un asistente que calcule evidencia real y la explique en
  lenguaje natural, sin que la IA invente cifras.
- **Contenido mínimo:** 2-3 bullets de objetivo (detectar, explicar, visualizar).
- **Visual sugerido:** ninguno, o el logo/nombre del proyecto.

### 3. Solución desarrollada
- **Título:** Nexo IA
- **Mensaje principal:** sube un CSV, calcula 31 combinaciones posibles entre 5 dimensiones, y
  permite preguntarle al copiloto qué pasó.
- **Contenido mínimo:** las 5 dimensiones (sucursal, familia, sector, asesor, clase de cliente)
  y la cifra de 31 combinaciones.
- **Visual sugerido:** captura del dashboard completo (KPIs + hallazgos + copiloto).

### 4. Cómo funciona
- **Título:** Python calcula, la IA interpreta
- **Mensaje principal:** separación estricta entre cómputo (determinístico) e interpretación
  (IA), con validación automática antes de mostrar cualquier respuesta.
- **Contenido mínimo:** flujo de 4 pasos (subir → calcular → investigar con IA → validar).
- **Visual sugerido:** diagrama simple de flujo (puede ser el mismo del README).

### 5. Arquitectura y tecnologías
- **Título:** Stack
- **Mensaje principal:** frontend y backend separados, IA como capa final con herramientas de
  solo lectura.
- **Contenido mínimo:** Next.js/TypeScript, FastAPI/Polars, OpenAI (tool-calling), Supabase
  opcional.
- **Visual sugerido:** diagrama de arquitectura de `docs/DECISIONES_DEL_PROYECTO.md`.

### 6. Ejemplos de uso
- **Título:** En acción
- **Mensaje principal:** mostrar una pregunta real, su respuesta con evidencia citada, y el
  gráfico generado.
- **Contenido mínimo:** una captura de pregunta + respuesta, una captura de un gráfico (línea o
  ranking).
- **Visual sugerido:** 2 capturas del copiloto respondiendo.

### 7. Decisiones y desafíos
- **Título:** Cómo se evita que la IA invente
- **Mensaje principal:** cada cifra citada se contrasta contra el dato real antes de mostrarse;
  si no coincide, se rechaza y se reintenta.
- **Contenido mínimo:** 2-3 decisiones clave (JSON Schema estricto, validador determinístico,
  fallback sin IA).
- **Visual sugerido:** ninguno, o un esquema simple "IA → validador → respuesta / reintento".

### 8. Resultados, limitaciones y próximos pasos
- **Título:** Estado actual
- **Mensaje principal:** funciona de punta a punta, con limitaciones conocidas y honestas.
- **Contenido mínimo:** 2-3 logros (tests en verde, deploy funcionando, fallback robusto) + 2-3
  limitaciones (sin autenticación, historial acotado, depende de la calidad del CSV) + 1-2
  próximos pasos (autenticación, persistencia completa de corridas).
- **Visual sugerido:** ninguno, slide de cierre.
