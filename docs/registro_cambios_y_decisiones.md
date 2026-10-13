# Registro técnico completo: cambios, decisiones y siguientes pasos

**Estado del registro:** 6 de octubre de 2026
**Rama:** `feature/DS-Semana3`

Este documento resume los cambios recientes al flujo de Datos y Ciencia de
Datos, por qué se hicieron, qué validan y qué permanece pendiente. No reemplaza
los contratos técnicos ni la guía de ejecución.

## Alcance

Los cambios iniciales se concentraron en trazabilidad, reproducibilidad,
evaluación de clasificaciones y documentación del flujo. La interfaz Streamlit
no se modificó. OCI no se integró al procesamiento de Ciencia de Datos; en un
cambio posterior solo se añadieron validaciones de respuestas opcionales en la
utilidad `tests/test_storage.py` para corregir diagnósticos de Pylance.

## Cambios publicados

### Trazabilidad de fallos

Se agregaron registros estructurados de fallos asociados a la interacción y a
la etapa que los produjo. Cuando corresponde, también se conserva la ruta del
activo. El registro incluye tipo de error y mensaje; la lista de texto
`errores` se mantiene para compatibilidad. El contrato de salida resume el
total y la distribución por etapa.

**Motivo:** una cadena de error por sí sola no permitía saber fácilmente qué
mensaje o generador falló, ni distinguir un problema de análisis de uno de
generación.

**Límite:** hay trazabilidad, pero no reintento selectivo automático.

### Metadatos de ejecución

El informe preparado para el flujo de IA incluye la fecha de referencia, la
versión del criterio de relevancia, la configuración aplicada y los parámetros
no secretos del cliente Gemini, junto al identificador de modelo configurado.

**Motivo:** poder comparar corridas y saber con qué contexto se produjo una
selección o análisis.

**Límite:** el identificador de modelo es el valor configurado por el proyecto,
no una revisión inmutable garantizada por el proveedor.

### Huellas de prompts

El informe incorpora `prompts_ia`, con algoritmo SHA-256, huella global y
huellas individuales para las plantillas de análisis y generación. Se incluyen
el rol, formato, variables y texto de cada plantilla; no se incluyen los
mensajes de una corrida.

**Motivo:** poder identificar si dos ejecuciones utilizaron la misma definición
de prompts, incluso cuando el modelo y sus parámetros coinciden.

### Evaluación de regresión

El evaluador funciona offline por defecto y compara dos ejecuciones guardadas.
Mide coincidencia en sentimiento, tema, tipo y rutas; muestra precisión,
recall, F1 y matrices de confusión por clase. Las rutas se tratan como una
clasificación multilabel, con métricas binarias por ruta. La opción `--en-vivo`
invoca Gemini explícitamente.

**Motivo:** detectar cambios por dimensión y por clase, no ocultar errores bajo
una sola cifra global. La comparación offline evita llamadas externas durante
la suite normal.

**Límite importante:** las ejecuciones guardadas son snapshots históricos, no
etiquetas de referencia aprobadas por personas. La coincidencia entre ellas
mide estabilidad, no exactitud semántica.

### Documentación

El [README](../README.md) se actualizó como punto de entrada al proyecto y usa
kaomojis, según la marca personal indicada. Las instrucciones de ejecución y
pruebas se consolidaron en la [guía unificada](guia_pruebas.md); las tres
guías semanales redundantes se retiraron.

**Motivo:** reducir instrucciones duplicadas y reemplazar rutas y resultados
obsoletos por comandos vigentes.

## Conjunto candidato de etiquetas

Hay una propuesta local de 10 casos en
[`tests/fixtures/casos_referencia_ia_candidatos.json`](../tests/fixtures/casos_referencia_ia_candidatos.json).
Incluye procedencia, justificación, metadatos de Datos y etiquetas candidatas
para las cuatro dimensiones evaluadas. La prueba asociada verifica IDs,
contenido y contexto contra las fuentes, taxonomías permitidas y coherencia de
las rutas deterministas.

