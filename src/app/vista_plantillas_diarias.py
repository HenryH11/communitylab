"""Catálogo de Marketing y adaptación local de contenido preparado."""

from datetime import datetime, timezone
import logging
from uuid import uuid4

import streamlit as st

from src.app import publicacion_redes
from src.app.horas import fecha_local, zona_usuario
from src.app.plantillas_diarias import (
    CatalogoDiario, PLANTILLAS_DIARIAS, RepositorioCatalogo, ZONA,
)


@st.cache_data(ttl=45, max_entries=32, show_spinner=False)
def leer_catalogo(revision: str = "") -> CatalogoDiario | None:
    """La revisión forma parte de la clave de caché, sin invalidar otras sesiones."""
    return RepositorioCatalogo.desde_entorno().leer()[0]


def _seleccionar(identificador: str) -> None:
    st.session_state["diaria_seleccion"] = identificador


@st.fragment(run_every="60s")
def render():
    st.subheader("Contenido del día")
    zona = zona_usuario()
    ahora = datetime.now(timezone.utc)
    horario = ahora.replace(hour=13, minute=0, second=0, microsecond=0)
    st.caption(f"Renovación diaria: 13:00 UTC · Hoy: {fecha_local(horario, zona)}")
    recargar = st.button(
        "Volver a cargar catálogo", key="actualizar_catalogo_diario",
        help="Consulta las versiones publicadas. No genera contenido ni reintenta las plantillas pendientes.",
    )
    if recargar:
        st.session_state["diarias_revision"] = uuid4().hex
    try:
        revision = st.session_state.get("diarias_revision", "")
        catalogo = leer_catalogo(revision) if revision else leer_catalogo()
    except Exception:
        logging.getLogger(__name__).exception("No se pudo leer el catálogo diario de OCI")
        st.error("No se pudo actualizar el catálogo. Puedes volver a intentarlo en unos momentos.")
        catalogo = st.session_state.get("diarias_ultimo_catalogo")
        if catalogo is None:
            return
        st.warning("Se conserva el último catálogo que pudiste consultar; la recarga no se completó.")
    else:
        if catalogo is not None:
            st.session_state["diarias_ultimo_catalogo"] = catalogo
        else:
            st.session_state.pop("diarias_ultimo_catalogo", None)
    if catalogo is None:
        st.info("El equipo todavía no ha publicado el primer catálogo diario.")
        return
    st.caption(f"Último intento de renovación: {fecha_local(catalogo.intentado_en, zona)}")
    if catalogo.intentado_en.astimezone(ZONA).date() < ahora.date():
        st.warning("El catálogo todavía no se ha actualizado hoy. Comprueba la fecha de cada contenido.")
    busqueda = st.text_input("Buscar contenido", key="diarias_busqueda")
    categoria = st.segmented_control(
        "Mostrar", ["Todas", "Publicaciones", "Informes"], default="Todas",
        key="diarias_categoria",
    )
    visibles = [
        p for p in PLANTILLAS_DIARIAS
        if busqueda.casefold() in p.nombre.casefold()
        and (categoria in (None, "Todas")
             or (categoria == "Publicaciones") == (p.plataforma is not None))
    ]
    if not visibles:
        st.info("No hay plantillas que coincidan con la búsqueda.")
        return
    seleccion = st.session_state.get("diaria_seleccion")
    if seleccion not in {p.id for p in visibles}:
        seleccion = next((p.id for p in visibles if p.id in catalogo.entradas), visibles[0].id)
        st.session_state["diaria_seleccion"] = seleccion
    for inicio in range(0, len(visibles), 2):
        for columna, plantilla in zip(st.columns(2, gap="medium"), visibles[inicio:inicio + 2]):
            with columna, st.container(border=True, height="stretch"):
                st.markdown(f"**{plantilla.nombre}**")
                entrada = catalogo.entradas.get(plantilla.id)
                if plantilla.id in catalogo.fallos:
                    st.caption("Pendiente de renovación" if entrada else "Pendiente")
                elif entrada:
                    st.caption("Disponible para revisar")
                else:
                    st.caption("Sin contenido todavía")
                st.button(
                    "Seleccionada" if plantilla.id == seleccion else "Abrir plantilla",
                    key=f"abrir_diaria_{plantilla.id}", on_click=_seleccionar,
                    args=(plantilla.id,), width="stretch",
                    type="primary" if plantilla.id == seleccion else "secondary",
                )
    plantilla = next(p for p in visibles if p.id == seleccion)
    st.subheader(plantilla.nombre)
    fallo = catalogo.fallos.get(seleccion)
    entrada = catalogo.entradas.get(seleccion)
    if fallo:
        st.warning(f"{fallo} Se conserva la última versión disponible, si existe.")
    if entrada is None:
        st.info("Todavía no hay contenido preparado para esta plantilla.")
        return
    st.caption(f"Generado: {fecha_local(entrada.generado_en, zona)}")
    if entrada.generado_en.astimezone(ZONA).date() < ahora.date():
        st.warning(f"Contenido anterior: generado el {fecha_local(entrada.generado_en, zona)}.")
    salida = entrada.salida
    if salida.get("verificacion", {}).get("estado") == "sin_evidencia":
        st.info("Sin evidencia para esta plantilla en la captura actual.")
        st.markdown(salida["respuesta"])
        return
    clave = f"diaria_{seleccion}_{entrada.generado_en.isoformat()}"
    borrador = salida.get("borrador")
    editor, previa = st.columns(2, gap="medium")
    with editor, st.container(border=True):
        st.markdown("**Adapta el contenido**")
        if borrador:
            titulo = st.text_input("Título", value=borrador["titulo"], key=f"{clave}_titulo") or ""
            contenido = st.text_area(
                "Contenido", value=borrador["contenido"], height=260, key=f"{clave}_contenido",
            ) or ""
            hashtags = st.text_input(
                "Hashtags", value=" ".join(borrador["hashtags"]), key=f"{clave}_hashtags",
            ) or ""
            adaptado = dict(borrador, titulo=titulo, contenido=contenido, hashtags=hashtags.split())
            cambiado = adaptado != borrador
            hay_contenido = bool(
                contenido.strip() or (titulo.strip() and borrador["plataforma"] != "x")
            )
            texto = publicacion_redes.texto_publicacion(adaptado) if hay_contenido else ""
        else:
            texto = st.text_area(
                "Contenido", value=salida["respuesta"], height=320, key=f"{clave}_contenido",
            ) or ""
            cambiado = texto != salida["respuesta"]
        st.caption("Los cambios son locales a esta vista; no sustituyen el catálogo publicado.")
    with previa, st.container(border=True):
        st.markdown("**Vista previa**")
        if cambiado:
            st.warning("Adaptación sin verificar: revisa las afirmaciones y las fuentes antes de compartir.")
        st.markdown(texto)
        if not texto.strip():
            st.info("Escribe contenido para descargarlo o preparar la publicación.")
            return
        st.download_button(
            "Descargar texto", texto, file_name=f"{seleccion}.txt",
            mime="text/plain", key=f"{clave}_descargar",
        )
        if borrador:
            publicacion_redes.render(adaptado, clave=clave)
        else:
            with st.expander("Copiar texto"):
                st.code(texto, language=None, wrap_lines=True)
    verificacion = salida.get("verificacion", {})
    if verificacion.get("estado") == "requiere_revision":
        st.warning("La verificación del original encontró afirmaciones que requieren revisión.")
    with st.expander("Fuentes y revisión del original"):
        if verificacion.get("resumen"):
            st.caption(verificacion["resumen"])
        if salida["citas"]:
            st.caption("Fuentes: " + ", ".join(salida["citas"]))
