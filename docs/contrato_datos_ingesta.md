# Contrato de ingesta para revisión de Arquitectura e IA

Propuesta de Jhonattan sobre el formato existente de Gustavo. No modifica los
nombres del brief.

**Estado (Semana 1):** se reconcilió la divergencia que había entre esta
propuesta y el schema oficial de Nelson
(`docs/arquitectura-solucion/contrato-intermedio-ingesta.schema.json`) — ver
"Contrato de entrega entre equipos" más abajo. **Pendiente el visto bueno
explícito de Nelson** sobre esa sección antes de darla por cerrada; el resto de
este documento (formato interno) no cambia.

## Entradas admitidas (formato interno, sin cambios)

Esta sección describe lo que acepta `validar_y_limpiar`/`procesar_datos` como
**entrada interna** del equipo — sigue siendo flexible a propósito, para no
atarnos de manos mientras se arma/edita el dataset. La forma estricta que sí
debe cumplir el schema de Nelson es la de **entrega** (ver más abajo), no esta.

Un lote individual, como el ejemplo oficial:

```json
{
  "origen_comunidad": "Discord_Grupo_ONE_G10",
  "periodo_referencia": "Semana_00",
  "interacciones": [
    {
      "autor": "Lucas Albuquerque",
      "canal": "#dudas-langgraph",
      "tipo": "pregunta_tecnica",
      "texto": "Tengo dudas sobre los nodos condicionales de LangGraph."
    }
  ]
}
```

O un contenedor `{"metadata": {...}, "lotes": [lote1, lote2]}`, como los archivos
de Gustavo. `metadata` es opcional. No se admite mezclar ambas formas ni un arreglo
de mensajes suelto. `lotes` e `interacciones` pueden estar vacíos.

| Campo de interacción | Validación |
| --- | --- |
| `autor`, `canal` | Obligatorios, cadenas no vacías antes y después de limpiar |
| `tipo` | Obligatorio: `testimonio`, `pregunta_tecnica`, `comentario` o `feedback` |
| `texto` | Obligatorio, cadena; el texto vacío se registra como descarte |
| `id`, `fecha`, `idioma` | Opcionales. Si aparecen, deben ser cadenas no vacías |
| Otros campos | Se preservan sin reinterpretarlos |

Una fecha ISO 8601 con zona horaria permite puntuar frescura. Una cadena de fecha
inválida genera advertencia y cero puntos de frescura. No se infiere el idioma.
Un error de estructura detiene el procesamiento con una ubicación como
`lotes[0].interacciones[2].autor`; no se produce una salida parcial silenciosa.

## Salidas

`procesar_datos` retorna `(seleccion, informe)`. `seleccion` conserva la forma
original y los campos adicionales; solo limpia autor/canal/texto y reemplaza cada
lista de interacciones por las seleccionadas, ordenadas por relevancia. No añade
campos de puntaje al contrato del LLM. Los metadatos de origen se copian; no se
deben interpretar como estadísticas de la selección.

`informe` contiene versión del criterio, referencia temporal, configuración,
conteos totales y las evaluaciones de todos los mensajes, incluidos los descartados.
Cada evaluación incluye `indice`, `id` opcional (`null` si no existe), `puntaje`,
`desglose`, `palabras_clave`, `seleccionado`, `motivos` y `advertencias`. Los índices
se refieren a la entrada, no a la lista ordenada de salida. No copia los textos.

## Contrato de entrega entre equipos (frontera con Arquitectura / Data Science)

Divergencia que existía y cómo se resolvió: esta propuesta admitía `id`/`fecha`/
`idioma` opcionales y dos formas de contenedor (lote plano o envoltorio
`{metadata, lotes}`); el schema oficial de Nelson
(`docs/arquitectura-solucion/contrato-intermedio-ingesta.schema.json`) exige los
siete campos obligatorios y `additionalProperties: false` (sin campos extra) en
un objeto siempre plano. **Se resuelve con un modelo de dos niveles, no
cambiando el formato interno:**

- **Formato interno** (`mensajes_comunidad_simulados.json`, la entrada de
  `procesar_datos`): sigue como está — envoltorio opcional,
  `id`/`fecha`/`idioma` opcionales, se preservan campos adicionales. Sin cambios,
  para no romper nada de lo ya construido.
- **Formato de entrega** (los archivos-ciclo que genera `--tamano-ciclo`, ver
  [`README.md`](../src/data/README.md)): siempre plano, siempre los siete campos
  exactos (`id`, `autor`, `canal`, `tipo`, `texto`, `fecha`, `idioma`), sin
  ningún campo adicional — coincide con el schema de Nelson.

Esto ya no es solo una intención documentada: `construir_ciclos` proyecta cada
interacción con `_interaccion_para_entrega` (`src/data/ingest.py`), que **falla
si falta alguno de los siete campos** y **descarta cualquier campo extra** antes
de escribir el archivo-ciclo. Es decir, un archivo-ciclo que se generó sin error
ya es, por construcción, válido contra el schema de Nelson — no depende de que
alguien lo recuerde ni de una revisión manual.

