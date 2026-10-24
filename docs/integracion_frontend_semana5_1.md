# Integración de la página de Plantillas (Semana 5.1)

Rama: `feature/integracion-diseno-semana5.1`, creada desde `origin/develop`
(`10bdc92`, 2026-10-19). Acordado en Discord (18/10): Ramses integra las
plantillas y Eduardo prepara los casos de prueba del chat.

## Estado de partida

### Inicio de Marketing

La identidad usa el logo **Núcleo** (dos cintas y una semilla), centralizado
en `src/app/tema.py`. Cabecera, footer, Ayuda, agente e icono de pestaña
comparten la misma geometría, con color adaptado a cada superficie.
La cabecera y las pestañas comparten sus estilos en `tema.py` en todas las
vistas; el agente solo adapta la paleta al fondo nocturno. Sus selectores
no afectan a los radios de los ajustes del chat.

Los ajustes del agente se renderizan en un fragmento de Streamlit: cambiar
modelo, redacción o verificación actualiza únicamente los controles, sin
volver a dibujar la conversación ni consultar la fuente. La siguiente pregunta
lee los ajustes actuales del estado de sesión. Quitar un adjunto sí actualiza
la vista completa para reflejar el cambio de datos, conservando el historial.

El Inicio público se renderiza desde `src/app/vista_inicio.py`: hero,
conversación ilustrativa, capacidades, tres ejemplos de plantillas y footer.
Los botones usan la navegación de Streamlit, sin recargar la sesión ni llamar
a la IA. El Inicio interno conserva el acceso al flujo de Datos y su estado.
Los ejemplos no representan consultas reales ni contenido del catálogo.

El degradado de fondo es fijo y exclusivo de Inicio. Los textos aparecen al
entrar en pantalla mediante `IntersectionObserver`, respetando la preferencia
de movimiento reducido; sin JavaScript, el contenido permanece visible.
La portada ocupa el espacio restante de la primera pantalla, descontando la
marca y la navegación; el recorrido comienza fuera del área visible. Una flecha
decorativa y no interactiva invita a bajar. Tras desplazar 120 píxeles se oculta
y guarda esa preferencia en el navegador (localStorage), incluso entre recargas.
Si el almacenamiento está bloqueado, se avisa en consola y se conserva la
preferencia durante la vida de la página. Su movimiento se desactiva
con la preferencia de movimiento reducido. El footer usa botones terciarios
sin recuadro y el ejemplo presenta los turnos como una conversación.
El recorrido usa espaciado compacto, énfasis tipográfico y tarjetas alineadas
con acentos de color discretos, sin giros ni decoración de notas adhesivas.
El footer agrupa la navegación en una fila adaptable, con marca e información
de contacto en columnas y una línea legal separada.
La animación requiere el soporte de `st.html(unsafe_allow_javascript=True)`
de Streamlit 1.65 o posterior. El footer remite al administrador de la
instalación mientras no exista un canal oficial de contacto.

- **Diseño:** Jhonattan, rama `feature/frontend-streamlit-local`. Dos vistas del
  boceto: *Plantillas* (el catálogo) y *Resultado* (la plantilla abierta). En su
  rama todo es simulado: el SVG lleva botones transparentes encima y
  `simular_plantilla` arma los borradores sin IA.
- **App funcional:** develop, `src/app/app.py`. Tiene el pipeline real, las
  gráficas y la curaduría (editar, aprobar y guardar en OCI). La curaduría la
  escribió Eduardo en `0908e66`, y Marco y Renato la completaron.
- **Eduardo en la Semana 5.1** (`feature/streamlit-agente-vivo-semana5.1`, sin cambios en `src/app`):
  - QA-1, archivo vacío: `tests/test_archivo_vacio.py`.
  - QA-2, latencia: 23 mensajes en 283 a 392 s con Gemini, es decir, unos 12 a 17 s por mensaje y muy variable.
  - Riesgo que anotó: perder el procesamiento y la curaduría si se fusiona el frontend nuevo sin revisarlo.
  - QA-3, la regresión del frontend nuevo, la deja pendiente hasta que se defina la integración.

**Decisión:** el código sale de develop y el diseño de Jhonattan, rehecho
con componentes nativos de Streamlit. Las plantillas **no vuelven a llamar a
la IA**: muestran y curan lo que el pipeline ya generó. Con la latencia que
midió Eduardo, una llamada por clic no es viable para la demo.

