"""Pestañas Plantillas y Resultado: catálogo, borradores, curaduría y guardado en OCI.

Reproduce las vistas "Plantillas" y "Resultado" del boceto de Jhonattan con
componentes de Streamlit. Los editores, las aprobaciones y el guardado son la
curaduría que antes vivía en app.py; sus claves no cambian.
"""

import asyncio
import html
import os
from copy import deepcopy
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st

from src.app.curaduria_oci import guardar_curaduria, validar_activo_curado
from src.app.navegacion import CLAVE_PLANTILLA, navegar_a
from src.app.plantillas_catalogo import (
    CATEGORIAS,
    PLANTILLAS,
    borradores,
    contar,
    distribucion,
    filtrar,
    tipos_sin_plantilla,
)

ESTILOS = """
<style>
    .section-title { color: #161c32; font-size: 1.35rem; font-weight: 400; margin: 1.1rem 0 .6rem; }
    .pl-top { display: flex; align-items: center; gap: 12px; }
    .pl-icon { width: 40px; height: 40px; border-radius: 10px; background: #f0edff; color: #6557e8;
               display: flex; align-items: center; justify-content: center; font-weight: 700; flex: none; }
    .pl-icon.analitica { background: #e7f7f4; color: #078f83; }
    .pl-icon.conocimiento { background: #ebf3ff; color: #3977d5; }
    .pl-titulo { font-size: 2rem; font-weight: 400; color: #161c32; margin: 0 0 .3rem; }
    .pl-subtitulo { color: #4a556b; font-size: 1rem; margin-bottom: 1.4rem; }
    .pl-name { font-weight: 400; color: #161c32; font-size: 1.2rem; flex: 1; }
    .pl-tag { font-size: .66rem; letter-spacing: 1px; color: #68748a; background: #f2f4f8;
              border-radius: 6px; padding: 3px 8px; }
    .pl-desc { color: #161c32; margin: 12px 0 2px; font-size: .92rem; }
    .pl-detail { color: #68748a; font-size: .82rem; }
    .pl-count { color: #6557e8; font-weight: 600; font-size: .82rem; margin-top: 8px; }
    .pl-count.soon { color: #bc7521; }
    .pl-off, .pl-off .pl-name, .pl-off .pl-desc, .pl-off .pl-detail { color: #8a94a8; }
    .pl-off .pl-icon { background: #f2f4f8; color: #8a94a8; }
    [class*="st-key-pl_card_"] .pl-count { margin: 0; }
    [class*="st-key-pl_card_"] [data-testid="stHorizontalBlock"] [data-testid="stMarkdownContainer"] p { margin: 0; }
    .st-key-plantillas_categoria label { padding: .55rem .7rem; border-radius: 10px; width: 100%; }
    .st-key-plantillas_categoria label:has(input:checked) { background: #f0edff; }
    .st-key-plantillas_orden [data-baseweb="select"] > div { background: transparent; border: 0; }
    .pl-pill { display: inline-block; font-size: .7rem; letter-spacing: 1px; font-weight: 600;
               border-radius: 6px; padding: 4px 10px; background: #f0edff; color: #6557e8; }
    .pl-pill.ambar { background: #fff3e4; color: #bc7521; }
    .pl-pill.verde { background: #e7f7f4; color: #078f83; }
    .pl-config-titulo { font-size: 1.1rem; font-weight: 600; color: #161c32; margin-bottom: .8rem; }
    .pl-campo { margin-bottom: .8rem; }
    .pl-campo span { display: block; font-size: .78rem; color: #68748a; margin-bottom: .3rem; }
    .stApp .pl-campo > div { border: 1px solid #e4e9f1; border-radius: 8px; padding: .5rem .7rem; font-size: .9rem; color: #161c32; }
    .pl-crumbs { color: #68748a; font-size: .85rem; margin-bottom: .2rem; }
    .st-key-plantilla_activa [role="tab"] p { font-size: .85rem; }
    .st-key-plantilla_activa [role="tablist"] { gap: .9rem; }
    .stApp [data-testid="stExpander"] details { border-color: #e4e9f1; border-radius: 14px; }
    .stApp [data-testid="stExpander"] summary { background: #f7f9fc; font-size: .85rem; }
    .pl-heading { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: .6rem; }
    .pl-heading h2 { margin: 0; padding: 0; font-size: 1.7rem; font-weight: 400; color: #161c32; }
    .pl-preview { background: white; border: 1px solid #e4e9f1; border-radius: 14px; padding: 14px; }
    .pl-preview .org { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #161c32;
                       font-size: .85rem; margin-bottom: 10px; }
    .pl-preview .org::before { content: ""; width: 14px; height: 14px; border-radius: 50%; background: #6557e8; }
    .pl-preview .org span { margin-left: auto; color: #68748a; }
    .pl-preview .hero { position: relative; overflow: hidden; min-height: 9rem; background: #e8eaff; border-radius: 12px;
                        padding: 18px 16px; color: #161c32; font-size: 1.15rem; font-weight: 600; line-height: 1.25; }
    .pl-preview .hero::after { content: ""; position: absolute; width: 5rem; height: 5rem; right: -1.4rem; bottom: -1.4rem;
                               border-radius: 50%; background: #cad2fa; opacity: .7; }
    .pl-preview .hero small { display: block; font-size: .78rem; font-weight: 400; color: #68748a; margin-top: 10px; }
    .pl-preview .body { white-space: pre-wrap; color: #161c32; font-size: .85rem; line-height: 1.5; margin-top: 12px;
                        max-height: 14rem; overflow: auto; }
    .pl-preview .tags { color: #6557e8; font-size: .8rem; margin-top: 8px; }
    .pl-preview .note { display: inline-block; color: #bc7521; background: #fff3e4; border-radius: 6px;
                        font-size: .66rem; letter-spacing: 1px; padding: 4px 8px; margin-top: 12px; }
</style>
"""

