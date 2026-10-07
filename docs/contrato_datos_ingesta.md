# Contrato de ingesta para revisión de Arquitectura y Ciencia de Datos

Propuesta de Jhonattan sobre el formato existente de Gustavo. Pendiente de
validación de Ramses y del subequipo de Ciencia de Datos. No modifica los nombres
definidos en la especificación.

**Estado, 26 de septiembre:** implementación consolidada en la rama de Gustavo.
Se recuperan validaciones y separación de poblaciones del avance local de Jhonattan.
Pendiente la revisión conjunta de DA, DS y Ramses antes de integrar en develop.
El esquema de Arquitectura continúa en el PR #2, fuera de develop.

## Entradas admitidas (formato interno, sin cambios)

Esta sección describe lo que acepta `validar_y_limpiar`/`procesar_datos` como
**entrada interna** del equipo — sigue siendo flexible a propósito, para no
limitarnos mientras se prepara el conjunto de datos. La forma estricta que sí
debe cumplir el esquema de Nelson es la de **entrega** (ver más abajo), no esta.

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
de Gustavo. `metadata` es opcional. No se admite mezclar ambas formas ni una lista
de mensajes suelta. `lotes` e `interacciones` pueden estar vacíos.

| Campo de interacción | Validación |
| --- | --- |
| `autor`, `canal` | Obligatorios, cadenas no vacías antes y después de limpiar |
| `tipo` | Obligatorio: `testimonio`, `pregunta_tecnica`, `pregunta_programa`, `comentario` o `feedback` |
| `texto` | Obligatorio, cadena; el texto vacío se registra como descarte |
| `id`, `fecha`, `idioma` | Opcionales en la lectura base. Si aparecen, deben ser cadenas no vacías |
| Otros campos | Se preservan sin reinterpretarlos |

Al preparar la **entrega a Ciencia de Datos**, los siete campos `id`, `autor`,
`canal`, `tipo`, `texto`, `fecha` e `idioma` son obligatorios. Los ID deben ser
no vacíos, no llevar espacios exteriores y ser únicos en toda la entrega, incluso
entre lotes. Esta validación adicional la aplica `preparar_entrega()`.

Una fecha ISO 8601 con zona horaria permite puntuar frescura. Una cadena de fecha
inválida genera advertencia y cero puntos de frescura. No se infiere el idioma.
Un error de estructura detiene el procesamiento con una ubicación como
`lotes[0].interacciones[2].autor`; no se produce una salida parcial silenciosa.

## Salidas

`procesar_datos` devuelve `(seleccion, informe)`. `seleccion` conserva la forma
original y los campos adicionales; solo limpia autor/canal/texto y reemplaza cada
lista de interacciones por las seleccionadas, ordenadas por relevancia. No añade
campos de puntaje al contrato del modelo de lenguaje. Los metadatos de origen se
copian; no se deben interpretar como estadísticas de la selección.

`informe` contiene versión del criterio, referencia temporal, configuración,
recuentos totales y evaluaciones de todos los mensajes, incluidos los descartados.
Cada evaluación incluye `indice`, `id` (puede ser `null` en el procesamiento base), `puntaje`,
`desglose`, `palabras_clave`, `seleccionado`, `motivos` y `advertencias`. Los índices
se refieren a la entrada, no a la lista ordenada de salida. No copia los textos.

## Entrega estricta entre equipos

La entrada interna sigue admitiendo cuatro campos obligatorios. Para entregar a IA
se requieren siete: `id`, `autor`, `canal`, `tipo`, `texto`, `fecha`, `idioma`.
Se validan cadenas no vacías, tipo admitido y fecha real ISO 8601 con segundos
y zona (`T`, `Z` o desplazamiento `±HH:MM`). No se inventan metadatos.
Los IDs deben ser únicos en toda la entrega y no tener espacios exteriores.
Estas restricciones de identidad son adicionales al esquema de Arquitectura.