## Las 6 plantillas del boceto frente a lo que genera el pipeline

El pipeline (`nodos_generadores.py`) produce por mensaje `activos_generados` de
cinco tipos: `linkedin`, `boletin`, `preguntas_frecuentes`, `caso_exito` e
`insight_mejora`. Además, el análisis aporta `sentimiento`, `tema_principal`,
`subtema` y `tipo_detectado`. La curaduría solo valida y guarda en OCI esos
cinco tipos (`curaduria_oci.MODELOS_ACTIVO`).

| Plantilla del boceto | Categoría | Fuente real | Estado |
| --- | --- | --- | --- |
| Publicación para LinkedIn | Contenido | activo `linkedin` (`titulo`, `contenido`, `hashtags`) | ✅ Directa, con curaduría y OCI |
| Preguntas de la comunidad | Conocimiento | activo `preguntas_frecuentes` (`tema`, `respuesta`) | ✅ Directa, con curaduría y OCI |
| Sentimiento de comunidad | Analítica | campo `sentimiento` de cada mensaje | ✅ Calculada: gráfica de dona y resumen, sin IA ni curaduría |
| Temas y tendencias | Analítica | `tema_principal` y `subtema` | ✅ Calculada: ranking y gráfica de barras, sin IA |
| Post para Instagram | Contenido | **no hay generador** | ⚠️ Ver opciones |
| Publicación para X | Contenido | **no hay generador** | ⚠️ Ver opciones |

Además hay tres activos reales que el boceto no tiene: **Newsletter**
(`boletin`), **Caso de éxito** (`caso_exito`) y **Oportunidades de mejora**
(`insight_mejora`). Propongo añadirlos como tarjetas en *Contenido para redes*
y *Analíticas*, porque ya funcionan con curaduría y OCI.

### Instagram y X: próximamente

Decisión del 20/10: se muestran en el catálogo como **"Próximamente"**,
sin borradores, hasta que el equipo decida si DS añade las rutas `instagram`
y `x` (prompt, modelo Pydantic y entrada en `MODELOS_ACTIVO`). Cuando existan,
basta con cambiar su `fuente` a `"activo"` en `plantillas_catalogo.py`.

## Diseño de la página

En `st.tabs`, la pestaña **Plantillas** tiene dos partes.

**A. Catálogo**, según la vista "Elige el resultado que necesitas":
- Columna izquierda: buscador (`st.text_input`), categoría (`st.radio`: Todas, Contenido para redes, Analíticas, Preguntas frecuentes) y "Fuente de datos: JSON importado · redes conectadas: no requeridas".
- Cuadrícula de tarjetas en `st.columns(2)`: icono, nombre, etiqueta de categoría, descripción y un **contador real**, por ejemplo "8 borradores". Ordenar: recomendadas o por número de borradores.
- Sin resultado procesado: tarjetas atenuadas con el aviso "Todavía no hay un lote procesado".

**B. Resultado**, según la vista "Publicación generada a partir de conversaciones":
- Una sub-pestaña por plantilla (`st.tabs`) para abrirla.
- Izquierda: *Configuración*, de solo lectura (lote, formato de salida, objetivo y tono fijos de la plantilla) y la nota "La plantilla define la tarea. No muestra prompts al usuario."
- Centro: *Resultado estructurado*, con un selector de borrador ("1 de 8 · autor · tema"), los editores de la curaduría actual (`st.text_area`) y los botones **Aprobar**, **Copiar contenido** y **Abrir LinkedIn ↗**.
- Derecha: *Vista previa* tipo tarjeta de la red social, con el aviso "La apertura no publica automáticamente".
- Al final, el bloque actual "Activos aprobados listos para OCI" con el botón `guardar_aprobados_oci`.

### Restricciones de las pruebas (no romper)

- `test_curaduria_oci.py` arranca `app.py` con un `resultado` y busca
  `text_area` cuya clave termine en `linkedin_contenido`, botones `…int-demo_linkedin` y
  `guardar_aprobados_oci`. Por eso las sub-pestañas de B tienen que pintarse
  **todas**: `st.tabs` lo hace, mientras que un selector que solo pinta la plantilla activa
  ocultaría los editores. Hay que conservar las claves actuales (`edit_{lote}_{id}_{tipo}_{campo}`,
  `btn_{lote}_{id}_{tipo}`) y **mover** la curaduría a esta pestaña, sin duplicarla: con claves
  repetidas, Streamlit da error.