CAMPOS_TEXTO = ("titulo", "titular", "seccion", "tema", "hallazgo", "contenido", "resumen",
                "respuesta", "sugerencia_detectada")


def texto_para_copiar(activo):
    """Texto plano del activo en un orden legible, con las listas al final."""
    partes = [activo[c] for c in CAMPOS_TEXTO if isinstance(activo.get(c), str) and activo[c].strip()]
    partes += [v for k, v in activo.items() if k not in CAMPOS_TEXTO and isinstance(v, str) and v.strip()
               and k not in ("area", "canal_recomendado")]
    partes += [" ".join(str(x) for x in v) for v in activo.values() if isinstance(v, list) and v]
    return "\n\n".join(partes)


def _catalogo(resultados):
    st.markdown('<div class="pl-titulo">Elige el resultado que necesitas</div>'
                '<div class="pl-subtitulo">Cada opción ejecuta una tarea predefinida con datos disponibles y '
                "presenta un resultado reutilizable. Las plantillas no vuelven a llamar a la IA.</div>",
                unsafe_allow_html=True)
    filtros, tarjetas = st.columns([1, 3], gap="medium")
    with filtros:
        with st.container(border=True):
            st.markdown("**Filtrar resultados**")
            busqueda = st.text_input("Buscar plantillas", placeholder="Buscar plantillas...",
                                     key="plantillas_busqueda", label_visibility="collapsed")
            categoria = st.radio("CATEGORÍA", CATEGORIAS, key="plantillas_categoria")
            st.divider()
            st.caption("FUENTE DE DATOS")
            st.markdown('<span class="pl-pill verde">JSON IMPORTADO</span>', unsafe_allow_html=True)
            st.caption("Redes conectadas: no requeridas")
    visibles = filtrar(busqueda, categoria)
    with tarjetas:
        cabecera, orden, _ = st.columns([1, 1.4, 1.6], vertical_alignment="center")
        cabecera.markdown(f'<span class="pl-pill">{len(visibles)} PLANTILLAS</span>', unsafe_allow_html=True)
        criterio = orden.selectbox("Ordenar", ("Recomendadas", "Más borradores"), key="plantillas_orden",
                                   label_visibility="collapsed")
        if criterio == "Más borradores" and resultados is not None:
            visibles = sorted(visibles, key=lambda p: -contar(p, resultados))
        # Las plantillas que aún no tienen generador van al final.
        visibles = sorted(visibles, key=lambda p: p["fuente"] == "proxima")
        if not visibles:
            st.info("Ninguna plantilla coincide con la búsqueda.")
        columnas = st.columns(2)
        for indice, plantilla in enumerate(visibles):
            with columnas[indice % 2]:
                _tarjeta(plantilla, resultados)
    if resultados is None:
        st.info("Procesa un lote en **Datos** para ver los resultados de cada plantilla.")
        st.button("Ir a Datos →", key="plantillas_ir_datos", on_click=navegar_a, args=("Datos",))


