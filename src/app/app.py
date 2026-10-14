"""Frontend local de CommunityLab. No importa clientes de IA ni de nube."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import altair as alt
import pandas as pd
import streamlit as st

from src.app.local import PLANTILLAS, cargar_entrada, ejemplo, simular_plantilla

st.set_page_config(page_title="CommunityLab · Local", page_icon="🟣", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1240px;padding-top:2rem;padding-bottom:2rem;}
.brand {display:flex;align-items:center;gap:12px;font-size:24px;font-weight:650;color:#17213c;}
.brand span {background:#7056df;color:white;border-radius:12px;padding:3px 13px;font-size:30px;}
.eyebrow {color:#6344c6;font-size:12px;font-weight:700;letter-spacing:1px;margin:24px 0 12px;}
.hero-title {font-size:clamp(32px,4vw,52px);line-height:1.12;letter-spacing:-1.5px;color:#17213c;font-weight:700;margin:10px 0 20px;}
.hero-copy {color:#56617b;font-size:17px;max-width:570px;line-height:1.65;}
.flow {background:#141e39;color:#f7f8ff;border-radius:18px;padding:32px;margin-top:24px;min-height:235px;}
.flow h3 {color:white;font-size:23px;line-height:1.3;}
.flow p {color:#cbd2e9;line-height:1.6;}
.flow-step {background:#283554;padding:12px 16px;border-radius:9px;margin-top:10px;}
div[data-testid="stMetric"] {background:white;border:1px solid #e5e3f0;border-radius:12px;padding:18px;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px;}
div[data-testid="stRadio"] > div {gap:8px 24px;}
@media(max-width:640px) {.block-container {padding:4.2rem 1.2rem 1.2rem;} .flow {padding:22px;min-height:unset;} .hero-title {font-size:34px;} }
</style>
""", unsafe_allow_html=True)

for key, value in {"pagina": "Inicio", "datos": [], "origen": "", "resultado": None}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def navegar(pagina):
    st.session_state.pagina = pagina


def conservar_seleccion():
    st.session_state.seleccion_exportar = st.session_state._seleccion_exportar


def importar(contenido, origen):
    # Validar todo antes de sustituir el estado activo.
    try:
        mensajes = cargar_entrada(contenido)
    except (ValueError, UnicodeError, RecursionError) as error:
        st.error(f"No se pudo cargar: {error}")
        return
    st.session_state.datos = mensajes
    st.session_state.origen = origen
    st.session_state.resultado = None
    st.session_state.pop("seleccion_exportar", None)
    st.session_state.pop("_seleccion_exportar", None)
    st.success(f"{len(mensajes)} mensajes validados. Ya puedes explorarlos o probar una plantilla.")


def cargar_ejemplo():
    importar(ejemplo(), "Ejemplo del proyecto · datos simulados")


def importar_pegado():
    importar(st.session_state.entrada_json, "JSON pegado")


def importar_archivo():
    archivo = st.session_state.archivo_json
    if archivo is not None:
        importar(archivo.getvalue(), archivo.name)


def vaciar():
    st.session_state.datos = []
    st.session_state.origen = ""
    st.session_state.resultado = None
    st.session_state.pop("seleccion_exportar", None)
    st.session_state.pop("_seleccion_exportar", None)


def requerir_datos():
    if st.session_state.datos:
        return True
    st.info("Carga tus interacciones o usa el ejemplo para empezar.")
    st.button("Ir a Carga", on_click=navegar, args=("Carga",))
    st.button("Usar ejemplo del proyecto", on_click=cargar_ejemplo)
    return False


st.markdown('<div class="brand"><span>C</span> communitylab</div>', unsafe_allow_html=True)
st.radio("Navegación", ["Inicio", "Plantillas", "Agente en vivo", "Analítica", "Ayuda", "Carga"],
         key="pagina", horizontal=True, label_visibility="collapsed")
st.caption("DEMO LOCAL · IA y almacenamiento en la nube pendientes de integración")
st.divider()

pagina = st.session_state.pagina
mensajes = st.session_state.datos

