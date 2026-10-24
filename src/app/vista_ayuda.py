"""Página de Ayuda: flujo en cuatro pasos, preguntas frecuentes y búsqueda."""

import unicodedata

import streamlit as st

from src.app import tema

PASOS = (
    ("Datos", "Importa", "Sube el JSON de la comunidad y revisa la muestra."),
    ("Datos", "Procesa", "El pipeline clasifica mensajes y genera activos."),
    ("Agente", "Pregunta", "Conversa con el agente sobre el lote procesado."),
    ("Plantillas", "Aprueba", "Edita, aprueba y guarda los activos en OCI."),
)

SECCIONES = (
    (
        "Datos y procesamiento",
        ":material/upload_file:",
        (
            (
                "¿Cómo importo conversaciones?",
                "Abre **Datos**, selecciona un archivo JSON compatible y revisa la "
                "vista previa (hasta 20 interacciones) antes de procesarlo.",
            ),
            (
                "¿Qué ocurre al procesar el lote?",
                "El pipeline analiza sentimiento y tipo de cada mensaje y genera "
                "activos según las rutas disponibles. Puede tardar según el tamaño "
                "del lote y el proveedor de IA.",
            ),
            (
                "¿Qué pasa si proceso otro lote?",
                "Análisis, Plantillas y el Agente pasan a trabajar con el último "
                "lote. La conversación con el agente se reinicia para no mezclar "
                "datos de lotes distintos.",
            ),
        ),
    ),
    (
        "Agente en vivo",
        ":material/cyclone:",
        (
            (
                "¿Qué le puedo preguntar al agente?",
                "Preguntas sobre el lote procesado: conteos, sentimiento, temas, "
                "listados (por ejemplo, *«dame los 10 mejores comentarios»*) y "
                "borradores para LinkedIn, Instagram o X. Admite seguimientos como "
                "*«¿y los negativos?»* o *«conviértelo en un post para X»*.",
            ),
            (
                "¿Puede inventar datos?",
                "No. Solo usa los mensajes del lote y cita sus IDs como fuente. Si "
                "pides 20 elementos y hay 12, entrega 12 y lo explica en lugar de "
                "rellenar.",
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
                "Sin ella (modo estricto) el agente responde con una sola llamada al "
                "modelo. Activada, revisa cada afirmación de los borradores contra "
                "las fuentes y muestra cuáles están respaldadas. Es más confiable, "
                "pero tarda más y consume más cuota.",
            ),
            (
                "¿Puedo usar el agente desde la terminal?",
                "Sí. Ejecuta `python -m scripts.agente_en_vivo` para abrir un chat, "
                "o pasa la pregunta entre comillas para una sola respuesta. Dentro "
                "del chat, `/verificar` y `/estricto` cambian el modo y `/ayuda` "
                "lista los comandos.",
            ),
        ),
    ),
    (
        "Plantillas y OCI",
        ":material/article:",
        (
            (
                "¿El contenido se publica automáticamente?",
                "No. Los activos requieren revisión y aprobación. Abrir un enlace a "
                "una red social no publica ni guarda el contenido.",
            ),
            (
                "¿Cómo guardo un activo aprobado?",
                "Aprueba el contenido en **Plantillas** y usa la sección de guardado "
                "en OCI al final de esa vista.",
            ),
            (
                "¿Por qué no veo un borrador para cada mensaje?",
                "El pipeline solo genera activos para los mensajes que cumplen las "
                "condiciones de sus rutas. Instagram y X aparecen como próximamente "
                "en el catálogo, aunque el agente sí puede redactarlos.",
            ),
        ),
    ),
    (
        "Problemas comunes",
        ":material/build:",
        (
            (
                "El agente dice que el modelo no está disponible (404)",
                "El modelo configurado no existe o no está habilitado para tu "
                "cuenta. Revisa las variables `COMMUNITYLAB_MODELO_NVIDIA_*` en "
                "`.env`.",
            ),
            (
                "El agente o el procesamiento fallan por credenciales",
                "Confirma que `.env` incluya las claves del proveedor (por ejemplo "
                "`NVIDIA_API_KEY`) y reinicia la aplicación.",
            ),
            (
                "La página del agente aparece vacía",
                "El agente necesita un lote procesado. Importa y procesa un archivo "
                "en **Datos** y vuelve a la página.",
            ),
        ),
    ),
)

ESTILO = """
<style>
    .ayuda-cabecera { text-align: center; margin: 1.5rem 0 1.4rem; }
    .ayuda-cabecera .cl-espiral { width: 2.4rem; height: 2.4rem; color: var(--cl-miel); }
    .ayuda-cabecera p.ayuda-versal {
        margin: 0.5rem 0 0;
        font-family: var(--cl-versal);
        font-size: 0.78rem;
        letter-spacing: 0.3em;
        color: var(--cl-miel-oscura);
    }
    .ayuda-cabecera p.ayuda-titulo {
        margin: 0.1rem 0 0.2rem;
        font-family: var(--cl-titulo);
        font-size: 2.6rem;
        font-weight: 600;
        color: var(--cl-tinta);
    }
    .ayuda-cabecera p.ayuda-lema { margin: 0; color: var(--cl-tinta-suave); }
    .st-key-ayuda_busqueda { max-width: 620px; margin: 0 auto 1.6rem; }
    .ayuda-paso-numero {
        font-family: var(--cl-titulo);
        font-size: 2.1rem;
        line-height: 1;
        color: var(--cl-miel);
    }
    .ayuda-paso-titulo {
        margin-top: 0.3rem;
        font-family: var(--cl-versal);
        font-size: 0.82rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--cl-tinta);
    }
    .ayuda-paso-texto { color: var(--cl-tinta-suave); font-size: 0.92rem; min-height: 2.8rem; }
    .ayuda-cierre {
        margin-top: 2rem;
        padding: 1.1rem 1.4rem;
        border-left: 3px solid var(--cl-miel);
        border-radius: 0 0.6rem 0.6rem 0;
        background: var(--cl-miel-clara);
        color: var(--cl-tinta);
    }
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
        f"{tema.espiral()}"
        '<p class="ayuda-versal">CENTRO DE AYUDA</p>'
        '<p class="ayuda-titulo">¿En qué podemos ayudarte?</p>'
        '<p class="ayuda-lema">Del lote de conversaciones a contenido aprobado, '
        "paso a paso.</p></div>",
        unsafe_allow_html=True,
    )
    with st.container(key="ayuda_busqueda"):
        busqueda = st.text_input(
            "Buscar en la ayuda",
            placeholder="Busca por tema: verificación, OCI, JSON, terminal…",
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
        for pregunta, respuesta in preguntas:
            with st.expander(pregunta, expanded=bool(busqueda.strip())):
                st.markdown(respuesta)

    st.markdown(
        '<div class="ayuda-cierre"><b>¿Sigues con dudas?</b> La guía técnica del '
        "agente está en <code>docs/agente_conversacional.md</code> y el detalle "
        "de la interfaz en <code>docs/integracion_frontend_semana5_1.md</code>."
        "</div>",
        unsafe_allow_html=True,
    )