**Estado: pendiente de revisión humana.** El fixture no debe tratarse todavía
como un conjunto gold aprobado ni usarse para afirmar exactitud del modelo.
Los casos `int-006`, `int-011`, `int-016` e `int-020` se marcaron como
discutibles. El corpus actual tampoco contiene ejemplos de sentimiento
`muy_negativo`.

Después del merge se corrigió `int-006` a `neutral`, en concordancia con el
ejemplo explícito del prompt para una sugerencia de mejora. El fixture se
actualizó en el commit `149613f` y la aserción correspondiente quedó en
`4ca63e6`. Estos cambios posteriores no forman parte del PR #14. El fixture
sigue pendiente de revisión humana: estar comprometido no significa que sus
etiquetas estén aprobadas como verdad de terreno.

## Commits incluidos en el PR #14

| Commit | Cambio |
| --- | --- |
| `87e2cbd` | Agregar trazabilidad estructurada de fallos |
| `ee1ff9a` | Registrar metadatos de ejecución en informe IA |
| `d19c820` | Agregar evaluación regresiva offline para análisis IA |
| `51bd9f9` | Actualizar README y unificar guías de pruebas |
| `b5b1c01` | Medir métricas de clasificación por clase |
| `ec20515` | Registrar huellas de prompts en el informe |

## Estado de publicación

