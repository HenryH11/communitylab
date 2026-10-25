"""Página de Ayuda: flujo en cuatro pasos, preguntas frecuentes y búsqueda."""

import unicodedata
from html import escape

import streamlit as st

from src.app import tema

PASOS = (
    ("Agente", "Pregunta", "Consulta al agente lo que dice la comunidad."),
    ("Agente", "Adjunta", "Suma tus archivos para cruzarlos con la comunidad."),
    ("Análisis", "Explora", "Revisa métricas, temas y sentimiento."),
    ("Plantillas", "Publica", "Revisa el contenido del día y abre la red para publicarlo."),
)

SECCIONES = (
    (
        "Accesibilidad",
        ":material/accessibility_new:",
        (
            (
                "¿Cómo uso la aplicación con teclado o lector de pantalla?",
                "Usa Tab y Mayús+Tab para recorrer los controles; el foco se marca "
                "con un contorno. En la navegación principal, usa las flechas para "
                "cambiar de sección. Enter o Espacio activa botones y paneles de "
                "información. En Análisis, abre «Datos de las gráficas en texto» "
                "para consultar los mismos conteos sin depender del color. "
                "Puedes ampliar la página con el zoom del navegador.",
            ),
            (
                "¿Necesito escuchar audio o ver animaciones?",
                "No necesitas audio: las respuestas, avisos e instrucciones son "
                "textuales. La aplicación respeta la preferencia de movimiento "
                "reducido del sistema y conserva las funciones al desactivar "
                "animaciones. Los botones de redes mantienen su nombre además "
                "del logo.",
            ),
        ),
    ),
    (
        "Datos del agente",
        ":material/database:",
        (
            (
                "¿De dónde salen los datos?",
                "De la base de datos de la comunidad, que el equipo de CommunityLab "
                "mantiene con los mensajes ya clasificados por canal, sentimiento y "
                "tema. El agente solo la consulta: nunca la modifica.",
            ),
            (
                "¿Cada cuánto se actualizan?",
                "Al empezar tu sesión el agente toma una captura de la base y la usa "
                "para todas tus preguntas, sin volver a consultarla cada vez. Cuando "
                "pasa más de una hora, la vuelve a capturar para traer lo más reciente.",
            ),
            (
                "¿Puedo usar mis propios datos?",
                "Sí. Usa el clip de la caja de texto para adjuntar archivos JSON, CSV "
                "o TXT (hasta 5 MB cada uno). No necesitan un formato especial: el "
                "agente busca el texto de cada mensaje y, si existen, el autor, el "
                "canal y la fecha. En un TXT, cada línea es un mensaje. Se combinan "
                "con la base solo durante tu sesión y no se guardan.",
            ),
            (
                "¿Cómo quito un archivo que adjunté?",
                "Abre **Tus datos**, junto a la caja de texto, y elige **Quitar**. La "
                "conversación sigue con el resto de la información.",
            ),
        ),
    ),
    (
        "Agente en vivo",
        ":material/cyclone:",
        (
            (
                "¿Dónde veo qué cambia cada ajuste?",
                "Usa el icono **i** junto a Modelo, Redacción o Estricto/Verificado. "
                "Al pasar el puntero o enfocar el icono con el teclado aparece una "
                "explicación: en pantallas amplias ocupa los márgenes del chat. "
                "Puedes tocar o pulsar el icono para dejarla abierta y volver a "
                "pulsarlo para cerrarla; en móvil se adapta al ancho disponible.",
            ),
            (
                "¿Qué le puedo preguntar al agente?",
                "Preguntas sobre los mensajes de la comunidad y tus archivos: conteos, "
                "sentimiento, temas, listados (por ejemplo, *«dame los 10 mejores "
                "comentarios»*) y contenido para LinkedIn, Instagram, X, Facebook, "
                "WhatsApp, Telegram, Threads, Bluesky o Mastodon. Admite "
                "seguimientos como *«¿y los negativos?»* o *«conviértelo en un post "
                "para X»*.",
            ),
            (
                "¿Puede inventar datos?",
                "No. Solo usa los mensajes de la base y de tus archivos, y cita sus IDs "
                "como fuente. Si pides 20 elementos y hay 12, entrega 12 y lo explica "
                "en lugar de rellenar.",
            ),
            (
                "¿Por qué a veces no responde lo que pedí?",
                "Cuando ningún mensaje coincide con los filtros, el agente explica "
                "el motivo: términos que nadie menciona, períodos sin fechas o "
                "filtros sin resultados. También rechaza pedidos fuera de su "
                "alcance, como programar o consultar noticias externas.",
            ),
            (
                "¿Qué hace la verificación automática?",
                "Abre **Estricto** o **Verificado** junto a la caja de texto. "
                "Con Verificar borradores apagado, no se hace "
                "una revisión separada del borrador. Encendido, revisa cada "
                "afirmación de los borradores contra los mensajes de la comunidad y "
                "muestra cuáles están respaldadas. Si detecta hechos sin respaldo, "
                "intenta corregirlos una vez y vuelve a revisar; si persisten, no "
                "muestra el borrador ni habilita sus acciones de publicación. "
                "Tarda más y consume más cuota; no sustituye la revisión editorial.",
            ),
            (
                "¿Para qué sirve el botón Redacción?",
                "Ajusta qué tan creativos son los borradores de marketing. En "
                "**Estilos** eliges Preciso (sobrio y directo), Equilibrado (variedad "
                "moderada) o Creativo (más recursos de redacción, sin inventar hechos). "
                "En **Manual** ajustas la temperatura (variedad del texto) y el top_p (amplitud del "
                "vocabulario). Puedes cambiarlo en cualquier momento del chat. Los "
                "análisis y conteos no cambian: siempre son exactos.",
            ),
            (
                "¿Puedo elegir el modelo?",
                "Sí. En **Modelo** eliges Super, recomendado para peticiones elaboradas, "
                "o Lightning, una alternativa ligera que puede requerir más ajustes. "
                "Cambia las respuestas siguientes sin borrar la conversación; no cambia "
                "cómo se interpreta tu petición ni cómo se verifican los borradores. "
                "Si el servicio falla, puede usarse un proveedor de respaldo.",
            ),
            (
                "¿Tengo que escribir solo palabras clave?",
                "No. Puedes saludar y hacer tu petición en el mismo mensaje. El "
                "agente separa la conversación de los temas y filtros que necesita "
                "para buscar. Si falta algo para entenderte, te lo pregunta antes "
                "de consultar los mensajes.",
            ),
        ),
    ),
    (
        "Plantillas y OCI",
        ":material/article:",
        (
            (
                "¿El contenido se publica automáticamente?",
                "No. X, Threads y Bluesky abren el editor con texto preparado. "
                "Para Mastodon, indica el servidor donde tienes tu cuenta. "
                "En WhatsApp eliges dónde enviar el mensaje; en Telegram añade "
                "un enlace para compartirlo con el texto o copia el mensaje. "
                "Facebook permite compartir un enlace, pero no garantiza precargar "
                "texto libre. Para LinkedIn e Instagram, copia el texto con "
                "el botón del recuadro, abre la red y pégalo. Instagram necesita además "
                "una imagen o video. Puede ser necesario iniciar sesión. Abrir la red "
                "no publica ni guarda el contenido en CommunityLab.",
            ),
            (
                "¿Y TikTok, YouTube o contenido multimedia?",
                "La integración multimedia está pendiente. Por ahora no se generan "
                "ni adjuntan imágenes o videos, ni se publican en TikTok o YouTube. "
                "Las acciones actuales preparan texto para revisión; no conectan cuentas.",
            ),
            (
                "¿Cómo guardo un activo aprobado?",
                "En el catálogo diario no necesitas guardarlo: el contenido preparado "
                "ya está almacenado. Abre **Plantillas**, revisa su fecha, las fuentes "
                "y cualquier aviso antes de copiarlo o abrir la red para publicarlo. "
                "Preparado para revisión no significa aprobado ni publicado.",
            ),
            (
                "¿Cuándo se renuevan las plantillas?",
                "La renovación está prevista todos los días a las 08:00, hora de Bogotá, "
                "una vez que el equipo active el servicio programado. Cada contenido "
                "nuevo sustituye al anterior. Si una plantilla falla, conserva su última "
                "versión disponible con la fecha y un aviso; las demás sí se actualizan. "
                "La página comprueba el catálogo cada minuto mientras está abierta y "
                "también puedes pulsar Actualizar catálogo.",
            ),
            (
                "¿Por qué no veo un borrador para cada mensaje?",
                "Cada plantilla diaria responde a una petición predefinida sobre "
                "la comunidad, no a cada mensaje individual. Si no hay evidencia "
                "suficiente o falla la preparación, se muestra un aviso en esa plantilla.",
            ),
        ),
    ),
    (
        "Problemas comunes",
        ":material/build:",
        (
            (
                "El agente dice que el modelo no está disponible",
                "El modelo de IA no está habilitado en este momento. Intenta de "
                "nuevo en unos minutos; si continúa, avisa al administrador de "
                "CommunityLab.",
            ),
            (
                "El agente o el procesamiento no logran conectarse",
                "La conexión con el proveedor de IA no fue autorizada. Avisa al "
                "administrador de CommunityLab para que revise el acceso y vuelve "
                "a intentarlo.",
            ),
            (
                "La página del agente aparece vacía",
                "El agente no pudo leer la base de la comunidad y no hay archivos "
                "adjuntos. El aviso en pantalla explica el motivo; mientras tanto "
                "puedes adjuntar tus propios archivos con el clip.",
            ),
            (
                "El agente dice que usa información de hace unos minutos",
                "La base no respondió al renovar la captura, así que el agente sigue "
                "con la última que obtuvo. Volverá a intentarlo en unos minutos.",
            ),
        ),
    ),
)

