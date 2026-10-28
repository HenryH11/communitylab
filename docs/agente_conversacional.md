# Flujo conversacional de CommunityLab

El MVP del agente en vivo es un flujo Python independiente de Streamlit. Recibe
resultados de Ciencia de Datos ya procesados, permite consultar y filtrar esos
mensajes, y puede generar borradores de marketing basados en evidencia. No
reemplaza el procesamiento por lotes de LangGraph ni publica en redes sociales.

El recorrido de aceptación posterior a fusión y despliegue coordinado está en
[aceptacion_funcional_agente.md](aceptacion_funcional_agente.md).
Su estado inicial es preparado, no ejecutado; las pruebas locales no sustituyen
la comprobación del navegador con los datos y la imagen realmente desplegados.

## Flujo

1. Valida la entrada y llama al modelo solicitando temperatura 0 para obtener un
   `PlanConsulta` estructurado (`src/agentes/interpretacion.py`). El modelo
   separa conversación, aclaración, consulta, borrador y fuera de alcance.
2. El plan contiene únicamente términos temáticos y filtros (sentimiento,
   tipo, canal, período, plataforma y cantidad), usando el historial, el último
   plan y un vocabulario acotado de metadatos. Un saludo mezclado con una tarea
   no se convierte en palabra de búsqueda. Un saludo solo se responde sin
   buscar; ante texto incomprensible se pide aclaración.
3. Busca los términos del plan sobre un índice invertido construido al crear
   la instancia o actualizar sus datos. Aplica los filtros de forma
   determinista. Las consultas reciben la cantidad solicitada, o todas las
   coincidencias si no se indica cantidad, sin el antiguo tope de 20.
   Esto también aplica a borradores: ya no hay topes de ocho fuentes ni tres
   para X. La extensión del post no limita el universo que se analiza.
4. Calcula distribuciones y conteos sobre todas las coincidencias, no solo
   sobre los mensajes incluidos en el contexto acotado.
5. Si se piden campos literales, `campos_listado` selecciona columnas del contrato:
   ID, autor, canal, sentimiento, tema, tipo, fecha o contenido textual.
   Python aplica filtros y cantidad sin enviar los textos al redactor. Un campo
   de metadatos produce valores distintos no vacíos; ID y contenido textual
   conservan cada mensaje. Varios campos producen filas y mantienen nulls.
   Para nombres/autores, `listar_autores=true` o `campos_listado=["autor"]` produce un listado local
   de nombres distintos no vacíos, respetando filtros y cantidad. Deduplica por
   nombre sin distinguir mayúsculas y usa un ID real de fuente por nombre;
   no identifica personas distintas que compartan nombre. No llama al redactor
   ni envía los textos. Reporta nombres disponibles y mensajes sin autor;
   nunca sustituye un nombre ausente por un ID de mensaje.
   Para análisis y redacción, empaca la evidencia por presupuesto de contexto.
   Si no cabe, extrae hallazgos por lotes y consolida las síntesis en uno o más
   niveles hasta poder redactar el resultado final. NVIDIA NIM conserva el
   fallback existente a Gemini con el mismo presupuesto operativo.
6. Valida que las citas correspondan a la evidencia recuperada y, cuando se
   solicitó un borrador, que la salida incluya la plataforma y hashtags
   estructurados.
   Las consultas analíticas generadas por IA pasan siempre por una revisión
   factual del texto final completo y sus hallazgos, contra los mensajes
   originales y agregados autorizados. No depende del selector de borradores.
7. El usuario de la sesión elige el modo para cada consulta de borrador:
   `prompt_estricto` no ejecuta una revisión separada;
   `verificacion_automatica` revisa afirmaciones factuales y devuelve el resumen,
   respaldo e IDs de fuente para mostrarlos en la interfaz. Si hay afirmaciones
   sin respaldo, intenta una única corrección con la misma evidencia y verifica
   de nuevo. Si sigue sin respaldo, faltan afirmaciones verificables o las citas
   no son válidas, lanza un error sin guardar ni habilitar ese borrador.

Cada turno requiere una llamada de interpretación. Los listados de campos
no requieren una segunda llamada: selección, deduplicación, conteos y
presentación se resuelven en Python. Las consultas sin
coincidencias no llaman al generador, y las interacciones de conversación,
aclaración o fuera de alcance se responden desde el intérprete sin buscar.
El modelo recibe la fecha UTC de referencia para interpretar períodos; `hoy`
permite fijarla en pruebas. El filtro `positivo` incluye `muy_positivo` y
`negativo` incluye `muy_negativo`; `muy positivo` filtra solo ese valor. Si el
modelo propone un borrador en una consulta analítica, se descarta.

En la app, los datos del agente vienen de una captura de la base de la
comunidad (renovada cada hora) más los archivos que adjunte el usuario; ver
`src/app/fuente_agente.py` y `docs/integracion_frontend_semana5_1.md`.
`AgenteConversacional.actualizar_datos` cambia los mensajes consultables sin
perder el historial de la sesión.

Cuando no hay coincidencias, el agente explica el motivo sin otra llamada al modelo:
términos que ningún mensaje menciona, filtros sin resultados, falta de fechas o
mensajes no aptos para contenido, junto con los sentimientos y tipos
disponibles. Pedidos como "los 20 mejores comentarios" se interpretan como
mensajes positivos ordenados con `muy_positivo` primero; la cantidad pedida
se respeta y, si hay menos, la respuesta lo dice sin rellenar. El esquema
acepta más de 20 citas y respuestas de más de 4000 caracteres; la cantidad
solicitada ya no está limitada a 1000 por el intérprete.

