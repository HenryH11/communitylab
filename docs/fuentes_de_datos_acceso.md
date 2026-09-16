# Fuentes de datos — cómo se accede a cada una

El brief oficial (`proyecto_3_community_lab.md`) permite ingerir datos "en lote o
en tiempo real (vía JSON, CSV, Webhook o integración con plataformas)". El
**MVP obligatorio ya está cubierto** por `src/data/mensajes_comunidad_simulados.json`
(datos simulados). Este documento cataloga cómo se accedería a cada fuente
mencionada en [`diagrama_flujo_datos_ingesta.md`](./diagrama_flujo_datos_ingesta.md),
marcando cuál ya está implementada como diferencial opcional.

## Tabla comparativa

| Fuente | Cómo se accedería | Formato/mecanismo | Estado en este proyecto |
|---|---|---|---|
| Discord | Bot de Discord (`discord.py`) con permisos de lectura de canal, o export manual de historial | Mensajes vía API/gateway del bot | Simulado (`Discord_Grupo_ONE_G10` en datos de ejemplo) |
| Slack | App de Slack (Bolt SDK / Events API) con OAuth token y suscripción a eventos de canal | Webhook de eventos o polling de Conversations API | No implementado, solo conceptual |
| Foros (ej. Discourse) | API REST propia del foro (requiere API key de admin) o RSS del foro si está disponible | Polling periódico vía API/RSS | No implementado, solo conceptual |
| GitHub | GitHub REST/GraphQL API o webhooks de repos (issues, PRs, discussions) con Personal Access Token | Webhook (tiempo real) o polling API (lote) | No implementado, solo conceptual |
| Formularios (Google Forms/Typeform) | Export CSV manual, o Google Sheets API / webhook de respuestas del formulario | CSV en lote o webhook por respuesta | Simulado (`Formulario_Feedback_ONE_G10`); acceso real conceptual |
| **Reddit** | Feeds RSS/Atom públicos de Reddit — sin API key ni cuenta de desarrollador | Batch: posts nuevos (`/new/.rss`) + comentarios por post (`/comments/<id>/.rss`) | **Implementado** (`src/data/ingesta_reddit.py`) — diferencial opcional |

## Reddit (implementado) — vía RSS, no PRAW/OAuth

**Por qué no usamos la API oficial con OAuth:** en 2026 Reddit deshabilitó la
creación self-serve de apps en `reddit.com/prefs/apps` como parte de su
"Responsible Builder Policy" (ver sección de cumplimiento más abajo y fuente
citada). El botón "create app" ya no funciona para desarrolladores
independientes sin afiliación corporativa, así que no hay forma práctica de
obtener `client_id`/`client_secret` para PRAW dentro del plazo del hackathon.
Devvit (la plataforma oficial de apps de Reddit) tampoco aplica: sirve para
apps que corren *dentro* de Reddit, no genera credenciales portables para un
script externo.

**Alternativa usada — feeds RSS/Atom públicos:** Reddit sigue exponiendo RSS
sin autenticación. Agregar `.rss` a cualquier listado de un subreddit da un
feed Atom:
- Posts nuevos: `https://www.reddit.com/r/<subreddit>/new/.rss`
- Comentarios de un post puntual: `https://www.reddit.com/r/<subreddit>/comments/<post_id36>/.rss`

`src/data/ingesta_reddit.py` primero trae los posts recientes del subreddit y
luego, por cada uno, sus comentarios — sin necesitar ningún registro previo.

**Paso 1 — Sin credenciales que configurar.** No hace falta `.env` ni crear
ninguna app en Reddit para esta versión.

**Paso 2 — Sin dependencias que instalar.** El script usa solo librería
estándar de Python (`urllib`, `xml.etree`). `requirements.txt` queda vacío
para esta parte.

**Paso 3 — Ejecutar:**
```
python src/data/ingesta_reddit.py --subreddit webdev --posts 5 --comentarios-por-post 20
```

**Esquema de salida:** `src/data/mensajes_reddit_webdev.json`, mismo esquema que
`src/data/mensajes_comunidad_simulados.json` (`metadata` + `lotes[]` con
`origen_comunidad`/`periodo_referencia`/`interacciones`). Cada corrida añade un
lote nuevo, no sobrescribe los anteriores.

**Limitaciones conocidas / decisiones tomadas:**
- `idioma` queda fijo en `"en"` por defecto (Reddit es mayormente en inglés); no
  hay detección real de idioma todavía.
- `tipo` se asigna con heurística simple (`?` en el texto → `pregunta_tecnica`,
  si no `comentario`); la clasificación fina la hace el pipeline de IA del
  Sub-equipo 2.
- Comentarios de cuentas borradas o eliminados se marcan con
  `autor: "usuario_eliminado"` en vez de `null`, y su contenido se descarta
  (ver cumplimiento más abajo).
- RSS es *pull* (hay que consultar periódicamente), no *push*: para algo
  parecido a "tiempo real" habría que correr este script cada cierto
  intervalo (ej. tarea programada/cron), no es un stream persistente como el
  que ofrecía PRAW.
