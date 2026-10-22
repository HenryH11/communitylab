# CommunityLab — Evaluación experimental de concurrencia

## 1. Objetivo

Evaluar si la ejecución concurrente reduce la latencia del procesamiento de mensajes sin comprometer el contrato de salida, la integridad de los datos ni la tolerancia a fallos.

Rama: `feature/DS-Semana5-Concurrencia-Experimental`.

Proveedor experimental: NVIDIA NIM.
Modelo de experimentos iniciales: `nvidia/nemotron-3-super-120b-a12b`.

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

Las comparaciones completas con lotes de 6 se presentan en la sección 3.4.

### 3.4. Flujo completo con Nemotron 3.5

Modelo: `nvidia/nemotron-3.5-super-vl-120b-a12b`.

Dataset: 23 mensajes simulados, lote de 6 y 35 activos.
Se mantuvo el mismo SHA256 indicado en la sección 2.

| Modo | Corrida | Timeout | Tiempo (s) | Errores LLM | Reintentos | Fallbacks |
|---|---:|---:|---:|---:|---:|---:|
| base (1+1) | 1 | 30 s | 158.12 | 1 | 1 | 0 |
| base (1+1) | 2 | 30 s | 90.07 | 3 | 2 | 1 |
| analisis (2+1) | 1 | 30 s | 159.90 | 4 | 4 | 0 |
| generacion (1+2) | 1 | 30 s | 99.93 | 7 | 6 | 1 |
| generacion (1+2) | 2 | 30 s | 106.54 | 3 | 3 | 0 |
| ambas (2+2) | 1 | 30 s | 74.36 | 0 | 0 | 0 |
| ambas (2+2) | 2 | 30 s | 208.19 | 7 | 7 | 0 |
| ambas (2+2) | 3 | 20 s | 41.35 | 0 | 0 | 0 |
| ambas (2+2) | 4 | 30 s | 74.85 | 2 | 2 | 0 |
| ambas (2+2) | 5 | 20 s | 77.83 | 7 | 6 | 1 |

Todas las corridas completaron 23 mensajes y 35 activos,
sin errores finales, conservando IDs, orden e integridad.
Los contratos de entrega fueron válidos.

Las corridas con fallback son ejecuciones multproveedor:
no representan rendimiento exclusivo de NVIDIA NIM.

#### Hallazgos de concurrencia

- El mejor tiempo observado fue 41.35 s con 2+2 y timeout de 20 s.
- La configuración 2+2 también registró 208.19 s.
- Existe variabilidad considerable entre ejecuciones.
- No se demuestra una configuración óptima con estas muestras.

#### Timeout de 20 y 30 segundos

Con timeout de 30 segundos se observaron solicitudes
que finalizaron mediante `OpenAITimeoutError` cerca de los 30 s.

Con timeout de 20 segundos se observaron dos solicitudes
que finalizaron por timeout cerca de los 20 s.

El nuevo límite funciona, pero no se ha demostrado
que reduzca sistemáticamente el tiempo total.

Los errores HTTP 500 son independientes del límite
de timeout y pueden producirse en menos de un segundo.

#### Retry, fallback y recuperación

- Retry: reintento con el proveedor primario NVIDIA.
- Fallback: uso de Gemini cuando NVIDIA no completa la operación.
- Recuperación posterior: mecanismo diferente, no equivalente
  a los dos anteriores.

Las ejecuciones demuestran continuidad de la entrega,
pero no garantizan disponibilidad constante de NVIDIA.

#### Compatibilidad de Nemotron 3.5

Se probaron individualmente las cinco rutas:
`preguntas_frecuentes`, `linkedin`, `boletin`,
`caso_exito` e `insight_mejora`.

Se validó también la generación multiruta
de tres activos con NVIDIA, sin fallback.

El adaptador aplica selectivamente `max_tokens=512`
para las FAQ del modelo Nemotron 3.5 Super VL.

El ajuste permite obtener FAQ válidas,
pero no elimina todos los HTTP 500.

La pregunta `int-021` falló tres veces con HTTP 500
durante una corrida base. En dos pruebas aisladas
posteriores funcionó en 1.30 s y 1.03 s.

No se determinó la causa exacta de esos fallos.

Las salidas históricas son evidencia para regresión
y estabilidad, no ground truth humano.

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

### 4.1. Regresión posterior con Nemotron 3.5

- Configuración 1+1: 327 pruebas aprobadas.
- Configuración 2+2: 327 pruebas aprobadas.
- Proveedor y adaptador NVIDIA: 25 pruebas aprobadas.

La implementación estable de Gemini no se modificó.

## 5. Alcance y limitaciones

Los resultados respaldan la viabilidad funcional de la concurrencia experimental.

Todavía no demuestran una mejora consistente del procesamiento completo ni justifican sustituir el flujo estable.

Retry, fallback de proveedor y recuperación posterior son mecanismos diferentes y deben evaluarse por separado.

Data conserva la autoridad sobre score_relevancia, tipo_original, elegible_contenido y elegible_faq.

## 6. Pendientes

- Repetir los cuatro modos con un mayor número de corridas y orden de ejecución balanceado.
- Evaluar calidad editorial con criterios independientes.
- Revisar comportamiento bajo límites de tasa y fallos del proveedor.
- Considerar integración estable solamente después de nuevas pruebas.

## 7. Conclusión

La concurrencia experimental supera las regresiones funcionales disponibles.

El análisis aislado muestra una reducción preliminar de latencia del 36.5 %, mientras que la primera medición completa no confirma esa mejora.

Decisión: mantener la implementación en su rama experimental y no habilitarla por defecto.

### 7.1. Decisión posterior a las nuevas corridas

Nemotron 3.5 muestra potencial de aceleración
con concurrencia de generación y configuración 2+2.

Sin embargo, la variabilidad de latencia, los timeouts
y los errores HTTP 500 impiden confirmar una mejora estable.

El timeout de 20 segundos se mantiene como alternativa
experimental. El predeterminado de 30 segundos no se reemplaza.

Se conserva la rama experimental y no se promueve
automáticamente ninguna configuración a producción.