### Presupuesto de contexto y cobertura

Esto elimina el recorte por número de registros, no los límites de tokens ni
la cuota del proveedor. La búsqueda y los agregados se calculan sobre la
captura completa. La cantidad del usuario selecciona el conjunto a procesar;
si no indica cantidad se procesan todas las coincidencias, también para posts.

`src/agentes/contexto.py` controla dos variables **solo del servidor**:

| Variable | Valor inicial | Uso |
|---|---:|---|
| `COMMUNITYLAB_CONTEXTO_TOKENS` | 32768 | Presupuesto operativo total por llamada. |
| `COMMUNITYLAB_SALIDA_TOKENS` | 4096 | Reserva y máximo de salida enviado a NVIDIA/Gemini. |

La entrada dispone de la diferencia entre ambos valores. El cálculo incluye
prompt, esquema estructurado, consulta, historial, agregados, evidencia y margen
de formato. Se usa una estimación conservadora por bytes UTF-8, no el tokenizer
exacto del proveedor: puede producir más lotes de los estrictamente necesarios.
Estos valores no afirman la capacidad máxima de ningún modelo. El equipo debe
elegir un presupuesto compatible con todos los modelos configurados y su respaldo.
Una configuración vacía, no positiva o con salida mayor/igual al total se rechaza.
Los dos Compose de Marketing transmiten estas variables al proceso de Streamlit;
no hay controles ni parámetros públicos para cambiarlas desde el navegador.

Ya no se recorta cada mensaje a 1200 caracteres. Si un texto individual no cabe,
se fragmenta conservando todos sus caracteres y el ID original. Cada lote se
procesa y sus síntesis conservan procedencia **por hallazgo**, no por lote
completo. Cada `hallazgo` contiene una afirmación atómica y sus IDs exactos.
Se genera una entrada intermedia por hallazgo, y al consolidar solo se expanden
las referencias de los hallazgos elegidos. Las citas de un hecho no heredan las
de los otros hechos de su lote. Las citas intermedias se traducen a IDs reales
antes de devolver la respuesta. Los conteos globales siguen siendo
los calculados en Python, no sumas del modelo. Analizar todo no garantiza
reproducir cada detalle en una síntesis: para extraer campos literalmente se usa
el listado determinista, sin comprimir sus valores.

Las extracciones y consolidaciones sin `hallazgos` se rechazan (excepto el
modo de agrupación, que usa `grupos_preguntas`). Cada referencia debe pertenecer
a la entrada de esa etapa, sin duplicados dentro de un hallazgo. Las citas
generales se calculan como unión de los hallazgos, no de todo lo procesado.
La salida conserva `hallazgos` traducidos a fuentes originales para filtrarlos
en el explorador. Esto evita la atribución indiscriminada por lote; no demuestra
por sí solo que el modelo eligió evidencia semánticamente correcta. Para
borradores se mantiene disponible la verificación factual independiente.

### Revisión obligatoria del análisis final

Las referencias válidas no garantizan que el texto final diga lo mismo que sus
hallazgos. `_verificar_analisis` revisa la respuesta completa y los hallazgos
candidatos en una llamada separada: debe extraer también las afirmaciones que
aparecen solo en la respuesta. Los hallazgos y sus citas NO se pasan como
evidencia autorizada; la evidencia son los mensajes originales seleccionados.

También se pasan exclusivamente los agregados calculados por Python: universo,
coincidencias, distribuciones, porcentajes, filtros y cantidad solicitada.
Un conteo puede recibir `respaldo_agregado=true` sin inventar un ID de mensaje.
Los agregados no demuestran causalidad, logros ni hechos que no contengan.
Un indicador de agregado no valida un borrador: solo se acepta en esta revisión
analítica con los agregados autorizados.

El verificador evalúa el texto real que verá el usuario, incluida la presentación
de preguntas agrupadas. Si necesita lotes, primero extrae las afirmaciones de
todo el candidato y evalúa exactamente las mismas en cada lote; conserva los
agregados globales, sin sumar resultados de síntesis. Una revisión vacía,
afirmaciones sin respaldo, citas ajenas, fallo del proveedor o presupuesto
agotado impiden mostrar/guardar la respuesta como válida. No se hace una
reescritura automática de análisis que pueda introducir nuevas afirmaciones.

El resultado expone `verificacion.obligatoria=true` y
`alcance="texto_final_y_hallazgos"`; la interfaz muestra la revisión aunque el
selector de verificación de borradores esté desactivado. Los respaldos por
agregados se identifican como tales, separados de los mensajes citados.
Los listados literales calculados en Python y las respuestas locales sin
coincidencias no pasan por esta llamada, pues no son análisis generados por IA.

Esta revisión consume el mismo presupuesto de intentos/tokens de la consulta
y usa el fallback existente. Aumenta latencia y costo. Es una comprobación por
modelo, no una prueba formal ni una garantía de extracción semántica perfecta.
Las pruebas offline usan verificadores simulados e integración sin red; no
sustituyen una evaluación real con el proveedor y el conjunto desplegados.

La verificación también respeta el presupuesto. Cuando necesita lotes, primero
extrae las afirmaciones del borrador y luego evalúa exactamente las mismas en
todos ellos. Solo acepta respaldo demostrado por las fuentes de un lote. Es
conservadora: un hecho que requiera combinar fragmentos puede necesitar revisión.

