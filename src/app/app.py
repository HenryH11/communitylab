import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import streamlit as st
import json
import pandas as pd
import altair as alt

from src.datos.entrega_ia import preparar_paquete_ia
from src.agentes.grafo import procesar_paquete_entrega

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
                    paquete = preparar_paquete_ia(datos, fecha_referencia="2026-09-17T12:00:00Z", tamano_ciclo=20)
                    resultado = procesar_paquete_entrega(paquete)
                    st.success("✅ Procesamiento completado")
                    
                    resultados = resultado.get("resultados_por_id", {})
                    total = len(resultados)
                    con_activos = sum(1 for r in resultados.values() if r.get("activos_generados"))
                    
                    # ============ MÉTRICAS ============
                    st.markdown('<div class="section-title">📊 Resultados del análisis</div>', unsafe_allow_html=True)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Mensajes procesados", total)
                    m2.metric("Con contenido", con_activos)
                    m3.metric("Sin contenido", total - con_activos)
                    
                    # Contar FAQs elegibles
                    faqs = sum(1 for r in resultados.values() if r.get("elegible_faq"))
                    m4.metric("Elegibles para FAQ", faqs)
                    
                    st.markdown("---")
                    
                    # ============ GRÁFICAS ============
                    st.markdown('<div class="section-title">📈 Visualización de datos</div>', unsafe_allow_html=True)
                    
                    # Preparar DataFrame
                    data_graficas = []
                    for id_msg, data in resultados.items():
                        data_graficas.append({
                            "autor": data.get("autor", "Anónimo"),
                            "canal": data.get("canal", "N/A"),
                            "sentimiento": data.get("sentimiento", "N/A"),
                            "tema": data.get("tema_principal", "N/A"),
                            "tipo": data.get("tipo_detectado", "N/A"),
                            "score": data.get("score_relevancia", 0),
                            "elegible": "Sí" if data.get("elegible_contenido") else "No",
                            "tiene_activos": "Sí" if data.get("activos_generados") else "No",
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
                    
                    # ============ DETALLES ============
                    st.markdown('<div class="section-title">📝 Detalle por mensaje</div>', unsafe_allow_html=True)
                    
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
                                    st.markdown(f"**{tipo.replace('_', ' ').title()}**")
                                    for k, v in activo.items():
                                        st.write(f"- **{k}:** {v}")
                    
                except Exception as e:
                    st.error(f"❌ Error durante el procesamiento: {e}")
    
    except json.JSONDecodeError:
        st.error("❌ El archivo no es un JSON válido. Por favor, verifica el formato y vuelve a intentarlo.")
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {e}")