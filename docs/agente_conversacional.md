# Flujo conversacional de CommunityLab

El MVP del agente en vivo es un flujo Python independiente de Streamlit. Recibe
resultados de Ciencia de Datos ya procesados, permite consultar y filtrar esos
mensajes, y puede generar borradores de marketing basados en evidencia. No
reemplaza el procesamiento por lotes de LangGraph ni publica en redes sociales.

## Flujo

1. Valida la consulta y rechaza solicitudes explícitas de programación o de
   actualidad externa.
2. Extrae filtros conocidos de forma determinista: sentimiento, tipo de
   interacción, período relativo y plataforma para borradores.
3. Busca términos sobre un índice invertido construido una vez al crear la
   instancia. Aplica los filtros antes de elegir hasta ocho mensajes como
   contexto para el modelo.
4. Calcula distribuciones y conteos sobre todas las coincidencias, no solo
   sobre los mensajes incluidos en el contexto acotado.
5. Si hay evidencia, realiza una llamada estructurada al proveedor de
   generación configurado. NVIDIA NIM conserva el fallback existente a Gemini.
6. Valida que las citas correspondan a la evidencia recuperada y, cuando se
   solicitó un borrador, que la salida incluya la plataforma y hashtags
   estructurados.
7. El usuario de la sesión elige el modo para cada consulta de borrador:
   `prompt_estricto` usa una llamada; `verificacion_automatica` agrega una
   segunda llamada que revisa afirmaciones factuales y devuelve el resumen,
   respaldo e IDs de fuente para mostrarlos en la interfaz.

Las consultas sin coincidencias y las solicitudes fuera del alcance no llaman
al modelo. Las fechas relativas se calculan en UTC; `hoy` permite fijar la fecha
para pruebas reproducibles. El filtro `positivo` incluye `muy_positivo` y
`negativo` incluye `muy_negativo`; `muy positivo` filtra solo ese valor. Si el
modelo propone un borrador en una consulta analítica, se descarta.

Cuando no hay coincidencias, el agente explica el motivo sin llamar al modelo:
términos que ningún mensaje menciona, filtros sin resultados, falta de fechas o
mensajes no aptos para contenido, junto con los sentimientos y tipos
disponibles. Pedidos como "los 20 mejores comentarios" se interpretan como
mensajes positivos ordenados con `muy_positivo` primero; la cantidad pedida
(hasta 20) se respeta y, si hay menos, la respuesta lo dice sin rellenar.

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
)
```

El resultado contiene `respuesta`, `citas` (IDs), `total_coincidencias`,
`filtros`, `modo` y, para solicitudes de creación, un `borrador` con plataforma,
título, contenido y hashtags. Las citas permiten a la futura interfaz enlazar
la respuesta con los mensajes cargados; el agente no publica contenido.
`verificacion` indica el modo y su estado: `no_verificado`,
`verificado`, `requiere_revision`, `sin_evidencia` o `no_aplica`. En modo
automático también contiene una lista breve de afirmaciones verificadas y sus
IDs de fuente. Es un chequeo automático asistido por modelo, no una garantía de
veracidad ni el razonamiento interno del modelo. La persona que inició la sesión
elige el modo y puede revisar las fuentes antes de usar el borrador.

`prompt_estricto` es el valor por defecto y realiza una llamada al modelo.
`verificacion_automatica` puede requerir una segunda llamada y más tiempo/tokens.
La opción solo ejecuta el verificador si se generó un borrador; las consultas
analíticas no necesitan la segunda llamada.

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

Cada instancia conserva un historial acotado en memoria. La instancia debe
pertenecer a una única sesión de usuario y a un único conjunto de datos. No se
crean cuentas, se escriben conversaciones en disco ni se usa una base de datos.
Un adaptador de almacenamiento puede sustituir la fuente de mensajes cuando se
incorpore la base de datos futura.

La búsqueda del MVP es lexical y usa los campos ya clasificados por Ciencia de
Datos; no hace una llamada adicional al modelo para planear la búsqueda, ni usa
embeddings. Está acotada en contexto para reducir tokens, pero todavía no
implementa una política de caché, medición de latencia ni búsqueda semántica.
Los resultados generados son borradores para revisión humana.

## Validación

```powershell
python -m pytest tests/agents/test_conversacion.py -q
```
