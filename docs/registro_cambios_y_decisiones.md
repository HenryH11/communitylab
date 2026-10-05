# Registro de cambios y decisiones técnicas

**Estado del registro:** 4 de octubre de 2026  
**Rama:** `feature/DS-Semana2`

Este documento resume los cambios recientes al flujo de Datos y Ciencia de
Datos, por qué se hicieron, qué validan y qué permanece pendiente. No reemplaza
los contratos técnicos ni la guía de ejecución.

## Alcance

Los cambios se concentraron en trazabilidad, reproducibilidad, evaluación de
clasificaciones y documentación del flujo. Se respetó la decisión de no tocar
Streamlit ni OCI.

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

En el último estado revisado, el fixture y su prueba estaban sin commit; no
forman parte de los commits publicados listados abajo.

## Commits publicados

| Commit | Cambio |
| --- | --- |
| `87e2cbd` | Agregar trazabilidad estructurada de fallos |
| `ee1ff9a` | Registrar metadatos de ejecución en informe IA |
| `d19c820` | Agregar evaluación regresiva offline para análisis IA |
| `51bd9f9` | Actualizar README y unificar guías de pruebas |
| `b5b1c01` | Medir métricas de clasificación por clase |
| `ec20515` | Registrar huellas de prompts en el informe |

## Validación y siguiente decisión

La última suite completa registrada pasó con **105 tests y 106 subtests**. La
validación estructural del conjunto candidato también pasó, pero no sustituye
la revisión semántica de sus etiquetas.

No se identifica una necesidad urgente de ampliar el código ahora. El siguiente
paso útil es que el equipo revise las etiquetas y justificaciones candidatas,
resuelva los casos marcados y cambie el estado del fixture solo cuando exista
aprobación explícita. Después de eso se pueden fijar umbrales por clase con
soporte suficiente.

Streamlit y OCI permanecieron fuera del alcance de estos cambios.