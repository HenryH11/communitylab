"""Tema visual gótico formal del agente en vivo.

Es la versión nocturna de la paleta "pergamino y miel" de `tema.py`: ébano,
bosque, nogal y miel encendida con titulares serif en bold y texto light (naturaleza, fauna
y madera en clave sobria). Comparte tonos con el resto de la app, pero resalta
por contraste de luz. Los estilos solo se inyectan al renderizar esa vista.
"""

from html import escape

from src.agentes.plataformas import NOMBRES_PLATAFORMA
from src.app.tema import logo

EMBLEMA = logo("gotico-emblema")

ESTILO = """
<style>
    :root {
        --ebano: #0c0b08;
        --noche: #15140e;
        --bosque: #1c1b14;
        --nogal: #241b10;
        --laton: #d6ab50;
        --blanco: #fbf7ec;
        --hueso: #ddd6c3;
        --linea: rgba(251, 247, 236, 0.14);
        --serif-titulo: "Cinzel", "Trajan Pro", Georgia, serif;
        --serif-display: "Cormorant Garamond", Garamond, Georgia, serif;
        --texto: "Inter", "Segoe UI", system-ui, sans-serif;
    }

    /* Fondo sólido para que el texto se vea nítido */
    .stApp {
        background: linear-gradient(180deg, var(--noche), var(--ebano));
        color: var(--blanco);
        --cl-header-tinta: var(--blanco);
        --cl-header-suave: var(--hueso);
        --cl-header-linea: var(--linea);
        --cl-header-activo: var(--bosque);
        --cl-header-logo: var(--laton);
    }
    header[data-testid="stHeader"] { background: transparent; }
    header[data-testid="stHeader"] * { color: var(--hueso); }

    /* Lienzo central, como un chat de LLM */
    .st-key-gotico_lienzo {
        max-width: 780px;
        margin: 0 auto;
        padding-bottom: 7rem;
    }
    .st-key-gotico_lienzo p,
    .st-key-gotico_lienzo li,
    .st-key-gotico_lienzo label {
        font-family: var(--texto);
        font-weight: 300;
        color: var(--blanco);
    }
    .st-key-gotico_lienzo strong { font-weight: 700; }

    .gotico-cabecera {
        text-align: center;
        margin: 9vh 0 2rem;
        animation: gotico-aparecer 0.8s ease-out both;
    }
    .gotico-emblema { width: 64px; height: 64px; color: var(--laton); }
    .gotico-cabecera p.gotico-titulo {
        margin: 0.9rem 0 0.2rem;
        font-family: var(--serif-titulo);
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.3em;
        color: var(--laton);
    }
    .gotico-cabecera p.gotico-lema {
        margin: 0;
        font-family: var(--serif-display);
        font-weight: 700;
        font-size: 2.7rem;
        line-height: 1.2;
        color: var(--blanco);
    }
    .gotico-ornamento {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        margin: 1rem auto 0;
        max-width: 320px;
        color: var(--laton);
        font-size: 1rem;
    }
    .gotico-ornamento::before,
    .gotico-ornamento::after {
        content: "";
        flex: 1;
        height: 1px;
        background: var(--linea);
    }

    /* Controles junto a la entrada: verificación y estilo de redacción */
    .st-key-gotico_controles { margin-bottom: 0.35rem; }
    [data-testid="stBottomBlockContainer"] > [data-testid="stVerticalBlock"]
    > [data-testid="stLayoutWrapper"]:has(> .st-key-gotico_controles) {
        order: -1;
    }
    .st-key-agente_barra { flex-wrap: wrap; gap: 0.4rem; }
    .st-key-gotico_controles [data-testid="stCheckbox"] label p {
        font-family: var(--texto) !important;
        font-weight: 300 !important;
        font-size: 0.88rem !important;
        color: var(--blanco) !important;
    }
    /* La pista del interruptor es el primer div sin testid de la etiqueta. */
    .st-key-gotico_controles [data-testid="stCheckbox"] label > div:not([data-testid]) {
        background: #4a4434 !important;
    }
    .st-key-gotico_controles [data-testid="stCheckbox"] label:has(input:checked) > div:not([data-testid]) {
        background: var(--laton) !important;
    }
    .st-key-gotico_controles [data-testid="stCheckbox"] label > div:not([data-testid]) > div {
        background: var(--blanco) !important;
    }
    .st-key-gotico_controles [data-testid="stTooltipIcon"] * { color: var(--hueso) !important; }
    .st-key-gotico_controles [data-testid="stPopover"] button {
        min-height: 2rem;
        padding: 0.2rem 0.85rem;
        background: var(--nogal);
        border: 1px solid var(--linea);
        border-radius: 999px;
        color: var(--blanco);
    }
    .st-key-gotico_controles [data-testid="stPopover"] button:hover { border-color: var(--laton); }
    .st-key-gotico_controles [data-testid="stPopover"] button p {
        font-family: var(--texto);
        font-weight: 300;
        font-size: 0.88rem;
        color: var(--blanco);
    }
    [data-testid="stPopoverBody"] {
        background: var(--nogal);
        border: 1px solid var(--linea);
    }
    [data-testid="stPopoverBody"]:has([class*="st-key-agente_panel_"]) {
        width: min(330px, calc(100vw - 32px)) !important;
        min-width: 0 !important;
        padding: 0.7rem !important;
    }
    [class*="st-key-agente_panel_"] {
        gap: 0.45rem !important;
    }
    [class*="st-key-agente_panel_"] [data-testid="stCaptionContainer"] p {
        font-size: 0.78rem;
        line-height: 1.35;
        margin-bottom: 0;
    }
    [class*="st-key-agente_panel_"] [data-testid="stCaptionContainer"] {
        margin-bottom: 0 !important;
    }
    .st-key-agente_panel_datos [data-testid="stText"] {
        font-family: var(--texto) !important;
        color: var(--blanco) !important;
        font-weight: 400;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.8rem;
    }
    .st-key-agente_panel_datos [data-testid="stText"] * {
        color: var(--blanco) !important;
    }
    .agente-info { width: 1.6rem; }
    .agente-info summary {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 1.5rem;
        height: 1.8rem;
        cursor: pointer;
        color: var(--blanco);
        font: 700 0.85rem var(--texto);
        list-style: none;
        border: 1px solid var(--linea);
        border-radius: 50%;
    }
    .agente-info summary::-webkit-details-marker { display: none; }
    .agente-info summary:hover,
    .agente-info summary:focus-visible {
        outline: 2px solid var(--laton);
        outline-offset: 2px;
    }
    .agente-info-tarjeta {
        display: none;
        position: fixed;
        bottom: 155px;
        left: 16px;
        width: min(330px, calc(100vw - 32px));
        max-height: min(440px, calc(100dvh - 200px));
        overflow-y: auto;
        padding: 1rem;
        background: var(--nogal);
        color: var(--blanco);
        border: 1px solid var(--linea);
        border-radius: 8px;
        box-shadow: 0 8px 28px #0008;
        z-index: 10000;
        font: 400 0.85rem/1.5 var(--texto);
    }
    .agente-info-tarjeta strong { color: var(--blanco); }
    .agente-info-tarjeta p {
        color: var(--blanco);
        font: 400 0.85rem/1.5 var(--texto) !important;
        margin: 0.6rem 0 0;
    }
    .agente-info details[open] + .agente-info-tarjeta,
    .agente-info:has(summary:focus-visible) .agente-info-tarjeta { display: block; }
    @media (hover: hover) {
        .agente-info:hover .agente-info-tarjeta { display: block; }
    }
    @media (max-width: 700px) {
        .agente-info-tarjeta {
            bottom: 250px;
            max-height: calc(100dvh - 290px);
        }
    }
    @media (min-width: 1350px) {
        .agente-info-tarjeta {
            left: max(16px, calc((100vw - 1320px) / 2));
            bottom: 180px;
            width: 230px;
        }
        .agente-info-derecha .agente-info-tarjeta {
            left: auto;
            right: max(16px, calc((100vw - 1320px) / 2));
        }
    }
    [data-testid="stPopoverBody"] p,
    [data-testid="stPopoverBody"] label p,
    [data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] {
        font-family: var(--texto);
        color: var(--blanco);
    }
    [data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] p { color: var(--hueso); }
    [data-testid="stPopoverBody"] [data-testid="stTooltipIcon"] * { color: var(--hueso) !important; }
    [data-testid="stPopoverBody"] [data-testid="stSliderThumbValue"] { color: var(--laton); }
    [data-testid="stPopoverBody"] [data-testid="stSlider"] [role="slider"] {
        background: var(--laton);
        border-color: var(--laton);
    }
    [data-testid="stPopoverBody"] [data-testid="stButtonGroup"] button {
        background: var(--bosque);
        border-color: var(--linea);
    }
    [data-testid="stPopoverBody"] [data-testid="stButtonGroup"] button[aria-checked="true"] {
        background: var(--laton) !important;
        border-color: var(--laton) !important;
    }
    [data-testid="stPopoverBody"] [data-testid="stButtonGroup"] button[aria-checked="true"] p {
        color: var(--ebano);
        font-weight: 700;
    }

    /* Mensajes */
    [data-testid="stChatMessage"] {
        background: transparent;
        padding: 0.4rem 0;
        margin-bottom: 1.1rem;
        animation: gotico-aparecer 0.5s ease-out both;
    }
    [data-testid="stChatMessage"] > [data-testid^="stChatMessageAvatar"],
    [data-testid="stChatMessage"] > div:first-child:not([data-testid="stChatMessageContent"]) {
        display: none;
    }
    [data-testid="stChatMessage"]:has(.gotico-voz-persona) {
        width: fit-content;
        max-width: 78%;
        margin-left: auto;
        padding: 0.75rem 1.1rem;
        border: 1px solid var(--linea);
        border-radius: 14px 14px 2px 14px;
        background: var(--nogal);
    }
    [data-testid="stChatMessage"] [data-testid="stElementContainer"]:has(.gotico-voz-persona) {
        display: none;
    }
    [data-testid="stChatMessage"]:has(.gotico-voz-agente) p,
    [data-testid="stChatMessage"]:has(.gotico-voz-agente) li {
        font-size: 1.05rem;
        line-height: 1.7;
    }
    [data-testid="stChatMessage"] strong { color: var(--blanco); }
    .gotico-firma {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-family: var(--serif-titulo);
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 0.2em;
        color: var(--laton);
    }
    .gotico-firma .gotico-emblema { width: 20px; height: 20px; }
    [data-testid="stChatMessage"]:has(.gotico-voz-agente) [data-testid="stMarkdownContainer"] .gotico-firma {
        margin-bottom: 0.25rem;
    }

    /* Borrador: folio sólido con filete neutro y título blanco */
    .gotico-borrador {
        margin: 0.9rem 0 0.3rem;
        padding: 1.3rem 1.5rem 1.1rem;
        border: 1px solid var(--linea);
        border-left: 3px solid var(--laton);
        border-radius: 4px;
        background: var(--bosque);
    }
    .gotico-borrador-plataforma {
        font-family: var(--serif-titulo);
        font-weight: 700;
        font-size: 0.78rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--laton);
    }
    .gotico-borrador-titulo {
        margin: 0.35rem 0 0.7rem;
        font-family: var(--serif-display);
        font-size: 1.7rem;
        font-weight: 700;
        color: var(--blanco);
    }
    .gotico-borrador-contenido {
        font-family: var(--texto);
        font-weight: 300;
        font-size: 1rem;
        line-height: 1.7;
        color: var(--blanco);
    }
    .gotico-hashtags {
        margin-top: 0.9rem;
        padding-top: 0.6rem;
        border-top: 1px solid var(--linea);
        font-family: var(--texto);
        font-weight: 700;
        font-size: 0.9rem;
        color: var(--hueso);
    }

    /* Desplegables de fuentes y verificación */
    .st-key-gotico_lienzo [data-testid="stExpander"] details {
        background: transparent;
        border: none;
        border-top: 1px solid var(--linea);
        border-radius: 0;
    }
    .st-key-gotico_lienzo [data-testid="stExpander"] summary p {
        font-family: var(--texto);
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--blanco);
    }
    .st-key-gotico_lienzo [data-testid="stExpander"] summary svg { color: var(--laton); }
    .st-key-gotico_lienzo [data-testid="stCaptionContainer"],
    .st-key-gotico_lienzo [data-testid="stCaptionContainer"] p { color: var(--hueso); }

    /* Avisos: el fondo del aviso es claro, así que el texto va oscuro */
    .st-key-gotico_lienzo [data-testid="stAlert"] p { color: var(--ebano); }

    /* Entrada fija al pie, como en un chat de LLM */
    [data-testid="stBottom"] > div { background: var(--ebano); }
    [data-testid="stBottomBlockContainer"] {
        max-width: 812px;
        padding-bottom: 1.6rem;
    }
    [data-testid="stChatInput"] {
        background: var(--bosque);
        border: 1px solid var(--linea) !important;
        border-radius: 14px;
        transition: border-color 0.3s ease;
    }
    [data-testid="stChatInput"]:focus-within { border-color: var(--laton) !important; }
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] > div:focus-within {
        background: transparent;
        border-color: transparent !important;
    }
    [data-testid="stChatInput"] textarea {
        font-family: var(--texto);
        font-weight: 300;
        font-size: 1.02rem;
        color: var(--blanco);
        caret-color: var(--laton);
    }
    [data-testid="stChatInput"] textarea::placeholder { color: #b3ab95; }
    [data-testid="stChatInput"] button {
        background: var(--laton);
        border: none;
        color: var(--ebano);
    }

    [data-testid="stSpinner"] p { font-family: var(--texto); font-weight: 300; color: var(--hueso); }

    @keyframes gotico-aparecer {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: none; }
    }
    @media (prefers-reduced-motion: reduce) {
        .gotico-cabecera, [data-testid="stChatMessage"],
        .gotico-cabecera .gotico-emblema path { animation: none; }
    }
</style>
"""


