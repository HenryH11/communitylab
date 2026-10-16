import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import streamlit as st
import json
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import pandas as pd
import altair as alt

from src.datos.entrega_ia import preparar_paquete_ia
from src.agentes.grafo import procesar_paquete_entrega
from src.app.curaduria_oci import (
    contexto_curaduria,
    guardar_curaduria,
    validar_activo_curado,
)

st.set_page_config(page_title="CommunityLab", layout="wide")

# ============ ESTILOS ============
st.markdown("""
<style>
    .hero {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 45px 30px;
        border-radius: 18px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .hero h1 { font-size: 2.6rem; font-weight: 700; margin-bottom: 12px; }
    .hero p { font-size: 1.1rem; opacity: 0.92; max-width: 700px; margin: 0 auto; line-height: 1.6; }
    .badge {
        display: inline-block; background: rgba(255,255,255,0.15);
        padding: 5px 14px; border-radius: 20px; font-size: 0.8rem;
        margin-bottom: 18px; letter-spacing: 1px;
    }
    .card {
        background: white; padding: 22px; border-radius: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        border-top: 4px solid #6C5CE7; margin-bottom: 15px; height: 100%;
    }
    .card .num {
        display: inline-block; background: linear-gradient(90deg, #6C5CE7, #a29bfe);
        color: white; width: 32px; height: 32px; border-radius: 50%;
        text-align: center; line-height: 32px; font-weight: 700; margin-bottom: 12px;
    }
    .card h3 { color: #1a1a2e; margin: 8px 0; font-size: 1.05rem; }
    .card p { color: #636e72; font-size: 0.92rem; line-height: 1.5; }
    .section-title { font-size: 1.5rem; font-weight: 700; color: #1a1a2e; margin: 30px 0 15px 0; }
    .stButton>button {
        background: linear-gradient(90deg, #6C5CE7, #a29bfe);
        color: white; border: none; border-radius: 10px;
        padding: 12px 28px; font-weight: 600; font-size: 1rem; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ============ HERO ============
st.markdown("""
<div class="hero">
    <div class="badge">HACKATHON ONE G10 · COMMUNITYLAB</div>
    <h1>De conversaciones a oportunidades</h1>
    <p>Carga las interacciones de tu comunidad, explora la información y prepárala para convertirla en insights y activos de marketing mediante inteligencia artificial.</p>
</div>
""", unsafe_allow_html=True)

# ============ TARJETAS ============
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""<div class="card"><div class="num">1</div><h3>Carga tus datos</h3><p>Importa interacciones desde archivos JSON de tu comunidad.</p></div>""", unsafe_allow_html=True)
with col2:
    st.markdown("""<div class="card"><div class="num">2</div><h3>Explora la comunidad</h3><p>Filtra y revisa las conversaciones antes de procesarlas con IA.</p></div>""", unsafe_allow_html=True)
with col3:
    st.markdown("""<div class="card"><div class="num">3</div><h3>Procesa con IA</h3><p>El pipeline analizará sentimiento, temas y relevancia automáticamente.</p></div>""", unsafe_allow_html=True)

# ============ CARGA ============
st.markdown('<div class="section-title">📥 Importar interacciones</div>', unsafe_allow_html=True)
st.caption("Sube el archivo JSON con los mensajes de la comunidad. Formato compatible: JSON.")

archivo_subido = st.file_uploader("Selecciona el archivo JSON", type=["json"], label_visibility="collapsed")

if archivo_subido is not None:
    try:
        datos = json.load(archivo_subido)
        st.success("✅ Archivo cargado correctamente")

        if st.button("🚀 Procesar con IA (Gemini + LangGraph)"):
            with st.spinner("Procesando mensajes con inteligencia artificial..."):
                try:
                    paquete = preparar_paquete_ia(
                        datos,
                        fecha_referencia="2026-09-17T12:00:00Z",
                        tamano_ciclo=20,
                    )
                    resultado = procesar_paquete_entrega(paquete)
                    st.session_state["resultado"] = resultado
                    st.success("✅ Procesamiento completado")
                except Exception as e:
                    st.error(f"❌ Error durante el procesamiento: {e}")

    except json.JSONDecodeError:
        st.error("❌ El archivo no es un JSON válido. Por favor, verifica el formato y vuelve a intentarlo.")
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {e}")

