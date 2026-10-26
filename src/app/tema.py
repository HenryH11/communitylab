"""Identidad visual compartida de CommunityLab: paleta "pergamino y miel".

Las páginas generales usan la versión diurna (pergamino claro, tinta sepia y
miel); el agente en vivo usa la versión nocturna de los mismos tonos (ébano,
bosque y miel encendida). Así ambas congenian, pero al entrar al agente la
página resalta por contraste de luz y no por cambio de identidad.
"""

from urllib.parse import quote


_TRAZOS_NUCLEO = (
    "M165 48C138 20 91 18 59 42C24 68 19 111 40 142C31 111 44 79 70 65C99 49 130 58 145 78Z",
    "M38 151C65 179 112 181 144 157C179 131 184 88 163 57C172 88 159 120 133 134C104 150 73 141 58 121Z",
    "M119 75C93 69 74 85 76 105C78 126 101 136 116 121C126 111 125 92 119 75Z",
)


def logo(clase: str = "cl-logo") -> str:
    """Núcleo: dos cintas opuestas alrededor de una semilla."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="{clase}" '
        'viewBox="0 0 200 200" fill="currentColor" aria-hidden="true">'
        + "".join(f'<path d="{trazo}"/>' for trazo in _TRAZOS_NUCLEO)
        + "</svg>"
    )


ICONO_PAGINA = "data:image/svg+xml," + quote(
    logo().replace('fill="currentColor"', 'fill="#8c6214"')
)

# Solo dos pesos por familia: bold para títulos y light para el texto.
FUENTES = (
    "@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700"
    "&family=Cormorant+Garamond:wght@300;700"
    "&family=Inter:wght@300;700&display=swap');"
)

# Colores de gráficas alineados con .streamlit/config.toml.
MIEL = "#b07d22"
MUSGO = "#5b6a42"

ESTILO_GLOBAL = f"""
<style>
    {FUENTES}

    :root {{
        --cl-pergamino: #f5efe1;
        --cl-superficie: #fffaf0;
        --cl-linea: #e3d5b3;
        --cl-tinta: #2b2216;
        --cl-tinta-suave: #54483a;
        --cl-miel: {MIEL};
        --cl-miel-oscura: #8c6214;
        --cl-miel-clara: #f1e2bd;
        --cl-musgo: {MUSGO};
        --cl-noche: #15160f;
        --cl-miel-noche: #d6ab50;
        --cl-titulo: "Cormorant Garamond", Garamond, Georgia, serif;
        --cl-versal: "Cinzel", "Trajan Pro", Georgia, serif;
        --cl-texto: "Inter", "Segoe UI", system-ui, sans-serif;
        --cl-header-tinta: #2b2216;
        --cl-header-suave: #54483a;
        --cl-header-linea: #e3d5b3;
        --cl-header-activo: #f1e2bd;
        --cl-header-logo: #8c6214;
    }}

    /* Fondo sólido: los degradados translúcidos hacían ver la página borrosa. */
    .stApp {{ background: var(--cl-pergamino); }}
    .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
    .stApp td, .stApp th {{
        font-family: var(--cl-texto);
        font-weight: 300;
        -webkit-font-smoothing: antialiased;
    }}
    .stApp strong, .stApp b {{ font-weight: 700; }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
        color: var(--cl-tinta);
        font-family: var(--cl-titulo);
        font-weight: 700;
        letter-spacing: 0.005em;
    }}
    .stApp h1 {{ font-size: 3.4rem; line-height: 1.1; }}
    .stApp h2 {{ font-size: 2.3rem; }}

    .communitylab-brand {{
        display: flex;
        align-items: center;
        gap: 14px;
        background: transparent;
        border-radius: 0;
        border-bottom: 1px solid var(--cl-header-linea);
        color: var(--cl-header-tinta);
        font-family: var(--cl-versal);
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: .06em;
        margin-bottom: 0;
        padding: 0 0 16px;
    }}
    .communitylab-brand .cl-logo {{
        width: 3rem;
        height: 3rem;
        color: var(--cl-header-logo);
    }}
    .st-key-navegacion_principal {{
        padding-top: 12px;
        padding-bottom: 6px;
    }}
    .st-key-navegacion_principal [role="radiogroup"] {{ gap: 6px; flex-wrap: wrap; }}
    .st-key-navegacion_principal label {{
        min-height: 44px;
        border-radius: 6px;
        padding: 8px 16px;
        transition: background 0.2s ease;
    }}
    .st-key-navegacion_principal label > div > div:not([data-testid]) {{ display: none; }}
    .st-key-navegacion_principal label p {{
        font-size: 14px; margin: 0; color: var(--cl-header-suave);
    }}
    .st-key-navegacion_principal label:hover {{ background: var(--cl-header-activo); }}
    .st-key-navegacion_principal label:has(input:checked) {{
        background: var(--cl-header-activo);
    }}
    .st-key-navegacion_principal label:has(input:checked) p {{
        color: var(--cl-header-tinta);
        font-weight: 700;
    }}
    .st-key-navegacion_principal label:has(input:focus-visible) {{
        outline: 2px solid var(--cl-header-logo); outline-offset: 3px;
    }}
    @media(max-width:480px) {{
        .communitylab-brand {{ font-size: 1.25rem; }}
    }}

    button[kind="primary"] {{
        background-color: var(--cl-miel-oscura);
        border-color: var(--cl-miel-oscura);
        color: #fffaf0;
    }}
    button[kind="primary"]:hover {{
        background-color: var(--cl-tinta);
        border-color: var(--cl-tinta);
        color: #fffaf0;
    }}
    [data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stExpander"] details {{
        background: var(--cl-superficie);
    }}
    /* Insignia de inicio: texto blanco sobre noche, no miel sobre miel */
    .st-key-inicio_insignia span {{
        background: var(--cl-noche) !important;
        color: #fffaf0 !important;
        font-weight: 700;
        letter-spacing: 0.08em;
    }}

    .st-key-inicio_card_datos button,
    .st-key-inicio_card_agente button,
    .st-key-inicio_card_analisis button,
    .st-key-inicio_card_an-lisis button,
    .st-key-inicio_card_plantillas button {{
        height: 9rem;
        justify-content: flex-start;
        text-align: left;
        white-space: pre-wrap;
    }}
    .block-container {{
        max-width: 1440px;
        padding-bottom: 2rem;
        padding-top: 3.6rem;
    }}
    .stApp :is(a, button, input, textarea, select, summary, [tabindex]):focus-visible {{
        outline: 3px solid var(--cl-header-logo) !important;
        outline-offset: 3px;
        scroll-margin-block: 6rem;
    }}
    .stApp :is(button, summary, [data-testid="stLinkButton"] a) {{
        min-height: 44px;
    }}
    .stApp :is(input, textarea) {{ font-size: 1rem; }}
    @media (prefers-reduced-motion: reduce) {{
        .stApp *, .stApp *::before, .stApp *::after {{
            animation: none !important;
            transition: none !important;
            scroll-behavior: auto !important;
        }}
    }}
    @media (forced-colors: active) {{
        .stApp :is(button, summary, input, textarea, [data-testid="stLinkButton"] a),
        .st-key-navegacion_principal label {{
            border: 1px solid ButtonText !important;
        }}
        .st-key-navegacion_principal label:has(input:checked) {{
            outline: 2px solid Highlight;
        }}
        .stApp :is(a, button, input, textarea, select, summary, [tabindex]):focus-visible {{
            outline-color: Highlight !important;
        }}
    }}
</style>
"""


def marca() -> str:
    return (
        f'<div class="communitylab-brand">{logo()}'
        "<span>COMMUNITYLAB</span></div>"
    )
