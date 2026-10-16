# Auditoría de estrés de Datos — Semana 4

**Matriz Rectora 2, Semana 4, tarea ALL:** «Correr simultáneamente los 3 lotes de datos simulados (casos de éxito de marketing, dudas complejas de FAQ y ruido/spam) para certificar cero caídas». Entregable: reporte interno de control de calidad en verde.

Este reporte cubre **la parte de Datos de la línea**: validación, limpieza, relevancia, población de sentimiento, estados del agente y plan de ciclos (`preparar_paquete_ia`). No llama a la IA, a OCI ni a la red. La corrida con IA la hace DS con su propio paquete, y la persistencia en el bucket la verifica CE.

## Cómo se corre

```sh
python scripts/estres_lotes_datos.py
python scripts/estres_lotes_datos.py --repeticiones 100 --hilos 8 --volumen 200 --salida-json estres.json --salida-md estres.md
python -m pytest tests/test_estres_lotes.py
```

El script sale con código 0 si todo queda en verde y con 1 si hay alguna caída, diferencia o entrada modificada.

## Los 3 lotes (`tests/fixtures/lotes_estres_semana4.json`)

| Lote | Mensajes | Origen |
|---|---|---|
| `Estres_Casos_Exito` | 8 | Los 8 testimonios de `src/datos/mensajes_comunidad_simulados.json` |
| `Estres_Dudas_FAQ` | 9 | Las 5 preguntas del programa y las 4 técnicas del mismo dataset (incluida `int-023`, la misma duda que `int-002` escrita por otra persona) |
| `Estres_Ruido_Spam` | 12 | Casos sintéticos escritos por DA; cada uno está descrito en `metadata.casos_ruido` |

Los IDs llevan el prefijo del lote (`exito-int-001`, `faq-int-004`, `ruido-01`…); los mensajes de éxito y FAQ conservan autor, canal, tipo, texto y fecha del dataset.

## Qué se verifica

1. **Concurrencia:** los 3 lotes por separado y, además, los 3 juntos en una sola entrega, cada uno N veces en paralelo. Cada corrida se compara con una corrida de referencia, y la entrada debe quedar intacta.
2. **Volumen:** cada lote repetido N veces, con IDs y autores distintos.
3. **Mojibake:** cada lote como lo leería Windows en CP1252. Los 5 bytes que CP1252 no define (`0x81`, `0x8D`, `0x8F`, `0x90` y `0x9D`) quedan como controles C1. Después de la limpieza, cada texto debe volver a su original.

## Resultado (vie 16 oct 2026, sobre develop `031e15e`)

Corrida exigente: 100 repeticiones, 8 hilos y volumen ×200. **EN VERDE: 406 corridas, 0 caídas, 0 diferencias con la referencia, 0 entradas modificadas, mojibake reparado.**

| Fase | Lote | Mensajes | Sentimiento | Contenido | FAQ | Corridas | Caídas | Distintas |
|---|---|---|---|---|---|---|---|---|
| base | Éxito | 8 | 8 | 8 | 0 | 100 | 0 | 0 |
| base | FAQ | 9 | 9 | 9 | 5 | 100 | 0 | 0 |
| base | Ruido/spam | 12 | 5 | 2 | 2 | 100 | 0 | 0 |
| base | Los 3 juntos | 29 | 22 | 19 | 7 | 100 | 0 | 0 |
| volumen | Éxito | 1600 | 1600 | 1600 | 0 | 1 | 0 | 0 |
| volumen | FAQ | 1800 | 1800 | 1800 | 1000 | 1 | 0 | 0 |
| volumen | Ruido/spam | 2400 | 1000 | 400 | 400 | 1 | 0 | 0 |
| mojibake | Éxito, FAQ y ruido/spam | 8 / 9 / 12 | 8 / 9 / 5 | 8 / 9 / 2 | 0 / 5 / 2 | 1 c/u | 0 | 0 |

La fase de volumen más grande (2400 mensajes) tardó menos de 3 s en una laptop con Windows. Los tiempos dependen de la máquina y no forman parte de la certificación.

## Ruido y spam, caso por caso

| ID | Caso | Sentimiento | Contenido | Motivos |
|---|---|---|---|---|
| ruido-01 | Spam semántico («Gana 500 dólares al día…») | **sí** | no | `bajo_umbral` |
| ruido-02 | Solo enlaces | no | no | `solo_enlaces` |
| ruido-03 | Una palabra repetida | no | no | `texto_repetitivo` |
| ruido-04 | Bloque de 3 palabras repetido | no | no | `texto_repetitivo` |
| ruido-05 | `[deleted]` | no | no | `contenido_eliminado` |
| ruido-06 | Texto vacío | no | no | `texto_vacio` |
| ruido-07 | Copia exacta de ruido-01 | no | no | `duplicado` |
| ruido-08 | «ok 👍» | sí | no | `texto_corto` |
| ruido-09 | Solo emojis | sí | no | `bajo_umbral` |
| ruido-10 | HTML alrededor de una pregunta real | sí | **sí** (FAQ) | — (se limpian las etiquetas) |
| ruido-11 | Caracteres invisibles de ancho cero | sí | **sí** (FAQ) | — (se limpian los caracteres) |
| ruido-12 | Texto muy largo repetido | no | no | `texto_repetitivo` |

## Hallazgos

1. **El spam semántico pasa las reglas de calidad.** `detectar_ruido` es conservador a propósito: su docstring aclara que no detecta spam semántico. ruido-01 queda fuera de contenido solo porque no llega al puntaje mínimo (37 < 40) y **sí entra a la población de sentimiento**, es decir, llegaría al análisis de la IA. Si el spam incluyera palabras clave del programa, podría superar el umbral. Se propone revisarlo con DS antes de la demo; no se cambia en esta rama.
2. **Los lotes chicos no forman ciclos por separado.** El plan exige un mínimo de 10 por ciclo, así que cada lote suelto deja todo pendiente; es lo que pide el diseño. Juntos, los 3 lotes forman 2 ciclos de 11.
3. **La limpieza resiste entradas hostiles:** HTML, caracteres invisibles, emojis, texto de unos 5700 caracteres y mojibake de Windows, sin caídas y con los textos recuperados.
4. **Recurrencia entre autores:** la misma duda escrita por otra persona (`faq-int-023`) no se marca como copia y se conserva.

## Pendiente del resto del equipo

- **DS:** correr los 3 lotes por el grafo con IA y anotar las caídas o los respaldos a Gemini.
- **CE:** verificar que los JSON resultantes se guarden en el bucket (Object Storage).