`resumen.procesamiento` informa registros procesados, lotes fuente, llamadas de
generación, niveles de consolidación y máximo estimado de entrada. La interfaz
muestra cobertura y llamadas, no controles de presupuesto; el contador no incluye
interpretación, verificación, reescrituras anteriores ni reintentos del proveedor.
Si falla un lote, las instrucciones ya no caben o las síntesis no reducen el
contexto, se lanza un error y no se guarda una respuesta parcial como exitosa.

### Admisión y presupuesto total por consulta

`src/agentes/consumo.py` envuelve la consulta completa, desde la interpretación
hasta la última corrección/verificación, con un contexto aislado por petición.
La fachada de modelos reserva consumo **antes de cada intento** de proveedor:
entrada estimada (incluido esquema/margen) más máximo de salida. Los reintentos
de la aplicación y el respaldo pasan por esa misma reserva. En estas llamadas
Gemini usa cero reintentos internos del cliente para que no existan intentos
ocultos fuera del contador; otros flujos conservan su política anterior.

| Variable del servidor | Inicial | Efecto |
|---|---:|---|
| `COMMUNITYLAB_MAX_INTENTOS_CONSULTA` | 30 | Máximo de intentos a proveedores de una consulta, incluidas todas sus etapas. |
| `COMMUNITYLAB_MAX_TOKENS_CONSULTA` | 250000 | Suma máxima de reservas conservadoras de entrada y salida. |
| `COMMUNITYLAB_MAX_CONSULTAS_ACTIVAS` | 2 | Consultas simultáneas admitidas en este proceso. |
| `COMMUNITYLAB_MAX_INTENTOS_HORA` | 0 | Intentos compartidos en ventana móvil de una hora; 0 desactiva la cuota. |

No son topes de registros. Si el trabajo no cabe en el presupuesto total, se
interrumpe antes del siguiente intento y no se guarda una respuesta incompleta
como éxito. Los intentos fallidos no se reembolsan en los contadores: también
pueden generar costo. Un error de cuota no activa otra ruta de proveedor para
saltarlo. La concurrencia y la cuota comparten un bloqueo en memoria, también
entre sesiones anónimas. Si no hay cupo se informa que el servicio está ocupado,
sin crear una cola ilimitada. El cupo se libera incluso si la consulta falla.

`salida.consumo` informa intentos y tokens reservados de **toda la consulta**.
No se confunde con `resumen.procesamiento.llamadas_generacion`, que solo describe
la generación final y sus lotes. La interfaz presenta ambos con su alcance.
Los tokens reservados no son facturación ni tokens realmente consumidos.

Por decisión de configuración inicial, la cuota horaria queda **desactivada**:
hay protección por petición y capacidad, pero no techo al gasto acumulado entre
visitantes. Activar esa cuota o configurar límites de gasto del proveedor sigue
siendo necesario para fijar ese techo. Los límites compartidos son por proceso:
reiniciarlo borra el historial horario y varias réplicas tienen cuotas separadas.
Para un despliegue distribuido hace falta un contador/limitador externo compartido;
este código no sustituye autenticación, protección de tráfico ni control de gasto.
Todas las variables se transmiten desde Compose/entorno, nunca desde el navegador.

### Explorador de fuentes citadas

`src/app/fuentes_citadas.py` conserva todas las referencias, sin renderizar
1200 textos al abrir el panel. Muestra diez fuentes por página, permite buscar
por ID, autor, canal o contenido y reinicia la página cuando cambia un filtro.
Cuando hay hallazgos, verificación o agrupación de dudas, permite seleccionar un
hallazgo, afirmación o duda para explorar exactamente sus referencias registradas.
Incluye las citas del verificador aunque no estuvieran en la lista general.

Cada fuente tiene una vista previa de 180 caracteres y un control para mostrar
su texto completo. La búsqueda examina todo el contenido, no solo esa vista.
El panel usa un fragmento de Streamlit: navegar, buscar o abrir un texto no
ejecuta otra consulta al modelo. Cada respuesta tiene claves independientes.
Las dudas agrupadas ya no imprimen todas sus referencias dentro de la respuesta:
las conservan en `grupos_preguntas`; los demás consumidores conservan acceso
programático a esos IDs.

Se distingue cantidad de registros procesados de cantidad de referencias.
La procedencia de las síntesis se conserva por hallazgo, sin expandir todas
las fuentes de un lote. El filtro muestra relaciones registradas por el modelo
o verificador, no una verificación nueva ni una garantía de verdad.
Al completar cada respuesta, la interfaz conserva en `salida.fuentes_citadas`
una referencia a la copia histórica del contenido y metadatos de las fuentes
referenciadas por la salida, hallazgos, verificación y grupos. El almacén
`fuentes_agente_versionadas` comparte esa copia entre respuestas que citan el
mismo ID con contenido y metadatos iguales. Solo copia versiones nuevas de las
fuentes citadas, no toda la base ni una copia por turno. Las copias son
independientes de los datos de entrada y se tratan como solo lectura; cambiar
texto o metadatos crea otra versión, sin modificar la anterior. Al inicializar
el almacén se deduplican también las copias ya presentes en el historial.
El explorador usa esa copia tanto para buscar como para mostrar
el texto: actualizar la captura, editar/eliminar mensajes o reutilizar un ID no
cambia las fuentes de respuestas ya guardadas. Si una fuente no se pudo conservar,
lo avisa y nunca la sustituye por un registro actual con ese ID.

