import json
import logging
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st

from src.agentes.conversacion import ESTILOS_REDACCION, AgenteConversacional
from src.agentes.grafo import procesar_paquete_entrega
from src.app import estilo_agente, fuente_agente, publicacion_redes, vista_ayuda, vista_inicio, vista_plantillas
from src.app import tema as identidad
from src.app.curaduria_oci import contexto_curaduria
from src.app.errores_agente import explicar_error
from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.metadatos import valor_publico

def render(*, modo_interno: bool = False) -> None:
    st.set_page_config(
        page_title="CommunityLab",
        page_icon=identidad.ICONO_PAGINA,
        layout="wide",
    )

    st.markdown(identidad.ESTILO_GLOBAL + identidad.marca(), unsafe_allow_html=True)

    # Datos es el flujo interno del equipo (importar → procesar → publicar en la
    # base); la versión pública solo consume lo publicado.
    MODO_INTERNO = modo_interno
    PAGINAS = (
        ("Inicio", "Datos") if MODO_INTERNO else ("Inicio",)
    ) + ("Agente", "Análisis", "Plantillas", "Ayuda")
    CLAVE_NAVEGACION = "navegacion_principal"
    CLAVE_ARCHIVOS = "archivos_usuario"


    def _navegar_a(pagina):
        if pagina not in PAGINAS:
            st.error("Esta sección no está disponible en esta aplicación.")
            return
        st.session_state["navegacion_pendiente"] = pagina


    def _interacciones_para_vista(datos):
        """Extrae filas de vista previa sin modificar ni validar el lote original."""
        if not isinstance(datos, dict):
            return []

        lotes = datos.get("lotes")
        if lotes is None:
            lotes = [datos]
        if not isinstance(lotes, list):
            return []

        filas = []
        for lote in lotes:
            if not isinstance(lote, dict):
                continue
            interacciones = lote.get("interacciones", [])
            if not isinstance(interacciones, list):
                continue
            for mensaje in interacciones:
                if not isinstance(mensaje, dict):
                    continue
                filas.append(
                    {
                        "id": mensaje.get("id", "—"),
                        "autor": mensaje.get("autor", "Anónimo"),
                        "canal": mensaje.get("canal", lote.get("origen_comunidad", "—")),
                        "tipo": mensaje.get("tipo", "—"),
                        "texto": mensaje.get("texto", ""),
                    }
                )
        return filas


    def _render_datos():
        if not MODO_INTERNO:
            st.error("El flujo de Datos solo está disponible en la aplicación interna.")
            return
        st.header("Prepara los datos antes de generar resultados")
        st.write(
            "Importa un lote JSON, revisa una muestra de las conversaciones y "
            "ejecuta el pipeline de análisis."
        )
        from src.app.carga_oracle import render_carga, solicitar
        from src.datos.conjunto_consultable import construir_conjunto_consultable

        preparado = st.file_uploader(
            "Conjunto Consultable ya procesado (sin repetir IA)", type=["json"],
            key="conjunto_para_oracle",
        )
        if preparado is not None:
            try:
                documento = json.loads(preparado.getvalue())
                if not isinstance(documento, dict) or not isinstance(documento.get("registros"), list):
                    raise ValueError("Se requiere un Conjunto Consultable con registros")
                render_carga(documento)
            except (ValueError, TypeError) as error:
                st.error(f"Conjunto invalido: {error}")
            return

        carga, guia = st.columns([2, 1])
        with carga:
            with st.container(border=True):
                st.subheader("Importar interacciones")
                st.caption("Formato compatible: JSON con lotes e interacciones.")
                archivo_subido = st.file_uploader(
                    "Selecciona el archivo JSON",
                    type=["json"],
                    key="archivo_interacciones",
                )

                if archivo_subido is not None:
                    try:
                        datos = json.load(archivo_subido)
                        st.success("Archivo JSON cargado correctamente.")
                        filas = _interacciones_para_vista(datos)
                        if filas:
                            st.caption(
                                f"Vista previa · {len(filas)} interacciones encontradas"
                            )
                            st.dataframe(
                                pd.DataFrame(filas).head(20),
                                hide_index=True,
                                width="stretch",
                            )
                            if len(filas) > 20:
                                st.caption("Se muestran las primeras 20 interacciones.")
                        else:
                            st.info(
                                "El JSON se pudo leer, pero no contiene una lista "
                                "de interacciones para mostrar."
                            )

                        if st.button("Comprobar Oracle antes del procesamiento"):
                            st.session_state.pop("destino_ingesta", None)
                            try:
                                st.session_state["destino_ingesta"] = solicitar("/destino")
                                st.success("Destino Oracle disponible.")
                            except (ValueError, RuntimeError) as error:
                                st.error(str(error))
                        if st.button(
                            "Procesar con IA",
                            type="primary",
                            icon=":material/rocket_launch:",
                            key="procesar_lote",
                            disabled=not st.session_state.get("destino_ingesta"),
                        ):
                            with st.spinner(
                                "Procesando mensajes con inteligencia artificial..."
                            ):
                                try:
                                    st.session_state.pop("conjunto_para_carga", None)
                                    paquete = preparar_paquete_ia(
                                        datos,
                                        fecha_referencia=datetime.now(timezone.utc).isoformat(),
                                        tamano_ciclo=20,
                                    )
                                    resultado = procesar_paquete_entrega(paquete)
                                    st.session_state["resultado"] = resultado
                                    if resultado.get("ids_pendientes"):
                                        raise ValueError("Quedan mensajes pendientes; no se habilita una carga parcial")
                                    resultados = list(resultado["resultados_por_id"].values())
                                    if any(r.get("errores") or r.get("fallos") for r in resultados):
                                        raise ValueError("Hay analisis fallidos; no se habilita la carga")
                                    st.session_state["conjunto_para_carga"] = construir_conjunto_consultable(
                                        {"interacciones": resultados}, datos,
                                    )
                                    st.session_state.pop("agente_conversacional", None)
                                    st.session_state.pop("historial_agente", None)
                                    st.success("Procesamiento completado.")
                                except Exception as error:
                                    st.error(
                                        f"Error durante el procesamiento: {error}"
                                    )

                    except json.JSONDecodeError:
                        st.error(
                            "El archivo no es un JSON válido. "
                            "Verifica el formato y vuelve a intentarlo."
                        )
                    except Exception as error:
                        st.error(f"Error al cargar el archivo: {error}")

        if st.session_state.get("conjunto_para_carga") is not None:
            render_carga(st.session_state["conjunto_para_carga"])

        with guia:
            with st.container(border=True):
                st.subheader("Antes de procesar")
                st.markdown(
                    "1. Selecciona un archivo JSON.\n"
                    "2. Revisa la muestra de interacciones.\n"
                    "3. Inicia el análisis con el pipeline de IA."
                )
                st.caption(
                    "El procesamiento analiza el lote y genera los activos "
                    "disponibles. No publica contenido en redes."
                )


    def _render_analisis(resultado):
        st.header("Estado de las conversaciones de la comunidad")
        if resultado is None:
            st.info("Todavía no hay un lote analizado para mostrar métricas.")
            return

        resultados = resultado.get("resultados_por_id", {})
        total = len(resultados)
        if not resultados:
            st.info("El lote terminó de procesarse, pero no contiene resultados.")
            return

        con_activos = sum(
            1 for data in resultados.values() if data.get("activos_generados")
        )
        faqs = sum(1 for data in resultados.values() if data.get("elegible_faq"))

        metrica_1, metrica_2, metrica_3, metrica_4 = st.columns(4)
        metrica_1.metric("Mensajes procesados", total)
        metrica_2.metric("Con contenido", con_activos)
        metrica_3.metric("Sin contenido", total - con_activos)
        metrica_4.metric("Elegibles para FAQ", faqs)

        st.subheader("Distribución de la comunidad")
        filas_grafica = [
            {
                "autor": data.get("autor", "Anónimo"),
                "canal": data.get("canal", "N/A"),
                "sentimiento": data.get("sentimiento", "N/A"),
                "tema": data.get("tema_principal", "N/A"),
                "elegible": "Sí" if data.get("elegible_contenido") else "No",
                "spam": data.get("es_spam_detectado") is True,
            }
            for data in resultados.values()
        ]
        df = pd.DataFrame(filas_grafica)
        df_sentimiento = df[~df["spam"]]
        total_spam = total - len(df_sentimiento)

        with st.container(border=True):
            tema_columna, sentimiento_columna = st.columns(2)
            with tema_columna:
                st.markdown("**Distribución por tema principal**")
                chart_temas = (
                    alt.Chart(df)
                    .mark_bar(color=identidad.MIEL)
                    .encode(
                        x=alt.X("tema:N", sort="-y", title="Tema"),
                        y=alt.Y("count():Q", title="Cantidad"),
                        tooltip=["tema:N", "count():Q"],
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart_temas, width="stretch")

            with sentimiento_columna:
                st.markdown("**Distribución por sentimiento**")
                if df_sentimiento.empty:
                    st.info("No hay mensajes legítimos para calcular el sentimiento.")
                else:
                    chart_sentimiento = (
                        alt.Chart(df_sentimiento)
                        .mark_arc(innerRadius=55)
                        .encode(
                            theta=alt.Theta("count():Q"),
                            color=alt.Color(
                                "sentimiento:N",
                                legend=alt.Legend(title="Sentimiento"),
                            ),
                            tooltip=["sentimiento:N", "count():Q"],
                        )
                        .properties(height=280)
                    )
                    st.altair_chart(chart_sentimiento, width="stretch")
                if total_spam:
                    st.caption(
                        f"Se excluyen {total_spam} mensaje(s) marcados como spam."
                    )

        with st.container(border=True):
            canal_columna, elegible_columna = st.columns(2)
            with canal_columna:
                st.markdown("**Distribución por canal**")
                chart_canal = (
                    alt.Chart(df)
                    .mark_bar(color=identidad.MIEL)
                    .encode(
                        x=alt.X("count():Q", title="Cantidad"),
                        y=alt.Y("canal:N", sort="-x", title="Canal"),
                        tooltip=["canal:N", "count():Q"],
                    )
                    .properties(height=260)
                )
                st.altair_chart(chart_canal, width="stretch")

            with elegible_columna:
                st.markdown("**Elegibles para contenido**")
                chart_elegible = (
                    alt.Chart(df)
                    .mark_arc(innerRadius=55)
                    .encode(
                        theta=alt.Theta("count():Q"),
                        color=alt.Color(
                            "elegible:N",
                            legend=alt.Legend(title="Elegible"),
                        ),
                        tooltip=["elegible:N", "count():Q"],
                    )
                    .properties(height=260)
                )
                st.altair_chart(chart_elegible, width="stretch")

        with st.expander("Datos de las gráficas en texto"):
            for titulo, datos, campo in (
                ("Temas", df, "tema"),
                ("Sentimientos (sin spam)", df_sentimiento, "sentimiento"),
                ("Canales", df, "canal"),
                ("Elegibilidad para contenido", df, "elegible"),
            ):
                st.markdown(f"**{titulo} · {len(datos)} mensajes**")
                if datos.empty:
                    st.write("Sin datos.")
                else:
                    for valor, cantidad in datos[campo].value_counts().items():
                        st.write(f"{valor}: {cantidad} mensajes.")

        st.subheader("Detalle por mensaje")
        st.caption(
            "Vista de solo lectura. Edita y aprueba los activos en Plantillas."
            if MODO_INTERNO else
            "Vista de solo lectura. El contenido diario de Marketing está en Plantillas."
        )
        for data in resultados.values():
            autor = data.get("autor", "Anónimo")
            tema = data.get("tema_principal", "sin tema")
            sentimiento = data.get("sentimiento", "N/A")
            activos = list(data.get("activos_generados") or {})
            icono = (
                "🚫"
                if data.get("es_spam_detectado") is True
                else ("📝" if activos else "💬")
            )

            with st.expander(f"{icono} {autor} — {tema} · {sentimiento}"):
                detalle_1, detalle_2 = st.columns(2)
                with detalle_1:
                    st.write(f"**Canal:** {data.get('canal', 'N/A')}")
                    st.write(f"**Tipo detectado:** {data.get('tipo_detectado', 'N/A')}")
                    st.write(f"**Score relevancia:** {data.get('score_relevancia', 'N/A')}")
                    st.write(
                        f"**Rutas:** {', '.join(data.get('rutas') or []) or 'ninguna'}"
                    )
                with detalle_2:
                    st.write(f"**Sentimiento:** {sentimiento}")
                    st.write(f"**Subtema:** {data.get('subtema', 'N/A')}")
                    st.write(
                        "**Elegible para contenido:** "
                        f"{'Sí' if data.get('elegible_contenido') else 'No'}"
                    )
                    if "elegible_faq" in data:
                        st.write(
                            "**Elegible para FAQ:** "
                            f"{'Sí' if data['elegible_faq'] else 'No'}"
                        )
                if data.get("es_spam_detectado") is True:
                    st.write(
                        f"**Spam:** {data.get('motivo_spam') or 'sin motivo indicado'}"
                    )

                st.markdown(f"*Texto original:* {data.get('texto', '')}")
                if activos:
                    st.caption(
                        "Activos generados: "
                        + ", ".join(activos)
                        + (
                            " · edítalos y apruébalos en Plantillas."
                            if MODO_INTERNO else " · resultados del procesamiento interno."
                        )
                    )
                else:
                    st.caption("Este mensaje no generó activos.")
                if data.get("errores"):
                    st.caption(
                        f"El pipeline registró {len(data['errores'])} error(es) "
                        "en este mensaje."
                    )


    def _render_inicio(resultado):
        if not MODO_INTERNO:
            vista_inicio.render(ir_a=_navegar_a)
            return
        contenido, resumen = st.columns([1.35, 1], vertical_alignment="center")
        with contenido:
            with st.container(key="inicio_insignia"):
                st.badge("COMMUNITYLAB · INTELIGENCIA PARA COMUNIDADES", color="primary")
            st.title("Tu comunidad habla. Convierte esa voz en valor.")
            st.write(
                "Transforma conversaciones en conocimiento, analítica y activos "
                "de marketing con revisión humana."
            )
            if resultado is not None:
                total = len(resultado.get("resultados_por_id", {}))
                st.success(f"El último lote tiene {total} mensajes procesados.")
            elif MODO_INTERNO:
                st.info("Comienza en Datos importando un archivo JSON.")
            else:
                st.info("Pregúntale al agente qué está diciendo tu comunidad.")

        with resumen:
            with st.container(border=True):
                st.markdown("#### De conversación a resultado")
                st.markdown(
                    (
                        ":material/upload_file: **Importar** · Lote JSON de la comunidad\n\n"
                        if MODO_INTERNO
                        else ":material/forum: **Preguntar** · Al agente sobre la comunidad\n\n"
                    )
                    + ":material/analytics: **Analizar** · Temas y sentimiento\n\n"
                    ":material/edit_note: **Revisar** · Editar y aprobar activos"
                )

        st.subheader("Explora CommunityLab")
        primera = (
            ("Datos", ":material/table_view:", "Importa y revisa interacciones antes de procesarlas.")
            if MODO_INTERNO
            else (
                "Agente",
                ":material/cyclone:",
                "Consulta a la comunidad y suma tus propios datos.",
            )
        )
        tarjetas = st.columns(3)
        for columna, (pagina, icono, descripcion) in zip(
            tarjetas,
            (
                primera,
                (
                    "Análisis",
                    ":material/insights:",
                    "Explora métricas, temas y sentimiento de la comunidad.",
                ),
                (
                    "Plantillas",
                    ":material/article:",
                    (
                        "Prepara contenidos y apruébalos antes de guardarlos."
                        if MODO_INTERNO else
                        "Revisa el contenido preparado cada día y ábrelo para publicar."
                    ),
                ),
            ),
        ):
            with columna:
                with st.container(border=True, key=f"inicio_card_{pagina.lower()}"):
                    st.button(
                        f"**{pagina}**\n\n{descripcion}",
                        icon=icono,
                        key=f"inicio_nav_{pagina.lower()}",
                        use_container_width=True,
                        on_click=_navegar_a,
                        args=(pagina,),
                    )


    def _mostrar_fuentes(salida, resultados):
        citas = salida.get("citas", [])
        if not citas:
            st.caption("La respuesta no incluye fuentes citadas.")
            return
        for cita in citas:
            fuente = resultados.get(cita, {})
            st.markdown(
                f"**{cita}** · "
                f"{valor_publico(fuente.get('autor')) or 'Autor desconocido'} · "
                f"{valor_publico(fuente.get('canal')) or 'Canal desconocido'}"
            )
            st.write(fuente.get("texto", ""))


    def _mostrar_verificacion(salida):
        verificacion = salida.get("verificacion", {})
        st.caption(f"Estado: {verificacion.get('estado', 'no_disponible')}")
        st.write(
            verificacion.get(
                "resumen",
                "El agente no devolvió un resumen de verificación.",
            )
        )
        for afirmacion in verificacion.get("afirmaciones", []):
            estado_afirmacion = (
                "Respaldada" if afirmacion.get("respaldada") else "Requiere revisión"
            )
            st.markdown(f"- **{estado_afirmacion}:** {afirmacion['afirmacion']}")
            if afirmacion.get("citas"):
                st.caption("Fuentes: " + ", ".join(afirmacion["citas"]))


    _ETIQUETAS_ESTILO = {
        "preciso": "Preciso",
        "equilibrado": "Equilibrado",
        "creativo": "Creativo",
    }
    _AJUSTE_ESTILOS = "Estilos"
    _AJUSTE_MANUAL = "Manual"
    _DESCRIPCIONES_ESTILO = {
        "preciso": "Preciso: redacción sobria y directa, con poca variación.",
        "equilibrado": "Equilibrado: claridad con variedad moderada.",
        "creativo": "Creativo: titulares y lenguaje más variados, sin inventar hechos.",
    }
    _ETIQUETAS_MODELO = {"super": "Super · Recomendado", "lightning": "Lightning · Ligero"}
    _DESCRIPCIONES_MODELO = {
        "super": "120B · Para peticiones elaboradas y borradores con más matices.",
        "lightning": "30B · Alternativa ligera; puede requerir más ajustes.",
    }


    def _quitar_archivo(nombre):
        st.session_state.get(CLAVE_ARCHIVOS, {}).pop(nombre, None)


    @st.fragment
    def _controles_agente(adjuntos):
        """Controles junto a la entrada; se pueden cambiar en cualquier momento del chat."""
        estado = st.session_state
        estado.setdefault("agente_ajuste", _AJUSTE_ESTILOS)
        estado.setdefault("agente_estilo", "equilibrado")
        estado.setdefault("agente_temperatura", ESTILOS_REDACCION["equilibrado"][0])
        estado.setdefault("agente_top_p", ESTILOS_REDACCION["equilibrado"][1])
        estado.setdefault("agente_modelo", "super")
        estado.setdefault("modo_verificacion", False)
        for clave in ("agente_estilo", "agente_temperatura", "agente_top_p"):
            estado[clave] = estado[clave]
        if estado["agente_estilo"] not in _ETIQUETAS_ESTILO:
            estado["agente_estilo"] = "equilibrado"
        if estado["agente_ajuste"] not in {_AJUSTE_ESTILOS, _AJUSTE_MANUAL}:
            estado["agente_ajuste"] = _AJUSTE_ESTILOS
        manual = estado["agente_ajuste"] == _AJUSTE_MANUAL
        if manual:
            etiqueta = "Redacción · Manual"
        else:
            etiqueta = f"Redacción · {_ETIQUETAS_ESTILO[estado['agente_estilo'] or 'equilibrado']}"

        with getattr(st, "bottom", st).container(key="gotico_controles"):
            with st.container(horizontal=True, gap="small", key="agente_barra"):
                modelo_panel = st.popover(
                    f"Modelo · {estado['agente_modelo'].capitalize()}", key="panel_modelo",
                )
                info_modelo = st.container(width="content")
                redaccion_panel = st.popover(etiqueta, key="panel_redaccion")
                info_redaccion = st.container(width="content")
                verificacion_panel = st.popover(
                    "Verificado" if estado["modo_verificacion"] else "Estricto",
                    key="panel_verificacion",
                )
                info_modo = st.container(width="content")
                datos_panel = (
                    st.popover(
                        f"Tus datos · {len(adjuntos)}",
                        icon=":material/attach_file:", key="panel_datos",
                    ) if adjuntos else None
                )

            with modelo_panel, st.container(key="agente_panel_modelo"):
                st.selectbox(
                    "Modelo de respuesta", list(_ETIQUETAS_MODELO),
                    format_func=lambda clave: _ETIQUETAS_MODELO[clave],
                    key="agente_modelo", label_visibility="collapsed",
                )

            with redaccion_panel, st.container(key="agente_panel_redaccion"):
                st.radio(
                    "Ajuste de redacción",
                    [_AJUSTE_ESTILOS, _AJUSTE_MANUAL],
                    key="agente_ajuste", horizontal=True, label_visibility="collapsed",
                )
                if estado["agente_ajuste"] == _AJUSTE_MANUAL:
                    temperatura_col, top_p_col = st.columns(2)
                    with temperatura_col:
                        st.number_input(
                            "Temperatura", min_value=0.0, max_value=1.0,
                            step=0.05, key="agente_temperatura",
                            help="Variedad: baja = más predecible; alta = más variable.",
                        )
                    with top_p_col:
                        st.number_input(
                            "top_p", min_value=0.1, max_value=1.0,
                            step=0.05, key="agente_top_p",
                            help="Amplitud de opciones: bajo = vocabulario más acotado.",
                        )
                else:
                    st.selectbox(
                        "Estilo",
                        list(_ETIQUETAS_ESTILO),
                        format_func=lambda clave: _ETIQUETAS_ESTILO[clave],
                        key="agente_estilo", label_visibility="collapsed",
                    )

            with verificacion_panel, st.container(key="agente_panel_verificacion"):
                verificacion = st.toggle(
                    "Verificar borradores", key="modo_verificacion",
                )

            with info_modelo:
                st.html(estilo_agente.informacion_lateral("modelo", "Modelo", [
                    f"Seleccionado: {_ETIQUETAS_MODELO[estado['agente_modelo']]}.",
                    _DESCRIPCIONES_MODELO[estado["agente_modelo"]],
                    "Super: recomendado para peticiones elaboradas. Lightning: alternativa ligera.",
                    "Solo cambia las respuestas siguientes; conserva el historial.",
                    "Interpretación y verificación no cambian. Puede usarse respaldo si falla.",
                ]))
            with info_redaccion:
                st.html(estilo_agente.informacion_lateral("redaccion", "Redacción", [
                    f"Ajuste actual: {estado['agente_ajuste']}.",
                    (
                        f"Temperatura: {estado['agente_temperatura']:g} · "
                        f"top_p: {estado['agente_top_p']:g}."
                        if estado["agente_ajuste"] == _AJUSTE_MANUAL
                        else f"Estilo: {_ETIQUETAS_ESTILO[estado['agente_estilo']]}."
                    ),
                    *_DESCRIPCIONES_ESTILO.values(),
                    "Manual: temperatura controla la variedad; top_p, la amplitud de opciones.",
                    "Solo afecta las publicaciones, no los filtros ni los conteos.",
                ], derecha=True))
            with info_modo:
                st.html(estilo_agente.informacion_lateral("modo", "Modo de respuesta", [
                    "Seleccionado: Verificado." if verificacion else "Seleccionado: Estricto.",
                    "Estricto: redacta con las fuentes, sin revisión adicional.",
                    "Verificado: contrasta las afirmaciones con las fuentes; tarda más y consume más cuota.",
                    "Si detecta hechos sin respaldo, corrige una vez y revisa de nuevo. Si persisten, bloquea el borrador.",
                    "Ambos usan evidencia. La verificación no garantiza exactitud.",
                ], derecha=True))

            if datos_panel is not None:
                total = sum(len(mensajes) for mensajes in adjuntos.values())
                with datos_panel, st.container(key="agente_panel_datos"):
                    st.caption(f"{total} mensajes · Solo en esta sesión; no se guardan.")
                    with st.container(height=min(180, max(48, len(adjuntos) * 48)), border=False):
                        for indice, (nombre, mensajes) in enumerate(adjuntos.items()):
                            archivo_col, quitar_col = st.columns([5, 1], vertical_alignment="center")
                            with archivo_col:
                                st.text(f"{nombre} · {len(mensajes)}", help=nombre)
                            with quitar_col:
                                quitar = st.button(
                                    "", key=f"agente_quitar_{indice}",
                                    icon=":material/close:", help=f"Quitar {nombre}",
                                    type="tertiary", on_click=_quitar_archivo, args=(nombre,),
                                )
                                if quitar:
                                    st.rerun(scope="app")

    def _ajustes_agente():
        estado = st.session_state
        modo = "verificacion_automatica" if estado["modo_verificacion"] else "prompt_estricto"
        if estado["agente_ajuste"] == _AJUSTE_MANUAL:
            temperatura, top_p = estado["agente_temperatura"], estado["agente_top_p"]
        else:
            # Si se deselecciona el estilo, se conserva el equilibrado.
            temperatura, top_p = ESTILOS_REDACCION[estado["agente_estilo"] or "equilibrado"]
        return modo, temperatura, top_p, estado["agente_modelo"]


    def _adjuntar(archivos):
        adjuntos = st.session_state.setdefault(CLAVE_ARCHIVOS, {})
        for archivo in archivos:
            try:
                adjuntos[archivo.name] = fuente_agente.leer_archivo_usuario(
                    archivo.name, archivo.getvalue()
                )
            except ValueError as error:
                st.warning(str(error))
            else:
                st.toast(f"«{archivo.name}» se sumó a tus datos.", icon=":material/attach_file:")


    def _datos_agente(resultado, adjuntos):
        """Mensajes que consulta el agente, firma para detectar cambios y aviso."""
        aviso = ""
        if resultado is not None:
            # Lote procesado internamente (pestaña Datos): el equipo lo revisa
            # antes de publicarlo en la base.
            base = list(resultado.get("resultados_por_id", {}).values())
            firma_base = ("lote", id(resultado))
        else:
            try:
                with st.spinner("Consultando la base de la comunidad…"):
                    captura = fuente_agente.obtener_captura(st.session_state)
            except fuente_agente.FuenteNoDisponible as error:
                base, firma_base, aviso = [], None, str(error)
                if adjuntos:
                    aviso += " Por ahora respondo solo con tus archivos."
            else:
                base, firma_base = list(captura.mensajes), captura.capturada_en
                if captura.desactualizada:
                    minutos = int(
                        (datetime.now(timezone.utc) - captura.capturada_en).total_seconds()
                        // 60
                    )
                    aviso = (
                        f"Estás viendo la información capturada hace {minutos} min. "
                        f"{captura.aviso}"
                    )
        firma = (firma_base, tuple((nombre, len(m)) for nombre, m in adjuntos.items()))
        return fuente_agente.combinar(base, adjuntos), firma, aviso


    def _agente_para(mensajes, firma):
        """Crea el agente o le cambia los datos sin borrar la conversación."""
        estado = st.session_state
        agente = estado.get("agente_conversacional")
        if agente is not None and estado.get("firma_agente") == firma:
            return agente
        if agente is None:
            agente = AgenteConversacional(mensajes)
        else:
            agente.actualizar_datos(mensajes)
        estado["agente_conversacional"] = agente
        estado["firma_agente"] = firma
        return agente


    def _render_agente(resultado):
        st.markdown(estilo_agente.ESTILO, unsafe_allow_html=True)
        adjuntos = st.session_state.setdefault(CLAVE_ARCHIVOS, {})
        # Fuera de contenedores para que quede fija al pie, como en un chat de LLM.
        entrada = st.chat_input(
            "Pregunta sobre la comunidad o adjunta tus datos…",
            accept_file="multiple",
            file_type=list(fuente_agente.FORMATOS_ARCHIVO),
        )
        consulta = (entrada.text or "").strip() if entrada else ""
        if entrada and entrada.files:
            _adjuntar(entrada.files)
        _controles_agente(adjuntos)
        modo, temperatura, top_p, modelo = _ajustes_agente()

        with st.container(key="gotico_lienzo"):
            mensajes, firma, aviso = _datos_agente(resultado, adjuntos)
            try:
                agente = _agente_para(mensajes, firma)
            except ValueError as error:
                logging.getLogger(__name__).warning(
                    "Datos inválidos para el agente", exc_info=error
                )
                st.warning(explicar_error(error))
                return
            historial = st.session_state.setdefault("historial_agente", [])
            if not mensajes:
                if not historial and not consulta:
                    st.markdown(
                        estilo_agente.cabecera("Bienvenido. ¿Qué te gustaría descubrir hoy?"),
                        unsafe_allow_html=True,
                    )
                st.info(
                    f"{aviso} Puedes conversar con el agente o adjuntar tus archivos "
                    "(JSON, CSV o TXT) con el clip de la caja de texto.".strip()
                )
            elif aviso:
                st.info(aviso)

            if mensajes and not historial and not consulta:
                st.markdown(
                    estilo_agente.cabecera("¿Qué deseas saber de la comunidad?"),
                    unsafe_allow_html=True,
                )
            resultados = {mensaje["id"]: mensaje for mensaje in mensajes}

            for indice, mensaje in enumerate(historial):
                with st.chat_message(mensaje["role"]):
                    st.markdown(
                        estilo_agente.marca_voz(mensaje["role"]),
                        unsafe_allow_html=True,
                    )
                    if "error" in mensaje:
                        st.warning(mensaje["error"])
                        continue
                    st.markdown(mensaje["content"])
                    salida = mensaje.get("salida")
                    if salida:
                        _mostrar_detalle_agente(mensaje, salida, resultados, clave=f"turno_{indice}")

            if consulta:
                with st.chat_message("user"):
                    st.markdown(estilo_agente.marca_voz("user"), unsafe_allow_html=True)
                    st.markdown(consulta)
                with st.chat_message("assistant"):
                    st.markdown(estilo_agente.marca_voz("assistant"), unsafe_allow_html=True)
                    try:
                        with st.spinner("Preparando la respuesta…"):
                            salida = agente.consultar(
                                consulta,
                                modo_verificacion=modo,
                                temperatura=temperatura,
                                top_p=top_p,
                                modelo_respuesta=modelo,
                            )
                    except Exception as error:
                        logging.getLogger(__name__).warning(
                            "Fallo al consultar al agente", exc_info=error
                        )
                        respuesta = {"role": "assistant", "error": explicar_error(error)}
                        st.warning(respuesta["error"])
                    else:
                        respuesta = {
                            "role": "assistant",
                            "content": salida["respuesta"],
                            "salida": salida,
                            "modo_verificacion": modo,
                        }
                        st.markdown(respuesta["content"])
                        _mostrar_detalle_agente(
                            respuesta, salida, resultados, clave=f"turno_{len(historial) + 1}",
                        )
                # Se guarda el turno completo para no dejar preguntas sin respuesta
                # si la ejecución se interrumpe a mitad de la consulta.
                historial.extend([{"role": "user", "content": consulta}, respuesta])

    def _mostrar_detalle_agente(mensaje, salida, resultados, *, clave):
        if salida.get("borrador"):
            st.markdown(estilo_agente.borrador(salida["borrador"]), unsafe_allow_html=True)
            publicacion_redes.render(salida["borrador"], clave=clave)
        if mensaje.get("modo_verificacion") == "verificacion_automatica":
            with st.expander("Verificación y fuentes", expanded=True):
                _mostrar_verificacion(salida)
                st.markdown("**Fuentes citadas**")
                _mostrar_fuentes(salida, resultados)
        elif salida.get("citas"):
            with st.expander("Fuentes citadas"):
                _mostrar_fuentes(salida, resultados)

    # Evita que Streamlit elimine los ajustes al ocultar sus widgets en otra página.
    for clave in (
        "agente_modelo", "agente_ajuste", "agente_estilo",
        "agente_temperatura", "agente_top_p", "modo_verificacion",
    ):
        if clave in st.session_state:
            st.session_state[clave] = st.session_state[clave]

    destino = st.session_state.pop("navegacion_pendiente", None)
    if destino is not None:
        st.session_state[CLAVE_NAVEGACION] = destino
    if st.session_state.get(CLAVE_NAVEGACION) not in (None, *PAGINAS):
        st.warning("Esta sección no está disponible en esta aplicación.")
        st.session_state[CLAVE_NAVEGACION] = "Inicio"

    pagina = st.session_state.setdefault(CLAVE_NAVEGACION, "Inicio")
    revision = st.session_state.get("navegacion_revision", 0)
    clave_selector = f"selector_navegacion_{revision}"
    if st.session_state.get(clave_selector, pagina) != pagina:
        # Remonta el selector cuando la navegación viene de un botón, no del radio.
        revision += 1
        st.session_state["navegacion_revision"] = revision
        clave_selector = f"selector_navegacion_{revision}"

    def _sincronizar_navegacion():
        st.session_state[CLAVE_NAVEGACION] = st.session_state[clave_selector]

    with st.container(key=CLAVE_NAVEGACION):
        pagina_actual = st.radio(
            "Navegación principal",
            PAGINAS,
            horizontal=True,
            index=PAGINAS.index(pagina),
            key=clave_selector,
            on_change=_sincronizar_navegacion,
            label_visibility="collapsed",
        )

    if MODO_INTERNO and pagina_actual == "Datos":
        _render_datos()

    resultado = st.session_state.get("resultado") if MODO_INTERNO else None
    curaduria = (
        contexto_curaduria(st.session_state, resultado)
        if resultado is not None
        else None
    )

    if pagina_actual == "Inicio":
        _render_inicio(resultado)
    elif pagina_actual == "Agente":
        _render_agente(resultado)
    elif pagina_actual == "Análisis":
        _render_analisis(resultado)
    elif pagina_actual == "Plantillas":
        if not MODO_INTERNO:
            from src.app.vista_plantillas_diarias import render as render_plantillas_diarias
            render_plantillas_diarias()
        elif resultado is None:
            vista_plantillas.render()
        else:
            vista_plantillas.render(resultado, curaduria)
    elif pagina_actual == "Ayuda":
        vista_ayuda.render(ir_a=_navegar_a)
