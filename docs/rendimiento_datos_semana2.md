# Rendimiento de Datos — Semana 2

Trabajo sobre `feature/gustavo-rendimiento-tokens-semana2`, a partir de
`6463086`. Se completa la medición de Gustavo con caracteres por población,
una revisión de conservación Unicode y un registro opcional del tiempo.

## Qué se mide

Las métricas viven en `paquete["informe"]["rendimiento"]` y tienen versión
`1.1`. Cada elemento de `rendimiento["lotes"]` corresponde al lote de entrada
con el mismo `indice`. No son los ciclos operativos ni los grupos de llamadas
del analizador de Ciencia de Datos.

| Campo por lote | Significado |
| --- | --- |
| `caracteres_entrada` | Largo de los textos originales, incluido HTML. |
| `caracteres_limpios` | Largo después de limpiar, antes de excluir ruido o seleccionar. |
| `interacciones_analisis` | Cantidad de mensajes válidos preparados para análisis. |
| `caracteres_analisis` | Largo de los textos de esos mensajes válidos. |
| `caracteres_contenido` | Largo de los textos seleccionados para contenido. |
| `tokens_estimados_analisis` | Suma de estimaciones sobre los mensajes válidos. |
| `tokens_estimados_contenido` | Suma de estimaciones sobre los seleccionados. |

Cada campo tiene un total con sufijo `_total` en `rendimiento`. Los caracteres
son puntos de código Unicode, medidos con `len(texto)`: un emoji compuesto
puede ocupar varios. No se cuentan bytes ni caracteres visuales.

`preparar_paquete_ia` y `preparar_entrega` calculan la población válida completa,
incluidos los mensajes pendientes de formar ciclo. Es una medición de datos
preparados, no de solicitudes ejecutadas. `procesar_datos` solo selecciona
contenido: devuelve `analisis_disponible: false` y métricas de análisis en
`null`. Una entrega completa vacía tiene análisis disponible y totales cero.

Se conserva la fórmula de Gustavo: por texto no vacío,
`max(1, round(len(texto) / 4))`; texto vacío produce cero. Se suman las
estimaciones individuales, no se redondea el largo del lote completo.
`tokens_estimados` por lote y `tokens_estimados_total` siguen siendo alias
de las métricas de contenido para mantener compatibilidad.

Los candidatos para contenido también pertenecen a la población de análisis.
Estas cifras no deben sumarse como un consumo real de Gemini. No incluyen
prompts, metadatos, respuestas ni reintentos. Medir el consumo real y controlar
el ritmo de llamadas corresponde al componente que ejecuta el modelo.

## Conservación del texto

La comparación usa el texto original recibido, también cuando se llama a
`preparar_paquete_ia`. Normaliza Unicode a NFC, decodifica entidades HTML y
admite retirar el marcado, scripts, estilos, controles y espacios que contempla
la limpieza existente.

Se compara la identidad y el orden de los caracteres no ASCII restantes,
incluidos los unidores de emojis. Cambiar `ñ` por `é` genera una alerta aunque
la cantidad de caracteres sea igual. El carácter de reemplazo `U+FFFD` también
genera una alerta porque puede indicar una pérdida de información anterior.

- `caracteres_especiales_preservados`: resultado de la revisión del lote.
- `interacciones_con_alerta_caracteres`: índices afectados dentro de ese lote.
- `lotes_con_alerta_caracteres`: índices de lotes con alguna alerta.

Todos los índices comienzan en cero. La alerta es informativa: no bloquea por
sí sola el procesamiento. La revisión no certifica la conservación de todo el
texto ASCII ni detecta todos los errores de decodificación previos. Los campos
de texto validados que contienen sustitutos Unicode aislados se rechazan con
un error que identifica el campo, porque no pueden guardarse en UTF-8.

## Registro de una ejecución

Desde la raíz del repositorio, con las dependencias de `requirements.txt`:

```sh
python -m src.datos.ingesta --configuracion configuracion/relevancia.json --fecha-referencia 2026-09-17T12:00:00Z --entrega-ia salida/datos/ia --tamano-ciclo 20 --registro-rendimiento salida/datos/rendimiento_ejecucion.json
```

El archivo opcional contiene `version`, `alcance_tiempo`,
`tiempo_procesamiento_seg` y una copia de `rendimiento`. Se reemplaza al repetir
el comando; para conservar ejecuciones, usar una ruta distinta por ejecución.
Se rechazan las colisiones con la entrada, configuración y otras salidas.

El tiempo abarca la preparación de Datos, incluido el paquete si se solicita.
Excluye lectura, escritura de archivos, exportación de fragmentos y ejecución
de IA. No equivale al tiempo de respuesta del producto completo.
El informe de relevancia queda separado del reloj y es reproducible con la
misma entrada, configuración y fecha de referencia.

## Compatibilidad y pruebas

El contrato de `EstadoAgente`, los IDs, la selección y los ciclos permanecen
iguales. Las métricas no se incluyen en los estados enviados al grafo.
El consumidor de Ciencia de Datos sigue recibiendo `estados` y `plan`.

```sh
python -m pytest tests/test_rendimiento_datos.py tests/test_integracion_ciencia_datos.py -v
python -m pytest tests --ignore=tests/test_storage.py -q -p no:cacheprovider
```

Las pruebas nuevas cubren español, portugués, emojis compuestos, normalización
Unicode, HTML, controles, corrupción simulada, poblaciones distintas, entradas
vacías, UTF-8 inválido, colisiones de rutas y separación del reloj.
Las pruebas de integración del repositorio sustituyen las llamadas al modelo:
verifican el contrato y el consumo de ciclos sin gastar cuota.

## Comprobación local — 29 de septiembre de 2026

Con el conjunto simulado del repositorio, `configuracion/relevancia.json`,
referencia `2026-09-17T12:00:00Z` y tamaño de ciclo 20:

| Resultado | Valor |
| --- | ---: |
| Estados preparados para análisis | 23 |
| Candidatos para contenido | 14 |
| Ciclos | 12 y 11 |
| Pendientes | 0 |
| Caracteres de entrada / limpios / análisis | 2704 / 2704 / 2704 |
| Caracteres de contenido | 1940 |
| Tokens estimados de análisis / contenido | 677 / 486 |
| Lotes con alertas de caracteres | 0 |

Se comparó la salida con el código de `6463086`: en esta muestra coinciden
`estados`, `plan`, `completos`, `contenido` y el informe de decisiones, excepto
la sección ampliada `rendimiento`.

Una medición local de `preparar_paquete_ia` en Windows con Python 3.12.14,
5 ejecuciones de calentamiento y 20 medidas, dio una mediana de **6,398 ms**
(mínimo 5,941 ms; máximo 9,020 ms). La lectura de archivos ocurrió antes de
medir y no se ejecutó IA. Es una referencia local para 23 mensajes, no una
garantía de latencia ni una prueba de mejora respecto al código anterior.

La verificación automatizada terminó con **100 pruebas y 124 subpruebas
correctas**, incluidas las 8 pruebas nuevas de rendimiento y los consumidores
de Ciencia de Datos. Se ejecutó el segundo comando anterior con pytest 9.1.1,
LangGraph 1.2.12, langchain-core 1.6.6 y Pydantic 2.13.5.
Se excluyó `test_storage.py`, que es un script manual de conexión y subida
a OCI y requiere su SDK. No se verificaron servicios cloud ni se hizo una
ejecución real de Gemini en esta comprobación.
