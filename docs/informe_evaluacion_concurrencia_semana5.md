# CommunityLab — Informe de evaluación experimental de concurrencia (Semana 5)

**Equipo:** Hackathon ONE G10 · Equipo 39  
**Componente:** Data Science — Cerebro de IA  
**Fecha de consolidación:** 21 de octubre de 2026  
**Rama evaluada:** `feature/DS-Semana5-Concurrencia-Experimental`  
**Commit de referencia:** `37da26cdea00d8afe656070e8538a621fbf5e8aa`  
**Estado:** evaluación inicial completada; **no aprobada aún para integración en la rama estable**.

## 1. Objetivo

Evaluar si habilitar concurrencia de **dos lotes de análisis** y **dos mensajes de generación** reduce el tiempo de ejecución del pipeline de CommunityLab, sin perder interacciones, activos ni consistencia de las clasificaciones observadas. Se compara la configuración secuencial `1 × 1` con la experimental `2 × 2` mediante auditorías del flujo completo.

Este documento presenta **evidencia de ejecución y regresión**, no una medición de exactitud frente a etiquetas validadas por personas.

## 2. Alcance y configuración

| Elemento | Configuración observada |
|---|---|
| Entrada | `src/datos/mensajes_comunidad_simulados.json` |
| Interacciones de entrada | 23 |
| Fecha de referencia utilizada por Data | `2026-09-17T12:00:00Z` |
| Comando base | `python -m scripts.generar_auditoria_semana4` |
| Proveedor primario de análisis y generación | NVIDIA NIM |
| Proveedor alternativo por fallback | Gemini |
| Modelo estándar — análisis individual y por lotes | `nvidia/nemotron-3.5-super-vl-120b-a12b` |
| Modelo rápido — FAQ y boletín | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| Modelo de razonamiento — LinkedIn, caso de éxito e insight de mejora | `nvidia/nemotron-3.5-super-vl-120b-a12b` |
| Gemini de respaldo | `gemini-3.5-flash-lite` |
| Concurrencia base | `COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS=1`, `COMMUNITYLAB_CONCURRENCIA_MENSAJES=1` |
| Concurrencia experimental | `COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS=2`, `COMMUNITYLAB_CONCURRENCIA_MENSAJES=2` |
| Salida | Paquete JSON de auditoría de Semana 4, con la misma estructura en ambos modos |

En las comprobaciones realizadas, las auditorías comparadas presentaron **el mismo hash del dataset**, los mismos IDs y la misma configuración de modelos. Los límites de concurrencia se aplicaron como variables de entorno a cada proceso.

**Control de cambios:** las dos corridas `1 × 1` se realizaron antes de los ajustes locales al prompt de preguntas frecuentes. Las dos corridas `2 × 2` se ejecutaron después de parte de esos ajustes; el repositorio registró `working_tree_limpio: false`. Esta diferencia **impide tratar la comparación como un benchmark estrictamente controlado**, aunque los modelos, el dataset y el formato de auditoría coincidieran.

## 3. Resultados de rendimiento

Los tiempos corresponden al **tiempo total de ejecución medido externamente**, incluida la inicialización del proceso y la operación del flujo; no equivalen a latencia individual de cada llamada LLM.

| Corrida | Configuración | Tiempo total | Resultados DS | Activos | Errores finales | Fallback de análisis | Fallback de generación |
|---|---|---:|---:|---:|---:|---|---|
| 1 | `1 × 1` | 181.90 s | 23 | 35 | 0 | 0 eventos / 0 interacciones | 1 evento / 1 activo |
| 2 | `1 × 1` | 193.62 s | 23 | 35 | 0 | 1 evento / 10 interacciones | 1 evento / 1 activo |
| 1 | `2 × 2` | 79.24 s | 23 | 35 | 0 | 0 eventos / 0 interacciones | 0 eventos / 0 activos |
| 2 | `2 × 2` | 101.42 s | 23 | 35 | 0 | 0 eventos / 0 interacciones | 0 eventos / 0 activos |

### 3.1. Comparación agregada

| Métrica | `1 × 1` | `2 × 2` |
|---|---:|---:|
| Ejecuciones | 2 | 2 |
| Tiempo medio | **187.76 s** | **90.33 s** |
| Mejor tiempo observado | 181.90 s | 79.24 s |
| Mayor tiempo observado | 193.62 s | 101.42 s |
| Resultados DS por corrida | 23 | 23 |
| Activos por corrida | 35 | 35 |
| Eventos totales de fallback en las dos corridas | 3 | 0 |
| Inconsistencias de auditoría | 0 | 0 |