Ejemplo (`enlace` y `nota_interna` son campos internos nuestros que no cruzan la
frontera):

```jsonc
// Interacción en el archivo interno (mensajes_comunidad_simulados.json)
{
  "id": "int-014", "autor": "Ana", "canal": "#dudas", "tipo": "pregunta_tecnica",
  "texto": "¿Cómo uso LangGraph?", "fecha": "2026-09-16T12:00:00Z", "idioma": "es",
  "enlace": "referencia", "nota_interna": "revisar antes de publicar"
}
```

```jsonc
// La misma interacción dentro de un archivo-ciclo de entrega (sin envoltorio,
// sin "enlace" ni "nota_interna" — exactamente el schema de Nelson)
{
  "id": "int-014", "autor": "Ana", "canal": "#dudas", "tipo": "pregunta_tecnica",
  "texto": "¿Cómo uso LangGraph?", "fecha": "2026-09-16T12:00:00Z", "idioma": "es"
}
```

Con el dataset real de hoy esto no cuesta nada (los siete campos están
presentes en el 100% de los 23 casos); el costo aparece solo si en el futuro se
agrega una interacción sin `id`/`fecha`/`idioma` — en ese caso `construir_ciclos`
falla explícitamente en vez de entregar algo que rompería la validación de
Nelson río abajo.

**Pendiente:** validación explícita de Nelson sobre este acuerdo (comunicado por
Discord, Semana 1). El PM (Enrique) también fue avisado de que el entregable de
"batching 10-30" se reinterpretó sobre `ingest.py` en vez de `ingesta_reddit.py`.

## Uso desde LangGraph

Desde la raíz del repositorio, con Python 3.11+:

```python
from src.data.ingest import cargar_json, procesar_datos, validar_y_limpiar
from src.data.relevancia import ConfigRelevancia

datos = cargar_json("src/data/mensajes_comunidad_simulados.json")
seleccion, informe = procesar_datos(
    datos,
    fecha_referencia="2026-09-17T12:00:00Z",
    config=ConfigRelevancia(**cargar_json("config/relevancia.json")),
)
for lote in seleccion["lotes"]:
    if lote["interacciones"]:
        # El subequipo de IA conecta aquí su nodo/grafo, recibiendo un lote.
        print(lote["origen_comunidad"], len(lote["interacciones"]))

# Para estadísticas de sentimiento, usar la población completa, no el ranking.
datos_limpios_completos = validar_y_limpiar(datos)
```

Los datos y la configuración iguales, con la misma referencia temporal, producen
las mismas decisiones. Las quejas y las preguntas recurrentes deben seguir
disponibles para IA aunque no entren en un cupo de marketing.

## Mapeo a `AgentState` (Sub-equipo 2)

`construir_estados_agente(seleccion, informe)` traduce la salida de `procesar_datos`
al subconjunto de entrada de `AgentState` (`src/agents/state.py`, rama de Data
Science), en el mismo orden de relevancia con el que ya se seleccionan las
interacciones. Reemplaza la necesidad de que Data Science importe funciones internas
de `relevancia.py` directamente.

Correspondencia de campos, confirmada con Data Science (no es una suposición):

| Data Analyst entrega | `AgentState` recibe | Detalle |
| --- | --- | --- |
| `autor`, `canal`, `texto` | `autor`, `canal`, `texto` | Sin cambios |
| `tipo` | `tipo_original` | **Se copia, no se renombra**: el campo `tipo` no se toca en ningún archivo de Data Analyst. Data Science guarda su propia copia como `tipo_original` para comparar contra una clasificación posterior que ellos mismos calculan. |
| `puntaje` (de `relevancia.py`) | `score_relevancia` | Renombre de valor al cruzar la frontera entre equipos |
| `origen_comunidad` (por lote) | `origen` (por interacción) | El valor de lote baja a cada interacción individual |
| `id`, `idioma` | `id`, `idioma` | Solo si la interacción los trae; no se fabrica ningún valor por defecto (hoy están presentes en el 100% del dataset real) |

No incluye `sentimiento`, `tema_principal`, `subtema`, `tipo_detectado`, `rutas`,
`activos_generados` ni `errores` — esos campos de `AgentState` los produce el propio
grafo de Data Science, no Data Analyst.

Sesión de consola reproducible (confirma que las interacciones traen los campos
obligatorios que pedía el PM — `autor`, `canal`, `tipo`, `texto` — antes de mapear):

```python
>>> from src.data.ingest import cargar_json, construir_estados_agente, procesar_datos
>>> datos = cargar_json("src/data/mensajes_comunidad_simulados.json")
>>> seleccion, informe = procesar_datos(datos, fecha_referencia="2026-09-17T12:00:00Z")
>>> estados = construir_estados_agente(seleccion, informe)
>>> all(all(c in e for c in ("autor", "canal", "texto")) for e in estados)
True
>>> {e.get("tipo_original") for e in estados} <= {"testimonio", "pregunta_tecnica", "comentario", "feedback"}
True
>>> estados[0]["score_relevancia"] >= estados[-1]["score_relevancia"]  # orden por relevancia
True
```