Esta conservación reside en el historial de Streamlit de la sesión, no en una
base persistente: aumenta el uso de memoria por conversación y se pierde al
reiniciar la sesión. Las respuestas antiguas que no tienen copia siguen
permitiendo consultar los datos actuales, pero muestran explícitamente que
podrían diferir del contenido usado originalmente. No se puede reconstruir
retroactivamente una fuente histórica que no se guardó.

El historial visual se presenta en páginas de diez turnos completos
(pregunta/respuesta, incluidos los errores). La página 1 muestra los más
recientes, en orden cronológico dentro de la página. Las páginas antiguas
conservan sus fuentes, controles y claves de turno originales. Enviar una
consulta desde cualquier página vuelve a la 1; el nuevo turno cuenta dentro
del máximo de diez visibles. Navegar no llama al modelo y no elimina turnos ni
cambia su contexto conversacional. Al reiniciar el historial desde el flujo
interno se limpia también el almacén de fuentes y la página seleccionada.

Esta estrategia reduce copias y trabajo de renderizado, pero no impone un
techo total de memoria: respuestas y versiones realmente distintas siguen
ocupando espacio mientras la sesión exista. No hay recorte silencioso ni
persistencia en disco.

Una pregunta puede contener varias dudas y su ID puede pertenecer a varios
grupos. Dentro de cada grupo los IDs siguen siendo únicos, deben pertenecer a
la evidencia y, entre todos los grupos, deben cubrir las preguntas recuperadas.
El total cuenta mensajes distintos, mientras que la frecuencia de cada duda
cuenta los IDs distintos de ese grupo; las frecuencias no se deben sumar como
si los grupos fueran excluyentes. Esto también admite que fragmentos de un mismo
mensaje aporten dudas diferentes tras consolidar.

El último plan de búsqueda se actualiza únicamente al completar la consulta
y guardar su turno (incluidos listados y respuestas sin coincidencias). Los
fallos de búsqueda, generación, revisión o presupuesto conservan el plan del
último turno completado; no contaminan los filtros de seguimientos posteriores.

La fuente Oracle ahora transporta `autor` nullable del Conjunto Consultable
1.2 hasta el agente. Tras desplegar el lector, las sesiones existentes deben
renovar su captura (vigencia de una hora) o reiniciarse para ver ese campo;
añadir la columna en DB no modifica una captura ya cargada en memoria.

Se eliminaron las listas de palabras vacías y las expresiones regulares que
decidían intención, filtros y seguimientos. El modelo devuelve un plan completo
para cada turno, de modo que puede conservar el tema, cambiar la tarea o quitar
filtros sin una herencia automática forzada. No hay fallback a esas heurísticas:
si falla la interpretación o el plan no es válido, se muestra un error.
La salida se valida con Pydantic (campos admitidos, rangos, fechas coherentes
y plataforma obligatoria para borradores). No se ejecuta SQL generado por IA.

Con NVIDIA, el intérprete usa Super VL 120B por defecto, separado del modelo
que redacta: se configura con `COMMUNITYLAB_MODELO_NVIDIA_INTERPRETACION`.
Esto no cambia la configuración de generación ni los tiers existentes. Si el
proveedor configurado es Gemini, usa su modelo configurado. La interpretación
NVIDIA conserva el fallback operativo a Gemini. En pruebas reales Lightning
30B confundió peticiones válidas con conversación en algunas repeticiones;
Super superó los casos evaluados, sin que eso garantice acierto en toda frase.
Gemini Flash Lite puede imponer muestreo fijo e ignorar la temperatura
solicitada; eso no modifica los conteos calculados por la aplicación.

Si una petición se sale del alcance, el mismo intérprete explica el límite y
ofrece una sugerencia opcional para retomar el último tema o borrador. No añade
otra llamada ni vuelve a enviar el conjunto completo. No fuerza esa
reorientación ante saludos o cambios de tema válidos.

La app ofrece **Super (120B)** y **Lightning (30B)** para responder.
`consultar(..., modelo_respuesta="super" | "lightning")` selecciona únicamente
la generación y la reescritura del turno actual, sin modificar variables
globales ni el historial. El intérprete y el verificador siguen sus propias
configuraciones. Se conserva el respaldo operativo a Gemini. Omitir el
parámetro mantiene el proveedor y enrutamiento configurados (por ejemplo, CLI).
Ultra queda fuera del selector hasta validarlo con el flujo actual.

## Criterio editorial de las publicaciones

Los botones de destino muestran el logo local de cada red junto con su nombre;
el control para copiar conserva el icono de portapapeles. Abrir una red no
publica automaticamente ni conecta cuentas.

### Accesibilidad de la interfaz

La navegación conserva controles nativos de teclado y un foco visible, separado
de la línea del encabezado. Los controles principales tienen objetivos de al
menos 44 px y los paneles de información conservan nombres accesibles. El agente
expone un encabezado para lectores de pantalla y oculta adornos decorativos.
Se respetan movimiento reducido y colores forzados del sistema. Las gráficas
de Análisis ofrecen los mismos conteos en texto, con la misma exclusión de spam
para sentimiento; no es necesario escuchar audio ni distinguir colores para
consultarlos. Ayuda incluye instrucciones de teclado. Estas mejoras no
constituyen una certificación WCAG ni sustituyen pruebas con tecnologías de
asistencia y personas usuarias.

