# Fuentes de datos — cómo se accede a cada una

La descripción oficial (`proyecto_3_community_lab.md`) permite ingerir datos "en lote o
en tiempo real (vía JSON, CSV, webhook o integración con plataformas)". El
**producto mínimo viable obligatorio ya está cubierto** por `src/datos/mensajes_comunidad_simulados.json`
(datos simulados). Este documento cataloga cómo se accedería a cada fuente
mencionada en [`diagrama_flujo_datos_ingesta.md`](./diagrama_flujo_datos_ingesta.md),
marcando cuál ya está implementada como mejora opcional.

## Tabla comparativa

| Fuente | Cómo se accedería | Formato/mecanismo | Estado en este proyecto |
| --- | --- | --- | --- |
| Discord | Bot de Discord (`discord.py`) con permisos de lectura de canal o exportación manual del historial | Mensajes vía API o pasarela del bot | Simulado (`Discord_Grupo_ONE_G10` en datos de ejemplo) |
| Slack | Aplicación de Slack (Bolt SDK / Events API) con token OAuth y suscripción a eventos del canal | Webhook de eventos o sondeo de Conversations API | No implementado; solo conceptual |
| Foros (ej. Discourse) | API REST propia del foro (requiere clave de administración) o RSS, si está disponible | Consulta periódica mediante API/RSS | No implementado; solo conceptual |
| Foro de Alura (comunidad del curso) | Requiere inicio de sesión obligatorio — sin API pública ni RSS (ver sección abajo) | No aplica sin credenciales | Simulado (`Alura_Forum_ONE_G10`); acceso real evaluado y descartado por riesgo |
| GitHub | API REST/GraphQL o webhooks de repositorios (incidencias, PR, debates) con token de acceso personal | Webhook (tiempo real) o sondeo de API por lote | No implementado; solo conceptual |
| Formularios (Google Forms/Typeform) | Exportación manual a CSV o API de Google Sheets / webhook de respuestas | CSV por lote o webhook por respuesta | Simulado (`Formulario_Feedback_ONE_G10`); acceso real conceptual |
| **Reddit** | Canales RSS/Atom públicos de Reddit — sin clave API ni cuenta de desarrollador | Lote: publicaciones nuevas (`/new/.rss`) y comentarios por publicación (`/comments/<id>/.rss`) | **Implementado** (`src/datos/ingesta_reddit.py`) — mejora opcional |

## Reddit (implementado) — vía RSS, no PRAW/OAuth

**Por qué no usamos la API oficial con OAuth:** en 2026 Reddit deshabilitó el
registro de autoservicio de aplicaciones en `reddit.com/prefs/apps` como parte de su
"Responsible Builder Policy" (ver sección de cumplimiento más abajo y fuente
citada). El botón «crear aplicación» ya no funciona para desarrolladores
independientes sin afiliación corporativa, así que no hay forma práctica de
obtener `client_id`/`client_secret` para PRAW dentro del plazo del hackathon.
Devvit (la plataforma oficial de apps de Reddit) tampoco aplica: sirve para
apps que corren *dentro* de Reddit, no genera credenciales portables para un
script externo.

**Alternativa utilizada — canales RSS/Atom públicos:** Reddit sigue ofreciendo
RSS sin autenticación. Agregar `.rss` a un listado de subreddit genera un canal
Atom:

- Publicaciones nuevas: `https://www.reddit.com/r/<subreddit>/new/.rss`
- Comentarios de una publicación: `https://www.reddit.com/r/<subreddit>/comments/<post_id36>/.rss`

`src/datos/ingesta_reddit.py` primero trae las publicaciones recientes de la
comunidad y luego consulta los comentarios de cada una, sin registro previo.

**Paso 1 — No hay credenciales que configurar.** No hace falta `.env` ni crear
ninguna app en Reddit para esta versión.

**Paso 2 — No hay dependencias que instalar.** El programa usa solo la biblioteca
estándar de Python (`urllib`, `xml.etree`). `requirements.txt` queda vacío
para esta parte.

**Paso 3 — Ejecutar:**