def _tarjeta(plantilla, resultados):
    proxima = plantilla["fuente"] == "proxima"
    if proxima:
        conteo = '<div class="pl-count soon">En definición con el equipo de DS</div>'
    elif resultados is None:
        conteo = '<div class="pl-count">Sin lote procesado</div>'
    else:
        n = contar(plantilla, resultados)
        if plantilla["fuente"] == "activo":
            unidad = "borrador" if n == 1 else "borradores"
        else:
            unidad = "mensaje analizado" if n == 1 else "mensajes analizados"
        conteo = f'<div class="pl-count">{n} {unidad}</div>'
    e = {k: html.escape(str(plantilla.get(k, ""))) for k in ("icono", "nombre", "etiqueta", "descripcion", "detalle")}
    tono = {"ANALÍTICA": " analitica", "CONOCIMIENTO": " conocimiento"}.get(plantilla.get("etiqueta"), "")
    with st.container(border=True, key=f"pl_card_{plantilla['id']}"):
        st.markdown(
            f'<div class="{"pl-off" if proxima or resultados is None else ""}">'
            f'<div class="pl-top"><div class="pl-icon{tono}">{e["icono"]}</div><div class="pl-name">{e["nombre"]}</div>'
            f'<span class="pl-tag">{e["etiqueta"]}</span></div>'
            f'<div class="pl-desc">{e["descripcion"]}</div><div class="pl-detail">{e["detalle"]}</div></div>',
            unsafe_allow_html=True,
        )
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
            st.markdown(conteo, unsafe_allow_html=True)
            if proxima:
                st.button("Próximamente", key=f"pl_abrir_{plantilla['id']}", disabled=True, type="tertiary")
            else:
                st.button("Ver resultado →", key=f"pl_abrir_{plantilla['id']}", type="tertiary",
                          on_click=navegar_a, args=("Resultado", plantilla["nombre"]))


ETIQUETAS_CAMPO = {
    "titulo": "Título", "contenido": "Texto del post", "hashtags": "Hashtags", "seccion": "Sección",
    "titular": "Titular", "resumen": "Resumen", "tema": "Tema", "respuesta": "Respuesta",
    "hallazgo": "Hallazgo", "sugerencia_detectada": "Sugerencia", "area": "Área",
    "canal_recomendado": "Canal recomendado",
}


def _etiqueta(campo):
    return ETIQUETAS_CAMPO.get(campo, campo.replace("_", " ").capitalize())


