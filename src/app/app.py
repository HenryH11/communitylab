import html
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import altair as alt
import pandas as pd
import streamlit as st

from src.agentes.conversacion import AgenteConversacional
from src.agentes.grafo import procesar_paquete_entrega
from src.app import vista_plantillas
from src.app.navegacion import CLAVE_NAVEGACION, PESTANAS, navegar_a
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
            --cl-violeta: #6557e8;
            --cl-tinta: #161c32;
            --cl-gris: #68748a;
            --cl-linea: #e4e9f1;
            --cl-fondo: #f7f9fc;
        }
        .stApp { background: var(--cl-fondo); }
        /* Helvetica en todo menos en los iconos de Material. */
        .stApp :is(div, p, span, li, label, button, input, textarea, h1, h2, h3, h4, code):not([data-testid="stIconMaterial"]) {
            font-family: Helvetica, Arial, sans-serif;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: var(--cl-tinta); font-weight: 400; }
        .block-container { max-width: 1440px; padding-top: 1rem; padding-bottom: 2rem; }
        /* La barra propia sustituye a la cabecera de Streamlit. */
        header[data-testid="stHeader"] { display: none; }

        /* Barra superior: marca a la izquierda, pestañas al centro y estado a la derecha, en una fila. */
        .cl-barra { display: flex; align-items: center; gap: .7rem; background: #ffffff; height: 3.6rem;
                    border: 1px solid var(--cl-linea); border-radius: 14px; padding: 0 1.2rem; }
        .cl-logo { width: 34px; height: 34px; border-radius: 9px; background: var(--cl-violeta); color: #fff;
                   display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.15rem; }
        .cl-marca { font-size: 1.25rem; color: var(--cl-tinta); }
        .cl-estado { margin-left: auto; font-size: .7rem; letter-spacing: 1px; color: var(--cl-gris);
                     background: var(--cl-fondo); border: 1px solid var(--cl-linea); border-radius: 6px; padding: 4px 10px; }

        /* Pestañas principales como navegación del boceto */
        /* Solo la barra principal: las sub-pestañas de Resultado quedan con el estilo normal. */
        .st-key-navegacion_principal > div > [role="tablist"] {
            margin: -3.6rem auto 2rem; width: max-content; max-width: calc(100% - 26rem);
            justify-content: center; gap: 2rem; border: 0; background: transparent; position: relative; z-index: 1;
        }
        .st-key-navegacion_principal > div > [role="tablist"] > [data-testid="stTab"] { height: 3.6rem; }
        .st-key-navegacion_principal > div > [role="tablist"] > [data-testid="stTab"] p { color: var(--cl-gris); font-size: .95rem; }
        .st-key-navegacion_principal > div > [role="tablist"] > [aria-selected="true"] p { color: var(--cl-violeta); font-weight: 500; }
        .st-key-navegacion_principal > div > [role="tablist"] .react-aria-SelectionIndicator { height: 4px; border-radius: 4px 4px 0 0; }
        .stApp .react-aria-SelectionIndicator { background-color: var(--cl-violeta); }
        /* En pantallas angostas las pestañas vuelven a su fila, bajo la marca. */
        @media (max-width: 1100px) {
            .cl-barra { border-radius: 14px 14px 0 0; }
            .st-key-navegacion_principal > div > [role="tablist"] {
                margin: 0 0 1.4rem; width: auto; max-width: none; justify-content: flex-start; gap: 1.2rem;
                background: #ffffff; border: 1px solid var(--cl-linea); border-top: 0; border-radius: 0 0 14px 14px; padding: 0 1rem;
            }
        }
        .cl-pie { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-top: 3rem;
                  padding-top: 1rem; border-top: 1px solid var(--cl-linea); color: var(--cl-gris); font-size: .75rem; }

        /* Botones y tarjetas */
        button[kind="primary"] { background-color: var(--cl-violeta); border-color: var(--cl-violeta); color: #fff; }
        button[kind="primary"]:hover { background-color: #5144cf; border-color: #5144cf; color: #fff; }
        button[kind="tertiary"] { color: var(--cl-violeta); font-weight: 600; padding-left: 0; }
        div[data-testid="stVerticalBlockBorderWrapper"] { background: #ffffff; border-color: var(--cl-linea); border-radius: 18px; }
        .stApp .stTextArea textarea, .stApp .stTextInput input { background: #ffffff; border: 1px solid var(--cl-linea); border-radius: 10px; }
        div[data-testid="stRadio"] label:has(input:checked) { color: var(--cl-violeta); font-weight: 700; }

        /* Inicio */
        .cl-eyebrow { display: inline-block; font-size: .72rem; letter-spacing: 1px; font-weight: 600; color: var(--cl-violeta);
                      background: #f0edff; border-radius: 6px; padding: 5px 10px; margin-bottom: 1rem; }
        .cl-hero h1 { font-size: 3rem; font-weight: 400; line-height: 1.15; margin: 0 0 1.2rem; padding: 0; }
        .cl-hero p { color: var(--cl-gris); font-size: 1.1rem; line-height: 1.5; max-width: 34rem; margin-bottom: 2rem; }
        .st-key-inicio_explorar_plantillas button, .st-key-inicio_hablar_agente button { min-height: 2.9rem; border-radius: 8px; }
        .cl-preview { background: #101a36; border-radius: 24px; padding: 1.8rem 2rem; color: #fff; }
        .cl-preview .tag { display: inline-block; font-size: .66rem; letter-spacing: 1px; background: #2c3856;
                           border-radius: 6px; padding: 4px 8px; color: #b7c5e3; }
        .cl-preview h3 { color: #fff !important; font-size: 1.7rem; font-weight: 400; margin: 1rem 0 .4rem; padding: 0; }
        .cl-preview p { color: #b7c5e3; font-size: .95rem; margin: 0 0 1.2rem; }
        .cl-fila { display: flex; align-items: center; gap: .9rem; background: #23365a; border-radius: 12px;
                   padding: 1.1rem 1rem; margin-top: .7rem; font-size: .9rem; }
        .cl-fila b { font-size: .66rem; letter-spacing: 1px; border-radius: 6px; padding: 4px 8px; background: #385577; }
        .cl-fila b.salida { background: #355d66; color: #ddfbf6; }
        .cl-nota { color: #b7c5e3; font-size: .72rem; margin-top: .8rem; }
        .cl-opcion { display: flex; align-items: center; gap: .8rem; }
        .cl-opcion .icono { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center;
                            justify-content: center; font-weight: 700; background: #f0edff; color: var(--cl-violeta); }
        .cl-opcion .icono.verde { background: #e7f7f4; color: #078f83; }
        .cl-opcion .icono.ambar { background: #fff3e4; color: #bc7521; }
        .cl-opcion span { font-size: 1.25rem; color: var(--cl-tinta); }
        .cl-seccion { font-size: 1.5rem; color: var(--cl-tinta); margin: 3rem 0 1rem; }
        [class*="st-key-inicio_opcion_"] { padding: 1.3rem 1.5rem; min-height: 12.5rem; }
        [class*="st-key-inicio_opcion_"] [data-testid="stButton"] { margin-top: 1.2rem; }
        .cl-desc { color: var(--cl-gris); font-size: 1.05rem; margin: 1rem 0 .2rem; }
        .cl-detalle { color: var(--cl-gris); font-size: .82rem; }
    </style>
    <div class="cl-barra"><div class="cl-logo">C</div><div class="cl-marca">communitylab</div>
    <div class="cl-estado">JSON IMPORTADO · SIN CUENTAS</div></div>
    """,
    unsafe_allow_html=True,
)


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
                                st.session_state.pop("agente_conversacional", None)
                                st.session_state.pop("historial_agente", None)
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
    st.header("Entiende las conversaciones de tu comunidad")
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
        "Vista de solo lectura. Edita y aprueba los activos en Resultado."
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
                    + " · edítalos y apruébalos en Resultado."
                )
            else:
                st.caption("Este mensaje no generó activos.")
            if data.get("errores"):
                st.caption(
                    f"El pipeline registró {len(data['errores'])} error(es) "
                    "en este mensaje."
                )


def _vista_previa_inicio(resultado):
    """Tarjeta oscura de Inicio: con lote, insight y salida reales; sin lote, el ejemplo del boceto."""
    insight, salida = "Interés en recomendaciones prácticas", "Publicación lista para revisar"
    nota = "Ejemplo ilustrativo · procesa un lote en Datos para ver el tuyo."
    resultados = (resultado or {}).get("resultados_por_id") or {}
    if resultados:
        temas = pd.Series([d.get("tema_principal") for d in resultados.values()
                           if d.get("tema_principal") and d.get("es_spam_detectado") is not True])
        if not temas.empty:
            tema = str(temas.value_counts().index[0]).replace("_", " ")
            insight = f"Tema más frecuente: {tema}"
        total_activos = sum(len(d.get("activos_generados") or {}) for d in resultados.values())
        salida = f"{total_activos} borrador(es) listos para revisar"
        nota = f"Último lote: {len(resultados)} mensajes procesados."
    return (
        '<div class="cl-preview"><span class="tag">VISTA PREVIA</span>'
        "<h3>De miles de mensajes a una idea</h3>"
        "<p>Se detectaron temas y opiniones útiles para construir contenidos relevantes.</p>"
        f'<div class="cl-fila"><b>INSIGHT</b>{html.escape(insight)}</div>'
        f'<div class="cl-fila"><b class="salida">SALIDA</b>{html.escape(salida)}</div>'
        f'<div class="cl-nota">{html.escape(nota)}</div></div>'
    )


def _render_inicio(resultado):
    contenido, resumen = st.columns([1.25, 1], gap="large", vertical_alignment="center")
    with contenido:
        st.markdown(
            '<div class="cl-hero"><span class="cl-eyebrow">DE CONVERSACIONES A OPORTUNIDADES</span>'
            "<h1>Tu comunidad habla.<br>Convierte esa voz en valor.</h1>"
            "<p>Analiza conversaciones, descubre lo que importa y crea contenidos "
            "para tus redes sin empezar desde cero.</p></div>",
            unsafe_allow_html=True,
        )
        primario, secundario, _ = st.columns([1.1, 1, 1])
        primario.button("Explorar plantillas →", type="primary", key="inicio_explorar_plantillas",
                        use_container_width=True, on_click=navegar_a, args=("Plantillas",))
        secundario.button("Hablar con agente", key="inicio_hablar_agente",
                          use_container_width=True, on_click=navegar_a, args=("Agente en vivo",))
        if resultado is None:
            st.caption("¿Primera vez? Empieza importando un lote en Datos.")
            st.button("Importar datos →", key="inicio_ir_datos", type="tertiary",
                      on_click=navegar_a, args=("Datos",))

    with resumen:
        st.markdown(_vista_previa_inicio(resultado), unsafe_allow_html=True)

    st.markdown('<div class="cl-seccion">Elige cómo quieres trabajar</div>', unsafe_allow_html=True)
    for columna, (destino, icono, tono, titulo, descripcion, detalle) in zip(
        st.columns(3),
        (
            ("Plantillas", "T", "", "Plantillas", "Resultados listos para adaptar", "Contenido · análisis"),
            ("Agente en vivo", "A", "verde", "Agente en vivo", "Pide un post, análisis o resumen", "Lenguaje natural"),
            ("Ayuda", "?", "ambar", "FAQ y ayuda", "Conoce capacidades y límites", "Guías · consultas"),
        ),
    ):
        with columna:
            with st.container(border=True, key=f"inicio_opcion_{destino.split()[0].lower()}"):
                st.markdown(
                    f'<div class="cl-opcion"><div class="icono {tono}">{icono}</div><span>{titulo}</span></div>'
                    f'<div class="cl-desc">{descripcion}</div><div class="cl-detalle">{detalle}</div>',
                    unsafe_allow_html=True,
                )
                st.button("Explorar →", key=f"inicio_nav_{destino.split()[0].lower()}", type="tertiary",
                          on_click=navegar_a, args=(destino,))


def _render_agente(resultado):
    st.header("Agente CommunityLab")
    st.write(
        "Explora los datos procesados de la comunidad y consulta sus "
        "conversaciones en lenguaje natural."
    )

    chat, estado_columna = st.columns([2, 1])
    with chat:
        with st.container(border=True):
            st.markdown("#### Conversación")
            modo_verificacion = st.toggle(
                "Modo de verificación automática",
                help=(
                    "Verifica automáticamente las afirmaciones de los borradores "
                    "de marketing y muestra las fuentes citadas."
                ),
                key="modo_verificacion",
            )
            resultados = (
                resultado.get("resultados_por_id", {})
                if resultado is not None
                else {}
            )
            if resultados:
                if "agente_conversacional" not in st.session_state:
                    try:
                        st.session_state["agente_conversacional"] = (
                            AgenteConversacional(resultado)
                        )
                    except ValueError as error:
                        st.warning(f"El agente no puede usar este lote: {error}")
                        return

                consulta = st.chat_input(
                    "Pregunta sobre las conversaciones procesadas..."
                )
                if consulta:
                    mensajes = st.session_state.setdefault("historial_agente", [])
                    mensajes.append({"role": "user", "content": consulta})
                    agente = st.session_state["agente_conversacional"]
                    modo = (
                        "verificacion_automatica"
                        if modo_verificacion
                        else "prompt_estricto"
                    )
                    try:
                        with st.spinner("Consultando al agente..."):
                            salida = agente.consultar(
                                consulta,
                                modo_verificacion=modo,
                            )
                        mensajes.append(
                            {
                                "role": "assistant",
                                "content": salida["respuesta"],
                                "salida": salida,
                                "modo_verificacion": modo,
                            }
                        )
                    except Exception as error:
                        mensajes.append(
                            {
                                "role": "assistant",
                                "error": str(error),
                            }
                        )

                for mensaje in st.session_state.get("historial_agente", []):
                    with st.chat_message(mensaje["role"]):
                        if "error" in mensaje:
                            st.error(f"No se pudo consultar al agente: {mensaje['error']}")
                            continue
                        st.markdown(mensaje["content"])
                        if mensaje.get("modo_verificacion") == "verificacion_automatica":
                            salida = mensaje["salida"]
                            verificacion = salida.get("verificacion", {})
                            with st.expander("Verificación y fuentes", expanded=True):
                                st.caption(
                                    f"Estado: {verificacion.get('estado', 'no_disponible')}"
                                )
                                st.write(
                                    verificacion.get(
                                        "resumen",
                                        "El agente no devolvió un resumen de verificación.",
                                    )
                                )
                                for afirmacion in verificacion.get("afirmaciones", []):
                                    estado_afirmacion = (
                                        "Respaldada"
                                        if afirmacion.get("respaldada")
                                        else "Requiere revisión"
                                    )
                                    st.markdown(
                                        f"- **{estado_afirmacion}:** "
                                        f"{afirmacion['afirmacion']}"
                                    )
                                    if afirmacion.get("citas"):
                                        st.caption(
                                            "Fuentes: "
                                            + ", ".join(afirmacion["citas"])
                                        )

                                citas = salida.get("citas", [])
                                if citas:
                                    st.markdown("**Fuentes citadas**")
                                    for cita in citas:
                                        fuente = resultados.get(cita, {})
                                        st.markdown(
                                            f"**{cita}** · "
                                            f"{fuente.get('autor', 'Autor desconocido')} · "
                                            f"{fuente.get('canal', 'Canal desconocido')}"
                                        )
                                        st.write(fuente.get("texto", ""))
                                else:
                                    st.caption("La respuesta no incluye fuentes citadas.")
            else:
                st.info("Importa y procesa un lote desde Datos para iniciar el chat.")
    with estado_columna:
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
            "Aprueba el contenido en Resultado y usa la sección de guardado "
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


# Todas las pestañas se pintan en cada ejecución, así que cambiar de pestaña no
# pierde nada de st.session_state. Datos se llena primero para que un lote recién
# procesado aparezca en las demás pestañas en esta misma ejecución.
pestanas = dict(zip(PESTANAS, st.tabs(PESTANAS, key=CLAVE_NAVEGACION, on_change="rerun")))

with pestanas["Datos"]:
    _render_datos()

resultado = st.session_state.get("resultado")
curaduria = (
    contexto_curaduria(st.session_state, resultado)
    if resultado is not None
    else None
)

with pestanas["Inicio"]:
    _render_inicio(resultado)
with pestanas["Plantillas"]:
    vista_plantillas.render_plantillas(resultado)
with pestanas["Resultado"]:
    vista_plantillas.render_resultado(resultado, curaduria)
with pestanas["Agente en vivo"]:
    _render_agente(resultado)
with pestanas["Analíticas"]:
    _render_analisis(resultado)
with pestanas["Ayuda"]:
    _render_ayuda()

st.markdown(
    '<div class="cl-pie"><span>CommunityLab · de conversaciones a oportunidades</span>'
    "<span>Revisión humana antes de publicar · nada se publica automáticamente</span></div>",
    unsafe_allow_html=True,
)
