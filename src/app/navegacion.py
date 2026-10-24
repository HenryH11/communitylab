"""Pestañas principales de la app y navegación entre ellas.

Se usa st.tabs con clave: todas las pestañas se pintan en cada ejecución (la
curaduría y sus pruebas lo necesitan) y la pestaña activa se puede cambiar
desde un botón escribiendo su nombre en st.session_state antes de dibujarlas.
"""

import streamlit as st

PESTANAS = ("Inicio", "Datos", "Plantillas", "Resultado", "Agente en vivo", "Analíticas", "Ayuda")
CLAVE_NAVEGACION = "navegacion_principal"
CLAVE_PLANTILLA = "plantilla_activa"


def navegar_a(pestana, plantilla=None):
    """Callback de botón: abre una pestaña y, opcionalmente, una plantilla en Resultado."""
    st.session_state[CLAVE_NAVEGACION] = pestana
    if plantilla is not None:
        st.session_state[CLAVE_PLANTILLA] = plantilla
