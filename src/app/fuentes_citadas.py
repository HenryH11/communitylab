"""Explorador paginado de referencias, sin limitar la evidencia del agente."""

from copy import deepcopy

import streamlit as st

from src.datos.metadatos import valor_publico


FUENTES_POR_PAGINA = 10


def conservar_fuentes(
    salida: dict, resultados: dict, *, almacen: dict[str, list[dict]] | None = None,
) -> None:
    """Conserva las fuentes citadas del turno, independientes de futuras capturas."""
    citas = set(salida.get("citas", []))
    for elementos in (
        salida.get("hallazgos", []),
        salida.get("verificacion", {}).get("afirmaciones", []),
        salida.get("grupos_preguntas", []),
    ):
        for elemento in elementos:
            citas.update(elemento.get("citas", []))
    captura = {}
    for cita in citas:
        if cita not in resultados:
            continue
        fuente = resultados[cita]
        if almacen is None:
            captura[cita] = deepcopy(fuente)
            continue
        versiones = almacen.setdefault(cita, [])
        conservada = next((version for version in versiones if version == fuente), None)
        if conservada is None:
            conservada = deepcopy(fuente)
            versiones.append(conservada)
        captura[cita] = conservada
    salida["fuentes_citadas"] = captura


def _reiniciar_pagina(clave: str) -> None:
    st.session_state[clave] = 1


@st.fragment
def render(salida: dict, resultados: dict, *, clave: str) -> None:
    captura = salida.get("fuentes_citadas")
    if captura is not None:
        resultados = captura
    grupos = [
        (f"Hallazgo: {hallazgo['afirmacion']}", hallazgo.get("citas", []))
        for hallazgo in salida.get("hallazgos", [])
        if hallazgo.get("citas")
    ] + [
        (f"Afirmación: {afirmacion['afirmacion']}", afirmacion.get("citas", []))
        for afirmacion in salida.get("verificacion", {}).get("afirmaciones", [])
        if afirmacion.get("citas")
    ] + [
        (f"Duda: {grupo['duda']}", grupo.get("citas", []))
        for grupo in salida.get("grupos_preguntas", [])
        if grupo.get("citas")
    ]
    citas = list(dict.fromkeys([
        *salida.get("citas", []),
        *(cita for _, referencias in grupos for cita in referencias),
    ]))
    if not citas:
        st.caption("La respuesta no incluye fuentes citadas.")
        return

    if captura is None:
        st.warning(
            "Esta respuesta antigua no conserva una copia de sus fuentes. "
            "Se muestran los datos actuales, que pueden diferir de los usados al responder."
        )
    else:
        st.caption("Fuentes conservadas al responder; no cambian con las capturas posteriores de la sesión.")
    st.caption(
        f"{len(citas)} fuentes citadas. Este panel conserva todas las referencias; "
        "la paginación no limita los registros analizados."
    )
    st.caption(
        "Cada hallazgo conserva sus propias referencias. Esa relación registrada "
        "por el modelo no equivale por sí sola a una verificación factual independiente."
    )
    clave_pagina = f"{clave}_pagina"
    if grupos:
        indice = st.selectbox(
            "Filtrar por hallazgo, afirmación o duda",
            options=[-1, *range(len(grupos))],
            format_func=lambda i: "Todas las fuentes" if i == -1 else grupos[i][0],
            key=f"{clave}_grupo",
            on_change=_reiniciar_pagina,
            args=(clave_pagina,),
        )
        if indice != -1:
            citas = list(dict.fromkeys(grupos[indice][1]))
    busqueda = st.text_input(
        "Buscar en las fuentes citadas",
        placeholder="ID, autor, canal o texto",
        key=f"{clave}_busqueda",
        on_change=_reiniciar_pagina,
        args=(clave_pagina,),
    ).strip().casefold()
    filtradas = []
    for cita in citas:
        fuente = resultados.get(cita)
        if not busqueda or any(
            busqueda in valor.casefold()
            for valor in (
                cita,
                valor_publico((fuente or {}).get("autor")),
                valor_publico((fuente or {}).get("canal")),
                valor_publico((fuente or {}).get("texto")),
            )
        ):
            filtradas.append(cita)
    if not filtradas:
        st.info("No hay fuentes citadas que coincidan con la búsqueda.")
        return

    paginas = (len(filtradas) + FUENTES_POR_PAGINA - 1) // FUENTES_POR_PAGINA
    st.session_state[clave_pagina] = min(
        max(st.session_state.get(clave_pagina, 1), 1), paginas,
    )
    pagina = int(st.number_input(
        "Página de fuentes",
        min_value=1, max_value=paginas, step=1,
        key=clave_pagina, disabled=paginas == 1,
    ))
    inicio = (pagina - 1) * FUENTES_POR_PAGINA
    seleccion = filtradas[inicio:inicio + FUENTES_POR_PAGINA]
    st.caption(
        f"Mostrando {inicio + 1}–{inicio + len(seleccion)} de {len(filtradas)} "
        f"fuentes coincidentes · Página {pagina} de {paginas}."
    )
    for cita in seleccion:
        fuente = resultados.get(cita)
        if fuente is None:
            detalle = (
                "no se conservó al generar esta respuesta"
                if captura is not None else "no está disponible en los datos actuales"
            )
            st.warning(f"La fuente {cita} {detalle}. La referencia se conserva, pero no se puede mostrar su contenido.")
            continue
        autor = valor_publico(fuente.get("autor")) or "Autor desconocido"
        canal = valor_publico(fuente.get("canal")) or "Canal desconocido"
        with st.expander(f"{cita} · {autor} · {canal}"):
            texto = fuente.get("texto", "")
            vista_previa = " ".join(texto.split())
            st.text(vista_previa[:180] + ("..." if len(vista_previa) > 180 else ""))
            if st.toggle("Mostrar texto completo", key=f"{clave}_texto_{cita}"):
                st.text(texto)