def _editor_activo(id_msg, tipo, activo, curaduria):
    """Editores y aprobación de un activo; devuelve el contenido tal como está editado."""
    clave = (id_msg, tipo)
    key_activo = f"{curaduria['lote']}_{id_msg}_{tipo}"
    if key_activo not in st.session_state:
        st.session_state[key_activo] = activo.copy()

    activo_editado = {}
    for k, v in st.session_state[key_activo].items():
        if isinstance(v, str):
            activo_editado[k] = st.text_area(_etiqueta(k), value=v, key=f"edit_{key_activo}_{k}", height=100)
        elif isinstance(v, list):
            nuevo_valor = st.text_area(
                f"{_etiqueta(k)} (uno por línea)",
                value="\n".join(str(x) for x in v),
                key=f"edit_{key_activo}_{k}",
                height=80,
            )
            activo_editado[k] = [line for line in nuevo_valor.split("\n") if line.strip()]
        else:
            activo_editado[k] = v

    # Una aprobación corresponde a una versión exacta del texto.
    if clave in curaduria["aprobados"] and curaduria["aprobados"][clave] != activo_editado:
        curaduria["aprobados"].pop(clave)
        curaduria["guardados"].pop(clave, None)
        curaduria["informe"] = None
        st.session_state[f"aprobado_{key_activo}"] = False

    if st.button("✅ Aprobar", key=f"btn_{key_activo}", type="primary"):
        try:
            validar_activo_curado(tipo, activo_editado)
        except ValueError as error_validacion:
            st.error(f"❌ {error_validacion}")
        except TypeError:
            st.error("❌ Revisa los campos del activo antes de aprobar: El formato no es válido.")
        else:
            st.session_state[key_activo] = deepcopy(activo_editado)
            curaduria["aprobados"][clave] = deepcopy(activo_editado)
            st.session_state[f"aprobado_{key_activo}"] = True
            st.success(f"✅ {tipo} aprobado correctamente.")

    if st.session_state.get(f"aprobado_{key_activo}"):
        st.info("🟢 Este activo ya fue aprobado para guardar en OCI.")
    return activo_editado