- El selector "1 de 8" no puede ocultar los editores de los demás
  borradores. Dentro de cada sub-pestaña, cada borrador va en un `st.expander` con el
  primero abierto.
- `test_tolerancia_app.py`: el pipeline sigue en `app.py`, dentro de `try` y sin `st.rerun`.

## Implementado en esta rama

```
src/app/plantillas_catalogo.py  # 9 plantillas (7 activas, Instagram y X próximamente), filtros y contadores; sin Streamlit
src/app/vista_plantillas.py     # catálogo + pestañas de resultado + curaduría + guardado en OCI (movidos desde app.py)
src/app/app.py                  # pipeline y analíticas sin cambios; al final llama a vista_plantillas.render()
tests/test_plantillas.py        # catálogo, contadores, filtros y render con AppTest
```

- La curaduría conserva sus claves y su comportamiento: `test_curaduria_oci.py` pasa sin cambios.
- Los tipos de activo que el catálogo no conozca aparecen en una pestaña "Otros activos", para no perderlos.
- Suite completa: 620 pruebas aprobadas (sin `tests/integracion`, que llama a proveedores reales).

## Actualización de interfaz (22 de octubre de 2026)

La app integra una navegación superior con las vistas **Inicio**, **Datos**,
**Agente**, **Análisis**, **Plantillas** y **Ayuda**. La carga JSON conserva
el procesamiento existente y ahora muestra una vista previa de hasta 20
interacciones antes de procesar. Análisis mantiene las métricas, gráficas y el
detalle de solo lectura. Plantillas conserva las claves de edición, aprobación
y guardado en OCI, con configuración, editor y previsualización organizados en
tres paneles. La paleta global vive en `.streamlit/config.toml`.

La pestaña **Agente** explica el flujo real, pero no simula un chat: el proyecto
no tiene una función de respuesta a preguntas libres. Instagram y X continúan
como próximas plantillas hasta que exista un generador. La validación final del
diseño debe hacerse en el navegador con lotes representativos y el entorno OCI
configurado si se prueba el guardado.

## Identidad visual y agente en vivo (23 de octubre de 2026)

- Paleta "pergamino y miel": las vistas generales usan pergamino claro, tinta
  sepia, miel y musgo (`.streamlit/config.toml` para los widgets nativos y
  `src/app/tema.py` para tipografía, marca y estilos compartidos).
- El logo es una espiral minimalista (`tema.espiral()`), presente en la barra de
  marca, el agente y la ayuda.
- **Agente** es ahora un chat en vivo con estética gótica formal
  (`src/app/estilo_agente.py`): la versión nocturna de la misma paleta (ébano,
  bosque y miel encendida). Congenia con el resto de la app, pero resalta por
  contraste de luz.
- **Ayuda** (`src/app/vista_ayuda.py`) incluye el flujo en cuatro pasos con
  accesos directos, preguntas frecuentes por tema (datos, agente, plantillas y
  problemas comunes) presentadas como bloques en cuadrícula, y una búsqueda que
  ignora mayúsculas y acentos. Los textos de ayuda no mencionan código, archivos
  ni variables de entorno: el usuario final no tiene acceso a ellos.
- Ajustes tras la revisión de equipo: solo pesos bold (títulos) y light (texto)
  con Inter para el cuerpo; barra de marca y títulos más grandes; fondos sólidos
  sin texturas ni resplandores (se veían borrosos); el texto va en blanco y el
  dorado queda para acentos, sin dorado sobre dorado (pestaña activa, insignia
  de inicio, bordes del agente).
- Controles del agente junto a la entrada del chat (`st.bottom`): se retiró la
  barra de estado ("Lote procesado · N mensajes · N con activos"), que no le
  aportaba al usuario. Ahora hay un interruptor de **Verificación automática** y
  un botón **Redacción** con dos formas de ajuste: **Estilos** (Preciso 0.0/1.0,
  Equilibrado 0.4/0.9 por defecto, Creativo 0.8/0.95 de temperatura/top_p) o
  **Manual** (deslizadores de temperatura 0–1 y top_p 0.1–1). Todo se puede
  cambiar en cualquier momento del chat. La creatividad solo se aplica a
  borradores; análisis y conteos siguen en temperatura 0.
