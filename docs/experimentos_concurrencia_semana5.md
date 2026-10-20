# CommunityLab — Evaluación experimental de concurrencia

## 1. Objetivo

Evaluar si la ejecución concurrente reduce la latencia del procesamiento de mensajes sin comprometer el contrato de salida, la integridad de los datos ni la tolerancia a fallos.

Rama: `feature/DS-Semana5-Concurrencia-Experimental`.

Proveedor experimental: NVIDIA NIM.
Modelo: `nvidia/nemotron-3-super-120b-a12b`.

La implementación estable con Gemini no se reemplaza.

## 2. Configuración

Variables de control:

- `COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS`: 1 o 2.
- `COMMUNITYLAB_CONCURRENCIA_MENSAJES`: 1 o 2.

Ambas utilizan 1 trabajador por defecto.

Modos evaluables:

| Modo | Análisis | Generación |
|---|---:|---:|
| base | 1 | 1 |
| analisis | 2 | 1 |
| generacion | 1 | 2 |
| ambas | 2 | 2 |

Dataset: 23 mensajes simulados de CommunityLab.

SHA256:
`acd059644cc5f89b38133e640dc4f74f0de3383b61cc0376f9ae71eb3435829e`

Las etiquetas y respuestas históricas no constituyen ground truth humano.

## 3. Resultados experimentales

### 3.1. Análisis aislado

Tamaño de lote: 6 mensajes.
Generación desactivada mediante mock.
Recuperación posterior desactivada.

Dos comparaciones controladas:

- Tiempo promedio secuencial: 28.83 s.
- Tiempo promedio concurrente: 18.32 s.
- Reducción preliminar: 36.5 %.

Se conservaron los 23 IDs y su orden.
No se detectaron errores finales en estas mediciones.

Las diferencias observadas en tema y subtema pueden reflejar variabilidad de las respuestas LLM; no demuestran por sí mismas pérdida de calidad causada por la concurrencia.

### 3.2. Generación concurrente

Comparación inicial:

- Secuencial: 93.61 s.
- Concurrente: 71.61 s.
- Reducción preliminar: 23.5 %.

El benchmark de generación mantiene la concurrencia de análisis fijada en 1.

La revisión editorial disponible fue favorable, pero no equivale a una evaluación con etiquetas humanas independientes.

### 3.3. Flujo completo

Comparación inicial con tamaño de lote 10:

| Modo | Tiempo |
|---|---:|
| base (1+1) | 122.40 s |
| analisis (2+1) | 139.14 s |

En ambas ejecuciones se registraron:

- 23 mensajes procesados.
- 35 activos generados.
- 39 llamadas al proveedor.
- 0 errores finales.
- Contrato de salida válido.

El modo de análisis concurrente fue un 13.7 % más lento en esta comparación completa.

Los lotes desbalanceados y la variabilidad del proveedor son posibles factores. No se ha demostrado causalidad.

No se dispone aún de comparaciones completas de los cuatro modos utilizando lotes de 6.

## 4. Validación funcional

Regresión de agentes:

- Configuración 1+1: 323 pruebas aprobadas.
- Configuración 2+2: 323 pruebas aprobadas.

Coberturas relevantes:

- Conservación de IDs y orden.
- Propagación del contexto de ejecución.
- Límite de dos trabajadores.
- Aislamiento de fallos por lote y mensaje.
- Detección de resultados faltantes o excedentes.
- Conservación de campos autoritativos de Data.

Prueba integral simulada del benchmark combinado:

- Ejecución correcta de 23 mensajes: aprobada.
- Detección de un mensaje faltante: aprobada.
- Observabilidad sin eventos: métricas desconocidas registradas como null.

Las pruebas simuladas no realizan llamadas LLM.

## 5. Alcance y limitaciones

Los resultados respaldan la viabilidad funcional de la concurrencia experimental.

Todavía no demuestran una mejora consistente del procesamiento completo ni justifican sustituir el flujo estable.

Retry, fallback de proveedor y recuperación posterior son mecanismos diferentes y deben evaluarse por separado.

Data conserva la autoridad sobre score_relevancia, tipo_original, elegible_contenido y elegible_faq.

## 6. Pendientes

- Comparar los cuatro modos extremo a extremo con el mismo tamaño de lote.
- Ampliar el número de repeticiones y controlar el orden de ejecución.
- Evaluar calidad editorial con criterios independientes.
- Revisar comportamiento bajo límites de tasa y fallos del proveedor.
- Considerar integración estable solamente después de nuevas pruebas.

## 7. Conclusión

La concurrencia experimental supera las regresiones funcionales disponibles.

El análisis aislado muestra una reducción preliminar de latencia del 36.5 %, mientras que la primera medición completa no confirma esa mejora.

Decisión: mantener la implementación en su rama experimental y no habilitarla por defecto.
