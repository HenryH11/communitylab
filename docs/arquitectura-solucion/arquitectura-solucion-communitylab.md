# Arquitectura de solución — CommunityLab

Integración de contratos de Semana 3, actualizada el 10 de octubre de 2026.
Responsable: Nelson Ramses Aviles Reyes.

## Decisión de contratos

Se propone adoptar la entrega de `preparar_entrega_resultados` como contrato
operativo entre DS, Streamlit y persistencia. Se soportan explícitamente 1.2
(compatibilidad histórica) y 1.3 (develop, tras el PR #22). La propuesta se revisa en el PR; este documento
no acredita aprobación del equipo ni modifica las bases del reto.

| Esquema | Frontera |
| --- | --- |
| contrato-entrada.schema.json | Lote público con origen, periodo y cuatro campos por interacción |
| contrato-intermedio-ingesta.schema.json | Fragmento plano DA → DS: agrega id, fecha e idioma |
| contrato-salida.schema.json | Salida de preparar_entrega_resultados para UI y persistencia |

Entrada e intermedio aceptan testimonio, pregunta_tecnica, pregunta_programa,
comentario y feedback. La entrada pública exige al menos una interacción;
el intermedio admite cero después de filtrar. El contenedor interno de lotes,
el paquete de estados y el plan no son lotes planos: se valida cada lote por separado.

## Elegibilidad y metadatos

`elegible_faq` es un booleano del estado de DA y de la interacción entregada por DS.
No se añade al transporte de siete campos. DA lo calcula para pregunta_programa,
con pregunta completa, vocabulario del programa y puntaje suficiente. El tipo por
sí solo no garantiza elegibilidad. El puntaje viaja en el informe y como
`score_relevancia` en el estado. Se separan población para sentimiento y contenido.

Con el dataset versionado y la fecha de demo `2026-09-17T12:00:00Z`, los elegibles
esperados son int-004, int-007, int-010, int-013 e int-015. Cambiar la fecha puede
cambiar la selección por frescura.

DA conserva mayúsculas, tildes y emojis. ID, fecha e idioma proceden de la entrada;
no se inventan metadatos ni se detecta automáticamente el idioma.

## Salida operativa DS

Ambas versiones requieren version_contrato, resumen_comunidad, interacciones,
activos, fallos, pendientes e ids_pendientes. La 1.3 agrega id_ejecucion,
ids_reintentables y resumen_comunidad.total_fallos_reintentables.
Los campos exclusivos de 1.3 no se aceptan bajo la etiqueta 1.2.

El resumen incluye conteos, distribuciones y temas con tema/cantidad. El sentimiento
predominante puede ser null cuando no hay análisis o hay empate. Se permiten cero
activos, resultados vacíos, fallos sin análisis y pendientes sin procesar. Exigir
dos activos en toda respuesta impediría representar estos casos; el objetivo de
la demo de producir varios tipos debe comprobarse por separado.

El contenido específico de cada activo continúa bajo responsabilidad de los modelos
de los generadores: este esquema exige objetos, sin redefinir sus campos. Los fallos
requieren id, etapa, tipo_error y mensaje; admiten metadatos adicionales.

JSON Schema comprueba estructura, no toda la semántica: la unicidad de IDs entre
lotes, coherencia de conteos, correspondencia de activos/fallos por ID y separación
de procesados/pendientes requieren validaciones de código e integración.

## Relación con el brief

La propuesta anterior describía un envoltorio final con status,
activos_distribucion_generados y almacenamiento_oci, conservado en la historia de
feature/arquitectura-solucion. Ese envoltorio no es la salida actual de DS.
Si las bases exigen ese formato final, se necesita un adaptador después de la
curaduría/persistencia. PM y Arquitectura deben confirmarlo con las bases oficiales.
No se afirma que el contrato operativo 1.2/1.3 satisfaga por sí solo ese requisito.

## Integración

Ver [diagrama E2E](diagrama-e2e-communitylab.md). DA limpia, prepara poblaciones,
estados y ciclos; DS analiza y genera; Streamlit permite curaduría; Cloud persiste.
Los estados de almacenamiento pertenecen a Cloud.

La base develop incluye los PR #18 (Cloud), #19 (Streamlit) y #22 (DS).
El alias src.agentes.grafo.procesar_paquete_entrega delega en procesamiento.py
y conserva la compatibilidad con la UI. Se declaran pandas y altair explícitamente,
y jsonschema para las pruebas. La fecha fija de la app queda pendiente de UI:
hacerla configurable permite mantener la demo reproducible y usar fechas actuales.

## Verificación

```sh
python -m pip install -r requirements.txt
python -m pytest tests/test_contratos_arquitectura.py -q
```

Pruebas con productores reales de DA y serializador DS, con resultados controlados,
sin llamadas a IA ni ejecución de Streamlit. Usar Draft202012Validator y
FormatChecker para comprobar date-time. No se ha añadido validación JSON Schema
al flujo de ejecución de la app; requiere acordar cómo gestionar los errores.