def _vista_previa(plantilla, activo_editado):
    texto = texto_para_copiar(activo_editado)
    titular = next((activo_editado[c] for c in CAMPOS_TEXTO
                    if isinstance(activo_editado.get(c), str) and activo_editado[c].strip()), plantilla["nombre"])
    cuerpo = next((activo_editado[c] for c in ("contenido", "resumen", "respuesta", "sugerencia_detectada")
                   if isinstance(activo_editado.get(c), str) and activo_editado[c].strip()), "")
    etiquetas = " ".join(str(x) for v in activo_editado.values() if isinstance(v, list) for x in v)
    st.markdown("**Vista previa de publicación**")
    st.markdown(
        f'<div class="pl-preview"><div class="org">tu_organizacion<span>•••</span></div>'
        f'<div class="hero">{html.escape(titular)}<small>{html.escape(plantilla["nombre"])}</small></div>'
        f'<div class="body">{html.escape(cuerpo)}</div>'
        + (f'<div class="tags">{html.escape(etiquetas)}</div>' if etiquetas else "")
        + '<div class="note">LA APERTURA NO PUBLICA AUTOMÁTICAMENTE</div></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Copiar contenido"):
        st.code(texto, language=None, wrap_lines=True)
    if plantilla.get("red"):
        nombre, url = plantilla["red"]
        st.link_button(f"Abrir {nombre} ↗", url, use_container_width=True)


def _resultado_activo(plantilla, resultados, curaduria):
    lista = borradores(plantilla, resultados)
    if not lista:
        st.info("Este lote no generó borradores para esta plantilla.")
        return

    st.caption(
        f"{len(resultados)} mensajes en el lote · {len(lista)} borrador(es) · "
        "revisión humana antes de guardar"
    )
    for numero, (id_msg, data, activo) in enumerate(lista, start=1):
        titulo = (f"{numero} de {len(lista)} · {data.get('autor', 'Anónimo')} — "
                  f"{data.get('tema_principal', 'sin tema')} · {data.get('sentimiento', 'N/A')}")
        with st.expander(titulo, expanded=numero == 1):
            configuracion, editor, previa = st.columns([1, 2, 1.35])
            with configuracion:
                with st.container(border=True):
                    campos = "".join(
                        f'<div class="pl-campo"><span>{html.escape(etiqueta)}</span><div>{html.escape(str(valor))}</div></div>'
                        for etiqueta, valor in (("Lote", f"{len(resultados)} mensajes procesados"),
                                                ("Formato de salida", plantilla["nombre"]),
                                                ("Objetivo de comunicación", plantilla.get("objetivo", "Sin definir")),
                                                ("Tono", plantilla.get("tono", "Sin definir")))
                    )
                    st.markdown(f'<div class="pl-config-titulo">Configuración</div>{campos}', unsafe_allow_html=True)
                    st.caption(
                        "La plantilla define la tarea. "
                        "No muestra prompts al usuario."
                    )

            with editor:
                with st.container(border=True):
                    st.markdown('<span class="pl-pill verde">RESULTADO ESTRUCTURADO</span>', unsafe_allow_html=True)
                    st.caption(f"Fuente: {data.get('canal', 'N/A')} · {id_msg}")
                    st.markdown(f"*Texto original:* {data.get('texto', '')}")
                    activo_editado = _editor_activo(
                        id_msg,
                        plantilla["tipo"],
                        activo,
                        curaduria,
                    )

            with previa:
                with st.container(border=True):
                    _vista_previa(plantilla, activo_editado)


def _resultado_analisis(plantilla, resultados):
    conteos = distribucion(plantilla, resultados)
    excluidos = len(resultados) - sum(n for _, n in conteos)
    if excluidos:
        st.caption(f"Se excluyen {excluidos} mensaje(s) marcados como spam, igual que en el resumen de DS.")
    if not conteos:
        st.info("No hay mensajes analizados en este lote.")
        return
    total = sum(n for _, n in conteos)
    etiqueta = "Sentimiento" if plantilla["campo"] == "sentimiento" else "Tema"
    df = pd.DataFrame([{etiqueta: k.replace("_", " "), "Mensajes": n, "Porcentaje": round(100 * n / total)}
                       for k, n in conteos])
    principal, n_principal = conteos[0]
    st.markdown(f"**Hallazgo:** el {round(100 * n_principal / total)}% de los {total} mensajes es "
                f"**{principal.replace('_', ' ')}**.")
    grafico, tabla = st.columns([3, 2])
    with grafico:
        if plantilla["campo"] == "sentimiento":
            chart = alt.Chart(df).mark_arc(innerRadius=50).encode(
                theta="Mensajes:Q", color=alt.Color(f"{etiqueta}:N"), tooltip=[f"{etiqueta}:N", "Mensajes:Q"])
        else:
            chart = alt.Chart(df).mark_bar(color="#6557e8").encode(
                x="Mensajes:Q", y=alt.Y(f"{etiqueta}:N", sort="-x"), tooltip=[f"{etiqueta}:N", "Mensajes:Q"])
        st.altair_chart(chart.properties(height=260), use_container_width=True)
    with tabla:
        st.dataframe(df, hide_index=True, use_container_width=True)
    if plantilla["campo"] == "tema_principal":
        subtemas = pd.Series([d.get("subtema") for d in resultados.values() if d.get("subtema")])
        if not subtemas.empty:
            st.caption("Subtemas más mencionados: " + " · ".join(subtemas.value_counts().head(5).index))


def _guardado_oci(resultado, curaduria):
    st.markdown('<div class="section-title">📦 Activos aprobados listos para OCI</div>', unsafe_allow_html=True)
    aprobados = curaduria["aprobados"]

    if aprobados:
        st.success(f"✅ {len(aprobados)} activo(s) aprobado(s).")
        for identificador, tipo in aprobados:
            st.write(f"- {identificador}: {tipo}")
    else:
        st.info("Aún no has aprobado ningún activo. Edita y aprueba los borradores de arriba para preparar el guardado en OCI.")

    bucket = os.getenv("OCI_BUCKET_NAME", "bkt-communitylab-marketing")
    periodo = st.text_input(
        "Período de almacenamiento",
        value=datetime.now(timezone.utc).strftime("%Y-%m"),
        key=f"periodo_oci_{curaduria['lote']}",
        help="Usa letras, números, guiones o guiones bajos.",
    )
    # El recibo corresponde también al destino, no solo al contenido.
    destino = (bucket, periodo)
    pendientes = {
        clave: contenido for clave, contenido in aprobados.items()
        if curaduria["guardados"].get(clave) != (destino, contenido)
    }
    st.caption(f"Destino: {bucket} · período {periodo}")
    if st.button(
        "Guardar aprobados en OCI",
        key="guardar_aprobados_oci",
        disabled=not pendientes,
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Guardando los activos aprobados..."):
            try:
                informe = asyncio.run(guardar_curaduria(resultado, pendientes, periodo=periodo, bucket=bucket))
            except Exception:
                curaduria["informe"] = None
                st.error(
                    "No se pudo confirmar el guardado. Revisa el período, "
                    "la configuración y los permisos de OCI. Puedes reintentar."
                )
            else:
                curaduria["informe"] = informe
                for guardado in informe["guardados"]:
                    clave = (guardado["id_interaccion"], guardado["tipo"])
                    curaduria["guardados"][clave] = (destino, deepcopy(pendientes[clave]))

    informe = curaduria["informe"]
    if informe:
        if informe["guardados"]:
            st.success(f"OCI confirmó {len(informe['guardados'])} activo(s) guardado(s).")
        for fallo in informe["fallidos"]:
            st.error(f"Sin confirmación de guardado: {fallo['id_interaccion']} ({fallo['tipo']}). Puedes reintentar.")


def render_plantillas(resultado=None):
    """Pestaña Plantillas: el catálogo. Sin resultado se ve atenuado."""
    st.markdown(ESTILOS, unsafe_allow_html=True)
    _catalogo(None if resultado is None else resultado.get("resultados_por_id", {}))


def render_resultado(resultado=None, curaduria=None):
    """Pestaña Resultado: una sub-pestaña por plantilla, curaduría y guardado en OCI."""
    st.markdown(ESTILOS, unsafe_allow_html=True)
    if resultado is None:
        st.markdown("## Resultado")
        st.info("Todavía no hay resultados. Procesa un lote en **Datos** y elige una plantilla.")
        st.button("Ir a Datos →", key="resultado_ir_datos", on_click=navegar_a, args=("Datos",))
        return
    resultados = resultado.get("resultados_por_id", {})

    aprobados = len(curaduria["aprobados"]) if curaduria else 0
    st.markdown('<div class="pl-crumbs">Plantillas  /  Resultado</div>'
                '<div class="pl-heading"><h2>Resultado generado a partir de conversaciones</h2>'
                f'<span><span class="pl-pill verde">{aprobados} APROBADO(S)</span> '
                '<span class="pl-pill ambar">REVISIÓN HUMANA</span></span></div>', unsafe_allow_html=True)

    # Todas las sub-pestañas se pintan en cada ejecución: los editores existen aunque
    # la plantilla no esté a la vista (la curaduría y sus pruebas dependen de ello).
    # Las tarjetas del catálogo abren la suya escribiendo su nombre en CLAVE_PLANTILLA.
    extras = tipos_sin_plantilla(resultados)
    nombres = [p["nombre"] for p in PLANTILLAS] + (["Otros activos"] if extras else [])
    if st.session_state.get(CLAVE_PLANTILLA) not in nombres:
        st.session_state.pop(CLAVE_PLANTILLA, None)
    pestanas = st.tabs(nombres, key=CLAVE_PLANTILLA, on_change="rerun")
    for pestana, plantilla in zip(pestanas, PLANTILLAS):
        with pestana:
            st.markdown(f'<div class="pl-crumbs">Plantillas  /  {html.escape(plantilla["nombre"])}  /  Resultado</div>',
                        unsafe_allow_html=True)
            if plantilla["fuente"] == "activo":
                _resultado_activo(plantilla, resultados, curaduria)
            elif plantilla["fuente"] == "analisis":
                _resultado_analisis(plantilla, resultados)
            else:
                st.info("Próximamente. El equipo está definiendo el generador de esta plantilla; "
                        "mientras tanto no se generan borradores.")
    if extras:
        with pestanas[-1]:
            for tipo in extras:
                generica = {"tipo": tipo, "fuente": "activo", "nombre": tipo.replace("_", " ").title(),
                            "objetivo": "Sin definir", "tono": "Sin definir"}
                st.markdown(f"#### {generica['nombre']}")
                _resultado_activo(generica, resultados, curaduria)

    with st.container(border=True):
        _guardado_oci(resultado, curaduria)