```powershell
python src/datos/ingesta_reddit.py --comunidad programacion --publicaciones 5 --comentarios-por-publicacion 20
```

El valor predeterminado es `r/programacion` (comunidad en español de programación
y desarrollo). Se puede elegir otra comunidad con `--comunidad`; si usa otro
idioma, se debe indicar también `--idioma en` (u otro código).

**Esquema de salida:** `src/datos/mensajes_reddit.json` (nombre genérico; cada
ejecución agrega un lote identificado por `origen_comunidad` (por ejemplo,
`Reddit_r_programacion`). Usa el mismo esquema que
`src/datos/mensajes_comunidad_simulados.json` (`metadata` + `lotes[]` con
`origen_comunidad`/`periodo_referencia`/`interacciones`).

**Limitaciones conocidas / decisiones tomadas:**

- `idioma` toma el valor indicado por `--idioma` (por defecto, `"es"`, porque
   r/programacion es hispanohablante); no hay detección automática. Si se usa
   otra comunidad, se debe indicar su idioma para evitar etiquetarlo mal.
- `tipo` se asigna con una regla sencilla (`?` en el texto → `pregunta_tecnica`,
   si no → `comentario`); la clasificación completa la hace el flujo de IA.
- Los comentarios de cuentas eliminadas usan `autor: "usuario_eliminado"` y su
   contenido se descarta, según las reglas de cumplimiento indicadas abajo.
- RSS requiere consultas periódicas, no envía cambios automáticamente. Para
   acercarse al tiempo real habría que ejecutar el programa en intervalos; no
   es un flujo persistente como el de PRAW.
- **Límite de solicitudes de Reddit:** en pruebas, Reddit respondió `429`
   después de pocas llamadas sin autenticar (`x-ratelimit-remaining: 0.0`).
   `descargar_xml(...)` reintenta con espera progresiva, respetando
   `x-ratelimit-reset`/`Retry-After` y hasta `MAXIMO_REINTENTOS_429` intentos.
   El programa también espera `PAUSA_ENTRE_PETICIONES_SEGUNDOS` entre
   publicaciones. Con comunidades muy activas o muchas publicaciones, los
   reintentos pueden alargar la ejecución.
- El contenido de Reddit no se filtra por lenguaje. La curaduría antes de
   publicar corresponde al panel del Sub-equipo 1, no a esta etapa de ingesta.

**Cómo probar:**

1. `python -m py_compile src/datos/ingesta_reddit.py` — valida sintaxis.
2. `python -m pytest tests/test_ingesta_reddit.py -v` — prueba el análisis Atom
   y la transformación con ejemplos XML (publicaciones, comentarios y un
   comentario eliminado), sin red.
3. `python src/datos/ingesta_reddit.py --help` — confirma que el CLI arranca
   sin ninguna configuración previa.
4. **Validado contra Reddit real** (16 de septiembre 2026): primero se probó
   contra `r/webdev` (inglés, prueba de concepto inicial) y luego, tras
   decidir usar una comunidad en español, contra `r/programacion` con
   `python src/datos/ingesta_reddit.py --comunidad programacion --publicaciones 1 --comentarios-por-publicacion 5`.
   Se confirmó: estructura del feed Atom idéntica a lo asumido en los
   ejemplos (el primer `<entry>` del canal de comentarios es la publicación
   misma con identificador `t3_`, seguida de comentarios `t1_`), texto limpio sin residuos de
   HTML, y — caso nuevo que no se pudo probar con contenido en inglés —
   **tildes, ñ y signos de interrogación invertidos (¿) preservados
   correctamente en UTF-8** (ej. "básico", "¿En qué capítulo...", "Raúl
   González"). El manejo de `429` volvió a activarse (esperó 52s y reintentó
   exitosamente). Resultado conservado como evidencia en
   `tests/fixtures/prueba_reddit_controlada.json` (datos reales de Reddit,
   sin anonimizar; reemplaza la corrida anterior de r/webdev).

**Nota:** esta integración es un **diferencial opcional** según la lista de
verificación oficial; el requisito del producto mínimo viable (ingesta funcional con datos
simulados) ya está cubierto por `src/datos/mensajes_comunidad_simulados.json` y no
depende de esta fuente.

## Foro de Alura — por qué no se implementó acceso real

Se evaluó el foro de Alura (`app.aluracursos.com/forum/`) como fuente
adicional real, dado que el programa ONE se dicta en esa plataforma.
Verificación directa contra la página: **requiere inicio de sesión obligatorio**
(redirige a `/loginForm` con el mensaje "¿Todavía no tienes acceso? ¡Estudie
con nosotros!"); no se encontró RSS, API JSON, ni ningún endpoint público sin
autenticación. Las rutas observadas (`/forum/todos/1`,
`/forum/topico-<nombre>-<id>`, `/forum/categoria-<nombre>`,
`/forum/subcategoria-<nombre>`, `/user/<nombre>`) sugieren un foro a medida
(no Discourse/phpBB), sin documentación pública de API.

**Por qué no se construyó un recolector automatizado autenticado:**
  del equipo — riesgo de seguridad y de exposición de una cuenta personal.
  (scraping de contenido detrás de inicio de sesión).
  cualquier cambio de la plataforma.
  igual que se hace con Reddit) sin acceso documentado a una API.

**Decisión:** tratar Alura como una fuente **simulada**, igual que
Discord/LinkedIn/Formulario, con el lote `Alura_Forum_ONE_G10` en
`src/datos/mensajes_comunidad_simulados.json` (5 interacciones: preguntas
técnicas, testimonio, comentario y feedback, con `canal` inspirado en las
rutas reales de categorías/subcategorías observadas).

**Trabajo futuro opcional (fuera de este PR):** si el equipo decide
explícitamente asumir el riesgo, una vía menos riesgosa sería usar una
**cuenta de prueba dedicada** (no personal) con aprobación explícita del
equipo/organizadores antes de construir cualquier recolector automatizado autenticado.

## Cumplimiento y privacidad (Reddit)

**Contexto del cambio de método:** en 2026 Reddit implementó su "Responsible
Builder Policy" y desactivó la creación autoservicio de apps OAuth en
`reddit.com/prefs/apps` (para frenar scraping masivo de datos por empresas de
IA y apps de terceros no autorizadas, y empujar a los desarrolladores hacia
Devvit). Para un desarrollador independiente sin afiliación corporativa, el
formulario oficial de solicitud de acceso tiene una tasa de rechazo muy alta,
por lo que no era viable dentro del plazo del hackathon
([fuente](https://redditorshop.com/blog/the-end-of-the-self-serve-reddit-api-why-you-can-t-create-an-api-key-in-2026)).
Por eso se usa RSS/Atom público en vez de PRAW/OAuth — es un mecanismo
soportado y documentado por la propia Reddit, no scraping de HTML.

Independientemente del mecanismo de acceso (RSS, API con OAuth o Devvit),
se aplican las mismas reglas de la plataforma sobre los datos de las personas:

- **Respetar eliminaciones:** si un comentario se borra o es retirado por
   moderación en Reddit, no debe conservarse. `src/datos/ingesta_reddit.py`
   implementa `comentario_fue_eliminado(...)` y descarta textos `"[deleted]"` /
   `"[removed]"` o autores `"[deleted]"` antes de guardar el contenido.
- **Sin perfilado personal:** el proyecto no infiere ni almacena atributos
   protegidos. La clasificación se limita al campo `tipo` para curar contenido,
   no para perfilar personas.
- **Sin vigilancia, reventa ni entrenamiento externo:** los datos se usan
   únicamente dentro de CommunityLab para activos y análisis internos; no se
   venden, comparten con terceros ni se usan para entrenar modelos externos.
- **Solo datos públicos:** se leen publicaciones y comentarios de comunidades
   públicas; no se accede a mensajes privados, votos, contenido guardado ni a
   información que requiera permisos adicionales.
- **Identificación transparente:** el programa envía una cabecera `User-Agent`
   descriptiva (`AGENTE_USUARIO_POR_DEFECTO`), configurable con
   `--agente-usuario`, en vez de simular ser un navegador.
