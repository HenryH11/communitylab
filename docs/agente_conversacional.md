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
   `verificacion_automatica` agrega una llamada que revisa afirmaciones
   factuales y devuelve el resumen,
   respaldo e IDs de fuente para mostrarlos en la interfaz.

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
