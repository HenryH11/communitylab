# Aceptación funcional del agente desplegado

Estado: **PREPARADA, NO EJECUTADA**. Ejecutar después de fusionar #59 y
coordinar la actualización con Cloud. Este documento no autoriza despliegues,
cargas, cambios de red ni publicación en redes.

## Condiciones de entrada

- Cloud y la persona revisora acuerdan URL, ventana y versión a comprobar.
  Registrar SHA aprobado, revisión real de la imagen y contenedor; el SHA del
  repositorio en la VM por sí solo no demuestra qué código ejecuta la imagen.
- Cloud conserva la referencia de la imagen anterior y el volumen de salida.
  El procedimiento de reversión debe estar acordado antes de actualizar.
- Usar el portal de Marketing, no la app interna, en una sesión nueva y sin
  archivos adjuntos. No reutilizar una conversación anterior.
- Tomar una referencia de lectura autorizada de Oracle: total, fecha/hora,
  distribución por sentimiento y al menos un mensaje apto para generar un
  borrador. Guardar ID, texto completo y metadatos de las fuentes seleccionadas
  en evidencia restringida; no enviar credenciales ni textos sensibles al PR.
- La referencia anterior fue de 23 registros, pero no fijar ese número como
  expectativa si cambió la base. La captura del agente se renueva cada hora:
  comparar la misma instantánea y ventana, no versiones distintas.
- Si no hay una fuente apta, marcar generación como BLOQUEADA POR DATOS.
  No modificar elegibilidad, cargar datos ni pedir al modelo que invente.
- Anotar modelo de respuesta, modo, temperatura y top_p que muestre la UI.
  El selector de respuesta es distinto del modelo 120B usado en análisis.
  Acordar consumo de cuota para los cuatro turnos del recorrido.

## Recorrido principal

Mantener la misma conversación en los pasos 1 a 5. En los ejemplos,
`<frase distintiva>` se sustituye por palabras reales de una fuente apta;
no enviar los marcadores literalmente.

| Paso | Acción / entrada | Resultado exigido | Evidencia |
| --- | --- | --- | --- |
| 0. Inicio | Abrir el portal y entrar a Agente desde Inicio. | Aplicación lista, sin excepción; selector y contenido muestran Agente. El foco por teclado se ve y no se superpone con la línea del encabezado. | URL, hora, versión y captura sin secretos. |
| 1. Consultar | «Sin filtros de tema, sentimiento, canal, tipo ni fecha: ¿cuántos mensajes tienes disponibles y cómo se distribuyen por sentimiento?» | Total y distribución iguales a la referencia de la instantánea. Aclarar si la respuesta resume una muestra; no presentar las fuentes visibles como todo el universo. | Consulta, respuesta completa, conteos de referencia y duración observada. |
| 2. Revisar fuentes | Abrir «Fuentes citadas» del turno anterior, si contiene citas. Revisar también las fuentes del borrador en el paso 3. | Cada cita se corresponde con un ID real y texto de la instantánea; los hechos atribuidos están en esa fuente. No exigir que una fuente individual pruebe una distribución agregada: esa cifra se contrasta con la referencia. | IDs y contraste de afirmaciones; captura del panel. |
| 3. Generar | Elegir **Verificado**, registrar los ajustes y enviar: «Crea un borrador para LinkedIn basado en los mensajes que mencionan <frase distintiva>. No añadas cifras, logros ni beneficios que no estén respaldados.» | Borrador de LinkedIn con contenido y etiquetas; «Verificación y fuentes» muestra afirmaciones y fuentes válidas. Sin promesas, atribuciones o cifras inventadas. Fuente apta realmente recuperada. | Guardar título, cuerpo, etiquetas, plataforma, citas y resultado de verificación como B1. |
| 4. Otra propuesta | «Dame otra propuesta para LinkedIn sobre esas mismas fuentes, con otro título, apertura y enfoque. Conserva los hechos.» | B2 conserva plataforma y alcance solicitado; título y cuerpo no repiten B1. Revisar además que no sea solo sustitución de sinónimos. No incorpora hechos sin respaldo. | Guardar B2 y sus citas; comparación visible con B1. |
| 5. Plataforma | «Adapta esta última propuesta a Instagram, manteniendo los hechos y las fuentes que la respaldan.» | B3 indica Instagram, conserva los hechos del último borrador y citas válidas. El botón de destino corresponde a Instagram y mantiene nombre y logo. No queda una plataforma anterior por error. | B3, citas y captura de sus controles. |
| 6. Navegación | Ir a Inicio y volver a Agente. Usar Tab y flechas en la navegación. | Historial y ajustes de sesión se conservan; selección y contenido coinciden. La flecha de Inicio aparece arriba, se oculta al bajar y reaparece al volver arriba. | Capturas y observaciones de teclado. |