**Reducción del tiempo medio observada:**

`(187.76 - 90.33) / 187.76 × 100 = 51.89 %` (aproximadamente **51.9 %**).

**Aceleración observada:** `187.76 / 90.33 = 2.08×`.

La muestra es pequeña (**dos ejecuciones por modo**) y la configuración tuvo diferencias de versión del prompt y ocurrencia de fallback. Estas cifras describen **las corridas medidas**, no una promesa de rendimiento productivo.

## 4. Integridad del procesamiento

Las cuatro auditorías finalizaron con **código de salida `0`**, produjeron **23 resultados DS** y **35 activos**, sin errores finales ni inconsistencias reportadas. La distribución de activos fue idéntica:

| Ruta | Activos por corrida |
|---|---:|
| `caso_exito` | 8 |
| `boletin` | 8 |
| `linkedin` | 8 |
| `preguntas_frecuentes` | 9 |
| `insight_mejora` | 2 |
| **Total** | **35** |

La validación automatizada sobre los JSON comprobó:

- Igualdad de hash del dataset, configuración de IA, conjunto de IDs y estructura raíz del JSON para `1 × 1` corrida 1 frente a `2 × 2` corrida 1.
- Igualdad de hash, configuración e IDs entre ambas corridas `2 × 2`.
- Ausencia de diferencias en **`sentimiento`**, **`tipo_detectado`** y **`tema_principal`** entre las dos corridas concurrentes; tampoco hubo diferencias en esos tres campos entre `1 × 1` corrida 1 y `2 × 2` corrida 1.

Esta comprobación **no valida automáticamente `subtema`, fidelidad semántica de los activos ni calidad editorial**.

## 5. Resiliencia y fallback de proveedor

En las ejecuciones secuenciales se observaron fallos transitorios resueltos mediante el proveedor alternativo:

| Corrida | Etapa | Caso(s) afectados | Motivo registrado | Resolución |
|---|---|---|---|---|
| `1 × 1` — 1 | Generación LinkedIn | `int-012` | `http_500` | Fallback a Gemini |
| `1 × 1` — 2 | Generación caso de éxito | `int-001` | `http_500` | Fallback a Gemini |
| `1 × 1` — 2 | Análisis de un lote | `int-011` a `int-020` | `timeout` | Un evento de fallback a Gemini afectó a 10 interacciones |

No se registraron eventos de fallback en las dos corridas `2 × 2`. El flujo completó las cuatro auditorías sin errores finales.

**Interpretación:** los resultados respaldan que el **fallback de proveedor** permitió completar operaciones afectadas por HTTP 500 y timeout. No debe confundirse con los **reintentos dentro de una solicitud** ni con la **recuperación posterior** de resultados fallidos. La evidencia presentada no cuantifica por separado la participación de estos dos últimos mecanismos.

La ausencia de fallback con `2 × 2` en dos ejecuciones no demuestra que mayor concurrencia reduzca los fallos de NVIDIA: la disponibilidad, las cuotas y la latencia del proveedor pueden variar entre momentos.

## 6. Consistencia y calidad del contenido

### 6.1. Clasificaciones

Entre las dos corridas secuenciales (`1 × 1`) se observaron:

- **1 diferencia de sentimiento:** `int-012`, `muy_positivo` con NVIDIA frente a `positivo` con Gemini.
- **1 diferencia de tema principal:** `int-019`, `programacion` con NVIDIA frente a `aprendizaje` con Gemini.
- **0 diferencias en tipo detectado**.

En las dos corridas `2 × 2` **no hubo diferencias** en esos tres campos. Esta es una medida de **consistencia entre ejecuciones**, no de precisión contra un ground truth humano.

### 6.2. Revisión de activos

El contraste de contenido entre las corridas concurrentes identificó, entre otros, estos ejemplos:

- **FAQ `int-023`:** similitud textual del **69.5 %**. Ambas versiones explican el enrutamiento condicional y mencionan reintentos, pero **no entregan el ejemplo práctico de router solicitado**. Se trata de un problema de utilidad de la generación que permanece pendiente.
- **Boletín `int-012`:** similitud textual del **87.4 %**. Las dos versiones conservan los hechos principales: cambio de carrera a los 35 años y trabajo en análisis de datos en una fintech; varía la redacción del titular.

Los porcentajes de similitud textual permiten **seleccionar ejemplos para revisión**, pero no son una puntuación de calidad o exactitud semántica. No se dispone aquí de una evaluación humana exhaustiva de los 35 activos.

