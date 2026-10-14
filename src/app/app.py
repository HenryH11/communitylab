"""Streamlit con el componente de interfaz extraído del boceto de Excalidraw."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import streamlit.components.v1 as components
from streamlit import runtime
from src.app.bridge import aplicar_evento, estado_inicial
from src.app.downloads import registrar_descarga

st.set_page_config(page_title="CommunityLab", page_icon="🟣", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none;}
.block-container {padding:0!important;max-width:none!important;}
[data-testid="stMainBlockContainer"] {padding:0!important;max-width:none!important;}
[data-testid="stVerticalBlock"] {gap:0!important;}
[data-testid="stMain"] {overflow-y:scroll!important;scrollbar-gutter:stable;}
iframe[title*="communitylab_excalidraw"] {display:block;border:0;}
.stApp {background:#F7F9FC;}
</style>""", unsafe_allow_html=True)

if "estado_local" not in st.session_state:
    st.session_state.estado_local = estado_inicial()


def procesar_evento():
    st.session_state.estado_local = aplicar_evento(st.session_state.estado_local, st.session_state.communitylab_ui)


@st.cache_resource
def componente():
    return components.declare_component("communitylab_excalidraw", path=str(Path(__file__).with_name("frontend")))


estado = st.session_state.estado_local
descarga = None
if estado.get("exportacion"):
    exportacion = estado["exportacion"]
    descarga = {"id": exportacion["id"], "nombre": exportacion["nombre"],
                "url": registrar_descarga(exportacion, runtime.get_instance().media_file_mgr)}
componente()(estado=estado, descarga=descarga, key="communitylab_ui", default=None, on_change=procesar_evento)
