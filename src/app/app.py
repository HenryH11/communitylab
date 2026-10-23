import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import altair as alt
import pandas as pd
import streamlit as st

from src.agentes.grafo import procesar_paquete_entrega
from src.app import vista_plantillas
from src.app.curaduria_oci import contexto_curaduria
from src.datos.entrega_ia import preparar_paquete_ia

st.set_page_config(
    page_title="CommunityLab",
    page_icon=":material/forum:",
    layout="wide",
)

st.markdown(
    """
    <style>
        :root {
            --communitylab-violet: #6557E8;
            --communitylab-heading: #17213c;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: var(--communitylab-heading);
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            gap: 0.4rem;
        }
        div[data-testid="stRadio"] label {
            border-radius: 0.6rem;
            padding: 0.45rem 0.8rem;
        }
        div[data-testid="stRadio"] label:has(input:checked) {
            background: #f0edff;
            color: var(--communitylab-violet);
            font-weight: 700;
        }
        button[kind="primary"] {
            background-color: var(--communitylab-violet);
            border-color: var(--communitylab-violet);
            color: #ffffff;
        }
        button[kind="primary"]:hover {
            background-color: #5144cf;
            border-color: #5144cf;
            color: #ffffff;
        }
        .st-key-inicio_card_datos button,
        .st-key-inicio_card_analisis button,
        .st-key-inicio_card_plantillas button {
            height: 9rem;
            justify-content: flex-start;
            text-align: left;
            white-space: pre-wrap;
        }
        .communitylab-brand {
            background: #111b3a;
            border-radius: 0.75rem;
            color: #ffffff;
            font-weight: 700;
            letter-spacing: 0.04em;
            margin-bottom: 1rem;
            padding: 0.85rem 1.1rem;
        }
        .block-container {
            max-width: 1440px;
            padding-bottom: 2rem;
            padding-top: 1.25rem;
        }
    </style>
    <div class="communitylab-brand">◉ COMMUNITYLAB</div>
    """,
    unsafe_allow_html=True,
)

PAGINAS = ("Inicio", "Datos", "Agente", "Análisis", "Plantillas", "Ayuda")
CLAVE_NAVEGACION = "navegacion_principal"


def _navegar_a(pagina):
    st.session_state[CLAVE_NAVEGACION] = pagina


def _interacciones_para_vista(datos):
    """Extrae filas de vista previa sin modificar ni validar el lote original."""
    if not isinstance(datos, dict):
        return []

    lotes = datos.get("lotes")
    if lotes is None:
        lotes = [datos]
    if not isinstance(lotes, list):
        return []

    filas = []
    for lote in lotes:
        if not isinstance(lote, dict):
            continue
        interacciones = lote.get("interacciones", [])
        if not isinstance(interacciones, list):
            continue
        for mensaje in interacciones:
            if not isinstance(mensaje, dict):
                continue
            filas.append(
                {
                    "id": mensaje.get("id", "—"),
                    "autor": mensaje.get("autor", "Anónimo"),
                    "canal": mensaje.get("canal", lote.get("origen_comunidad", "—")),
                    "tipo": mensaje.get("tipo", "—"),
                    "texto": mensaje.get("texto", ""),
                }
            )
    return filas


