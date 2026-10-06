# Semana 3: validación de Jhonattan

Preparado el 6 de octubre de 2026, sobre `origin/develop` en `e8177ba`, en la rama
`feature/jhonattan-validacion-semana3`.

## Qué se añadió

- `tests/agents/test_tolerancia_fallas.py`: 19 pruebas del recorrido Datos → grafo real → contrato de salida de Data Science. Se sustituyen las llamadas a modelos por respuestas controladas.
- `scripts/test_nvidia_nim_latency.py`: ensayo independiente de NVIDIA con planificación sin red y ejecución real opcional.
- `tests/test_nvidia_nim_latency.py`: pruebas del ensayo con transporte simulado.

Las pruebas comprueban rechazo de datos inválidos antes de llamar a IA, conservación
de Unicode e IDs, exclusión de ruido, conservación de pendientes y continuidad de
los siguientes mensajes cuando falla un lote o un generador. Cubren timeouts,
errores de cuota simulados y respuestas incompletas. Las entradas de estas pruebas
son sintéticas y propias; no reemplazan los datos de referencia del equipo.

La tolerancia comprobada corresponde a entradas que pasan por `preparar_paquete_ia`.
No demuestra que cualquier estado construido manualmente sea seguro, ni prueba la
interfaz de Streamlit o la conexión con OCI.

## Modelos Free Endpoint

El ensayo admite únicamente estos modelos. Sus fichas mostraban **Free Endpoint:
Available** al verificarlas el 6 de octubre de 2026:

| ID admitido | Ficha oficial |
| --- | --- |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | [Nemotron 3.5 Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/build) |
| `deepseek-ai/deepseek-v4.1-flash` | [DeepSeek V4.1 Flash](https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash) |

La lista es una verificación manual fechada, no una consulta automática de disponibilidad.
Revisar las fichas antes de una ejecución real. Para incorporar otro modelo, primero
confirmar su etiqueta y actualizar `MODELOS_FREE_ENDPOINT` y la fecha en el script.
La etiqueta sirve para seleccionar candidatos al prototipo; todavía no hay medidas
reales que permitan recomendar un ganador.

## Comandos para el equipo

Ejecutar desde la raíz del repositorio, con el entorno Python del proyecto activo
y sus dependencias instaladas. En este equipo, puede sustituirse `python` por
`.\.venv\Scripts\python.exe`.

Pruebas nuevas, sin llamadas a proveedores:

```powershell
python -B -m pytest tests/agents/test_tolerancia_fallas.py tests/test_nvidia_nim_latency.py -q -p no:cacheprovider
```

Planificar el análisis de los 23 mensajes en ambos modelos, sin usar una clave:

```powershell
python -B -m scripts.test_nvidia_nim_latency --modelo nvidia/nemotron-3.5-lightning-30b-a3b --modelo deepseek-ai/deepseek-v4.1-flash --salida salida/validacion_semana3/plan_analisis.json
```

Este comando prepara 46 solicitudes individuales, pero no las envía. El benchmark
incluye todos los estados válidos aunque algunos estén pendientes de completar un
ciclo de producción. No ejecuta el grafo ni reproduce su análisis por lotes.

También se pueden planificar generación de FAQ y LinkedIn agregando `--tarea faq`
o `--tarea linkedin`. La selección usa el tipo original y las elegibilidades del
paquete: FAQ técnicas seleccionadas o administrativas elegibles; LinkedIn para
testimonios seleccionados. No reproduce el enrutamiento posterior a la clasificación.

Para una prueba real, configurar `NVIDIA_API_KEY` en el entorno local o en el `.env`
ignorado por Git y añadir `--en-vivo`. Ejemplo de una primera corrida con un modelo:

```powershell
python -B -m scripts.test_nvidia_nim_latency --modelo nvidia/nemotron-3.5-lightning-30b-a3b --en-vivo --salida salida/validacion_semana3/nemotron_analisis.json
```