- **Rate limiting de Reddit:** en pruebas reales, Reddit devuelve `429 Too Many
  Requests` a peticiones sin autenticar después de solo 1-2 llamadas seguidas
  (`x-ratelimit-remaining: 0.0`). `descargar_xml(...)` reintenta con backoff
  (respetando `x-ratelimit-reset`/`Retry-After` si Reddit los envía, hasta
  `REINTENTOS_429_MAX` veces), y el script espera
  `PAUSA_ENTRE_PETICIONES_SEGUNDOS` entre cada post para no dispararlo
  innecesariamente. Con subreddits muy activos o `--posts` alto, de todas
  formas puede tardar más por los reintentos — es esperable, no un error.
- El contenido de los comentarios no pasa por ningún filtro de lenguaje: en la
  prueba real aparecieron comentarios con groserías. Es contenido público sin
  editar, tal como lo pide el brief para la etapa de ingesta — la curaduría
  (filtrar antes de publicar) es responsabilidad del panel de Streamlit que
  arma Sub-equipo 1, no de esta etapa.

**Cómo probar:**
1. `python -m py_compile src/data/ingesta_reddit.py` — valida sintaxis.
2. `python src/data/verificar_transformacion_reddit.py` — prueba el parseo de
   Atom y la transformación con fixtures de XML (posts, comentarios,
   comentario borrado), sin red.
3. `python src/data/ingesta_reddit.py --help` — confirma que el CLI arranca
   sin ninguna configuración previa.
4. **Validado contra Reddit real** (16 de septiembre 2026): se corrió
   `python src/data/ingesta_reddit.py --subreddit webdev --posts 1 --comentarios-por-post 5`
   contra `r/webdev` real. Se confirmó: estructura del feed Atom idéntica a lo
   asumido en los fixtures (el primer `<entry>` del feed de comentarios es el
   post mismo con fullname `t3_`, seguido de comentarios `t1_`), texto limpio
   sin residuos de HTML, tildes/comillas UTF-8 preservadas correctamente, y el
   manejo de `429` funcionando (esperó y reintentó exitosamente).

**Nota:** esta integración es un **diferencial opcional** según el checklist del
brief oficial; el requisito obligatorio del MVP (ingestión funcional con datos
simulados) ya está cubierto por `src/data/mensajes_comunidad_simulados.json` y no
depende de esta fuente.

## Cumplimiento y privacidad (Reddit)

**Contexto del cambio de método:** en 2026 Reddit implementó su "Responsible
Builder Policy" y desactivó la creación self-serve de apps OAuth en
`reddit.com/prefs/apps` (para frenar scraping masivo de datos por empresas de
IA y apps de terceros no autorizadas, y empujar a los desarrolladores hacia
Devvit). Para un desarrollador independiente sin afiliación corporativa, el
formulario oficial de solicitud de acceso tiene una tasa de rechazo muy alta,
por lo que no era viable dentro del plazo del hackathon
([fuente](https://redditorshop.com/blog/the-end-of-the-self-serve-reddit-api-why-you-can-t-create-an-api-key-in-2026)).
Por eso se usa RSS/Atom público en vez de PRAW/OAuth — es un mecanismo
soportado y documentado por la propia Reddit, no scraping de HTML.

Independientemente del mecanismo de acceso (RSS, API con OAuth o Devvit),
aplican las mismas reglas de la plataforma sobre los datos de los usuarios:

- **Respetar eliminaciones:** si un comentario se borra o es removido por
  moderación en Reddit, no debe conservarse. `src/data/ingesta_reddit.py`
  implementa `comentario_fue_eliminado(...)`, que descarta cualquier
  comentario cuyo texto sea literalmente `"[deleted]"`/`"[removed]"` (o cuyo
  autor aparezca como `"[deleted]"`) **antes** de transformarlo o guardarlo —
  no llegan a `src/data/mensajes_reddit_webdev.json`.
- **Sin perfilado de características personales:** el proyecto no infiere ni
  almacena atributos protegidos de los usuarios (etnia, opiniones políticas,
  salud, orientación sexual, etc.). La única clasificación que se hace es
  `tipo` de interacción (testimonio/pregunta_tecnica/comentario/feedback) para
  fines de curaduría de contenido de marketing, no para perfilar personas.
- **Sin vigilancia, reventa ni entrenamiento de modelos externos:** los datos
  ingeridos se usan exclusivamente dentro del pipeline de este proyecto
  (CommunityLab) para generar activos de marketing y análisis internos; no se
  venden, comparten con terceros, ni se usan para entrenar modelos de IA fuera
  del alcance del hackathon.
- **Datos públicos únicamente:** solo se leen posts y comentarios públicos de
  subreddits públicos, vía los feeds RSS que Reddit expone para ese fin; no se
  accede a mensajes privados, historial de voto, contenido guardado ni ningún
  dato que requiera permisos más allá de lectura pública.
- **Identificación honesta:** el script se identifica con un `User-Agent`
  descriptivo (`USER_AGENT_POR_DEFECTO` en `src/data/ingesta_reddit.py`,
  configurable con `--user-agent`) en vez de simular ser un navegador.