- Errores del agente: en lugar del error técnico se muestra un aviso claro
  (`src/app/errores_agente.py`): modelo no disponible, acceso rechazado, límite
  de uso, servicio caído o sin conexión con el servicio de IA o la fuente de
  datos. El detalle técnico queda en el log. Este mismo patrón cubrirá la
  futura conexión a base de datos.
- Conteos de mensajes: solo se muestran para los datos que adjunta el usuario
  (botón **Tus datos**), no para la base.

## Fuente de datos del agente: base de la comunidad + datos del usuario

- **Datos sale del frontend público.** Es el flujo interno del equipo
  (importar → procesar con la segunda capa → publicar en la base). Solo aparece
  en la entrada independiente `src/app/app_interna.py`. Marketing ejecuta
  `src/app/app.py`: su navegación es Inicio, Agente, Análisis, Plantillas y Ayuda,
  incluso si el servidor conserva `COMMUNITYLAB_MODO_INTERNO=1`.
  Esta variable ya no habilita funciones internas. Ver el aislamiento de procesos,
  credenciales y acceso en [Docker para Cloud](docker_cloud_semana4.md).
- **Captura de la base** (`src/app/fuente_agente.py`): el agente lee
  `conjunto_consultable` completo una vez por sesión con el usuario de solo
  lectura (`db_client.obtener_conexion_lectura` + `leer_conjunto`) y reutiliza
  esa captura para todas las preguntas. A la hora la vuelve a leer. Si la base
  falla y hay una captura previa, la sigue usando y avisa cuántos minutos
  tiene; sin captura previa, explica el motivo (no conectada, sin datos
  publicados, en actualización o sin conexión). Tras un fallo espera 2 minutos
  antes de reintentar, para no consultar la base en cada clic.
- **Mapeo al agente:** `id → id`, `contenido_textual → texto`, `canal`,
  `sentimiento`, `tema → tema_principal`, `tipo → tipo_detectado`, `fecha`.
  La base no trae autor ni elegibilidad; las respuestas citan el id.
- **Datos del usuario:** se adjuntan con el clip de la caja de texto (JSON, CSV
  o TXT, hasta 5 MB y 5.000 mensajes por archivo). No exigen estructura: se
  detecta la columna de texto por nombre (`texto`, `comentario`, `message`…)
  o, si no hay ninguna conocida, la de textos más largos; también autor, canal
  y fecha si existen. Un TXT es un mensaje por línea. Se combinan con la
  captura solo en la sesión (ids sin colisiones) y nunca se escriben en la base.
- Al cambiar la captura o los archivos, el agente actualiza sus datos con
  `AgenteConversacional.actualizar_datos` sin perder la conversación.
- En `src/app/app_interna.py`, con un lote procesado en Datos, el agente usa
  ese lote (para revisarlo antes de publicarlo) en lugar de la base.
- Pendiente: Análisis y Plantillas siguen dependiendo de un lote procesado
  internamente; la base no guarda activos.

## Interpretación del lenguaje en el agente

- El modelo separa saludos, aclaraciones, tareas sobre los datos y solicitudes
  fuera de alcance antes de buscar. Se retiraron los diccionarios y regex de
  interpretación; la recuperación y los conteos siguen siendo deterministas.
- Un mensaje puede saludar y pedir un post: solo los temas reales entran en la
  búsqueda; plataforma, sentimiento y cantidad pasan como filtros.
- Saludos y aclaraciones no necesitan mensajes cargados: la interfaz permite
  conversar aun si la base no está disponible.
- Cada turno añade una llamada de interpretación a temperatura 0, con
  historial y último plan acotados. Si falla, se muestra el error sin recurrir
  silenciosamente al intérprete anterior.

## Controles compactos y modelo de respuesta

Las explicaciones se abren desde un icono **i** junto a Modelo, Redacción y
Modo: al pasar el puntero o enfocar con teclado se muestra una tarjeta en los
márgenes laterales (pantallas de 1350 px o más), sin tapar el chat central.
En móvil se superpone una tarjeta limitada al ancho de pantalla; tocar el
icono permite abrirla y cerrarla. Los menús conservan solo sus controles.
Los nombres de adjuntos usan texto blanco cálido sobre nogal con tipografía
Inter/Segoe UI y peso normal para asegurar legibilidad.