El agente en vivo usa `src/agentes/prompts/conversacion.py`; el generador
especializado de LinkedIn conserva su voz institucional sobria por separado.
Una versión nueva puede cambiar el ángulo, la apertura y el cierre, no los
hechos ni la atribución de cada experiencia. Los ejemplos editoriales del
prompt son ficticios y no forman parte de las fuentes recuperadas.

El plan marca `nueva_version` solo ante una petición explícita de otra propuesta
o enfoque. Si su título o cuerpo repite el último borrador de la sesión
(ignorando mayúsculas, tildes y espacios), se solicita una reescritura. Si
persiste la repetición, se rechaza sin guardar el turno. Los cambios de tono,
longitud o plataforma no activan esta restricción. Es un control de repetición
textual, no una garantía de diversidad semántica.
Aceptar con «dale» una oferta explícita de otro enfoque también pide una nueva
versión; «más cercano» por sí solo solicita un cambio de tono.
La generación de otra propuesta recibe el último borrador completo en JSON
como referencia que no debe repetir, sin depender del historial truncado.
El único reintento incluye también el candidato rechazado, con título y cuerpo.
Estos controles no modifican el texto original guardado como petición del usuario.

El tono solicitado decide si encajan agradecimientos, reconocimiento o una
invitación a conversar: no se imponen felicitaciones, emojis ni una pregunta
final en cada publicación. Una dificultad no se presenta como un éxito.
Tampoco se afirma que el equipo ya esté adaptando clases o preparando contenidos
en respuesta a una solicitud sin evidencia de ese trabajo; una sugerencia no
se convierte en un anuncio ni un compromiso institucional.
Usar un script o detectar duplicados no demuestra por sí solo ahorro de tiempo,
productividad ni calidad. Una mejora reportada conserva su atribución y no se
convierte en un resultado medido o compartido por otras personas.
El modo Verificado revisa también esos beneficios y los hechos implícitos en
reconocimientos; no trata una felicitación como prueba del logro mencionado.
Estas instrucciones reducen riesgos, pero no sustituyen la revisión editorial
ni garantizan que cada publicación sea correcta.

### Detección de spam en capa 2

El analizador de capa 2 distingue quejas y solicitudes de apoyo de captación
comercial: relatar una convocatoria no significa convocar, y advertir contra
una estafa no significa promoverla. Se conservan los controles positivos de
promoción no solicitada y ofertas engañosas, incluso si se presentan como
ayuda. La evaluación optativa `tests/integracion/prueba_spam_regresion.py`
comprueba ejemplos originales y variantes, individualmente y por lote.
Los resultados ya guardados no cambian al modificar estas instrucciones;
cualquier corrección de las marcas antiguas debe versionarse por separado.

### Tipos y temas: evaluación editorial acotada

El analizador y las descripciones del contrato distinguen pedir información
existente de proponer una mejora, acceso institucional de configuración técnica,
y elogios de experiencias con resultado. El tema se determina por el objeto
central, no por mencionar el curso: una entrevista laboral sigue siendo
empleabilidad y contactar al mentor sigue siendo mentoria.

La evaluación optativa [prueba_semantica_regresion.py](../tests/integracion/prueba_semantica_regresion.py)
usa 27 mensajes revisados y ocho controles adicionales. Solo exige campos
adjudicados: 34 tipos, 21 temas y 35 marcas de no spam por modo. Los nueve
sentimientos revisados se registran como observaciones, no como criterio de
aprobación de este ajuste de tipos y temas. No se pasan etiquetas propuestas
al analizador ni se modifican los 600 resultados históricos.

La evaluación anterior obtuvo 30/34 tipos y 20/21 temas concordantes por lote;
individualmente, 31/34 tipos y 20/21 temas. Los 35 casos conservaron la marca
de no spam en ambos modos; el control adicional de spam mantuvo 40/40 decisiones
esperadas. Esa versión dejó cinco casos por lote y cuatro individuales
con diferencias.

#### Cierre acotado de los pendientes

Se acordó una frontera editorial explícita: un reporte puntual de fallo es
feedback, incluso en primera persona; un logro alcanzado, aprendizaje,
transformación o trayectoria personal puede ser testimonio. Un aprendizaje
desarrollado a partir de un fracaso sigue siendo testimonio. Se corrigió un
ejemplo contradictorio que clasificaba un fallo de despliegue como comentario.
También se readjudicaron `syn-eval-0459` y `syn-eval-0495`, antes considerados
testimonio, como feedback. **Estas dos readjudicaciones son un cambio de
criterio acordado, no una mejora atribuible al modelo.**

La prueba `test_pendientes_y_contrastes` selecciona únicamente los siete casos
discrepantes de ambos modos, ocho controles existentes y cuatro contrastes
adicionales: 19 textos. Se evalúan 19 tipos, 13 temas y 19 marcas de no spam
por ejecución; los cuatro sentimientos adjudicados son solo observaciones.
No se pasa ninguna etiqueta esperada al modelo.

Con las mismas instrucciones finales, dos repeticiones por modo dieron:

| Modelo NVIDIA | Lote, repetición 1 / 2 | Individual, repetición 1 / 2 |
| --- | --- | --- |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | 17/19 y 16/19 | 18/19 y 18/19 |
| `nvidia/nemotron-3.5-super-vl-120b-a12b` | 19/19 y 19/19 | 19/19 y 19/19 |

Los conteos exigen coincidencia en todos los campos adjudicados de cada texto,
excepto sentimiento. Las trazas confirmaron NVIDIA sin fallback a Gemini.
La configuración local autorizada de análisis usa el segundo modelo, con el
timeout existente de 15 segundos: repitió 76/76 evaluaciones concordantes y
los controles de spam mantuvieron 40/40 decisiones esperadas.
Los modelos de redacción no se cambiaron. No se actualizó la VM.

