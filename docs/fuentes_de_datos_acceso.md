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
| Foro de Alura (comunidad del curso) | Requiere login obligatorio — sin API pública ni RSS (ver sección abajo) | No aplica sin credenciales | Simulado (`Alura_Forum_ONE_G10`); acceso real evaluado y descartado por riesgo |
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
python src/data/ingesta_reddit.py --subreddit programacion --posts 5 --comentarios-por-post 20
```
El default es `r/programacion` (comunidad en español de programación/
desarrollo). Se puede apuntar a cualquier otro subreddit con `--subreddit`;
si no es hispanohablante, pasar también `--idioma en` (u otro código) para no
mal-etiquetar el idioma.

**Esquema de salida:** `src/data/mensajes_reddit.json` (nombre genérico, no
atado a un subreddit — cada corrida agrega un lote nuevo distinguido por
`origen_comunidad`, ej. `Reddit_r_programacion`), mismo esquema que
`src/data/mensajes_comunidad_simulados.json` (`metadata` + `lotes[]` con
`origen_comunidad`/`periodo_referencia`/`interacciones`).

**Limitaciones conocidas / decisiones tomadas:**
- `idioma` se asigna con el flag `--idioma` (default `"es"`, porque el
  subreddit por defecto — r/programacion — es hispanohablante); no hay
  detección automática de idioma. Si se apunta a un subreddit en otro idioma
  hay que pasar `--idioma` explícito, o cada interacción quedará mal
  etiquetada.
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
2. `python tests/verificar_transformacion_reddit.py` — prueba el parseo de
   Atom y la transformación con fixtures de XML (posts, comentarios,
   comentario borrado), sin red.
3. `python src/data/ingesta_reddit.py --help` — confirma que el CLI arranca
   sin ninguna configuración previa.
4. **Validado contra Reddit real** (16 de septiembre 2026): primero se probó
   contra `r/webdev` (inglés, prueba de concepto inicial) y luego, tras
   decidir usar una comunidad en español, contra `r/programacion` con
   `python src/data/ingesta_reddit.py --subreddit programacion --posts 1 --comentarios-por-post 5`.
   Se confirmó: estructura del feed Atom idéntica a lo asumido en los
   fixtures (el primer `<entry>` del feed de comentarios es el post mismo con
   fullname `t3_`, seguido de comentarios `t1_`), texto limpio sin residuos de
   HTML, y — caso nuevo que no se pudo probar con contenido en inglés —
   **tildes, ñ y signos de interrogación invertidos (¿) preservados
   correctamente en UTF-8** (ej. "básico", "¿En qué capítulo...", "Raúl
   González"). El manejo de `429` volvió a activarse (esperó 52s y reintentó
   exitosamente). Resultado conservado como evidencia en
   `tests/fixtures/prueba_reddit_controlada.json` (datos reales de Reddit,
   sin anonimizar; reemplaza la corrida anterior de r/webdev).

**Nota:** esta integración es un **diferencial opcional** según el checklist del
brief oficial; el requisito obligatorio del MVP (ingestión funcional con datos
simulados) ya está cubierto por `src/data/mensajes_comunidad_simulados.json` y no
depende de esta fuente.

## Foro de Alura — por qué no se implementó acceso real

Se evaluó el foro de Alura (`app.aluracursos.com/forum/`) como fuente
adicional real, dado que el programa ONE se dicta en esa plataforma.
Verificación directa contra la página: **requiere login obligatorio**
(redirige a `/loginForm` con el mensaje "¿Todavía no tienes acceso? ¡Estudie
con nosotros!"); no se encontró RSS, API JSON, ni ningún endpoint público sin
autenticación. Las rutas observadas (`/forum/todos/1`,
`/forum/topico-<nombre>-<id>`, `/forum/categoria-<nombre>`,
`/forum/subcategoria-<nombre>`, `/user/<nombre>`) sugieren un foro a medida
(no Discourse/phpBB), sin documentación pública de API.

**Por qué no se construyó un scraper autenticado:**
- Requeriría guardar/usar credenciales personales de Alura de un integrante
  del equipo — riesgo de seguridad y de exposición de una cuenta personal.
- Probablemente viola los Términos de Servicio de una plataforma paga
  (scraping de contenido detrás de login).
- Es frágil: HTML no documentado ni versionado, sujeto a romperse con
  cualquier cambio de la plataforma.
- No hay forma de verificar cumplimiento (p. ej. "respetar eliminaciones",
  igual que se hace con Reddit) sin acceso documentado a una API.

**Decisión:** tratar Alura como una fuente **simulada**, igual que
Discord/LinkedIn/Formulario, con el lote `Alura_Forum_ONE_G10` en
`src/data/mensajes_comunidad_simulados.json` (5 interacciones: preguntas
técnicas, testimonio, comentario y feedback, con `canal` inspirado en las
rutas reales de categorías/subcategorías observadas).

**Trabajo futuro opcional (fuera de este PR):** si el equipo decide
explícitamente asumir el riesgo, una vía menos riesgosa sería usar una
**cuenta de prueba dedicada** (no personal) con aprobación explícita del
equipo/organizadores antes de construir cualquier scraper autenticado.

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
  no llegan a `src/data/mensajes_reddit.json`.
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
