"""Archivos descargables en memoria, servidos por el mismo localhost de Streamlit.

El gestor es el mismo que utiliza st.download_button. Está aislado aquí para
validar su compatibilidad al actualizar Streamlit; no guarda archivos en OCI.
"""
import json


def registrar_descarga(exportacion, gestor):
    contenido = json.dumps(exportacion["contenido"], ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    return gestor.add(contenido, "application/json", "communitylab.exportacion", file_name=exportacion["nombre"], is_for_static_download=True)