Para repetir solo el cierre y los controles de spam:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integracion\prueba_semantica_regresion.py tests\integracion\prueba_spam_regresion.py -k "pendientes or quejas" -q -s
```

Los JSON de evaluación guardan texto, expectativa parcial, resultado y
diferencias; un archivo de contexto separado registra el modelo configurado
y las resoluciones de proveedor para detectar fallback. Usar un directorio
temporal aislado para conservar evidencia si se ejecutan otras suites.
La muestra completa de 35 no se volvió a ejecutar tras este ajuste.
Este cierre no estima la precisión de los 600: hay ejemplos cercanos en las
instrucciones, expectativas parciales, una sola revisión editorial y
variabilidad del proveedor. No es una evaluación ciega ni una certificación.

#### Validación nueva con expectativas congeladas

Después del cierre acotado se fijaron 24 mensajes sintéticos nuevos en
[datos_validacion_semantica_nueva.json](../tests/datos_validacion_semantica_nueva.json),
sin repetir literalmente textos de los 600, controles ni ejemplos previos.
Se guardaron huellas SHA-256 de muestra, prompt y contrato antes de ejecutar.
Las expectativas, instrucciones y contrato permanecieron sin cambios durante
la ronda y después de conocer los resultados.

La muestra contiene ocho casos de quejas y spam (cuatro positivos de spam),
seis fallos o testimonios, seis preguntas administrativas o técnicas y cuatro
ambiguos. Las alternativas aceptables de los ambiguos y sus justificaciones
se fijaron de antemano; no se fuerza una única etiqueta en esas dimensiones.
No se evalúa sentimiento. Las expectativas solo las lee el evaluador, nunca
se envían al modelo.

Una ejecución por modo con `nvidia/nemotron-3.5-super-vl-120b-a12b` dio:

| Criterio adjudicado | Lote | Individual |
| --- | --- | --- |
| Casos concordantes en todos sus campos | 23/24 | 21/24 |
| Tipo | 19/19 | 19/19 |
| Tema | 16/17 | 14/17 |
| Spam | 24/24 | 24/24 |
| Casos ambiguos dentro de las alternativas previstas | 4/4 | 4/4 |

Los casos ambiguos ya están incluidos en los totales, no son ocho aciertos
adicionales. Los cuatro positivos de spam y los veinte negativos coincidieron
en ambos modos. Las 27 resoluciones de proveedor confirmaron NVIDIA, sin
fallback a Gemini; no hubo errores finales de ejecución o contrato.

**La validación nueva no aprueba el criterio de coincidencia total.** Quedan
estas diferencias, sin reajustar el prompt ni ampliar las alternativas:

| ID | Modo | Tema esperado | Tema obtenido |
| --- | --- | --- | --- |
| nuevo-10 | Individual | datos_ia | cloud_infraestructura |
| nuevo-13 | Lote e individual | datos_ia | aprendizaje |
| nuevo-15 | Individual | cloud_infraestructura | plataforma |

Corresponden al guardado de pesos durante entrenamiento, al aprendizaje de
correlación/causalidad y al permiso para crear una máquina virtual.
Una eventual corrección debe ser una ronda posterior, no sustituir estos
resultados ni convertir esta muestra ya observada en una nueva prueba ciega.

La prueba optativa genera un JSON por modo con expectativas, resultados,
diferencias, huellas antes/después y trazas de proveedor:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integracion\prueba_validacion_semantica_nueva.py -q -s
```

Es una muestra dirigida y sintética, con una sola persona autora/adjudicadora,
no una medición representativa, ciega o independiente. La disjunción comprobada
es textual exacta, no novedad conceptual; dos modos tampoco son 48 textos
independientes. Los 600 históricos no se reprocesaron y no se desplegó nada.

#### Rendimiento de esa misma ronda

Se agregaron los tiempos ya guardados, sin repetir llamadas a los proveedores.
Son duraciones de llamadas de aplicación: incluyen cliente, red, validación y
los reintentos que ocurran dentro; no son tiempo puro de inferencia ni latencia
de la interfaz.

| Medida | Lote | Individual secuencial |
| --- | --- | --- |
| Mensajes / llamadas de aplicación | 24 / 3 (10, 10 y 4) | 24 / 24 |
| Tiempo acumulado | 16,41 s | 51,92 s |
| Mediana por llamada | 5,43 s por lote | 1,24 s |
| Media por llamada | 5,47 s por lote | 2,16 s |
| Máximo por llamada | 8,72 s por lote | 18,89 s |
| P95 observado por rango más próximo | 8,72 s por lote | 4,05 s |
| Tiempo amortizado por mensaje | 0,68 s | 2,16 s |
| Fallback a Gemini / errores finales | 0 / 0 | 0 / 0 |

En esta ronda, completar los 24 textos por lote consumió 3,16 veces menos
tiempo acumulado que hacerlo individualmente. Los 0,68 s amortizados no
significan que cada mensaje de un lote reciba su respuesta en ese tiempo.
Los percentiles se calculan con el elemento `ceil(p*n)` de las duraciones
ordenadas; con solo tres lotes, el P95 coincide con el máximo y no es robusto.
No deben interpretarse como un SLA.