def cabecera(lema: str) -> str:
    return (
        '<div class="gotico-cabecera">'
        f"{EMBLEMA}"
        '<p class="gotico-titulo">AGENTE COMMUNITYLAB</p>'
        f'<p class="gotico-lema">{escape(lema)}</p>'
        '<div class="gotico-ornamento">❧</div>'
        "</div>"
    )


def marca_voz(rol: str) -> str:
    """Marca que da a cada mensaje su estilo según quién habla."""
    if rol == "user":
        return '<span class="gotico-voz-persona"></span>'
    return (
        '<div class="gotico-firma gotico-voz-agente">'
        f"{EMBLEMA}<span>COMMUNITYLAB</span></div>"
    )


def informacion_lateral(clave: str, titulo: str, parrafos: list[str], *, derecha: bool = False) -> str:
    lado = " agente-info-derecha" if derecha else ""
    contenido = "".join(f"<p>{escape(texto)}</p>" for texto in parrafos)
    return (
        f'<div class="agente-info{lado}"><details name="agente-informacion">'
        f'<summary aria-label="Información de {escape(titulo, quote=True)}" '
        f'aria-describedby="info-{escape(clave, quote=True)}">i</summary></details>'
        f'<aside class="agente-info-tarjeta" id="info-{escape(clave, quote=True)}" '
        f'aria-label="{escape(titulo, quote=True)}">'
        f"<strong>{escape(titulo)}</strong>{contenido}</aside></div>"
    )


def borrador(datos: dict) -> str:
    plataforma = NOMBRES_PLATAFORMA.get(datos.get("plataforma", ""), "Publicación")
    contenido = escape(datos.get("contenido", "")).replace("\n", "<br>")
    hashtags = " · ".join(escape(etiqueta) for etiqueta in datos.get("hashtags", []))
    return (
        '<div class="gotico-borrador">'
        f'<div class="gotico-borrador-plataforma">Publicación preparada · {escape(plataforma)}</div>'
        f'<div class="gotico-borrador-titulo">{escape(datos.get("titulo", ""))}</div>'
        f'<div class="gotico-borrador-contenido">{contenido}</div>'
        f'<div class="gotico-hashtags">{hashtags}</div>'
        "</div>"
    )
