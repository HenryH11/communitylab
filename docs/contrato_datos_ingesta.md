# Contrato de ingesta para revisión de Arquitectura y Ciencia de Datos

Propuesta de Jhonattan sobre el formato existente de Gustavo. Pendiente de
validación de Ramses y del subequipo de Ciencia de Datos. No modifica los nombres
definidos en la especificación.

## Entradas admitidas

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
| `tipo` | Obligatorio: `testimonio`, `pregunta_tecnica`, `comentario` o `feedback` |
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

## Uso desde LangGraph

Desde la raíz del repositorio, con Python 3.11+:

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