ESTILO = """
<style>
    .ayuda-cabecera { text-align: center; margin: 1.5rem 0 1.4rem; }
    .ayuda-cabecera .cl-logo { width: 2.4rem; height: 2.4rem; color: var(--cl-miel); }
    .ayuda-cabecera p.ayuda-versal {
        margin: 0.5rem 0 0;
        font-family: var(--cl-versal);
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.3em;
        color: var(--cl-miel-oscura);
    }
    .ayuda-cabecera p.ayuda-titulo {
        margin: 0.1rem 0 0.2rem;
        font-family: var(--cl-titulo);
        font-size: 3rem;
        font-weight: 700;
        color: var(--cl-tinta);
    }
    .ayuda-cabecera p.ayuda-lema { margin: 0; color: var(--cl-tinta-suave); }
    .st-key-ayuda_busqueda { max-width: 620px; margin: 0 auto 1.6rem; }
    .ayuda-paso-numero {
        font-family: var(--cl-titulo);
        font-weight: 700;
        font-size: 2.3rem;
        line-height: 1;
        color: var(--cl-miel-oscura);
    }
    .ayuda-paso-titulo {
        margin-top: 0.3rem;
        font-family: var(--cl-versal);
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--cl-tinta);
    }
    .ayuda-paso-texto { color: var(--cl-tinta-suave); font-size: 0.92rem; min-height: 2.8rem; }
    .ayuda-bloque-pregunta {
        margin-bottom: 0.4rem;
        font-family: var(--cl-texto);
        font-weight: 700;
        font-size: 1.02rem;
        color: var(--cl-tinta);
    }
    [class*="st-key-ayuda_bloque_"] p { color: var(--cl-tinta-suave); }
</style>
"""


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in sin_acentos if not unicodedata.combining(c))


