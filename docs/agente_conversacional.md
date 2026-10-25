# Flujo conversacional de CommunityLab

El MVP del agente en vivo es un flujo Python independiente de Streamlit. Recibe
resultados de Ciencia de Datos ya procesados, permite consultar y filtrar esos
mensajes, y puede generar borradores de marketing basados en evidencia. No
reemplaza el procesamiento por lotes de LangGraph ni publica en redes sociales.

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
   determinista antes de elegir hasta ocho mensajes como contexto, o la
   cantidad solicitada hasta un máximo de 20. En X se limita a tres fuentes.
4. Calcula distribuciones y conteos sobre todas las coincidencias, no solo
   sobre los mensajes incluidos en el contexto acotado.
5. Si hay evidencia, realiza una llamada estructurada al proveedor de
   generación configurado. NVIDIA NIM conserva el fallback existente a Gemini.
6. Valida que las citas correspondan a la evidencia recuperada y, cuando se
   solicitó un borrador, que la salida incluya la plataforma y hashtags
   estructurados.
7. El usuario de la sesión elige el modo para cada consulta de borrador:
   `prompt_estricto` no ejecuta una revisión separada;
   `verificacion_automatica` revisa afirmaciones factuales y devuelve el resumen,
   respaldo e IDs de fuente para mostrarlos en la interfaz. Si hay afirmaciones
   sin respaldo, intenta una única corrección con la misma evidencia y verifica
   de nuevo. Si sigue sin respaldo, faltan afirmaciones verificables o las citas
   no son válidas, lanza un error sin guardar ni habilitar ese borrador.

Cada turno requiere una llamada de interpretación. Las consultas sin
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
(hasta 20) se respeta y, si hay menos, la respuesta lo dice sin rellenar.

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

TikTok y YouTube quedan pendientes del trabajo de integración multimedia:
no son destinos del contrato de texto y el intérprete debe explicar el límite
sin prometer generación, subida ni publicación de imágenes o videos.

### Reutilización para Plantillas diarias

`python -m scripts.generar_plantillas_diarias` ejecuta nueve peticiones
predefinidas a partir de las 08:00 de Bogotá. Usa una captura de la base y
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