def _render_datos():
    st.header("Prepara los datos antes de generar resultados")
    st.write(
        "Importa un lote JSON, revisa una muestra de las conversaciones y "
        "ejecuta el pipeline de análisis."
    )

    carga, guia = st.columns([2, 1])
    with carga:
        with st.container(border=True):
            st.subheader("Importar interacciones")
            st.caption("Formato compatible: JSON con lotes e interacciones.")
            archivo_subido = st.file_uploader(
                "Selecciona el archivo JSON",
                type=["json"],
                key="archivo_interacciones",
            )

            if archivo_subido is not None:
                try:
                    datos = json.load(archivo_subido)
                    st.success("Archivo JSON cargado correctamente.")
                    filas = _interacciones_para_vista(datos)
                    if filas:
                        st.caption(
                            f"Vista previa · {len(filas)} interacciones encontradas"
                        )
                        st.dataframe(
                            pd.DataFrame(filas).head(20),
                            hide_index=True,
                            width="stretch",
                        )
                        if len(filas) > 20:
                            st.caption("Se muestran las primeras 20 interacciones.")
                    else:
                        st.info(
                            "El JSON se pudo leer, pero no contiene una lista "
                            "de interacciones para mostrar."
                        )

                    if st.button(
                        "Procesar con IA (Gemini + LangGraph)",
                        type="primary",
                        icon=":material/rocket_launch:",
                        key="procesar_lote",
                    ):
                        with st.spinner(
                            "Procesando mensajes con inteligencia artificial..."
                        ):
                            try:
                                paquete = preparar_paquete_ia(
                                    datos,
                                    fecha_referencia="2026-09-17T12:00:00Z",
                                    tamano_ciclo=20,
                                )
                                resultado = procesar_paquete_entrega(paquete)
                                st.session_state["resultado"] = resultado
                                st.success("Procesamiento completado.")
                            except Exception as error:
                                st.error(
                                    f"Error durante el procesamiento: {error}"
                                )

                except json.JSONDecodeError:
                    st.error(
                        "El archivo no es un JSON válido. "
                        "Verifica el formato y vuelve a intentarlo."
                    )
                except Exception as error:
                    st.error(f"Error al cargar el archivo: {error}")

    with guia:
        with st.container(border=True):
            st.subheader("Antes de procesar")
            st.markdown(
                "1. Selecciona un archivo JSON.\n"
                "2. Revisa la muestra de interacciones.\n"
                "3. Inicia el análisis con el pipeline de IA."
            )
            st.caption(
                "El procesamiento analiza el lote y genera los activos "
                "disponibles. No publica contenido en redes."
            )


