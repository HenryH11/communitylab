from urllib.parse import unquote
from xml.etree import ElementTree

from src.app import estilo_agente, tema


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
