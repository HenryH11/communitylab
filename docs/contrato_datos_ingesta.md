# Contrato de ingesta para revisión de Arquitectura e IA

Propuesta de Jhonattan sobre el formato existente de Gustavo. Pendiente del visto
bueno de Ramses y del subequipo de IA. No modifica los nombres del brief.

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