def _render_analisis(resultado):
    st.header("Estado de las conversaciones de la comunidad")
    if resultado is None:
        st.info("Carga y procesa un lote desde Datos para ver las métricas.")
        return

    resultados = resultado.get("resultados_por_id", {})
    total = len(resultados)
    if not resultados:
        st.info("El lote terminó de procesarse, pero no contiene resultados.")
        return

    con_activos = sum(
        1 for data in resultados.values() if data.get("activos_generados")
    )
    faqs = sum(1 for data in resultados.values() if data.get("elegible_faq"))

    metrica_1, metrica_2, metrica_3, metrica_4 = st.columns(4)
    metrica_1.metric("Mensajes procesados", total)
    metrica_2.metric("Con contenido", con_activos)
    metrica_3.metric("Sin contenido", total - con_activos)
    metrica_4.metric("Elegibles para FAQ", faqs)

    st.subheader("Distribución de la comunidad")
    filas_grafica = [
        {
            "autor": data.get("autor", "Anónimo"),
            "canal": data.get("canal", "N/A"),
            "sentimiento": data.get("sentimiento", "N/A"),
            "tema": data.get("tema_principal", "N/A"),
            "elegible": "Sí" if data.get("elegible_contenido") else "No",
            "spam": data.get("es_spam_detectado") is True,
        }
        for data in resultados.values()
    ]
    df = pd.DataFrame(filas_grafica)
    df_sentimiento = df[~df["spam"]]
    total_spam = total - len(df_sentimiento)

    with st.container(border=True):
        tema_columna, sentimiento_columna = st.columns(2)
        with tema_columna:
            st.markdown("**Distribución por tema principal**")
            chart_temas = (
                alt.Chart(df)
                .mark_bar(color="#6557e8")
                .encode(
                    x=alt.X("tema:N", sort="-y", title="Tema"),
                    y=alt.Y("count():Q", title="Cantidad"),
                    tooltip=["tema:N", "count():Q"],
                )
                .properties(height=280)
            )
            st.altair_chart(chart_temas, width="stretch")

        with sentimiento_columna:
            st.markdown("**Distribución por sentimiento**")
            if df_sentimiento.empty:
                st.info("No hay mensajes legítimos para calcular el sentimiento.")
            else:
                chart_sentimiento = (
                    alt.Chart(df_sentimiento)
                    .mark_arc(innerRadius=55)
                    .encode(
                        theta=alt.Theta("count():Q"),
                        color=alt.Color(
                            "sentimiento:N",
                            legend=alt.Legend(title="Sentimiento"),
                        ),
                        tooltip=["sentimiento:N", "count():Q"],
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart_sentimiento, width="stretch")
            if total_spam:
                st.caption(
                    f"Se excluyen {total_spam} mensaje(s) marcados como spam."
                )

    with st.container(border=True):
        canal_columna, elegible_columna = st.columns(2)
        with canal_columna:
            st.markdown("**Distribución por canal**")
            chart_canal = (
                alt.Chart(df)
                .mark_bar(color="#6557e8")
                .encode(
                    x=alt.X("count():Q", title="Cantidad"),
                    y=alt.Y("canal:N", sort="-x", title="Canal"),
                    tooltip=["canal:N", "count():Q"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart_canal, width="stretch")

        with elegible_columna:
            st.markdown("**Elegibles para contenido**")
            chart_elegible = (
                alt.Chart(df)
                .mark_arc(innerRadius=55)
                .encode(
                    theta=alt.Theta("count():Q"),
                    color=alt.Color(
                        "elegible:N",
                        legend=alt.Legend(title="Elegible"),
                    ),
                    tooltip=["elegible:N", "count():Q"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart_elegible, width="stretch")

    st.subheader("Detalle por mensaje")
    st.caption(
        "Vista de solo lectura. Edita y aprueba los activos en Plantillas."
    )
    for id_msg, data in resultados.items():
        autor = data.get("autor", "Anónimo")
        tema = data.get("tema_principal", "sin tema")
        sentimiento = data.get("sentimiento", "N/A")
        activos = list(data.get("activos_generados") or {})
        icono = (
            "🚫"
            if data.get("es_spam_detectado") is True
            else ("📝" if activos else "💬")
        )

        with st.expander(f"{icono} {autor} — {tema} · {sentimiento}"):
            detalle_1, detalle_2 = st.columns(2)
            with detalle_1:
                st.write(f"**Canal:** {data.get('canal', 'N/A')}")
                st.write(f"**Tipo detectado:** {data.get('tipo_detectado', 'N/A')}")
                st.write(f"**Score relevancia:** {data.get('score_relevancia', 'N/A')}")
                st.write(
                    f"**Rutas:** {', '.join(data.get('rutas') or []) or 'ninguna'}"
                )
            with detalle_2:
                st.write(f"**Sentimiento:** {sentimiento}")
                st.write(f"**Subtema:** {data.get('subtema', 'N/A')}")
                st.write(
                    "**Elegible para contenido:** "
                    f"{'Sí' if data.get('elegible_contenido') else 'No'}"
                )
                if "elegible_faq" in data:
                    st.write(
                        "**Elegible para FAQ:** "
                        f"{'Sí' if data['elegible_faq'] else 'No'}"
                    )
            if data.get("es_spam_detectado") is True:
                st.write(
                    f"**Spam:** {data.get('motivo_spam') or 'sin motivo indicado'}"
                )

            st.markdown(f"*Texto original:* {data.get('texto', '')}")
            if activos:
                st.caption(
                    "Activos generados: "
                    + ", ".join(activos)
                    + " · edítalos y apruébalos en Plantillas."
                )
            else:
                st.caption("Este mensaje no generó activos.")
            if data.get("errores"):
                st.caption(
                    f"El pipeline registró {len(data['errores'])} error(es) "
                    "en este mensaje."
                )


def _render_inicio(resultado):
    contenido, resumen = st.columns([1.35, 1], vertical_alignment="center")
    with contenido:
        st.badge("COMMUNITYLAB · INTELIGENCIA PARA COMUNIDADES", color="violet")
        st.title("Tu comunidad habla. Convierte esa voz en valor.")
        st.write(
            "Transforma conversaciones en conocimiento, analítica y activos "
            "de marketing con revisión humana."
        )
        if resultado is None:
            st.info("Comienza en Datos importando un archivo JSON.")
        else:
            total = len(resultado.get("resultados_por_id", {}))
            st.success(f"El último lote tiene {total} mensajes procesados.")

    with resumen:
        with st.container(border=True):
            st.markdown("#### De conversación a resultado")
            st.markdown(
                ":material/upload_file: **Importar** · Lote JSON de la comunidad\n\n"
                ":material/analytics: **Analizar** · Temas y sentimiento\n\n"
                ":material/edit_note: **Revisar** · Editar y aprobar activos"
            )

    st.subheader("Explora CommunityLab")
    tarjetas = st.columns(3)
    for columna, pagina, icono, titulo, descripcion in zip(
        tarjetas,
        ("Datos", "Análisis", "Plantillas"),
        (":material/table_view:", ":material/insights:", ":material/article:"),
        ("Datos", "Análisis", "Plantillas"),
        (
            "Importa y revisa interacciones antes de procesarlas.",
            "Explora métricas, temas y sentimiento de la comunidad.",
            "Prepara contenidos y apruébalos antes de guardarlos.",
        ),
    ):
        with columna:
            with st.container(border=True, key=f"inicio_card_{pagina.lower()}"):
                st.button(
                    f"**{titulo}**\n\n{descripcion}",
                    icon=icono,
                    key=f"inicio_nav_{pagina.lower()}",
                    use_container_width=True,
                    on_click=_navegar_a,
                    args=(pagina,),
                )


def _render_agente(resultado):
    st.header("Agente CommunityLab")
    st.write(
        "El agente actual analiza lotes y crea activos a partir de las "
        "conversaciones. La interfaz todavía no ofrece un chat de preguntas libres."
    )

    instrucciones, estado = st.columns([2, 1])
    with instrucciones:
        with st.container(border=True):
            st.markdown("#### Flujo de procesamiento")
            st.markdown(
                ":material/description: **1. Entrada** · Conversaciones del lote\n\n"
                ":material/psychology: **2. Análisis** · Tema, sentimiento y rutas\n\n"
                ":material/auto_awesome: **3. Generación** · Activos según las rutas\n\n"
                ":material/fact_check: **4. Revisión humana** · Edición y aprobación"
            )
    with estado:
        with st.container(border=True):
            st.markdown("#### Estado del lote")
            if resultado is None:
                st.badge("Pendiente", color="orange")
                st.write("Importa y procesa un lote desde Datos.")
            else:
                total = len(resultado.get("resultados_por_id", {}))
                con_activos = sum(
                    bool(item.get("activos_generados"))
                    for item in resultado.get("resultados_por_id", {}).values()
                )
                st.badge("Procesado", color="green")
                st.metric("Mensajes analizados", total)
                st.metric("Mensajes con activos", con_activos)

    st.info(
        "No se simulan respuestas de chat: las acciones disponibles corresponden "
        "al pipeline real de procesamiento por lotes."
    )


def _render_ayuda():
    st.header("¿En qué podemos ayudarte?")
    st.write("Respuestas rápidas para importar, analizar y revisar un lote.")
    preguntas = (
        (
            "¿Cómo importo conversaciones?",
            "Abre Datos, selecciona un archivo JSON compatible y revisa la "
            "muestra antes de procesarlo.",
        ),
        (
            "¿Qué ocurre al procesar el lote?",
            "El pipeline analiza los mensajes y genera resultados según las "
            "rutas disponibles. El procesamiento puede tardar según el lote "
            "y el proveedor de IA.",
        ),
        (
            "¿El contenido se publica automáticamente?",
            "No. Los activos requieren revisión y aprobación. Abrir un enlace "
            "a una red social no publica ni guarda el contenido.",
        ),
        (
            "¿Cómo guardo un activo aprobado?",
            "Aprueba el contenido en Plantillas y usa la sección de guardado "
            "en OCI al final de esa vista.",
        ),
        (
            "¿Por qué no veo un borrador para cada mensaje?",
            "El pipeline solo genera activos para los mensajes que cumplen "
            "las condiciones de sus rutas.",
        ),
    )
    for pregunta, respuesta in preguntas:
        with st.expander(pregunta):
            st.write(respuesta)


pagina_actual = st.radio(
    "Navegación principal",
    PAGINAS,
    horizontal=True,
    key=CLAVE_NAVEGACION,
    label_visibility="collapsed",
)

if pagina_actual == "Datos":
    _render_datos()

resultado = st.session_state.get("resultado")
curaduria = (
    contexto_curaduria(st.session_state, resultado)
    if resultado is not None
    else None
)

if pagina_actual == "Inicio":
    _render_inicio(resultado)
elif pagina_actual == "Agente":
    _render_agente(resultado)
elif pagina_actual == "Análisis":
    _render_analisis(resultado)
elif pagina_actual == "Plantillas":
    if resultado is None:
        vista_plantillas.render()
    else:
        vista_plantillas.render(resultado, curaduria)
elif pagina_actual == "Ayuda":
    _render_ayuda()
