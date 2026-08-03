# Estructura de la presentación

8 diapositivas centradas en el proceso de construcción, la lógica del sistema y por qué se
eligió cada herramienta — no un pitch de producto genérico.

---

### 1. Problema
- **Título:** Los totales esconden la causa real
- **Mensaje principal:** una variación agregada puede estar concentrada en un cruce muy
  específico de dimensiones, invisible al mirar el dato de forma agregada.
- **Contenido mínimo:** un ejemplo numérico corto (ej. "ventas -12%, pero -61% en una sola
  combinación sucursal × familia").
- **Visual sugerido:** captura del KPI de USD del dashboard junto a un hallazgo concentrado del
  Centro de Hallazgos.

### 2. La lógica del sistema
- **Título:** Python calcula, la IA interpreta
- **Mensaje principal:** el sistema separa estrictamente el cómputo (siempre determinístico) de
  la interpretación en lenguaje natural (IA) — la IA nunca calcula ni inventa una cifra.
- **Contenido mínimo:** flujo de 5 pasos (subir CSV → validar → calcular 31 cruces → IA investiga
  con herramientas → validador contrasta cada cifra antes de mostrar la respuesta).
- **Visual sugerido:** diagrama de flujo (el mismo del README/decisiones).

### 3. Cómo se construyó
- **Título:** El orden importó
- **Mensaje principal:** primero se construyó el motor determinístico completo (validación, 31
  cruces, hallazgos priorizados) sin ninguna IA — así la app ya era útil y nunca dependió de que
  la IA funcionara. La capa de IA se agregó encima, como intérprete, no como motor.
- **Contenido mínimo:** 3 etapas (motor determinístico → capa de IA con tool-calling → validador
  anti-invención) presentadas en orden.
- **Visual sugerido:** línea de tiempo simple de 3 pasos.

### 4. Herramientas utilizadas y por qué
- **Título:** Por qué cada pieza
- **Mensaje principal:** cada tecnología se eligió para resolver una restricción concreta del
  proyecto, no por default.
- **Contenido mínimo:** tabla con 4-5 filas (Polars, FastAPI, OpenAI tool-calling + JSON Schema,
  Next.js/TypeScript, ECharts) — para qué se usa y por qué esa y no otra.
- **Visual sugerido:** la tabla de herramientas de `docs/DECISIONES_DEL_PROYECTO.md`.

### 5. Desafíos reales durante el desarrollo
- **Título:** Lo que se rompió y cómo se encontró
- **Mensaje principal:** varios bugs reales aparecieron recién al probar con datos reales o en
  producción, no en el diseño en papel.
- **Contenido mínimo:** 2-3 ejemplos concretos (ej. un validador que colapsaba comparaciones de
  varios valores en un solo cruce; la IA inventando valores de filtro inexistentes) y cómo se
  detectaron y corrigieron.
- **Visual sugerido:** ninguno, o un extracto corto de log/mensaje de error real.

### 6. Cómo se evita que la IA invente
- **Título:** El validador, no el prompt, es la garantía
- **Mensaje principal:** pedirle "no inventes" a un modelo no alcanza — la garantía real es un
  validador de código que contrasta cada cifra citada contra el dato calculado por Python.
- **Contenido mínimo:** 2-3 mecanismos (JSON Schema estricto, contraste numérico con tolerancia
  del 5%, prohibición de inventar valores de filtro, fallback determinístico sin IA).
- **Visual sugerido:** esquema simple "IA → validador → respuesta / reintento".

### 7. Arquitectura y stack
- **Título:** Dos capas separadas, un solo contrato
- **Mensaje principal:** frontend y backend desacoplados; dentro del backend, el cómputo y la
  interpretación por IA viven en módulos separados y auditables.
- **Contenido mínimo:** diagrama de arquitectura + lista de tecnologías por capa.
- **Visual sugerido:** diagrama de `docs/DECISIONES_DEL_PROYECTO.md`.

### 8. Resultados y estado actual
- **Título:** Estado actual
- **Mensaje principal:** funciona de punta a punta, con limitaciones conocidas y honestas.
- **Contenido mínimo:** 2-3 logros (tests en verde, deploy funcionando, fallback robusto) + 2-3
  limitaciones (sin autenticación, historial acotado, depende de la calidad del CSV).
- **Visual sugerido:** ninguno, slide de cierre.
