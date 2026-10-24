"""Catálogo de Marketing leído desde OCI, sin ejecutar modelos en la web."""

from datetime import datetime, timezone
import logging

import streamlit as st

from src.app import publicacion_redes
from src.app.plantillas_diarias import (
    CatalogoDiario, PLANTILLAS_DIARIAS, RepositorioCatalogo, ZONA,
)


@st.cache_data(ttl=45, show_spinner=False)
def leer_catalogo() -> CatalogoDiario | None:
    return RepositorioCatalogo.desde_entorno().leer()[0]


@st.fragment(run_every="60s")
def render():
    st.subheader("Contenido del día")
    st.caption(
        "Renovación diaria prevista: 08:00 · Bogotá. "
        "Revisa el contenido y confirma la publicación en cada red."
    )
    if st.button("Actualizar catálogo", key="actualizar_catalogo_diario"):
        leer_catalogo.clear()
    try:
        catalogo = leer_catalogo()
    except Exception:
        logging.getLogger(__name__).exception("No se pudo leer el catálogo diario de OCI")
        st.error(
            "No se pudo cargar el contenido preparado. Intenta actualizar; "
            "si continúa, avisa al equipo de CommunityLab."
        )
        return
    if catalogo is None:
        st.info("El equipo todavía no ha publicado el primer catálogo diario.")
        return
    ahora = datetime.now(timezone.utc).astimezone(ZONA)
    st.caption(
        f"Último intento: {catalogo.intentado_en.astimezone(ZONA):%d/%m/%Y %H:%M} · Bogotá"
    )
    if catalogo.intentado_en.astimezone(ZONA).date() < ahora.date():
        st.warning("El catálogo todavía no se ha actualizado hoy. Comprueba la fecha de cada contenido.")
    busqueda = st.text_input("Buscar contenido", key="diarias_busqueda")
    for plantilla in PLANTILLAS_DIARIAS:
        if busqueda.casefold() not in plantilla.nombre.casefold():
            continue
        entrada = catalogo.entradas.get(plantilla.id)
        fallo = catalogo.fallos.get(plantilla.id)
        with st.expander(plantilla.nombre, expanded=False):
            if fallo:
                st.warning(f"{fallo} Se conserva la última versión disponible, si existe.")
            if entrada is None:
                st.info("Todavía no hay contenido preparado para esta plantilla.")
                continue
            fecha = entrada.generado_en.astimezone(ZONA)
            st.caption(f"Generado el {fecha:%d/%m/%Y a las %H:%M} · Preparado para revisión")
            if fecha.date() < ahora.date():
                st.warning(f"Contenido anterior: corresponde al {fecha:%d/%m/%Y}, no a hoy.")
            salida = entrada.salida
            if salida.get("verificacion", {}).get("estado") == "sin_evidencia":
                st.info("Sin evidencia para esta plantilla en la captura actual.")
            st.markdown(salida["respuesta"])
            if salida.get("borrador"):
                st.markdown("**" + salida["borrador"]["titulo"] + "**")
                st.write(salida["borrador"]["contenido"])
                st.caption(" ".join(salida["borrador"]["hashtags"]))
                publicacion_redes.render(
                    salida["borrador"], clave=f"diaria_{plantilla.id}_{fecha.isoformat()}",
                )
            else:
                st.code(salida["respuesta"], language=None, wrap_lines=True)
            verificacion = salida.get("verificacion", {})
            if verificacion.get("estado") == "requiere_revision":
                st.warning("La verificación encontró afirmaciones que requieren revisión antes de publicar.")
            if verificacion.get("resumen"):
                st.caption(verificacion["resumen"])
            if salida["citas"]:
                st.caption("Fuentes: " + ", ".join(salida["citas"]))
    st.caption("TikTok, YouTube y generación multimedia: integración pendiente.")