```python
from src.datos.ingesta import cargar_json, procesar_datos, validar_y_limpiar
from src.datos.relevancia import ConfiguracionRelevancia

datos = cargar_json("src/datos/mensajes_comunidad_simulados.json")
seleccion, informe = procesar_datos(
    datos,
    fecha_referencia="2026-09-17T12:00:00Z",
    configuracion=ConfiguracionRelevancia(**cargar_json("configuracion/relevancia.json")),
)
for lote in seleccion["lotes"]:
    if lote["interacciones"]:
        # El subequipo de Ciencia de Datos conecta aquí su nodo/grafo por lote.
        print(lote["origen_comunidad"], len(lote["interacciones"]))

# Para estadísticas de sentimiento, usar la población completa, no la selección.
datos_limpios_completos = validar_y_limpiar(datos)
```

Con los mismos datos, configuración y referencia temporal se obtienen las mismas
decisiones. Las quejas y preguntas recurrentes deben seguir disponibles para el
análisis de sentimiento aunque no sean elegibles para generar contenido.
Los archivos de transporte son lotes planos con `origen_comunidad`,
`periodo_referencia` e `interacciones`; cada mensaje contiene solo siete claves.
Se preservan mayúsculas, tildes y emojis; el idioma procede de la entrada.
No se afirma detección de idioma ni ejecución de un validador JSON Schema externo.
La comprobación implementada cubre tipos, campos, enum y fechas del contrato
consultado; su aprobación por Ramses sigue pendiente.

## Una sola entrada por consola

Desde la raíz del repositorio:

```sh
python -m src.datos.ingesta --configuracion configuracion/relevancia.json --fecha-referencia 2026-09-17T12:00:00Z --entrega-ia salida/datos/ia --tamano-ciclo 20
```

| Archivo | Contenido |
| --- | --- |
| `salida/datos/mensajes_filtrados.json` | Población seleccionada para contenido, agrupada en lotes |
| `salida/datos/informe_relevancia.json` | Puntaje, elegibilidad y razones de exclusión por ID |
| `salida/datos/ia/mensajes_limpios_completos.json` | Población válida para sentimiento; contenedor de lotes |
| `salida/datos/ia/estados_agente.json` | Lista de estados iniciales compatibles con las claves de Ciencia de Datos |
| `salida/datos/ia/plan_procesamiento.json` | Ciclos por ID, remanentes e IDs elegibles para contenido |
| `salida/datos/entregas/manifiesto.json` | Índice de fragmentos planos por origen |
| `salida/datos/entregas/*_lote*_ciclo*.json` | Fragmentos de transporte con siete campos por interacción |

Sin `--entrega-ia`, el comando mantiene la selección de contenido de Gustavo.
Con `--tamano-ciclo` solamente, los fragmentos contienen esa selección.
Con ambos flags, los fragmentos contienen la población válida completa.
El plan es un archivo de coordinación; no es un lote del contrato JSON de Nelson.

Toda validación de datos y rutas ocurre antes de comenzar las escrituras.
Las escrituras no son una transacción ante un fallo físico del disco.
El directorio de fragmentos debe estar bajo `salida/`, sin ser esa carpeta ni contener
entrada, configuración u otras salidas. Solo se retiran archivos enumerados en el
manifiesto anterior. Los archivos ajenos se conservan y las colisiones se rechazan.

## Sentimiento y contenido

`preparar_entrega` devuelve `(completos, contenido, informe)`.
Una crítica breve o un mensaje fuera de `maximo_por_lote` sigue disponible para sentimiento.
Se excluyen texto vacío, contenido eliminado, solo enlaces, repetición y duplicados
textuales del mismo autor/canal dentro del lote; cada exclusión queda documentada.
Un mismo ID repetido es un error de identidad, no un descarte silencioso.

Con el dataset corregido y la referencia del ejemplo:
**23 mensajes para sentimiento y 19 para contenido**.
Cambiar la referencia temporal puede cambiar la selección por frescura.