El PR [#14](https://github.com/HenryH11/communitylab/pull/14), desde
`feature/DS-Semana2` hacia `develop`, fue fusionado el 5 de octubre de 2026.
Incluyó 30 archivos, con 7.696 adiciones y 989 eliminaciones en el diff del PR.
Después del merge se desarrolló la rama `feature/DS-Semana3`. Al corte de este
registro, la rama está sincronizada con `origin/feature/DS-Semana3`; los
siguientes commits están publicados en esa rama, pero aún son posteriores al
PR #14 y no se incluyen en su historial:

| Commit | Cambio |
| --- | --- |
| `3133323` | Agregar el manual maestro de lectura del código. |
| `c25a4b5` | Validar respuestas opcionales de OCI en la utilidad de prueba. |
| `4ca63e6` | Separar métricas de evaluación del CLI. |
| `e74b26e` | Separar validación y resumen de la entrega. |
| `42f9465` | Separar prompts y modelos de generación. |
| `c3173ad` | Agregar recuperación y observabilidad de fallos. |
| `9364854` | Corregir tipos del enrutamiento y Datos. |
| `b198d47` | Actualizar el índice del README. |
| `c1b810d` | Ajustar acceso tipado en una demostración. |
| `149613f` | Ajustar la etiqueta candidata de `int-006`. |
| `9a5ab21` | Documentar logs y reprocesamiento de fallos. |

Este documento se está actualizando para reflejar ese estado; su modificación
actual todavía está pendiente de commit.

## Flujo técnico y funciones

La secuencia de responsabilidad queda así:

```text
src/datos/entrega_ia.py
	preparar_paquete_ia()
				↓
src/agentes/procesamiento.py
	procesar_paquete_entrega()
				↓
src/agentes/grafo.py
	procesar_estados_por_lotes()
				↓
src/agentes/nodos/nodo_analizador.py
	analizar_lote() / _analizar_individualmente()
				↓
LangGraph: determinar_rutas() → generar_activos()
				↓
src/agentes/entrega_resultados.py
	preparar_entrega_resultados()
```

### Preparación y consumo del paquete

- `preparar_paquete_ia()` en `src/datos/entrega_ia.py` reutiliza el pipeline de
	Datos. Devuelve interacciones completas, selección para contenido, informe,
	estados de agente y plan de procesamiento. Adjunta al informe configuración
	del modelo y hashes de prompts sin invocar Gemini.
- `procesar_paquete_entrega()` en `src/agentes/procesamiento.py` valida que los IDs sean
	únicos y que ciclos más pendientes cubran todos los estados. Procesa cada
	ciclo por ID y devuelve resultados, índice `resultados_por_id`, ciclos y
	pendientes.
- `procesar_estados_por_lotes()` divide el trabajo en grupos acotados a un
	máximo de 10 interacciones por solicitud. Integra análisis, elegibilidad y
	routing individual sin perder la asociación entre estado e ID.

### Análisis, fallback y routing

- `analizar_lote()` en `nodo_analizador.py` serializa los mensajes como JSON,
	llama a la cadena de análisis por lote, valida la respuesta con `AnalisisLote`
	y reconstruye el orden por ID.
- Si una respuesta válida omite o duplica un ID, ese mensaje se vuelve a
	analizar individualmente mediante `_analizar_individualmente()`. Esto es un
	fallback para respuestas incompletas, no un reintento general ante cualquier
	fallo transitorio.
- Si la invocación del lote falla, el fallo se registra para cada estado del
	lote; actualmente no se vuelve a invocar automáticamente ese lote.
- `determinar_rutas()` consume `tipo_detectado`, sentimiento, puntaje y las
	elegibilidades calculadas por Datos. `pregunta_programa` usa
	`elegible_faq`; las otras rutas dependen de `elegible_contenido` y de la
	clasificación.

### Generación y contrato de salida

- `generar_activos()` intenta cada ruta por separado. Un fallo en una ruta no
	impide generar las demás. También registra fallos al inicializar generadores
	o si una ruta no tiene generador configurado.
- `preparar_entrega_resultados()` valida resultados y transforma la salida
	interna en el contrato público. La versión incluida en el PR #14 era `1.2`;
	la versión actual es `1.3` (ver sección de reintentos y callbacks).
- El contrato conserva `errores` como lista de texto e incorpora `fallos` por
	interacción y en el nivel superior. El resumen añade `total_fallos` y
	`fallos_por_etapa`, además de conservar `total_con_errores`.

Un fallo serializado tiene esta forma conceptual:

```json
{
	"id": "int-006",
	"etapa": "generar_activos",
	"ruta": "insight_mejora",
	"tipo_error": "RuntimeError",
	"mensaje": "..."
}
```

`ruta` aparece cuando el error pertenece a una ruta de generación. El contrato
valida que el ID, etapa, tipo y mensaje tengan forma válida. No guarda traceback.

## Modelo y parámetros actuales

`src/agentes/modelo_ia.py` centraliza el cliente Gemini:

| Parámetro | Valor configurado |
| --- | --- |
| Modelo | `gemini-3.5-flash-lite` |
| `max_retries` del cliente | `2` (antes `6`) |
| `requests_per_second` | `0.20` |
| `check_every_n_seconds` | `0.1` |
| `max_bucket_size` | `1` |

`obtener_configuracion_modelo()` expone estos valores no secretos para el
informe. `max_retries` es el reintento interno del cliente LangChain / Gemini;
se bajó de 6 a 2 porque ahora la aplicación tiene su propia política de
reintentos y ambos se multiplican.

## Reproducibilidad: informe y prompts

El informe de `preparar_paquete_ia()` conserva:

- `fecha_referencia` en UTC;
- `version_criterio` y `configuracion` de relevancia;
- `modelo_ia`, con proveedor, ID configurado, reintentos y parámetros del
	limitador;
- `prompts_ia`, con algoritmo SHA-256, hash global y hashes por tarea.

`src/agentes/trazabilidad_prompts.py` calcula hashes de siete plantillas:
análisis individual, análisis por lote, LinkedIn, boletín, FAQ, caso de éxito e
insight de mejora. El hash incorpora rol, formato, variables y texto. No añade
los mensajes de cada corrida al hash.

Esto permite saber qué configuración declarada produjo el informe; no hace que
un alias de modelo del proveedor sea una versión inmutable ni vuelve
determinista la generación probabilística.

## Evaluación: qué mide y qué no

`scripts/evaluar_casos_ambiguos.py` tiene dos modos:

1. **Predeterminado, offline:** compara las evidencias JSON históricas y prueba
	 las rutas de la referencia reciente contra `determinar_rutas()`.
2. **`--en-vivo`:** usa `analizar_lote()` con el modelo actual, compara contra la
	 referencia y calcula rutas. Requiere credenciales y consume cuota Gemini.

`calcular_metricas()` mide coincidencia global para sentimiento, tema, tipo y
rutas; también calcula precisión, recall, F1, soporte y matrices de confusión.
Las tres primeras dimensiones son categóricas. Las rutas son multilabel y se
calculan como clasificación binaria por ruta. Los umbrales globales configurados
son 80% para sentimiento, tema y tipo, y 75% para rutas.

En la comparación histórica observada: sentimiento 100%, tema 91,3%, tipo 100%
y rutas 78,3%. La matriz mostraba dos diferencias de tema (`int-015` e
`int-018`) y recall de 44,4% para `preguntas_frecuentes`, principalmente por
cinco preguntas de programa cuya elegibilidad cambió entre snapshots. Estos
números describen acuerdo entre corridas guardadas, no exactitud frente a
etiquetas humanas.

## Fixture candidato y corrección de `int-006`

`tests/fixtures/casos_referencia_ia_candidatos.json` propone diez IDs del
dataset actual. Texto, autor, canal, idioma y tipo original se contrastan con
`src/datos/mensajes_comunidad_simulados.json`; puntaje y elegibilidad se
contrastan con la evidencia guardada. La prueba verifica taxonomías,
justificaciones y rutas deterministas.

Las etiquetas semánticas son propuestas, no un resultado de Gemini ni una
verdad aprobada. La suite solo puede comprobar forma y consistencia mecánica;
no puede decidir si una interpretación de sentimiento o tema es correcta.
`int-011`, `int-016` e `int-020` siguen deliberadamente marcados para revisión.

`int-006` dice: “Sería genial tener más talleres prácticos...”. El prompt de
análisis incluye un ejemplo análogo (“Sería bueno agregar más ejercicios...”)
etiquetado como `neutral` + `feedback`. Por esa regla, la etiqueta candidata
local se corrigió de `positivo` a `neutral` y se añadió una aserción de prueba.
Esta corrección ocurrió después del merge del PR y todavía está sin commit.

## Reintentos, logs estructurados y callbacks (implementado)

### Reintentos: `src/agentes/reintentos.py`

- `ejecutar_con_reintentos(operacion, *, contexto, max_intentos=None)` ejecuta
	`operacion(intento)` hasta `MAX_INTENTOS = 3` veces, con backoff exponencial y
	jitter (`ESPERA_BASE_SEGUNDOS = 2.0`, tope `ESPERA_MAXIMA_SEGUNDOS = 30.0`).
- `es_error_transitorio(error)` decide si se reintenta: `TimeoutError`,
	`ConnectionError`, clases como `ResourceExhausted`/`ServiceUnavailable`,
	códigos 429/500/502/503/504 o mensajes de cuota/timeout. Validación Pydantic,
	credenciales y configuración no se reintentan.
- Al agotar intentos o ante error permanente lanza `FalloOperacion` con
	`causa`, `intentos` y `reintentable`.
- `construir_fallo()` y `describir_error()` generan el registro del contrato y
	el texto histórico de `errores`. Cada fallo ahora incluye `intentos` y
	`reintentable`.
- Peor caso por unidad de trabajo: 3 intentos de aplicación × (1 + 2 reintentos
	del cliente) = 9 llamadas, frente a 7 con la configuración anterior sin
	reintentos de aplicación.

### Dónde se aplica

- `analizar_lote()`: reintenta el lote completo; al agotar, marca cada ID del
	lote con el fallo (reintentable o no).
- `_analizar_individualmente()`: reintenta el análisis individual usado como
	fallback para IDs omitidos o duplicados.
- `generar_activos()`: reintenta solo la ruta que falla; las rutas exitosas no
	se repiten.

### Recuperación y reporte: `src/agentes/procesamiento.py` y `src/agentes/recuperacion.py`

- `procesar_paquete_entrega(..., pasadas_recuperacion=1)`: al terminar los
	ciclos hace una pasada sobre los IDs con fallos reintentables. Si el fallo fue
	de análisis, se reanaliza el estado limpio; si fue de generación, solo se
	regeneran las rutas fallidas y se conservan los activos ya generados.
- `reprocesar_fallidos(salida, *, solo_reintentables=True)`: misma lógica,
	invocable después sobre una salida guardada.
- La salida añade `id_ejecucion` y `reprocesamientos` (IDs intentados y
	recuperados por pasada).
- `procesar_estados_por_lotes()` ahora fija `elegible_contenido` también cuando
	el análisis falla, para que el reprocesamiento respete la elegibilidad de
	Datos.
- `scripts/reprocesar_fallidos.py` lee una entrega JSON (por defecto
	`output/entrega_ciencia_datos_completa.json`), reprocesa los fallos
	reintentables y escribe `output/entrega_ciencia_datos_reprocesada.json`.
	`--incluir-permanentes` fuerza también los no transitorios. Sale con código 1
	si quedan fallos reintentables.

### Contrato de salida 1.3

- `id_ejecucion` para cruzar la entrega con los logs.
- `ids_reintentables` en el nivel superior.
- `resumen_comunidad.total_fallos_reintentables`.
- Cada fallo incluye `intentos` y `reintentable`. Sigue sin traceback.

### Logs estructurados y callbacks: `src/agentes/observabilidad.py`

- `configurar_logging()` escribe una línea JSON por evento en
	`salida/logs/ciencia_datos.jsonl` (carpeta ignorada por git). Variables:
	`COMMUNITYLAB_LOGS=0` desactiva, `COMMUNITYLAB_LOG_DIR` cambia la carpeta,
	`COMMUNITYLAB_LOG_LEVEL` cambia el nivel (por defecto `INFO`). La suite de
	pytest los desactiva mediante `tests/conftest.py`.
- `contexto_ejecucion()` asigna un `id_ejecucion` común a todos los eventos de
	una corrida.
- `ManejadorObservabilidad` (`BaseCallbackHandler`) registra `llm_inicio`
	(DEBUG), `llm_fin` (duración y tokens) y `llm_error`, con etapa, intento, ID,
	ruta y modelo. No registra prompts ni texto de mensajes.
- `config_ejecucion(etapa, *, intento, ...)` arma el `RunnableConfig` con el
	callback, metadatos, tags y `run_name` que se pasa en cada `invoke()`. En
	`cadenas.py`, `_invocar_analisis` y `_invocar_analisis_lote` ahora reciben
	y propagan `config`.
- Eventos de aplicación: `procesamiento_iniciado`, `procesamiento_finalizado`,
	`reintento_programado`, `operacion_fallida` (con traceback) y
	`reprocesamiento_finalizado`.

### Límites

- Los reintentos internos del transporte del cliente no se ven uno por uno en
	los callbacks; se ven los intentos de aplicación.
- La pasada de recuperación aumenta llamadas si el proveedor está caído; se
	puede desactivar con `pasadas_recuperacion=0`.
- Las pruebas usan modelos simulados; la recuperación real frente a Gemini se
	valida en las ejecuciones E2E en vivo.

### Métricas operativas sugeridas

- tasa de errores iniciales y tasa de recuperación después de retry;
- intentos promedio y proporción de trabajos que agotan el límite;
- latencia por etapa y ruta, idealmente percentiles P50/P95;
- llamadas/tokens por interacción si el proveedor devuelve uso fiable;
- duplicados prevenidos y porcentaje de activos completados por interacción.

## Reorganización de módulos (sin cambios de comportamiento)

Se separaron archivos largos por responsabilidad. Las huellas SHA-256 de los
siete prompts se verificaron idénticas antes y después, y la suite completa
sigue pasando.

- `src/agentes/prompts/`: un módulo por plantilla (`analisis.py`,
	`linkedin.py`, `boletin.py`, `preguntas_frecuentes.py`, `caso_exito.py`,
	`insight_mejora.py`). `cadenas.py` queda solo con la construcción e
	invocación de las cadenas de análisis.
- `src/agentes/modelos.py`: ahora también contiene los modelos de salida de
	los activos, que antes vivían en `nodos_generadores.py`.
- `src/agentes/grafo.py`: solo construcción del grafo y
	`procesar_estados_por_lotes()`.
- `src/agentes/procesamiento.py`: validación del paquete, ciclos y
	`procesar_paquete_entrega()`.
- `src/agentes/recuperacion.py`: `reprocesar_fallidos()` y la pasada de
	recuperación.
- `src/agentes/validacion_entrega.py`: validación de IDs, resultados, rutas,
	errores y fallos antes de construir el contrato.
- `src/agentes/resumen_entrega.py`: agregaciones y distribuciones del resumen
	comunitario.
- `src/evaluacion.py`: métricas por clase, matrices de confusión, evaluación
	determinista de rutas y umbrales de aprobación. El script CLI conserva la
	carga de archivos, la opción en vivo y la presentación de resultados.

## Modularización de Ingesta y Robustez Unicode

Se modularizó `src/datos/ingesta.py` (previamente con más de 600 líneas) aplicando el principio de responsabilidad única (SRP), manteniendo 100% de compatibilidad hacia atrás con todos los contratos y tests:

- `src/datos/limpieza.py`: Encapsula la decodificación HTML, normalización NFC, filtrado de categorías de control invisibles, estimación de tokens (~4 caracteres por token), y detección/reparación de secuencias de mojibake (`detectar_mojibake`, `reparar_mojibake`, `PATRON_MOJIBAKE`). Repara automáticamente cadenas corruptas (ej. UTF-8 mal leído como Latin-1 como `pÃ©sima` -> `pésima` o `maÃ±ana` -> `mañana`) sin provocar falsos positivos en español válido y preservando emojis compuestos.
- `src/datos/ciclos_transporte.py`: Encapsula la lógica de fragmentación en ciclos de transporte (10 a 30 interacciones), la validación estricta del contrato intermedio de Nelson (7 campos exactos: `id`, `autor`, `canal`, `tipo`, `texto`, `fecha`, `idioma`), la sanitización de nombres de archivo para evitar escapes de directorio y la gestión atómica del `manifiesto.json`.
- `src/datos/ingesta.py`: Actúa como fachada y orquestador del pipeline de datos y CLI, re-exportando todas las funciones y constantes públicas para no romper consumidores ni mocks dinámicos en tests.

## Estrategia de IA: Enrutamiento Adaptativo de Modelos y Contenerización

Se implementó el enrutamiento adaptativo de modelos multi-tier según la complejidad cognitiva del activo y el análisis requerido, complementando el fallback automático a Gemini y facilitando el despliegue mediante Docker:

- **Arquitectura en Cascada de Tiers de Modelos (`src/agentes/configuracion_ia.py`):**
  - **Tier Rápido (`rapido`):** Orientado a respuestas ágiles de baja latencia (`preguntas_frecuentes`, `boletin`). Modelo por defecto: `meta/llama-3.1-8b-instruct`.
  - **Tier Estándar (`estandar`):** Para tareas de clasificación semántica estructurada (`analisis`, `analisis_lote`). Modelo por defecto: `google/gemma-4-31b-it` (validado con 86.7% de apego a JSON Schema en evaluación empírica).
  - **Tier Razonamiento (`razonamiento`):** Para activos de síntesis profunda y alto impacto (`caso_exito`, `insight_mejora`, `linkedin`). Modelo por defecto: `meta/llama-3.3-70b-instruct`.
- **Integración con LangGraph y Observabilidad:**
  - El nodo enrutador (`src/agentes/nodos/nodo_enrutador.py`) clasifica y propaga el `tier_modelo` en el estado del agente (`EstadoAgente`).
  - La fachada de modelos (`src/agentes/modelo_ia.py`) resuelve dinámicamente el modelo según la ruta o tier solicitado, manteniendo total retrocompatibilidad cuando el enrutamiento adaptativo está desactivado (`COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO=false`).
  - Los generadores y cadenas registran el tier activo en los eventos estructurados de observabilidad (`proveedor_ia_resuelto`), permitiendo auditar qué modelo y tier procesaron cada activo.
- **Contenerización y Despliegue (`Dockerfile`, `docker-compose.yml`, `.env.example`, `.dockerignore`):**
  - Se configuró la imagen basada en Python 3.12 slim con multi-stage caching de dependencias y usuario no privilegiado (`appuser`).
  - Docker Compose define volúmenes para persistencia de datos procesados (`./data`), trazas de observabilidad (`./logs`) y reportes generados.
  - Se documentaron las variables para configurar modelos por tier (`COMMUNITYLAB_MODELO_NVIDIA_RAPIDO`, `COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR`, `COMMUNITYLAB_MODELO_NVIDIA_RAZONAMIENTO`).

## Archivos principales por responsabilidad

| Archivo | Responsabilidad en el flujo |
| --- | --- |
| `src/datos/ingesta.py` | Orquestador de ingesta, CLI y compatibilidad pública de datos. |
| `src/datos/limpieza.py` | Sanitización de texto, normalización NFC, tokens y reparación de mojibake. |
| `src/datos/ciclos_transporte.py` | Partición de ciclos (10-30), validación contrato Nelson y manifiesto. |
| `src/datos/entrega_ia.py` | Construir estados, selección, plan e informe reproducible. |
| `src/agentes/configuracion_ia.py` | Configuración de proveedores (NVIDIA/Gemini), tiers y variables de entorno. |
| `src/agentes/procesamiento.py` | Validar ciclos/IDs, ejecutar el paquete y la pasada de recuperación. |
| `src/agentes/grafo.py` | Grafo de LangGraph y análisis por lotes con routing. |
| `src/agentes/recuperacion.py` | Reanalizar o regenerar solo lo que falló. |
| `src/agentes/prompts/` | Plantillas de prompts, una por archivo. |
| `src/agentes/cadenas.py` | Construcción e invocación de las cadenas de análisis con métricas de tier. |
| `src/agentes/validacion_entrega.py` | Validar resultados internos antes de exponer el contrato. |
| `src/agentes/resumen_entrega.py` | Calcular contadores y distribuciones de la comunidad. |
| `src/evaluacion.py` | Métricas de regresión, rutas esperadas y umbrales. |
| `src/agentes/nodos/nodo_analizador.py` | Analizar lotes, asociar por ID y fallback individual. |
| `src/agentes/nodos/nodo_enrutador.py` | Aplicar reglas deterministas de elegibilidad, rutas y asignación de tier. |
| `src/agentes/nodos/nodos_generadores.py` | Producir activos estructurados por ruta adaptada al tier del modelo. |
| `src/agentes/entrega_resultados.py` | Convertir resultados al contrato DS v1.3 y serializar JSON. |
| `src/agentes/reintentos.py` | Reintentos acotados, clasificación de errores y registro de fallos. |
| `src/agentes/observabilidad.py` | Logs JSONL, ID de ejecución y callback de LangChain con trazabilidad de tier. |
| `scripts/reprocesar_fallidos.py` | Reprocesar fallos reintentables de una entrega guardada. |
| `src/agentes/modelo_ia.py` | Fachada de selección de proveedores y resolución adaptativa de modelos. |
| `src/agentes/trazabilidad_prompts.py` | Hashes SHA-256 estables por prompt y global. |
| `scripts/evaluar_casos_ambiguos.py` | Evaluación offline o explícitamente en vivo. |
| `tests/fixtures/casos_referencia_ia_candidatos.json` | Propuesta de etiquetas pendiente de revisión. |

## Validación registrada y próximos pasos

- La última suite completa ejecutada sobre estos cambios pasó con **207 tests y
	132 subtests** (incluyendo las pruebas de robustez de limpieza/mojibake y la
	nueva suite de enrutamiento adaptativo `test_enrutamiento_adaptativo.py`).
- Pylance no reportó diagnósticos en los archivos incluidos en los lotes de
	corrección revisados.
- El PR #14 fue fusionado en `develop` el 5 de octubre de 2026. La rama
	`feature/DS-Semana3` contiene los commits posteriores enumerados arriba y está
	sincronizada con `origin` al corte de este registro.
- La etiqueta candidata de `int-006` y su aserción están comprometidas en la
	rama de trabajo, pero el conjunto completo sigue pendiente de revisión humana.

El siguiente paso recomendado es que el equipo revise y apruebe las etiquetas
candidatas. Luego se puede congelar una referencia humana, ampliar la cobertura
de clases poco representadas (en particular `muy_negativo`) y establecer
umbrales por clase con soporte suficiente. Los reintentos, la recuperación
selectiva, los callbacks y los logs estructurados ya están implementados; sus
límites y comandos se documentan en la [guía de pruebas](guia_pruebas.md).

La interfaz Streamlit no se modificó. OCI no forma parte del flujo principal;
el cambio reciente fue solo una validación defensiva en `tests/test_storage.py`.