# ============ RESULTADOS ============
if "resultado" in st.session_state:
    resultado = st.session_state["resultado"]
    curaduria = contexto_curaduria(st.session_state, resultado)
    resultados = resultado.get("resultados_por_id", {})
    total = len(resultados)
    con_activos = sum(1 for r in resultados.values() if r.get("activos_generados"))

    st.markdown('<div class="section-title">📊 Resultados del análisis</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mensajes procesados", total)
    m2.metric("Con contenido", con_activos)
    m3.metric("Sin contenido", total - con_activos)
    faqs = sum(1 for r in resultados.values() if r.get("elegible_faq"))
    m4.metric("Elegibles para FAQ", faqs)

    st.markdown("---")

    # ============ GRÁFICAS ============
    st.markdown('<div class="section-title">📈 Visualización de datos</div>', unsafe_allow_html=True)

    data_graficas = []
    for id_msg, data in resultados.items():
        data_graficas.append({
            "autor": data.get("autor", "Anónimo"),
            "canal": data.get("canal", "N/A"),
            "sentimiento": data.get("sentimiento", "N/A"),
            "tema": data.get("tema_principal", "N/A"),
            "elegible": "Sí" if data.get("elegible_contenido") else "No",
        })
    df = pd.DataFrame(data_graficas)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**Distribución por tema principal**")
        chart_temas = alt.Chart(df).mark_bar().encode(
            x=alt.X('tema:N', sort='-y', title='Tema'),
            y=alt.Y('count():Q', title='Cantidad'),
            color=alt.Color('tema:N', legend=None),
            tooltip=['tema:N', 'count():Q']
        ).properties(height=300)
        st.altair_chart(chart_temas, use_container_width=True)

    with col_g2:
        st.markdown("**Distribución por sentimiento**")
        chart_sent = alt.Chart(df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta('count():Q'),
            color=alt.Color('sentimiento:N', legend=alt.Legend(title="Sentimiento")),
            tooltip=['sentimiento:N', 'count():Q']
        ).properties(height=300)
        st.altair_chart(chart_sent, use_container_width=True)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        st.markdown("**Distribución por canal**")
        chart_canal = alt.Chart(df).mark_bar().encode(
            x=alt.X('count():Q', title='Cantidad'),
            y=alt.Y('canal:N', sort='-x', title='Canal'),
            color=alt.Color('canal:N', legend=None),
            tooltip=['canal:N', 'count():Q']
        ).properties(height=300)
        st.altair_chart(chart_canal, use_container_width=True)

    with col_g4:
        st.markdown("**Elegibles para contenido**")
        chart_eleg = alt.Chart(df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta('count():Q'),
            color=alt.Color('elegible:N', legend=alt.Legend(title="Elegible")),
            tooltip=['elegible:N', 'count():Q']
        ).properties(height=300)
        st.altair_chart(chart_eleg, use_container_width=True)

    st.markdown("---")

    # ============ DETALLES CON CURADURÍA ============
    st.markdown('<div class="section-title">📝 Detalle por mensaje y curaduría</div>', unsafe_allow_html=True)

    for id_msg, data in resultados.items():
        autor = data.get("autor", "Anónimo")
        tema = data.get("tema_principal", "sin tema")
        sentimiento = data.get("sentimiento", "N/A")
        tiene_activos = bool(data.get("activos_generados"))
        icono = "📝" if tiene_activos else "💬"

        with st.expander(f"{icono} {autor} — {tema} · {sentimiento}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Canal:** {data.get('canal', 'N/A')}")
                st.write(f"**Tipo detectado:** {data.get('tipo_detectado', 'N/A')}")
                st.write(f"**Score relevancia:** {data.get('score_relevancia', 'N/A')}")
            with c2:
                st.write(f"**Sentimiento:** {sentimiento}")
                st.write(f"**Subtema:** {data.get('subtema', 'N/A')}")
                elegible = data.get("elegible_contenido", False)
                st.write(f"**Elegible para contenido:** {'Sí' if elegible else 'No'}")
                if "elegible_faq" in data:
                    st.write(f"**Elegible para FAQ:** {'Sí' if data['elegible_faq'] else 'No'}")

            st.markdown(f"*Texto original:* {data.get('texto', '')}")

            if tiene_activos:
                st.markdown("### 🎯 Activos generados")

                for tipo, activo in data["activos_generados"].items():
                    st.markdown(f"#### **{tipo.replace('_', ' ').title()}**")

                    clave = (id_msg, tipo)
                    key_activo = f"{curaduria['lote']}_{id_msg}_{tipo}"
                    if key_activo not in st.session_state:
                        st.session_state[key_activo] = activo.copy()

                    activo_editado = {}
                    for k, v in st.session_state[key_activo].items():
                        if isinstance(v, str):
                            nuevo_valor = st.text_area(
                                f"✏️ {k}",
                                value=v,
                                key=f"edit_{key_activo}_{k}",
                                height=100
                            )
                            activo_editado[k] = nuevo_valor
                        elif isinstance(v, list):
                            nuevo_valor = st.text_area(
                                f"✏️ {k} (uno por línea)",
                                value="\n".join(str(x) for x in v),
                                key=f"edit_{key_activo}_{k}",
                                height=80
                            )
                            activo_editado[k] = [line for line in nuevo_valor.split("\n") if line.strip()]
                        else:
                            activo_editado[k] = v

                    # Una aprobación corresponde a una versión exacta del texto.
                    if (
                        clave in curaduria["aprobados"]
                        and curaduria["aprobados"][clave] != activo_editado
                    ):
                        curaduria["aprobados"].pop(clave)
                        curaduria["guardados"].pop(clave, None)
                        curaduria["informe"] = None
                        st.session_state[f"aprobado_{key_activo}"] = False

                    col_btn1, col_btn2 = st.columns([1, 3])
                    with col_btn1:
                        if st.button(f"✅ Aprobar", key=f"btn_{key_activo}"):
                            try:
                                validar_activo_curado(tipo, activo_editado)
                            except (ValueError, TypeError):
                                st.error(
                                    "Revisa los campos del activo antes de "
                                    "aprobar: textos completos y hashtags "
                                    "válidos (3 a 4, con #)."
                                )
                            else:
                                st.session_state[key_activo] = deepcopy(activo_editado)
                                curaduria["aprobados"][clave] = deepcopy(activo_editado)
                                st.session_state[f"aprobado_{key_activo}"] = True
                                st.success(f"✅ {tipo} aprobado correctamente.")

                    if st.session_state.get(f"aprobado_{key_activo}"):
                        st.info("🟢 Este activo ya fue aprobado para guardar en OCI.")

                    st.markdown("---")

    # ============ RESUMEN DE APROBADOS ============
    st.markdown('<div class="section-title">📦 Activos aprobados listos para OCI</div>', unsafe_allow_html=True)
    aprobados = curaduria["aprobados"]

    if aprobados:
        st.success(f"✅ {len(aprobados)} activo(s) aprobado(s).")
        for identificador, tipo in aprobados:
            st.write(f"- {identificador}: {tipo}")
    else:
        st.info("Aún no has aprobado ningún activo. Edita y aprueba arriba para preparar el guardado en OCI.")

    bucket = os.getenv("OCI_BUCKET_NAME", "bkt-communitylab-marketing")
    periodo = st.text_input(
        "Período de almacenamiento",
        value=datetime.now(timezone.utc).strftime("%Y-%m"),
        key=f"periodo_oci_{curaduria['lote']}",
        help="Usa letras, números, guiones o guiones bajos.",
    )
    # El recibo corresponde también al destino, no solo al contenido.
    destino = (bucket, periodo)
    pendientes = {
        clave: contenido for clave, contenido in aprobados.items()
        if curaduria["guardados"].get(clave) != (destino, contenido)
    }
    st.caption(f"Destino: {bucket} · período {periodo}")
    if st.button(
        "Guardar aprobados en OCI",
        key="guardar_aprobados_oci",
        disabled=not pendientes,
    ):
        with st.spinner("Guardando los activos aprobados..."):
            try:
                informe = asyncio.run(guardar_curaduria(
                    resultado, pendientes, periodo=periodo, bucket=bucket
                ))
            except Exception:
                curaduria["informe"] = None
                st.error(
                    "No se pudo confirmar el guardado. Revisa el período, "
                    "la configuración y los permisos de OCI. Puedes reintentar."
                )
            else:
                curaduria["informe"] = informe
                for guardado in informe["guardados"]:
                    clave = (guardado["id_interaccion"], guardado["tipo"])
                    curaduria["guardados"][clave] = (
                        destino, deepcopy(pendientes[clave])
                    )

    informe = curaduria["informe"]
    if informe:
        if informe["guardados"]:
            st.success(f"OCI confirmó {len(informe['guardados'])} activo(s) guardado(s).")
        for fallo in informe["fallidos"]:
            st.error(
                f"Sin confirmación de guardado: {fallo['id_interaccion']} "
                f"({fallo['tipo']}). Puedes reintentar."
            )
