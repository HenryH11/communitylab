import streamlit as st
import json

st.set_page_config(page_title="CommunityLab", layout="wide")

st.title("CommunityLab - Panel de Control")
st.write("Sube el archivo JSON con los mensajes de la comunidad para empezar.")

archivo_subido = st.file_uploader("Selecciona el archivo JSON", type=["json"])

if archivo_subido is not None:
    datos = json.load(archivo_subido)
    st.success("¡Archivo cargado correctamente!")
    st.json(datos)