- Barra adaptable con **Modelo**, **Redacción**, **Estricto/Verificado** y
  **Tus datos** (solo con adjuntos). Los paneles tienen hasta 330 px de ancho,
  limitado por la pantalla; la lista de archivos tiene desplazamiento interno.
- Modelo: Super recomendado y Lightning ligero. Solo cambia las respuestas
  siguientes, sin recrear el agente, cambiar el intérprete/verificador ni
  modificar variables de entorno compartidas. Los proveedores conservan su
  respaldo operativo.
- Redacción: selector compacto con explicación del estilo activo. Preciso =
  sobrio/directo; Equilibrado = variedad moderada; Creativo = más variedad
  editorial sin inventar hechos. Manual usa dos campos numéricos en la misma
  fila, con ayuda sobre temperatura y top_p, en lugar de deslizadores.
- Los valores manuales y el estilo elegido se conservan al alternar.
- Estricto y Verificado explican su diferencia en una línea junto al
  interruptor; ambos trabajan con evidencia y ninguno garantiza exactitud.
- Los archivos se muestran por nombre y conteo, con un botón de quitar y altura
  acotada. No se expanden los mensajes de cada archivo en este menú.
- Las peticiones fuera de alcance reciben una sugerencia contextual opcional,
  generada en la misma llamada de interpretación; no se fuerza el retorno
  si el usuario cambió a otro tema válido.

## Abrir una publicación en la red social

El agente muestra **Publicación preparada** y acciones debajo del contenido,
tanto en el turno actual como en el historial (`src/app/publicacion_redes.py`).
El contrato interno sigue usando `borrador` para conservar compatibilidad.

- **X:** abre `https://twitter.com/intent/tweet` con `text` codificado, incluyendo
  contenido y hashtags. El título editorial no se envía. No se recorta el
  contenido: se avisa si supera 280 caracteres incluyendo etiquetas y
  separadores; el límite definitivo lo comprueba X. Existe copia como alternativa.
- **LinkedIn:** muestra el texto completo (título, contenido y hashtags) con
  copia nativa de Streamlit y un enlace a la red. La persona inicia una
  publicación y pega el contenido; no se promete precarga mediante URL.
- **Instagram:** mismo flujo de copia y apertura; requiere que la persona añada
  una imagen o video. No se generan ni suben archivos multimedia.
- **Threads / Bluesky:** abren sus editores oficiales con texto codificado,
  incluyendo título, contenido y etiquetas. Se avisa, sin recortar, cuando
  el conteo local supera 500/300 caracteres. Bluesky cuenta grafemas Unicode;
  el aviso local por puntos de código es conservador y el editor decide el límite.
- **WhatsApp:** `https://wa.me/?text=...` prepara un mensaje; la persona elige
  el destinatario. No es una publicación pública automática.
- **Telegram:** al añadir un enlace real, `https://t.me/share/url` recibe `url`
  y `text`. El enlace es obligatorio en el mecanismo oficial (un `url` vacío
  es rechazado, por ejemplo, por Telegram Desktop). Sin enlace se ofrece
  copiar y abrir Telegram, sin prometer precarga.
- **Facebook:** un enlace introducido por la persona se comparte con
  `https://www.facebook.com/sharer/sharer.php?u=...`. No se inventa un enlace
  ni se envía un parámetro de texto no admitido. Sin enlace queda copia y apertura.
- **Mastodon:** requiere el origen HTTPS del servidor de la cuenta, por ejemplo
  `https://mastodon.social`, y abre `/share?text=...` en ese servidor. No se
  presupone una instancia ni se contacta al servidor desde el backend.
- Los campos de enlace/servidor se validan y tienen claves por turno, también
  cuando hay publicaciones idénticas en el historial. Los errores se muestran
  junto al control y no se crea un botón con URL inválida.
- **Multimedia pendiente:** TikTok y YouTube quedan fuera del contrato de
  destinos de texto hasta definir la integración con el trabajo del equipo.
  No se crean acciones que prometan precargar videos ni subir archivos.
- No se conectan cuentas ni se usan APIs para publicar. Puede ser necesario
  iniciar sesión; la persona revisa y confirma en la red. Abrir un enlace no
  publica ni registra un guardado en OCI.

