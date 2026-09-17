# Criterio de puntuación de relevancia

Implementación de Jhonattan Benavides sobre el diseño inicial de Gustavo Vásquez.
Versión `1.0-propuesta`, 17 de septiembre de 2026. Los pesos son una propuesta
funcional para revisión conjunta con Gustavo y el subequipo de IA; no representan
un acuerdo ya aprobado ni resultados de una evaluación con usuarios reales.

## Función dentro del proyecto

`src/data/ingest.py` lee JSON, valida el contrato, limpia los textos y usa
`src/data/relevancia.py` para seleccionar mensajes para la generación de contenido.
Funciona con datos simulados y con la salida JSON de la ingesta de Reddit de Gustavo.
Usa solamente la biblioteca estándar de Python 3.11+ y no hace peticiones de red.

La selección devuelve el mismo formato de entrada y un informe separado con puntaje,
desglose, palabras clave encontradas, advertencias y motivos de descarte de cada
interacción. La función de Python no modifica la entrada. La CLI impide escribir
las salidas sobre el archivo de entrada o de configuración.

## Reglas implementadas

El puntaje por defecto está entre 0 y 100. Los parámetros se pueden cambiar en
`config/relevancia.json`; la suma máxima de los pesos configurados debe ser <= 100.

| Señal | Regla inicial |
| --- | --- |
| Tipo | `testimonio`: 40; `pregunta_tecnica`: 40; `feedback`: 30; `comentario`: 10 |
| Longitud | 1 punto por palabra hasta 20. Con otro peso: `floor(min(palabras, 20) * puntos_longitud / 20)` |
| Palabras clave | 5 puntos por término distinto hasta 30. Comparación de palabras completas sin distinguir mayúsculas ni tildes; no hay stemming |
| Frescura | 10 puntos si la fecha está entre el instante de referencia y 7 días antes, incluidos ambos extremos |

Las URLs no suman palabras ni palabras clave. Repetir `python` muchas veces no
incrementa el bonus de dominio. Se priorizan testimonios y preguntas por el objetivo
de producir historias de éxito y FAQ. Una queja útil puede conservarse como feedback.

Se excluyen mensajes con cualquiera de estas condiciones:

- Menos de 20 caracteres después de la limpieza (`texto_corto`).
- Uno o varios enlaces sin texto que aporte contexto (`solo_enlaces`).
- La misma palabra repetida 6 o más veces sin otras palabras (`texto_repetitivo`).
- Marcadores `[deleted]` / `[removed]`, o autor `[deleted]` (`contenido_eliminado`).
- ID ya visto en el mismo lote, o el mismo autor, canal y texto normalizados
  (`duplicado`). Se conserva la primera aparición. No se deduplica entre lotes;
  preguntas iguales de autores distintos se conservan para analizar recurrencia.
- Puntaje inferior a 40 (`bajo_umbral`).

Los candidatos se ordenan por puntaje descendente, manteniendo el orden original
en los empates. `top_n` limita la cantidad **por lote**, después de los descartes;
los demás reciben `fuera_top_n`. Por defecto es `null`: pasan todos los que cumplen
el umbral. No se fuerza un top 20% con una muestra pequeña y aún sin calibrar.
Un lote sin candidatos se conserva con `interacciones: []`.

## Decisiones y límites

- **Sentimiento:** se pospone la señal emocional del borrador. No se inventan
  etiquetas ni se duplica el análisis con LLM que corresponde a IA. El sentimiento
  general de la comunidad debe calcularse sobre los datos completos: usar únicamente
  la selección de marketing sesgaría sus métricas.
- **Fechas:** una fecha ausente, inválida, sin zona o futura no recibe bonus. Se
  registra una advertencia y no se sustituye por la fecha actual. Una fecha antigua
  válida simplemente recibe cero. La referencia es obligatoria en la API de Python;
  la CLI usa UTC actual si no se indica. Para comparar resultados, fijarla siempre.
- **Texto:** se conserva capitalización, tildes y emojis. Se quita HTML común,
  scripts/estilos, caracteres de control, U+FFFD y espacios repetidos. No se intenta
  reconstruir texto dañado ni detectar idioma. La limpieza aplana saltos de línea;
  los originales quedan en el archivo de entrada para revisar código multilínea.
- **Heurísticas:** no hay detección semántica de spam ni de duplicados. Una pregunta
  breve y válida puede quedar bajo el mínimo: revisar los descartes y ajustar pesos
  con el equipo. El vocabulario inicial se orienta al español y al programa ONE.

## Cómo ejecutar y comprobar

Desde la raíz del repositorio:

```sh
python -m src.data.ingest --config config/relevancia.json --fecha-referencia 2026-09-17T12:00:00Z
python -m unittest discover -s tests -p "test_*.py" -v
python tests/verificar_transformacion_reddit.py
```

Salidas locales (ignoradas por Git):

- `output/datos/mensajes_filtrados.json`: lotes para el equipo de IA.
- `output/datos/informe_relevancia.json`: decisiones trazables por lote, índice
  original de interacción (base cero) e ID, si existe; incluye configuración y fecha.

También se admite `python src/data/ingest.py`. Los caminos predeterminados se
resuelven desde el repositorio, aunque se ejecute desde otra carpeta. Los caminos
proporcionados por el usuario son relativos a su directorio actual. Las salidas
existentes se reemplazan; usar rutas distintas para conservar varias corridas.

Ejemplo con la muestra real de Gustavo y máximo de tres mensajes por lote:

```sh
python -m src.data.ingest --entrada tests/fixtures/prueba_reddit_controlada.json --salida output/reddit/mensajes_filtrados.json --informe output/reddit/informe_relevancia.json --top-n 3 --fecha-referencia 2026-09-17T12:00:00Z
```

## Integración pendiente de validación del equipo

Arthur, Danny y Arnold pueden consumir los lotes siguiendo
`docs/contrato_datos_ingesta.md`. Ramses debe validar el contrato propuesto.
Corresponde revisar conjuntamente pesos, mínimo de longitud, umbral y cantidad
máxima por lote. La implementación y sus pruebas ya permiten hacer esa revisión
sin desarrollar otro filtro.
