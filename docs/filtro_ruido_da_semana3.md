# Filtro de ruido antes de IA — Semana 3

Responsables de Data Analyst: Gustavo y Jhonattan. Actualización: 7 de octubre de 2026.

## Funcionamiento

`preparar_paquete_ia()` limpia y valida la entrada, calcula relevancia y separa el
ruido antes de construir `estados` y `plan`. Los mensajes excluidos no consumen
análisis ni generación. El informe conserva sus IDs y motivos; la entrada original
no se modifica. Un lote compuesto solo por ruido devuelve estados, ciclos y
pendientes vacíos y no llama al modelo.

`src/datos/relevancia.py` concentra las reglas de calidad. `entrega_ia.py` reutiliza
la misma lista de motivos para excluirlos del análisis, independientemente de su
puntaje. No se añade un tipo `spam` al contrato de DS ni se modifican sus rutas.

| Motivo | Regla |
| --- | --- |
| `texto_vacio` | Texto vacío después de la limpieza. |
| `solo_enlaces` | Contiene enlaces y no quedan caracteres de palabra fuera de ellos. |
| `contenido_eliminado` | Texto `[deleted]` o `[removed]`, o autor `[deleted]`. |
| `texto_repetitivo` | Una misma palabra al menos seis veces; o un bloque de 2–4 palabras repetido que ocupa todo el texto y suma al menos 12 palabras. Se ignoran mayúsculas, acentos y puntuación al comparar. |
| `duplicado` | Dentro del mismo lote: mismo autor, canal y texto normalizados, o ID repetido. La entrega para IA rechaza IDs repetidos como error de identidad antes del filtrado. |

Los marcadores de contenido eliminado se conservan por compatibilidad con los
datos existentes. Este cambio no reactiva la captura desde Reddit.

## Qué se conserva

- Las críticas breves y los mensajes con bajo puntaje siguen disponibles para
  analizar sentimiento, aunque no generen activos.
- Un enlace acompañado de una consulta válida no se descarta por contener una URL.
- Mensajes iguales de autores distintos o canales distintos no se eliminan como
  duplicados. Se mantiene la recurrencia útil para entender problemas comunes.
- Las preguntas del programa conservan `elegible_faq`; no se sustituye esta
  decisión por la elegibilidad general de contenido.

`elegible_contenido=False` por sí solo no evita llamadas al analizador. El ruido
debe quedar fuera de `estados`, mientras que un mensaje válido sin ruta puede
analizarse y finalizar en END en el grafo de DS.

## Alcance y límites

Son reglas deterministas para ruido evidente, no un clasificador universal de
spam. No detectan publicidad semántica, campañas coordinadas, duplicados entre
lotes ni variaciones deliberadas para evadir el filtro. No se usa una lista de
palabras comerciales para excluir opiniones o consultas legítimas.

La ampliación de Semana 3 centraliza el motivo de texto vacío y añade la repetición
de bloques. No cambia pesos, umbrales, tamaño de ciclos ni datos de referencia.
Los umbrales de repetición son una decisión conservadora de implementación,
pendiente de contrastarse con ejemplos reales del equipo. Antes de ampliar las
reglas, acordar ejemplos de ruido y ejemplos válidos que deben conservarse.

## Comprobación sin proveedores

Desde la raíz del proyecto y con su entorno Python activo:

```powershell
python -B -m pytest tests/test_filtro_ruido.py tests/test_entrega_ia.py tests/agents/test_tolerancia_fallas.py -q -p no:cacheprovider
```

`test_filtro_ruido.py` comprueba exclusión de ambas poblaciones y del plan,
conservación de opiniones y FAQ, trazabilidad y ausencia de cambios en la entrada.
Las pruebas de tolerancia ejecutan el grafo real con proveedores simulados:
verifican que los IDs de ruido no se envíen al modelo y que una entrega sin mensajes
válidos finalice sin llamadas ni pendientes.
