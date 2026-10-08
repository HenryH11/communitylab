import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import streamlit as st
import json

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
    .hero h1 {
        font-size: 2.6rem;
        font-weight: 700;
        margin-bottom: 12px;
        letter-spacing: -0.5px;
    }
    .hero p {
        font-size: 1.1rem;
        opacity: 0.92;
        max-width: 700px;
        margin: 0 auto;
        line-height: 1.6;
    }
    .badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-bottom: 18px;
        letter-spacing: 1px;
    }
    .card {
        background: white;
        padding: 22px;
        border-radius: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        border-top: 4px solid #6C5CE7;
        margin-bottom: 15px;
        height: 100%;
        transition: transform 0.2s;
    }
    .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 18px rgba(108,92,231,0.15);
    }
    .card .num {
        display: inline-block;
        background: linear-gradient(90deg, #6C5CE7, #a29bfe);
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        text-align: center;
        line-height: 32px;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .card h3 {
        color: #1a1a2e;
        margin: 8px 0;
        font-size: 1.05rem;
    }
    .card p {
        color: #636e72;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 30px 0 15px 0;
    }
    .stButton>button {
        background: linear-gradient(90deg, #6C5CE7, #a29bfe);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #5b4bc4, #8c7ae6);
        transform: translateY(-2px);
    }
    .result-card {
        background: #f8f9fd;
        padding: 16px 20px;
        border-radius: 12px;
        border-left: 4px solid #6C5CE7;
        margin-bottom: 12px;
    }
    .tag {
        display: inline-block;
        background: #e8e5ff;
        color: #5b4bc4;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .tag-green {
        background: #d4f8e0;
        color: #00b894;
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

# ============ TARJETAS INFORMATIVAS ============
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="card">
        <div class="num">1</div>
        <h3>Carga tus datos</h3>
        <p>Importa interacciones desde archivos JSON o CSV de tu comunidad.</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="card">
        <div class="num">2</div>
        <h3>Explora la comunidad</h3>
        <p>Filtra y revisa las conversaciones antes de procesarlas con IA.</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="card">
        <div class="num">3</div>
        <h3>Procesa con IA</h3>
        <p>El pipeline analizará sentimiento, temas y relevancia automáticamente.</p>
    </div>
    """, unsafe_allow_html=True)

# ============ CARGA DE ARCHIVO ============
st.markdown('<div class="section-title">📥 Importar interacciones</div>', unsafe_allow_html=True)
st.caption("Sube el archivo JSON con los mensajes de la comunidad. Formato compatible: JSON.")

archivo_subido = st.file_uploader("Selecciona el archivo JSON", type=["json"], label_visibility="collapsed")

if archivo_subido is not None:
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
                
                st.success("✅ Procesamiento completado")
                
                # ============ RESULTADOS ============
                st.markdown('<div class="section-title">📊 Resultados del análisis</div>', unsafe_allow_html=True)
                
                resultados = resultado.get("resultados_por_id", {})
                total = len(resultados)
                con_activos = sum(1 for r in resultados.values() if r.get("activos_generados"))
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Mensajes procesados", total)
                m2.metric("Con contenido generado", con_activos)
                m3.metric("Sin contenido", total - con_activos)
                
                st.markdown("---")
                
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
                        
                        st.markdown(f"*Texto original:* {data.get('texto', '')}")
                        
                        if tiene_activos:
                            st.markdown("### 🎯 Activos generados")
                            for tipo, activo in data["activos_generados"].items():
                                st.markdown(f"**{tipo.replace('_', ' ').title()}**")
                                for k, v in activo.items():
                                    st.write(f"- **{k}:** {v}")
                
            except Exception as e:
                st.error(f"❌ Error durante el procesamiento: {e}")