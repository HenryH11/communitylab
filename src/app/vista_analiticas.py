"""Analiticas publicas sobre la misma captura Oracle que usa el agente."""

from collections import Counter
import math

import pandas as pd
import streamlit as st

from src.app import fuente_agente

CAMPOS = {
    "tema_principal": "Tema", "sentimiento": "Sentimiento",
    "canal": "Canal", "tipo_detectado": "Tipo",
}


def categoria(mensaje: dict, campo: str) -> str:
    return mensaje.get(campo) or "Sin clasificar"


def filtrar(mensajes: tuple[dict, ...], filtros: dict[str, list[str]],
            busqueda: str = "") -> tuple[dict, ...]:
    termino = busqueda.strip().casefold()
    return tuple(
        m for m in mensajes
        if all(not valores or categoria(m, campo) in valores for campo, valores in filtros.items())
        and (not termino or termino in m.get("texto", "").casefold()
             or termino in m.get("id", "").casefold())
    )


def distribucion(mensajes: tuple[dict, ...], campo: str) -> pd.DataFrame:
    conteos = Counter(categoria(m, campo) for m in mensajes)
    return pd.DataFrame(
        sorted(conteos.items(), key=lambda par: (-par[1], par[0])),
        columns=["Categoria", "Mensajes"],
    )


@st.fragment
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
    st.subheader("Explorar la base")
    columnas = st.columns(4)
    filtros = {}
    for columna, (campo, etiqueta) in zip(columnas, CAMPOS.items()):
        with columna:
            filtros[campo] = st.multiselect(
                etiqueta, sorted({categoria(m, campo) for m in mensajes}),
                key=f"analiticas_filtro_{campo}",
            )
    busqueda = st.text_input("Buscar texto o ID", key="analiticas_busqueda")
    base = mensajes
    mensajes = filtrar(base, filtros, busqueda)
    st.caption(f"Seleccion: {len(mensajes)} de {len(base)} mensajes de la captura. Filtros combinados por interseccion.")
    if not mensajes:
        st.info("No hay mensajes que coincidan con estos filtros.")
        return
    total, canales, temas = st.columns(3)
    total.metric("Mensajes consultables", len(mensajes))
    canales.metric("Canales identificados", len({m["canal"] for m in mensajes if m.get("canal")}))
    temas.metric("Temas identificados", len({m["tema_principal"] for m in mensajes if m.get("tema_principal")}))
    st.caption(
        "Los registros consultables excluyen spam. Esta captura no incluye activos "
        "generados ni elegibilidad para contenido; no se infieren esas metricas."
    )
    resumen, cruces, fuentes = st.tabs(["Resumen", "Cruces", "Fuentes"])
    with resumen:
        st.caption(f"Porcentajes calculados sobre los {len(mensajes)} mensajes seleccionados, no sobre toda la base.")
        for campo, titulo in CAMPOS.items():
            st.subheader(titulo)
            tabla = distribucion(mensajes, campo)
            tabla["Porcentaje"] = (tabla["Mensajes"] * 100 / len(mensajes)).round(2)
            st.bar_chart(tabla.set_index("Categoria")["Mensajes"], horizontal=True)
            st.dataframe(tabla, hide_index=True, width="stretch")
    with cruces:
        fila = st.selectbox("Agrupar filas por", list(CAMPOS), format_func=lambda c: CAMPOS[c])
        opciones = [c for c in CAMPOS if c != fila]
        columna = st.selectbox("Comparar columnas por", opciones, format_func=lambda c: CAMPOS[c])
        tabla_cruce = pd.crosstab(
            pd.Series([categoria(m, fila) for m in mensajes], name=CAMPOS[fila]),
            pd.Series([categoria(m, columna) for m in mensajes], name=CAMPOS[columna]),
        )
        st.caption("Conteos exactos del subconjunto seleccionado; no implican causalidad ni tendencias temporales.")
        st.dataframe(tabla_cruce, width="stretch")
        st.download_button("Descargar cruce CSV", tabla_cruce.to_csv().encode("utf-8-sig"),
                           file_name="cruce_comunidad.csv", mime="text/csv")
    with fuentes:
        sin_fecha = sum(not m.get("fecha") for m in mensajes)
        st.caption(f"{len(mensajes)} fuentes seleccionadas; {sin_fecha} sin fecha. No se inventan fechas ni tendencias.")
        ordenados = sorted(mensajes, key=lambda m: m["id"])
        tabla_fuentes = pd.DataFrame(ordenados).reindex(columns=[
            "id", "texto", "canal", "sentimiento", "tema_principal", "tipo_detectado", "fecha",
        ])
        tamano = st.selectbox("Fuentes por pagina", [20, 50, 100])
        paginas = math.ceil(len(ordenados) / tamano)
        pagina = st.selectbox("Pagina", range(1, paginas + 1))
        inicio = (pagina - 1) * tamano
        st.dataframe(tabla_fuentes.iloc[inicio:inicio + tamano], hide_index=True, width="stretch")
        identificador = st.selectbox("Leer fuente completa", [m["id"] for m in ordenados])
        fuente = next(m for m in ordenados if m["id"] == identificador)
        st.text(fuente.get("texto") or "Texto no disponible")
        st.download_button(
            "Descargar fuentes seleccionadas CSV",
            tabla_fuentes.to_csv(index=False).encode("utf-8-sig"),
            file_name="fuentes_comunidad.csv", mime="text/csv",
        )
        st.caption("La descarga incluye textos completos: aplicar las reglas de privacidad del equipo.")
