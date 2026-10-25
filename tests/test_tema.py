from urllib.parse import unquote
from xml.etree import ElementTree

from src.app import estilo_agente, tema
from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_nucleo_es_svg_con_tres_formas_rellenas():
    svg = ElementTree.fromstring(tema.logo())
    assert svg.attrib["viewBox"] == "0 0 200 200"
    assert svg.attrib["fill"] == "currentColor"
    assert len(svg) == 3
    assert "stroke" not in svg.attrib
    assert tema.logo() in tema.marca()
    assert 'class="gotico-emblema"' in estilo_agente.EMBLEMA


def test_favicon_reutiliza_nucleo_en_color_miel():
    svg = ElementTree.fromstring(unquote(tema.ICONO_PAGINA.split(",", 1)[1]))
    assert svg.attrib["fill"] == "#8c6214"
    assert len(svg) == 3


def test_foco_movimiento_reducido_y_alto_contraste_no_se_ocultan():
    assert "padding-top: 12px" in tema.ESTILO_GLOBAL
    assert "min-height: 44px" in tema.ESTILO_GLOBAL
    assert ":focus-visible" in tema.ESTILO_GLOBAL
    assert "prefers-reduced-motion: reduce" in tema.ESTILO_GLOBAL
    assert "forced-colors: active" in tema.ESTILO_GLOBAL
    assert "outline-color: Highlight" in tema.ESTILO_GLOBAL


def test_cabecera_del_agente_es_encabezado_y_ornamento_decorativo():
    html = estilo_agente.cabecera("Bienvenido")
    assert 'role="heading" aria-level="1"' in html
    assert 'class="gotico-ornamento" aria-hidden="true"' in html
    assert "width: 2.75rem" in estilo_agente.ESTILO


def test_analisis_ofrece_conteos_textuales_con_mismo_filtro_spam():
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src" / "app" / "app_interna.py"),
        default_timeout=30,
    )
    app.session_state["navegacion_principal"] = "Análisis"
    app.session_state["resultado"] = {"resultados_por_id": {
        "a": {"id": "a", "tema_principal": "aprendizaje", "sentimiento": "positivo", "canal": "foro"},
        "b": {"id": "b", "tema_principal": "plataforma", "sentimiento": "negativo", "canal": "foro",
              "es_spam_detectado": True},
    }}
    app.run()
    assert not app.exception
    assert "Datos de las gráficas en texto" in [e.label for e in app.expander]
    textos = " ".join(m.value for m in app.markdown)
    assert "Sentimientos (sin spam) · 1 mensajes" in textos
    assert "Temas · 2 mensajes" in textos
    assert "positivo: 1 mensajes." in textos