def filtrar(secciones, busqueda: str):
    """Secciones con solo las preguntas que contienen todos los términos buscados."""
    terminos = _normalizar(busqueda).split()
    if not terminos:
        return list(secciones)
    filtradas = []
    for titulo, icono, preguntas in secciones:
        coincidencias = tuple(
            (pregunta, respuesta)
            for pregunta, respuesta in preguntas
            if all(
                termino in _normalizar(f"{titulo} {pregunta} {respuesta}")
                for termino in terminos
            )
        )
        if coincidencias:
            filtradas.append((titulo, icono, coincidencias))
    return filtradas


def _pasos(ir_a):
    columnas = st.columns(len(PASOS))
    for numero, (columna, (pagina, titulo, texto)) in enumerate(
        zip(columnas, PASOS), start=1
    ):
        with columna, st.container(border=True):
            st.markdown(
                f'<div class="ayuda-paso-numero">{numero:02d}</div>'
                f'<div class="ayuda-paso-titulo">{titulo}</div>'
                f'<div class="ayuda-paso-texto">{texto}</div>',
                unsafe_allow_html=True,
            )
            if ir_a is not None:
                st.button(
                    f"Ir a {pagina}",
                    key=f"ayuda_paso_{numero}",
                    type="tertiary",
                    icon=":material/arrow_forward:",
                    on_click=ir_a,
                    args=(pagina,),
                )


def render(ir_a=None):
    st.markdown(ESTILO, unsafe_allow_html=True)
    st.markdown(
        '<div class="ayuda-cabecera">'
        f"{tema.logo()}"
        '<p class="ayuda-versal">CENTRO DE AYUDA</p>'
        '<p class="ayuda-titulo">¿En qué podemos ayudarte?</p>'
        '<p class="ayuda-lema">De las conversaciones de tu comunidad a contenido aprobado, '
        "paso a paso.</p></div>",
        unsafe_allow_html=True,
    )
    with st.container(key="ayuda_busqueda"):
        busqueda = st.text_input(
            "Buscar en la ayuda",
            placeholder="Busca por tema: verificación, OCI, JSON, borradores…",
            icon=":material/search:",
            label_visibility="collapsed",
        )

    if not busqueda.strip():
        _pasos(ir_a)

    secciones = filtrar(SECCIONES, busqueda)
    if not secciones:
        st.info(
            "No hay respuestas para esa búsqueda. Prueba con otra palabra, "
            "como «agente», «lote» o «OCI»."
        )
    for titulo, icono, preguntas in secciones:
        st.subheader(f"{icono} {titulo}")
        _bloques(titulo, preguntas)


def _bloques(seccion, preguntas):
    """Cada pregunta como un bloque legible de un vistazo, en una cuadrícula."""
    # Con cuatro preguntas, 2 × 2 evita una tarjeta huérfana en la segunda fila.
    por_fila = 2 if len(preguntas) % 3 == 1 else 3
    for inicio in range(0, len(preguntas), por_fila):
        fila = preguntas[inicio : inicio + por_fila]
        for indice, (columna, (pregunta, respuesta)) in enumerate(
            zip(st.columns(por_fila), fila), start=inicio
        ):
            clave = f"ayuda_bloque_{_normalizar(seccion).replace(' ', '_')}_{indice}"
            with columna, st.container(border=True, key=clave, height="stretch"):
                st.markdown(
                    f'<div class="ayuda-bloque-pregunta">{escape(pregunta)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(respuesta)
