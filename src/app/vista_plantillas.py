"""Página de Plantillas: catálogo, resultado por plantilla y curaduría para OCI.

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
    .section-title { color: #2b2216; font-family: "Cormorant Garamond", Georgia, serif; font-size: 1.7rem; font-weight: 700; margin: 1.1rem 0 .6rem; }
    .pl-card { background: #fffaf0; border: 1px solid #e3d5b3; border-radius: 14px; padding: 18px 20px; margin-bottom: 14px; }
    .pl-card.off { opacity: .55; }
    .pl-top { display: flex; align-items: center; gap: 12px; }
    .pl-icon { width: 40px; height: 40px; border-radius: 10px; background: #f1e2bd; color: #b07d22;
               display: flex; align-items: center; justify-content: center; font-weight: 700; }
    .pl-name { font-weight: 700; color: #2b2216; font-size: 1.02rem; flex: 1; }
    .pl-tag { font-size: .68rem; letter-spacing: 1px; color: #6e604a; border: 1px solid #e3d5b3; border-radius: 6px; padding: 2px 8px; }
    .pl-desc { color: #2b2216; margin: 12px 0 2px; font-size: .92rem; }
    .pl-detail { color: #6e604a; font-size: .82rem; }
    .pl-count { color: #8c6214; font-weight: 700; font-size: .85rem; margin-top: 10px; }
    .pl-count.soon { color: #8a4b2a; }
    .pl-preview { background: #fffaf0; border: 1px solid #e3d5b3; border-radius: 14px; padding: 16px; }
    .pl-preview .org { font-weight: 700; color: #2b2216; margin-bottom: 10px; }
    .pl-preview .body { white-space: pre-wrap; color: #2b2216; font-size: .9rem; line-height: 1.5; }
    .pl-preview .note { color: #6e604a; font-size: .7rem; letter-spacing: 1px; margin-top: 12px; }
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
    st.markdown('<div class="section-title">🧩 Elige el resultado que necesitas</div>', unsafe_allow_html=True)
    st.caption("Cada opción presenta un resultado reutilizable a partir del lote procesado. "
               "Las plantillas no vuelven a llamar a la IA.")
    filtros, tarjetas = st.columns([1, 3])
    with filtros:
        busqueda = st.text_input("Filtrar resultados", placeholder="Buscar plantillas...", key="plantillas_busqueda")
        categoria = st.radio("Categoría", CATEGORIAS, key="plantillas_categoria")
        st.caption("FUENTE DE DATOS · JSON importado  \nRedes conectadas: no requeridas")
    visibles = filtrar(busqueda, categoria)
    with tarjetas:
        st.caption(f"{len(visibles)} PLANTILLAS")
        if not visibles:
            st.info("Ninguna plantilla coincide con la búsqueda.")
        columnas = st.columns(2)
        for indice, plantilla in enumerate(visibles):
            with columnas[indice % 2]:
                st.markdown(_tarjeta(plantilla, resultados), unsafe_allow_html=True)
    if resultados is None:
        st.info("Todavía no hay un lote procesado para mostrar los resultados de cada plantilla.")


def _tarjeta(plantilla, resultados):
    proxima = plantilla["fuente"] == "proxima"
    if proxima:
        conteo = '<div class="pl-count soon">Próximamente · el equipo está definiendo su generador</div>'
    elif resultados is None:
        conteo = '<div class="pl-count">Sin lote procesado</div>'
    else:
        n = contar(plantilla, resultados)
        unidad = "borrador" if plantilla["fuente"] == "activo" else "mensaje analizado"
        conteo = f'<div class="pl-count">{n} {unidad}{"" if n == 1 else ("es" if unidad == "borrador" else "s")} → abre su pestaña abajo</div>'
    e = {k: html.escape(str(plantilla.get(k, ""))) for k in ("icono", "nombre", "etiqueta", "descripcion", "detalle")}
    return (f'<div class="pl-card{" off" if proxima or resultados is None else ""}">'
            f'<div class="pl-top"><div class="pl-icon">{e["icono"]}</div><div class="pl-name">{e["nombre"]}</div>'
            f'<span class="pl-tag">{e["etiqueta"]}</span></div>'
            f'<div class="pl-desc">{e["descripcion"]}</div><div class="pl-detail">{e["detalle"]}</div>{conteo}</div>')


def _editor_activo(id_msg, tipo, activo, curaduria):
    """Editores y aprobación de un activo; devuelve el contenido tal como está editado."""
    clave = (id_msg, tipo)
    key_activo = f"{curaduria['lote']}_{id_msg}_{tipo}"
    if key_activo not in st.session_state:
        st.session_state[key_activo] = activo.copy()

    activo_editado = {}
    for k, v in st.session_state[key_activo].items():
        if isinstance(v, str):
            activo_editado[k] = st.text_area(f"✏️ {k}", value=v, key=f"edit_{key_activo}_{k}", height=100)
        elif isinstance(v, list):
            nuevo_valor = st.text_area(
                f"✏️ {k} (uno por línea)",
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
    st.markdown("**Vista previa**")
    st.markdown(
        f'<div class="pl-preview"><div class="org">tu_organizacion</div>'
        f'<div class="body">{html.escape(texto)}</div>'
        f'<div class="note">LA APERTURA NO PUBLICA AUTOMÁTICAMENTE</div></div>',
        unsafe_allow_html=True,
    )
    st.caption("Copiar contenido")
    st.code(texto, language=None, wrap_lines=True)
    if plantilla.get("red"):
        nombre, url = plantilla["red"]
        st.link_button(f"Abrir {nombre} ↗", url)


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
                    st.markdown("#### Configuración")
                    st.write(f"**Lote:** {len(resultados)} mensajes")
                    st.write(f"**Formato:** {plantilla['nombre']}")
                    st.write(f"**Objetivo:** {plantilla.get('objetivo', 'Sin definir')}")
                    st.write(f"**Tono:** {plantilla.get('tono', 'Sin definir')}")
                    st.caption(
                        "La plantilla define la tarea. "
                        "No muestra prompts al usuario."
                    )

            with editor:
                with st.container(border=True):
                    st.markdown("#### Resultado estructurado")
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
            chart = alt.Chart(df).mark_bar(color="#b07d22").encode(
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
        st.info("Aún no has aprobado ningún activo. Edita y aprueba en las plantillas para preparar el guardado en OCI.")

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


def render(resultado=None, curaduria=None):
    """Pinta la página. Sin resultado, solo el catálogo atenuado."""
    st.markdown(ESTILOS, unsafe_allow_html=True)
    resultados = None if resultado is None else resultado.get("resultados_por_id", {})
    _catalogo(resultados)
    if resultados is None:
        return

    # Todas las pestañas se pintan en cada ejecución: los editores existen aunque
    # la pestaña no esté a la vista (la curaduría y sus pruebas dependen de ello).
    extras = tipos_sin_plantilla(resultados)
    pestanas = st.tabs([p["nombre"] for p in PLANTILLAS] + (["Otros activos"] if extras else []))
    for pestana, plantilla in zip(pestanas, PLANTILLAS):
        with pestana:
            st.caption(f"Plantillas  /  {plantilla['nombre']}  /  Resultado")
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

    _guardado_oci(resultado, curaduria)