## Mapeo a EstadoAgente

Se conserva el adaptador de Gustavo:

```python
from src.datos.ingesta import cargar_json
from src.datos.entrega_ia import preparar_paquete_ia

paquete = preparar_paquete_ia(
  cargar_json("src/datos/mensajes_comunidad_simulados.json"),
    fecha_referencia="2026-09-17T12:00:00Z",
    tamano_ciclo=20,
)
estados_por_id = {e["id"]: e for e in paquete["estados"]}
for ciclo in paquete["plan"]["ciclos"]:
    estados_del_ciclo = [estados_por_id[i] for i in ciclo["ids"]]
    # Ciencia de Datos conecta aquí su grafo, un estado por interacción.
    print(len(estados_del_ciclo))
```

| Datos | EstadoAgente |
| --- | --- |
| autor, canal, texto, id, idioma | Mismos nombres y valores limpios |
| tipo | Copia en tipo_original; no modifica la clasificación original |
| origen_comunidad del lote | origen por interacción |
| puntaje del informe | score_relevancia, sin recalcular |
| pregunta completa del programa (`relevancia.py`) | elegible_faq: `true` solo si el tipo es `pregunta_programa`, el texto es una pregunta completa (`¿...?`, al menos 4 palabras), toca el vocabulario del programa y el puntaje alcanza el umbral |

`elegible_faq` es una marca para Ciencia de Datos: indica qué preguntas del
programa pueden enrutarse a `preguntas_frecuentes` (`pregunta_programa` +
`elegible_faq`). No reemplaza la clasificación de DS (`tipo_detectado`) y no
cruza la entrega de contenido con el contrato de Nelson, que mantiene sus siete
campos.

Fecha y periodo permanecen en los lotes y en el contexto del informe.
No se inventan campos de sentimiento, rutas, temas ni resultados de IA.

`construir_estados_agente(seleccion, informe)` mantiene la población de contenido.
Para población completa se usa `poblacion="sentimiento"` con el informe de
`preparar_entrega`. Ambas variantes cruzan por ID y verifican población, origen
y periodo. Rechazan IDs ausentes/repetidos, mensajes faltantes e informes
incompatibles. El orden de la salida es el de los mensajes recibidos.

## Ciclos operativos y remanentes

El tamaño máximo configurable está entre 10 y 30. Los fragmentos por origen pueden
tener menos de 10: preservan el contrato plano, no determinan cuántas llamadas
se hacen en un ciclo. El plan agrupa estados de diferentes orígenes sin perder
`origen` en cada mensaje.

El plan solo contiene ciclos de al menos 10 y a lo sumo el máximo configurado.
Reequilibra cuando es posible: **23 mensajes con máximo 20 → ciclos de 12 y 11**.
Si no es posible, conserva IDs en `pendientes`: 9 mensajes → 9 pendientes;
31 con máximo 10 → tres ciclos de 10 y uno pendiente.
No rellena, duplica ni descarta mensajes. DS debe conservar/reincorporar pendientes
al próximo ciclo y definir con PM el cierre de lotes pequeños; no hay cola persistente.

`ids_contenido` conserva por separado la elegibilidad para generar contenido.
Ciencia de Datos debe analizar la población válida y respetar esos IDs al generar activos.
El plan de ciclos no es un campo de `EstadoAgente` ni controla por sí solo el límite HTTP 429
del proveedor. Tampoco acredita una integración ejecutada con Gemini.

## Revisión pendiente

- Ramses/PM: aprobar la distinción entre fragmento por origen y ciclo operativo,
  el tratamiento de remanentes y las restricciones de identidad.
- DS: consumir la entrega, preservar la selección de contenido y acordar
  sentimientos, rutas, errores y persistencia con el resto del equipo.
- DA/DS: prueba conjunta con los 23 casos, crítica breve, spam y entradas inválidas.
- Sub-equipos: auditoría de la rama antes de su integración en develop.