La salida original de pytest mostró un error de LLM y un reintento programado
en modo individual, sin fallo final. La llamada más lenta fue `nuevo-18`
(18,89 s), pero el informe original no guardaba los campos de los eventos de
reintento: no se puede atribuirle ese evento ni afirmar su causa o espera
exacta. El `intento=1` de la resolución final tampoco descarta reintentos
internos del proveedor. No se observaron eventos de reintento por lote en esa
salida. No se han reconstruido métricas de tokens ni coste.

El evaluador ahora conserva, para próximas ejecuciones, eventos de fin/error
del LLM y reintentos con ID, duración, tipo de error y espera cuando existan;
no persiste mensajes de excepción en ese bloque. Este añadido no rellena
retroactivamente los informes originales ni requiere repetir esta muestra.

### Metadatos ausentes

La preparación de casos editoriales usa marcas reservadas
`__communitylab_ausente__:autor` (y equivalentes para canal, origen e idioma).
No son nombres reales: se retiran de los metadatos antes del análisis, de la
generación y del índice conversacional, y no se muestran como autores en las
fuentes del chat. Un alias real como `user1` se conserva; no se intenta adivinar
si un nombre real parece un placeholder. El texto del mensaje y los IDs de
trazabilidad no se sustituyen.

Una fecha desconocida se mantiene como `null`, sin puntos de frescura ni
coincidencias en filtros temporales. El contrato intermedio admite ahora
`fecha: null` y `tipo: null`; no admite fechas falsas o cadenas como
«desconocida». Un tipo ausente aporta cero puntos de tipo y se registra en las
advertencias; no se reemplaza por `tipo_propuesto`.

Preparación local, sin llamadas de análisis ni escritura en Oracle/OCI:

```powershell
python -m src.datos.casos_editoriales --entrada src\datos\casos_conciliados_propuestos.json --salida salida\datos\casos_editoriales --fecha-referencia 2026-10-24T00:00:00Z
```

La salida debe ser una carpeta nueva. Contiene entrada adaptada, paquete y plan
para análisis, no un resultado de capa 2. La fecha de referencia solo sirve para
puntuar fechas reales, no se asigna a mensajes sin fecha. Las etiquetas
propuestas se mantienen fuera de esa entrada y siguen en el archivo original.
La fuente de 600 casos sintéticos forma parte del repositorio en
`src/datos/casos_conciliados_propuestos.json`. El paquete derivado se genera
dentro de `salida/datos/casos_editoriales`, excluido de Git como las demás
salidas reproducibles; no depende de Descargas ni de archivos de sesión.

## Uso desde la terminal

El agente se usa directamente desde la terminal. Carga por defecto
`docs/evidencia2_entrega_ciencia_datos_completa.json` y usa las credenciales
de `.env`.

```bash
# Una pregunta y su respuesta
python -m scripts.agente_en_vivo "Crea un post de LinkedIn con testimonios positivos"

# Chat con historial de sesión: permite seguimientos como
# "y los negativos?" o "conviértelo en un post para X"
python -m scripts.agente_en_vivo
```

Opciones: `--verificar` activa `verificacion_automatica`, `--datos` usa otro
archivo de salida DS y `--detalle` muestra filtros y número de coincidencias.
Dentro del chat, `/estricto` y `/verificar` cambian el modo de verificación,
`/modo` muestra el modo actual y `/ayuda` lista los comandos. Cada borrador
indica si fue verificado y lista las afirmaciones sin respaldo.
Los eventos internos se escriben en `salida/logs/ciencia_datos.jsonl`, no en la
terminal. Las consultas al modelo consumen cuota real del proveedor.

## Uso desde código

```python
from datetime import date

from src.agentes.conversacion import AgenteConversacional

# Se puede pasar la lista `interacciones` del contrato de salida DS o
# directamente el objeto de salida que contiene `interacciones`/`resultados`.
agente = AgenteConversacional(salida_ciencia_datos)
respuesta = agente.consultar(
    "¿Qué mensajes negativos sobre Python hubo la semana pasada?",
    hoy=date(2026, 10, 21),
)

borrador = agente.consultar(
    "Crea un post para LinkedIn sobre aprendizaje",
    modo_verificacion="verificacion_automatica",
    temperatura=0.8,  # opcional, 0–1
    top_p=0.95,       # opcional, 0.1–1
)
```

El resultado contiene `respuesta`, `citas` (IDs), `total_coincidencias`,
`filtros`, `modo` y, para solicitudes de creación, un `borrador` con plataforma,
título, contenido y hashtags. Las citas permiten a la futura interfaz enlazar
la respuesta con los mensajes cargados; el agente no publica contenido.
La app presenta ese contenido como **Publicación preparada**: permite abrir los
editores compatibles con texto precargado, compartir un enlace o copiar y abrir
la red para pegarlo, según el destino (véase «Destinos y multimedia»).
La confirmación final ocurre en cada red; no hay publicación automática.
`verificacion` indica el modo y su estado: `no_verificado`,
`verificado`, `requiere_revision`, `sin_evidencia` o `no_aplica`. En modo
automático también contiene una lista breve de afirmaciones verificadas y sus
IDs de fuente. Es un chequeo automático asistido por modelo, no una garantía de
veracidad ni el razonamiento interno del modelo. La persona que inició la sesión
elige el modo y puede revisar las fuentes antes de usar el borrador.

`prompt_estricto` es el valor por defecto: normalmente hay una llamada para
interpretar y otra para responder con evidencia.
`verificacion_automatica` agrega una llamada si se redacta un borrador.
La opción solo ejecuta el verificador si se generó un borrador; las consultas
analíticas no necesitan esa revisión. La reescritura para X y los reintentos
pueden añadir llamadas.