## 7. Evidencias y rutas locales

Los siguientes archivos fueron generados durante las pruebas y están en el entorno local del experimento; **no se afirma que estén versionados en Git**:

| Ejecución | Archivo JSON |
|---|---|
| `1 × 1`, corrida 1 | `salida/experimentos/nvidia_nim_oct2026/corrida_01.json` |
| `1 × 1`, corrida 2 | `salida/experimentos/nvidia_nim_oct2026/corrida_02.json` |
| `2 × 2`, corrida 1 | `salida/experimentos/nvidia_nim_oct2026/concurrencia_2x2_01.json` |
| `2 × 2`, corrida 2 | `salida/experimentos/nvidia_nim_oct2026/concurrencia_2x2_02.json` |

El sistema registra eventos de observabilidad en `salida/logs/ciencia_datos.jsonl`, correlacionados por `id_ejecucion`.

Para las corridas concurrentes se utilizó `scripts/generar_auditoria_semana4.py` con las variables de entorno de concurrencia fijadas en `2`, `--fecha-referencia "2026-09-17T12:00:00Z"`, un destino JSON único por corrida y `--permitir-working-tree-sucio`. Esta última opción permitió ensayar los cambios locales, pero **no debe emplearse como sustituto de una revisión reproducible sobre un commit limpio**.

## 8. Limitaciones del experimento

1. **Tamaño muestral reducido:** solo dos mediciones por modo; no permite establecer intervalos de confianza útiles ni comportamiento bajo carga prolongada.
2. **Condiciones no idénticas:** el prompt de FAQ se modificó localmente entre los grupos `1 × 1` y `2 × 2`.
3. **Fallback desigual:** los tiempos de `1 × 1` incluyen tres eventos de fallback entre las dos ejecuciones; las corridas `2 × 2` no registraron ninguno. Parte de la diferencia temporal podría deberse a estas incidencias.
4. **Sin métricas desagregadas por etapa:** se midió el tiempo total, no la contribución separada de análisis, generación, reintentos o recuperación.
5. **Calidad no exhaustiva:** el contrato JSON, la integridad y la coincidencia de clasificaciones no equivalen a una auditoría humana de utilidad, relevancia y ausencia de alucinaciones.
6. **Evidencia con árbol de trabajo modificado:** las corridas concurrentes registraron `working_tree_limpio: false`, lo que reduce su reproducibilidad exacta desde el commit publicado.

## 9. Recomendaciones y próximos pasos

1. **Mantener la concurrencia configurable en la rama experimental** y conservar `1 × 1` como referencia estable hasta completar la validación adicional. No integrar directamente la configuración `2 × 2` 
2. **Cerrar la mejora de FAQ por separado:** continuar la evaluación del prompt de `src/agentes/prompts/preguntas_frecuentes.py`; las consultas técnicas que solicitan ejemplos siguen mostrando respuestas demasiado generales. No incluir ese ajuste inacabado en un commit dedicado únicamente a concurrencia.
3. **Repetir un benchmark controlado** con el mismo commit limpio, mismos prompts, dataset, proveedor, modelos, timeout y fecha de referencia. Alternar el orden de modos y aumentar el número de repeticiones para reducir el efecto del momento de ejecución.
4. **Registrar por separado** tiempos de análisis y generación, número de llamadas, tokens, HTTP 429/500, timeout, reintentos, fallback, recuperación posterior e IDs afectados.
5. **Auditar una muestra de activos por ruta** con criterios de fidelidad factual, utilidad, especificidad, adecuación al canal y ausencia de información inventada; registrar el juicio humano por separado de la consistencia interejecución.
6. **Preparar una decisión de integración** únicamente si se verifica una mejora reproducible sin regresiones funcionales ni degradación editorial.

## 10. Conclusión

En las cuatro ejecuciones evaluadas, CommunityLab conservó los **23 resultados DS**, los **35 activos** y un formato de auditoría consistente. Las dos corridas `2 × 2` no registraron fallback, errores finales ni diferencias en sentimiento, tipo detectado o tema principal; su tiempo medio fue de **90.33 s**, frente a **187.76 s** de `1 × 1` (**51.9 % menos tiempo observado**).

La evidencia respalda **continuar la experimentación con concurrencia `2 × 2`**, pero **no autoriza todavía presentarla como una mejora estable y generalizable**. Debe confirmarse mediante mediciones controladas y revisión de calidad, manteniendo intacta la implementación estable basada en Gemini.