if pagina == "Inicio":
    izquierda, derecha = st.columns([1.35, 1], gap="large")
    with izquierda:
        st.markdown('<div class="eyebrow">DE CONVERSACIONES A OPORTUNIDADES</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title">Tu comunidad habla.<br>Convierte esa voz en valor.</div>', unsafe_allow_html=True)
        st.markdown('<p class="hero-copy">Explora conversaciones, encuentra preguntas y revisa borradores de contenido desde un mismo lugar.</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.button("Descubrir plantillas", type="primary", on_click=navegar, args=("Plantillas",), width="stretch")
        c2.button("Cargar mis datos", on_click=navegar, args=("Carga",), width="stretch")
    with derecha:
        st.markdown('''<div class="flow"><p>UNA BASE, VARIOS RESULTADOS</p><h3>De miles de mensajes<br>a una idea útil.</h3><p>Empieza con una comunidad y elige cómo explorarla.</p><div class="flow-step">01 · Carga y revisa las conversaciones</div><div class="flow-step">02 · Prueba una plantilla y revisa el borrador</div></div>''', unsafe_allow_html=True)
    st.subheader("Elige cómo quieres trabajar")
    for columna, titulo, descripcion, destino in zip(st.columns(3),
        ["Plantillas", "Analítica de comunidad", "FAQ y ayuda"],
        ["Borradores para redes, preguntas y resúmenes.", "Mensajes, canales y tipos declarados en tu archivo.", "Formatos de entrada y guía para tu primer resultado."],
        ["Plantillas", "Analítica", "Ayuda"]):
        with columna, st.container(border=True):
            st.subheader(titulo)
            st.write(descripcion)
            st.button("Explorar", key=f"inicio_{destino}", on_click=navegar, args=(destino,))
    if mensajes:
        st.success(f"Tu sesión tiene {len(mensajes)} mensajes listos para explorar.")

elif pagina == "Carga":
    st.header("Prepara los datos antes de generar resultados")
    st.write("Carga un lote JSON o varios lotes del formato CommunityLab. Máximo 5 MB y 1.000 mensajes.")
    archivo = st.file_uploader("Archivo de interacciones", type=["json"], max_upload_size=5, key="archivo_json")
    st.button("Validar y cargar archivo", disabled=archivo is None, type="primary",
              on_click=importar_archivo)
    with st.expander("Pegar JSON manualmente"):
        st.text_area("Contenido JSON", height=180, key="entrada_json", placeholder='{"origen_comunidad": "Mi comunidad", "periodo_referencia": "Semana_01", "interacciones": [...]}')
        st.button("Validar JSON pegado", on_click=importar_pegado)
    c1, c2 = st.columns(2)
    c1.button("Usar ejemplo del proyecto", on_click=cargar_ejemplo, width="stretch")
    c2.download_button("Descargar ejemplo JSON", ejemplo(), "communitylab_ejemplo.json", "application/json", width="stretch")
    if mensajes:
        st.subheader("Estado de preparación")
        st.success(f"{len(mensajes)} mensajes disponibles · {st.session_state.origen}")
        st.caption("La validación reutiliza la limpieza del proyecto. Los datos permanecen en la memoria de esta sesión.")
        canales = ["Todos"] + sorted({m["canal"] for m in mensajes})
        filtro, busqueda = st.columns([1, 2])
        canal = filtro.selectbox("Canal", canales)
        texto = busqueda.text_input("Buscar por autor o mensaje")
        visibles = [m for m in mensajes if (canal == "Todos" or m["canal"] == canal)
                    and texto.casefold() in (m["autor"] + " " + m["texto"]).casefold()]
        st.caption(f"{len(visibles)} de {len(mensajes)} mensajes")
        if visibles:
            st.dataframe(pd.DataFrame(visibles)[["id", "autor", "canal", "tipo", "texto"]], hide_index=True, width="stretch")
            elegido = st.selectbox("Leer mensaje completo", [m["id"] for m in visibles])
            mensaje = next(m for m in visibles if m["id"] == elegido)
            with st.container(border=True):
                st.write(f"{mensaje['autor']} · {mensaje['canal']}")
                st.text(mensaje["texto"])
        else:
            st.info("No hay mensajes para estos filtros.")
        c1, c2 = st.columns(2)
        c1.button("Elegir plantilla →", on_click=navegar, args=("Plantillas",), type="primary")
        c2.button("Vaciar sesión", on_click=vaciar)

elif pagina == "Plantillas":
    st.header("Elige el resultado que necesitas")
    st.write("Un punto de partida para cada conversación. Revisa siempre el contenido antes de publicarlo.")
    columnas = st.columns(2)
    for indice, (nombre, config) in enumerate(PLANTILLAS.items()):
        with columnas[indice % 2], st.container(border=True):
            st.subheader(nombre)
            st.write(config["descripcion"])
    st.divider()
    if requerir_datos():
        configuracion, vista = st.columns([1, 2], gap="large")
        with configuracion:
            st.subheader("Configuración")
            plantilla = st.selectbox("Plantilla", list(PLANTILLAS))
            st.caption(f"Base disponible: {len(mensajes)} mensajes")
            st.info("Simulación local por tipo declarado. Sin análisis de IA.")
            if st.button("Generar borrador simulado", type="primary", width="stretch"):
                try:
                    st.session_state.resultado = simular_plantilla(mensajes, plantilla)
                    st.session_state.pop("seleccion_exportar", None)
                    st.session_state.pop("_seleccion_exportar", None)
                except ValueError as error:
                    st.error(str(error))
        with vista:
            resultado = st.session_state.resultado
            if resultado:
                st.subheader(resultado["plantilla"])
                st.warning("BORRADOR SIMULADO · No generado por IA. No guardado en la nube.")
                st.caption(resultado["criterio"])
                activos = resultado["borradores"]
                if activos:
                    for activo in activos:
                        with st.expander(activo["titulo"], expanded=len(activos) == 1):
                            st.text(activo["contenido"])
                            st.caption("Mensajes fuente: " + ", ".join(activo["fuentes"]))
                    opciones = list(range(len(activos)))
                    if "_seleccion_exportar" not in st.session_state:
                        st.session_state._seleccion_exportar = st.session_state.get("seleccion_exportar", opciones)
                    seleccion = st.multiselect("Selecciona borradores para descargar", opciones,
                        format_func=lambda i: activos[i]["titulo"], key="_seleccion_exportar", on_change=conservar_seleccion)
                    exportacion = {**resultado, "borradores": [activos[i] for i in seleccion]}
                    st.download_button("Descargar selección simulada", json.dumps(exportacion, ensure_ascii=False, indent=2),
                        "communitylab_borradores_simulados.json", "application/json", disabled=not seleccion,
                        width="stretch")
                else:
                    st.info("No hay mensajes del tipo requerido para esta plantilla. Prueba otra o carga un lote diferente.")
            else:
                st.info("Elige una plantilla y genera un borrador para ver aquí el resultado.")

elif pagina == "Analítica":
    st.header("Entiende las conversaciones de tu comunidad")
    st.caption("Conteos locales de los datos cargados. El tipo procede del JSON; no se ha inferido sentimiento ni elegibilidad con IA.")
    if requerir_datos():
        df = pd.DataFrame(mensajes)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mensajes", len(df))
        c2.metric("Canales", df.canal.nunique())
        c3.metric("Testimonios declarados", int((df.tipo == "testimonio").sum()))
        c4.metric("Preguntas declaradas", int(df.tipo.str.startswith("pregunta_").sum()))
        c1, c2 = st.columns(2)
        for columna, campo, titulo in [(c1, "tipo", "Tipos de conversación"), (c2, "canal", "Actividad por canal")]:
            with columna, st.container(border=True):
                st.subheader(titulo)
                chart = alt.Chart(df).mark_bar(color="#7056df", cornerRadiusEnd=4).encode(
                    x=alt.X("count():Q", title="Mensajes"), y=alt.Y(f"{campo}:N", sort="-x", title=None),
                    tooltip=[alt.Tooltip(f"{campo}:N"), alt.Tooltip("count():Q", title="Mensajes")]).properties(height=280)
                st.altair_chart(chart, width="stretch")
        st.subheader("Origen de los datos")
        st.dataframe(df.groupby(["origen_comunidad", "periodo_referencia"]).size().reset_index(name="mensajes"), hide_index=True, width="stretch")
        st.download_button("Descargar mensajes validados", df.to_csv(index=False).encode("utf-8-sig"),
                           "communitylab_mensajes_validados.csv", "text/csv")

elif pagina == "Agente en vivo":
    st.header("Agente CommunityLab")
    st.info("Integración pendiente. Esta versión local no envía mensajes a NVIDIA, Gemini ni OCI.")
    st.text_area("Consulta al agente (disponible al conectar la integración)", disabled=True,
        placeholder="Por ejemplo: ¿qué preguntas se repiten en mi comunidad?")
    st.button("Enviar consulta", disabled=True)
    st.button("Explorar plantillas simuladas", on_click=navegar, args=("Plantillas",))

elif pagina == "Ayuda":
    st.header("¿En qué podemos ayudarte?")
    preguntas = {
        "¿Cómo obtengo mi primer resultado?": "Abre Carga, usa el ejemplo o valida tu JSON. Después entra en Plantillas, elige un formato y genera un borrador simulado. Puedes revisar y descargar una selección.",
        "¿Qué formato acepta CommunityLab?": "Un objeto con origen_comunidad, periodo_referencia e interacciones; o un objeto con lotes. Cada interacción requiere autor, canal, tipo y texto. Tipos: testimonio, pregunta_tecnica, pregunta_programa, comentario y feedback. id, fecha e idioma son opcionales.",
        "¿Los resultados fueron generados por IA?": "No. Los borradores son simulaciones deterministas basadas en el tipo declarado del mensaje. Las métricas son conteos de los datos cargados; no representan sentimiento, relevancia ni aprobación real.",
        "¿Dónde quedan mis datos?": "En la memoria de esta sesión local. Las descargas son archivos en tu equipo y no implican guardado en OCI. Vaciar sesión elimina los datos de esta sesión; recargar el navegador puede iniciar una nueva.",
        "¿Qué ocurre si mi JSON tiene un error?": "La app indica el problema y mantiene el último lote válido. Corrige la entrada y vuelve a validarla. Un lote nuevo válido reemplaza la base activa y retira los borradores anteriores.",
    }
    for pregunta, respuesta in preguntas.items():
        with st.expander(pregunta):
            st.write(respuesta)
    with st.expander("Una base de datos, distintas salidas"):
        st.write("Carga JSON → validación y limpieza local → mensajes preparados → plantillas simuladas o conteos. La conexión futura reutilizará la entrega de DA, el grafo de DS y el guardado aprobado en OCI.")
    st.button("Empezar con mis datos", on_click=navegar, args=("Carga",), type="primary")

st.divider()
st.caption("CommunityLab · Hackathon ONE G10 · Prototipo local basado en el boceto compartido")