La ejecución real envía los textos a NVIDIA. El ensayo usa el endpoint oficial
`https://integrate.api.nvidia.com/v1/chat/completions` y no sigue redirecciones.
La clave no se incluye en los informes. Los informes completos contienen respuestas
del modelo: guardarlos en `salida/`, que ya está ignorada por Git.

## Qué mide y cómo interpretarlo

Por defecto se ejecuta una solicitud a la vez, con un segundo mínimo entre inicios,
una repetición y un máximo de 4096 tokens de salida. `--concurrencia` permite de 1 a 4;
no se lanzan 23 peticiones simultáneas. El intervalo controla el ritmo local, no
garantiza la cuota del proveedor. No hay reintentos automáticos.

El informe separa espera de programación, duración de cada solicitud, respuestas
válidas y errores. Incluye promedio, mediana y percentil 95; los errores rápidos no
reducen artificialmente el promedio de las respuestas válidas. Con pocas muestras,
el percentil 95 no permite afirmar un rendimiento estable. Los tokens se registran
solo cuando el proveedor los devuelve.

Se reutilizan plantillas y esquemas actuales de Data Science, agregando la instrucción
de devolver JSON. El proveedor debe aceptar `response_format=json_object`; esto aún
requiere verificación en vivo para cada modelo. Una respuesta rechazada o truncada
cuenta como fallo. `--max-tokens` permite ajustar el presupuesto hasta 32768. No se
configura el razonamiento interno del modelo; su valor por defecto y el presupuesto
pueden afectar la duración y la completitud. Registrar cualquier cambio al comparar.

Las tareas de generación llevan tema, subtema y tipo detectado vacíos porque este
ensayo no ejecuta un análisis previo. Miden el formato y rendimiento de esa solicitud
aislada, no la calidad del flujo completo. Validar el esquema tampoco demuestra
corrección semántica: los textos necesitan revisión humana.

`--umbral-segundos 1.8` es opcional y cuenta respuestas válidas que superan 1,8 segundos
**por solicitud**. No se presenta como criterio acordado del equipo ni activa un
respaldo hacia Gemini. El timeout de red se aplica a operaciones de socket, no es un
plazo máximo estricto para toda la corrida.

El script devuelve 0 para un plan o una corrida sin fallos, 1 cuando alguna solicitud
falla y 2 para errores de configuración o entrada. Conserva resultados de solicitudes
fallidas y continúa con las demás.

## Validación y pendientes

La revisión de base produjo 125 pruebas aprobadas y dos fallidas, además de 124
subpruebas aprobadas. Se excluyeron `tests/test_storage.py` y
`tests/test_persistencia_oci.py` porque este entorno no tiene instalado el SDK de OCI.
Con los cambios de esta rama, la misma revisión produjo **164 pruebas aprobadas,
dos fallidas y 124 subpruebas aprobadas**. Las 39 pruebas nuevas pasaron (19 del
recorrido con fallos y 20 del ensayo NVIDIA). Los planes sin red se verificaron con
23 mensajes de análisis, nueve de FAQ y ocho de LinkedIn. No se hicieron llamadas
reales a NVIDIA.

Comando para repetir esa revisión junto con las pruebas nuevas:

```powershell
python -B -m pytest tests --ignore=tests/test_storage.py --ignore=tests/test_persistencia_oci.py -q -p no:cacheprovider
```

Los dos desacuerdos conocidos siguen pendientes de conciliación con el equipo:

- `tests/test_entrega_ia.py::EntregaTests::test_dataset_23_sentimiento_19_contenido_dos_ciclos`: espera 14 seleccionados y el código actual entrega 19.
- `tests/agents/test_evaluacion_regresion.py::test_casos_candidatos_tienen_esquema_y_rutas_consistentes`: los tipos de los casos candidatos no coinciden con el dataset actual.

No se han cambiado esos datos ni esas expectativas. No debe declararse toda la suite
aprobada mientras continúen esos desacuerdos.

Pendiente: ejecutar las corridas reales con credenciales, revisar calidad de respuestas
y compartir evidencia con Data Science. Integrar NVIDIA o un respaldo en producción
requiere una decisión posterior del equipo; este ensayo no modifica Gemini, el router
ni el flujo de producción.
