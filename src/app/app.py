import streamlit as st
import json
import tempfile

from src.data.ingest import cargar_json
from src.data.entrega_ia import preparar_paquete_ia
from src.agentes.grafo import procesar_paquete_entrega

st.set_page_config(page_title="CommunityLab", layout="wide")

st.title("CommunityLab - Panel de Control")
st.write("Sube el archivo JSON con los mensajes de la comunidad para procesarlos con IA.")

archivo_subido = st.file_uploader("Selecciona el archivo JSON", type=["json"])

if archivo_subido is not None:
    datos = json.load(archivo_subido)
    st.success("¡Archivo cargado correctamente!")
    
    if st.button("🚀 Procesar con IA (Gemini + LangGraph)"):
        with st.spinner("Procesando mensajes... esto puede tomar unos segundos."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmp:
                    json.dump(datos, tmp, ensure_ascii=False, indent=2)
                    ruta_temporal = tmp.name
                
                paquete = preparar_paquete_ia(
                    cargar_json(ruta_temporal),
                    fecha_referencia="2026-09-17T12:00:00Z",
                    tamano_ciclo=20,
                )
                
                resultado = procesar_paquete_entrega(paquete)
                
                st.success("¡Procesamiento completado!")
                
                st.subheader("📊 Resultados del análisis")
                st.json(resultado["resultados_por_id"])
                
            except Exception as e:
                st.error(f"Error durante el procesamiento: {e}")
