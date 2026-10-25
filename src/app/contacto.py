"""Contacto habilitado solo despues de verificar el buzon."""

import logging
import os
import re
from urllib.parse import urlencode

import streamlit as st


def render() -> None:
    correo = os.getenv("COMMUNITYLAB_CONTACTO_EMAIL", "").strip()
    if not correo:
        st.write("El correo de soporte esta pendiente de habilitacion. "
                 "Mientras tanto, contacta al administrador de tu instalacion.")
        return
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", correo):
        logging.getLogger(__name__).error("COMMUNITYLAB_CONTACTO_EMAIL no es valido")
        st.error("El canal de contacto no esta disponible. Avisa al administrador.")
        return
    st.write(f"Correo de soporte: {correo}")
    st.link_button(
        "Escribir a soporte",
        f"mailto:{correo}?{urlencode({'subject': 'Soporte CommunityLab'})}",
    )
    st.caption("Abre tu aplicacion de correo. No envies contrasenas, claves ni datos sensibles. "
               "Describe la seccion, el problema y la hora UTC.")
