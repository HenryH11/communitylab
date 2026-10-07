# Guía de ejecución y pruebas

Guía unificada para validar el flujo de Datos y Ciencia de Datos. Los comandos
se ejecutan desde la raíz del repositorio.

## Entorno

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Las pruebas automáticas y la evaluación offline no necesitan clave de Gemini.
Para los comandos en vivo, configura `GEMINI_API_KEY` en un archivo `.env`
local. No publiques ese archivo ni compartas la clave.

## Validación sin Gemini

Ejecuta la suite normal:

```powershell
python -m pytest -q
```

La suite valida relevancia, ingesta, contratos, planificación, enrutamiento,
generación simulada y regresión del evaluador. Los archivos de integración con
prefijo `prueba_` no se descubren automáticamente: se ejecutan manualmente
porque realizan llamadas reales al proveedor.

El evaluador offline compara las dos ejecuciones guardadas y verifica las rutas
de referencia contra el enrutador actual:

```powershell
python -m scripts.evaluar_casos_ambiguos
```

Evalúa sentimiento, tema, tipo y rutas, muestra discrepancias por ID y termina
con estado distinto de cero si una métrica cae bajo su umbral. Los snapshots son
resultados históricos; sirven para regresión, no son una verdad de referencia
revisada por anotadores independientes.

## CLI de Datos

Consulta las opciones vigentes de cada comando:

```powershell
python -m src.datos.ingesta --help
python -m src.datos.ingesta_reddit --help
```

`ingesta.py` permite especificar entrada, salida, informe, configuración de
relevancia, fecha de referencia, tamaño de ciclo y exportación del paquete de
IA. La ayuda del CLI es la fuente de verdad para sus opciones actuales.

## Evaluación actual con Gemini

Para comparar el análisis del modelo actual con los casos guardados:

```powershell
python -m scripts.evaluar_casos_ambiguos --en-vivo
```

Este modo realiza llamadas de análisis a Gemini. Puede variar entre ejecuciones
y consume cuota; solo las métricas y las rutas se comparan, no el texto literal
de los activos.

## Demostraciones con Gemini

Estas demostraciones realizan llamadas reales y pueden tardar o consumir cuota:

```powershell
python -m scripts.demostracion_cadena_analisis
python -m scripts.demostracion_grafo_mensaje_unico
python -m scripts.demostracion_nodo_analizador
python -m scripts.demostracion_analisis_sin_contenido
python -m scripts.demostracion_lotes_ciencia_datos
```

En la demo de lotes se revisan `int-022` e `int-002`: el primero es un
testimonio elegible para activos y el segundo una pregunta técnica que puede
generar una FAQ. El texto exacto generado no es estable; verifica clasificación,
rutas, forma de los activos y ausencia de errores.

## Integraciones completas con Gemini

Se ejecutan explícitamente con pytest para evitar llamadas remotas durante la
suite normal:

```powershell
python -B -m pytest tests\integracion\prueba_paquete_completo_datos.py -v -s -p no:cacheprovider
python -B -m pytest tests\integracion\prueba_entrega_resultados_funcional.py -v -s -p no:cacheprovider
```

Ambas requieren conexión a Internet y `GEMINI_API_KEY`. Procesan el paquete de
Datos, llaman al modelo, ejecutan el routing y validan la salida. La prueba
funcional del contrato escribe sus resultados en `output/`.

## Logs y reprocesamiento de fallos

Cada ejecución de `procesar_paquete_entrega()` escribe eventos JSON en
`salida/logs/ciencia_datos.jsonl`, con `id_ejecucion`, etapa, ID, ruta,
intento, duración y tokens. Los tracebacks solo quedan en ese archivo, no en la
entrega. Variables útiles: `COMMUNITYLAB_LOGS=0` (desactivar),
`COMMUNITYLAB_LOG_DIR` y `COMMUNITYLAB_LOG_LEVEL`.

Los errores transitorios (timeouts, 429, 5xx) se reintentan automáticamente y,
al final de la corrida, se hace una pasada de recuperación sobre lo que quedó
fallido. Si aún quedan fallos reintentables en una entrega guardada:

```powershell
python -m scripts.reprocesar_fallidos
python -m scripts.reprocesar_fallidos --entrada ruta\entrega.json --salida ruta\nueva.json
```

Solo se repite lo que falló: análisis de los IDs afectados o las rutas de
activos fallidas. Requiere `GEMINI_API_KEY`. `--incluir-permanentes` fuerza
también errores no transitorios.

## Errores frecuentes

- `429 RESOURCE_EXHAUSTED`: se alcanzó el límite de frecuencia o cuota. Se
  reintenta automáticamente; si persiste, revisa `ids_reintentables` en la
  entrega y usa el reprocesamiento más tarde.
- `503 ServiceUnavailable`: suele ser temporal; se trata igual que un `429`.