Referencias de los mecanismos:
[Threads](https://developers.facebook.com/documentation/threads/threads-web-intents/),
[Bluesky](https://bsky.network/docs/intent-links/),
[Telegram](https://core.telegram.org/widgets/share),
[WhatsApp](https://faq.whatsapp.com/5913398998672934),
[Facebook](https://developers.facebook.com/docs/sharing/web/).
Mastodon usa la ruta `/share` de la instancia; requiere iniciar sesión en ella.

## Catálogo diario de Plantillas (flujo público)

La vista pública ya no obtiene las plantillas del lote cargado en Streamlit:
lee el catálogo preparado en OCI. El catálogo/editores anteriores se conservan
únicamente en la aplicación interna (`src/app/app_interna.py`).

El ejecutor `python -m scripts.generar_plantillas_diarias` realiza una pasada,
independiente del frontend. Está incluido en la imagen y permite sobrescribir
el comando de arranque sin arrancar Streamlit. No es un servicio en bucle.

- Hora del producto: **08:00 America/Bogota**, equivalente a **13:00 UTC**.
  Antes de esa hora no genera contenido. Una ejecución tardía prepara el día
  actual; no reconstruye días perdidos.
- La primera selección contiene nueve prompts definidos en
  `src/app/plantillas_diarias.py`: LinkedIn, Instagram, X, newsletter, caso de
  éxito, sentimiento, temas, oportunidades de mejora y preguntas frecuentes.
  Los análisis/boletín se guardan como texto con fuentes; los posts usan las
  acciones sociales. El caso de éxito se prepara para LinkedIn.
- Toma una sola captura de la base publicada; no incluye adjuntos de usuarios.
  Cada prompt usa una instancia nueva del agente conversacional sobre esa
  captura: no se heredan filtros o mensajes de otra plantilla.
- Usa Super para responder y modo de verificación automática. Se guarda como
  **preparado para revisión**, nunca como aprobado ni publicado. Un aviso de
  revisión del verificador se conserva y se muestra a Marketing.
  La verificación factual NVIDIA también usa Super, independientemente del modelo
  elegido para redactar en el chat; Lightning aprobó un título sin respaldo en
  la evaluación real. Se conserva el respaldo Gemini ante fallos del proveedor,
  por lo que seleccionar Super no garantiza que todas las llamadas terminen allí.
- Una plantilla exitosa sustituye su versión anterior. Una fallida conserva
  íntegra su última versión y registra un aviso. Sin versión anterior aparece
  como no disponible. Una captura vacía o fallida no borra el contenido.
  Una consulta sin coincidencias no es una caída del servicio: se guarda
  explícitamente como `sin_evidencia`, con cero coincidencias, sin borrador y
  sin citas. Puede sustituir una versión previa para no mostrar contenido que
  ya no corresponde a la captura. La vista lo distingue de un fallo de ejecución.
- Reejecutar el mismo día no regenera las plantillas ya exitosas; reintenta
  únicamente las pendientes. Un cambio del prompt requiere regeneración.
- El catálogo completo se guarda mediante un solo PUT condicional, con ETag
  (`If-Match`, o `If-None-Match: *` para crearlo). Ante dos ejecuciones
  concurrentes, la que tenga una versión obsoleta falla sin sobrescribir la
  más reciente. Pueden consumir IA duplicada antes de detectar el conflicto:
  el programador debe evitar solapamientos.
- Objeto único: `plantillas/catalogo_actual.json`, en `OCI_BUCKET_NAME`.
  El reemplazo elimina del documento actual el contenido anterior de cada
  plantilla exitosa; no genera carpetas diarias ni historial de aplicación.
  No se borran los objetos del antiguo flujo interno `activos/...`.
- **Retención física:** Marco informó que activará el versionado del bucket.
  OCI conservará versiones anteriores aunque el catálogo visible se reemplace.
  Se mantiene por ahora para el MVP; revisar el consumo y acordar con Cloud
  una política de limpieza posterior si hace falta. La aplicación no enumera
  ni borra versiones históricas, ni modifica políticas del bucket.
- El frontend solo lee OCI, sin llamadas a modelos. Comprueba cada minuto y
  reutiliza lecturas hasta 45 segundos; ofrece actualización manual. Los
  errores de acceso se muestran como errores, no como un catálogo vacío.

### Correcciones de calidad y evaluación opt-in

- El esquema de hashtags expone al modelo el prefijo `#` obligatorio y la
  prohibición de espacios; no se corrigen silenciosamente etiquetas inválidas.
- La generación de X y la interfaz comparten `texto_publicacion`: se cuenta
  contenido, hashtags y separadores, sin título. Si se exceden 280 caracteres,
  se pide una reescritura; si aún se exceden, la generación falla explícitamente,
  sin recortar texto ni sustituir la versión previa del catálogo.
  El conteo local es de caracteres Unicode, no un validador oficial de X.
- El intérprete admite `tipos_detectados` como alternativas OR. FAQ selecciona
  preguntas técnicas y del programa, sin filtrar sentimiento ni recuperar
  testimonios por defecto. La evidencia sigue acotada a 20 mensajes;
  los conteos se calculan sobre todas las coincidencias.
  Con `agrupar_preguntas=true`, el modelo entrega grupos estructurados de duda e
  IDs. La aplicación exige que cubran la evidencia sin duplicados ni fuentes
  ajenas y calcula las frecuencias y los grupos repetidos a partir de IDs únicos,
  no de las cifras narradas por el modelo. El resumen no propone respuestas:
  para responder dudas se requiere otra consulta que contraste sus fuentes.
- Los agregados distinguen `universo_total` de `total_coincidencias`.
  El boletín exige titular Markdown, máximo 180 palabras y explicita el
  subconjunto positivo. Si incumple titular o longitud no sustituye la versión
  previa; las plantillas analíticas no aceptan borradores de redes sociales.
  Temas solicita todos los conteos, incluidos empates. Las reglas editoriales
  evitan mezclar historias y exigen sustento para títulos y puntos de partida.

Evaluación real reproducible (consume cuota; no ejecutarla con la suite offline):

```powershell
python -m pytest tests\integracion\prueba_plantillas_diarias.py -q -p no:cacheprovider
```

Usa datos simulados versionados en el repositorio, no Oracle ni OCI. Comprueba
los nueve prompts, negativos sintéticos y títulos con/sin respaldo. Las salidas
de los nueve prompts se guardan en los temporales de pytest para revisión.
Los criterios medibles y el verificador no garantizan por sí solos calidad
editorial general ni estabilidad: Marketing debe revisar antes de publicar.

### Activación pendiente con Cloud

Se reutiliza el cliente existente de **Instance Principals**. Cloud confirmó
`bkt-communitylab-marketing` para guardar y leer las plantillas. El cliente,
el script de prueba y el ejemplo de entorno usan ese mismo nombre. Configurar
`OCI_BUCKET_NAME=bkt-communitylab-marketing` en el despliegue; una variable
ya definida con otro valor sigue teniendo prioridad sobre el predeterminado.

No se encontró un programador desplegado en el repositorio, y **no se ha
activado un horario en la nube**. Cloud debe:

1. Confirmar bucket, namespace, políticas de retención y permisos: lectura para
   frontend; lectura/escritura condicional del catálogo para el ejecutor.
2. Dar al ejecutor las credenciales de lectura de la base, acceso a Secretos y
   a los proveedores de IA, sin incorporar secretos a la imagen.
3. Programar la ejecución a las 13:00 UTC cada día con exclusión de solapamientos.
   Puede invocar la misma imagen con
   `python -m scripts.generar_plantillas_diarias`; no depende del navegador.
4. Alertar sobre código de salida 1 (fallo de acceso/guardado/conflicto) y 2
   (catálogo confirmado pero con plantillas pendientes). El 0 significa que
   quedó completo o todavía no era la hora. Configurar reintentos espaciados
   tras las 13:00 UTC, dentro del mismo día de Bogotá.
5. Hacer una prueba real de captura, generación, escritura y lectura antes de
   anunciar que el catálogo diario está operativo.

## Para Eduardo (QA-3 del flujo interno de Plantillas)

- Abrir Plantillas sin lote procesado: las tarjetas aparecen atenuadas y no hay error.
- Lote sin activos de un tipo: la plantilla muestra "0 borradores" y un mensaje claro.
- Editar, aprobar, volver a editar: la aprobación se pierde (ya está cubierto) y se ve en la plantilla.
- Mojibake en un borrador editado: el error de validación aparece junto al editor.
- X: el texto adaptado nunca pasa de 280 caracteres.
- Abrir la red no publica nada ni guarda en OCI.

## Verificación

```powershell
python -m pytest tests/test_tolerancia_app.py tests/test_curaduria_oci.py tests/test_docker_cloud.py tests/test_plantillas.py tests/test_ayuda.py -q
```