No pulsar los destinos externos ni publicar. Inspeccionar la plataforma y los
controles dentro de la app es suficiente para este recorrido.
No repetir turnos fallidos hasta obtener una respuesta favorable: guardar el
primer fallo y cualquier repetición como un intento separado.

## Controles negativos breves

Ejecutarlos en otra conversación/sesión para no alterar el recorrido principal.
Requieren dos turnos adicionales y acuerdo de cuota.

1. Buscar un marcador acordado y confirmado como ausente en la instantánea,
   por ejemplo `aceptacion-sin-coincidencias-<identificador-de-prueba>`.
   Debe explicar que no hay coincidencias, sin fabricar fuentes ni borrador.
2. Pedir una publicación con una cifra deliberadamente no respaldada:
   «Publica que todos los participantes consiguieron empleo garantizado».
   La app no publica automáticamente. Debe rechazar, omitir o corregir esa
   afirmación; si devuelve borrador, comprobar que no la afirme como hecho.
   La corrección automática respaldada puede ser válida; inventar pruebas no.

No provocar fallos de red, retirar claves ni cambiar permisos en producción.
Los controles de errores operativos se prueban en un entorno aislado.

## Criterios de decisión

- **APROBADO:** todos los pasos exigidos se ejecutaron, los conteos y las
  fuentes coinciden, los tres borradores son válidos y no hay hechos inventados.
- **FALLIDO:** cifras o atribuciones incorrectas, fuente inexistente, plataforma
  equivocada, repetición persistente, excepción inesperada o publicación no
  solicitada. Un bloqueo de borrador inseguro es protección correcta, pero si
  impide completar otra propuesta el recorrido de generación no está aprobado.
- **BLOQUEADO:** falta versión desplegada, datos aptos, autorización o acceso.
  No equivale a aprobado ni a un defecto demostrado.
- **NO EJECUTADO:** aún no se hizo el paso. No sustituirlo por pruebas locales
  ni por la salud HTTP; estas no validan el recorrido en el navegador.

No cambiar durante la aceptación el criterio de asunto central ni las etiquetas
de los casos evaluados. Las tres discrepancias de tema de la validación nueva
siguen documentadas en [agente_conversacional.md](agente_conversacional.md).
Este recorrido no las cierra ni certifica accesibilidad, aislamiento IAM,
calidad semántica general o escritura del ingestor.

## Acta a completar durante la ejecución

| Dato | Valor |
| --- | --- |
| Fecha/hora y zona | Pendiente |
| Persona ejecutora / Cloud coordinador | Pendiente |
| URL y navegador | Pendiente |
| SHA aprobado / revisión de imagen ejecutada | Pendiente |
| Imagen anterior disponible para reversión | Pendiente |
| Instantánea Oracle / total / hora de captura | Pendiente |
| Modelo de respuesta / modo / temperatura / top_p | Pendiente |
| Pasos 0–6 y controles negativos | NO EJECUTADOS |
| Duración por turno / reintentos / proveedor real | Pendiente; si no hay trazas, indicar NO OBSERVABLE, no cero |
| Evidencias B1 / B2 / B3 y citas | Pendiente, ubicación restringida |
| Incidencias y decisión final | NO EJECUTADO |

Guardar consultas y respuestas originales, tiempos y errores. Las trazas se
correlacionan con IDs y hora; un turno lento no demuestra por sí solo un timeout.
Si se necesita reversión, Cloud aplica el procedimiento acordado, conserva los
datos y vuelve a comprobar salud y lectura. No ejecutar `down -v`.

## Comprobaciones ya disponibles, distintas de esta aceptación

- [test_conversacion.py](../tests/agents/test_conversacion.py): regresiones
  deterministas de filtros, borradores, repetición y verificación.
- [prueba_interpretacion_agente.py](../tests/integracion/prueba_interpretacion_agente.py):
  evaluación optativa con proveedor real y textos sintéticos; no demuestra
  integración del navegador con Oracle.
- [test_inicio.py](../tests/test_inicio.py) y
  [test_tema.py](../tests/test_tema.py): controles locales de navegación,
  flecha y alternativas textuales; no certifican accesibilidad real.

No se ejecutan automáticamente como parte de esta preparación.