`temperatura` y `top_p` ajustan la creatividad de la redacción y **solo se
aplican a borradores** (incluida la reescritura para X); análisis y conteos
siempre usan temperatura 0. Sin ellos se conserva el comportamiento
determinista. `ESTILOS_REDACCION` define los ajustes de la interfaz: Preciso
(0.0/1.0), Equilibrado (0.4/0.9) y Creativo (0.8/0.95). Valores fuera de rango
se rechazan con `ValueError` antes de llamar al modelo. La temperatura no
sustituye a la verificación: una temperatura alta aumenta la variedad del texto,
no su exactitud.

## Criterio editorial

El prompt es estricto en el alcance y en los hechos, no en el estilo. Permite
titulares creativos, lenguaje promocional, frases inspiradoras, hashtags
pertinentes e invitaciones a participar acordes con el objetivo del usuario.
Estas expresiones no necesitan estar copiadas de los mensajes fuente.

El verificador contrasta únicamente afirmaciones factuales: logros, cifras,
plazos, atribuciones y promesas concretas. No penaliza creatividad sin contenido
factual ni la etiqueta como un hecho verificado. Por ejemplo, «Comparte tu
experiencia» no requiere respaldo; «Todos dominarán Python en seis semanas» no
se sostiene con el logro de una persona. Tampoco se pueden fusionar testimonios
distintos como si correspondieran a una sola persona.

Cada instancia pertenece a una única sesión de usuario y conserva un historial
acotado en memoria. Actualizar la captura de la base o los adjuntos no borra
la conversación ni escribe esos turnos o adjuntos en la base.

La planificación es semántica (modelo), pero la recuperación del MVP sigue
siendo léxica sobre los campos clasificados por Ciencia de Datos; no usa
embeddings. Conteos y porcentajes se calculan en código sobre las coincidencias.
La captura se reutiliza durante una hora por sesión; el plan se interpreta
en cada turno con contexto acotado.
Los resultados generados son borradores para revisión humana.

### Destinos y multimedia

El plan y la salida comparten el contrato `PlataformaPublicacion`: LinkedIn,
Instagram, X, Facebook, WhatsApp, Telegram, Threads, Bluesky y Mastodon.
La selección se interpreta mediante el modelo, sin añadir palabras clave al
enrutamiento. Las acciones de apertura se aplican al turno actual y al historial.

X, Threads y Bluesky admiten texto en sus editores. Mastodon requiere el
servidor de la cuenta. WhatsApp abre un mensaje para elegir destinatario.
Facebook comparte un enlace facilitado por el usuario y no garantiza precargar
texto libre. El mecanismo oficial de Telegram necesita un enlace junto al texto;
sin enlace se ofrece copiar el mensaje y abrir Telegram. LinkedIn e Instagram
conservan copia manual. Ninguna acción publica automáticamente ni conecta cuentas.

### Pendientes: integración oficial y usuarios

- Registrar aplicaciones en las redes elegidas y tramitar los permisos,
  aprobaciones y límites de sus APIs. Evaluar costes antes de activarlas:
  no se promete que la publicación mediante API sea gratuita.
- Implementar la autorización del titular de cada cuenta, con OAuth cuando
  corresponda, almacenamiento seguro de tokens, renovación, revocación y
  desconexión de cuentas. Nunca pedir tokens en el chat ni guardarlos en Git.
- Crear registro o invitaciones, inicio y cierre de sesión, recuperación de
  acceso, roles y permisos por equipo, y administración de usuarios.
- Asociar las cuentas sociales a usuarios autorizados, registrar acciones y
  exigir revisión y confirmación antes de publicar.

Todo lo anterior está pendiente, no implementado. La sesión del navegador no
es una cuenta de usuario ni proporciona autenticación. Las acciones actuales
de copiar y abrir redes se mantienen sin solicitar permisos ni tokens.
La página de Ayuda presenta estas limitaciones como pendientes buscables.

TikTok y YouTube quedan pendientes del trabajo de integración multimedia:
no son destinos del contrato de texto y el intérprete debe explicar el límite
sin prometer generación, subida ni publicación de imágenes o videos.

### Reutilización para Plantillas diarias

`python -m scripts.generar_plantillas_diarias` ejecuta nueve peticiones
predefinidas a partir de las 13:00 UTC. Usa una captura de la base y
una conversación nueva por plantilla, sin datos adjuntos ni historial de
usuarios. Los posts pasan por verificación; análisis y newsletter se guardan
como texto con citas. El catálogo se almacena automáticamente para revisión
de Marketing, sin publicar en redes.

Solo los éxitos sustituyen su contenido anterior en OCI; los fallos conservan
la última versión y se reintentan sin regenerar los éxitos del mismo día.
La vista pública de Plantillas lee ese catálogo; el flujo de curaduría del lote
permanece en modo interno. El programador externo y la comprobación real de OCI
siguen pendientes de Cloud. Ver la sección «Catálogo diario» de
[integración frontend](integracion_frontend_semana5_1.md) para horario, permisos,
retención y códigos de salida.

## Validación

```powershell
python -m pytest tests/agents/test_conversacion.py tests/agents/test_interpretacion.py -q
```

Evaluación explícita con el modelo configurado y datos sintéticos (consume cuota):

```powershell
python -m pytest tests/integracion/prueba_interpretacion_agente.py -q
```
