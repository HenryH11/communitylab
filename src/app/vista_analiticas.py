"""Analiticas publicas sobre la misma captura Oracle que usa el agente."""

from collections import Counter

import pandas as pd
import streamlit as st

from src.app import fuente_agente


def distribucion(mensajes: tuple[dict, ...], campo: str) -> pd.DataFrame:
    conteos = Counter(m.get(campo) or "Sin clasificar" for m in mensajes)
    return pd.DataFrame(
        sorted(conteos.items(), key=lambda par: (-par[1], par[0])),
        columns=["Categoria", "Mensajes"],
    )


def render() -> None:
    st.header("Estado de las conversaciones de la comunidad")
    st.caption("Fuente: captura de Oracle compartida con el agente. No ejecuta IA.")
    forzar = st.button("Actualizar datos", key="actualizar_analiticas_oracle")
    try:
        captura = fuente_agente.obtener_captura(st.session_state, forzar=forzar)
    except fuente_agente.FuenteNoDisponible as error:
        st.error(str(error))
        return
    if captura.desactualizada:
        st.warning(captura.aviso)
        st.caption("Se muestra la ultima captura disponible, no una lectura actual.")
    st.caption(f"Captura: {captura.capturada_en:%d/%m/%Y %H:%M} UTC")
    mensajes = captura.mensajes
    if not mensajes:
        st.info("Oracle no contiene mensajes consultables en esta captura.")
        return
    total, canales, temas = st.columns(3)
    total.metric("Mensajes consultables", len(mensajes))
    canales.metric("Canales identificados", len({m["canal"] for m in mensajes if m.get("canal")}))
    temas.metric("Temas identificados", len({m["tema_principal"] for m in mensajes if m.get("tema_principal")}))
    st.caption(
        "Los registros consultables excluyen spam. Esta captura no incluye activos "
        "generados ni elegibilidad para contenido; no se infieren esas metricas."
    )
    for campo, titulo in (
        ("tema_principal", "Temas"),
        ("sentimiento", "Sentimiento"),
        ("canal", "Canales"),
        ("tipo_detectado", "Tipos de mensaje"),
    ):
        st.subheader(titulo)
        tabla = distribucion(mensajes, campo)
        st.bar_chart(tabla.set_index("Categoria"), horizontal=True)
        st.dataframe(tabla, hide_index=True, width="stretch")
