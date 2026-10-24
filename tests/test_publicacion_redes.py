from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from streamlit.testing.v1 import AppTest

from src.agentes.plataformas import NOMBRES_PLATAFORMA
from src.app.publicacion_redes import REDES, enlace_publicacion, texto_publicacion, validar_url


def publicacion(plataforma):
    return {
        "plataforma": plataforma,
        "titulo": "Una comunidad & sus ideas",
        "contenido": "¡Aprender juntos!\n¿Te sumas? #IA + 100%",
        "hashtags": ["#Comunidad", "#Aprendizaje", "#Datos"],
    }


@pytest.mark.parametrize("plataforma", ["linkedin", "instagram", "x"])
def test_contenido_completo_y_url_conservan_caracteres(plataforma):
    datos = publicacion(plataforma)
    texto = texto_publicacion(datos)
    assert datos["contenido"] in texto
    assert texto.endswith("#Comunidad #Aprendizaje #Datos")
    assert ("Una comunidad & sus ideas" in texto) is (plataforma != "x")
    url = urlparse(enlace_publicacion(datos))
    assert url.scheme == "https"
    if plataforma == "x":
        assert url.netloc == "twitter.com"
        assert url.path == "/intent/tweet"
        assert parse_qs(url.query) == {"text": [texto]}
    else:
        assert url.netloc in {"www.linkedin.com", "www.instagram.com"}
        assert not url.query


def test_no_se_recorta_texto_ni_se_inventa_una_red():
    datos = publicacion("x")
    datos["contenido"] = "x" * 400
    assert "x" * 400 in texto_publicacion(datos)
    with pytest.raises(ValueError, match="no es compatible"):
        enlace_publicacion(publicacion("https://ejemplo.com"))
    with pytest.raises(ValueError, match="necesita contenido"):
        texto_publicacion({"plataforma": "x", "contenido": ""})


@pytest.mark.parametrize("plataforma", list(REDES))
def test_ui_prepara_publicaciones_actuales_y_del_historial(plataforma):
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src" / "app" / "app_interna.py"),
        default_timeout=30,
    )
    datos = publicacion(plataforma)
    salida = {"respuesta": "Publicación preparada.", "borrador": datos, "citas": []}
    app.session_state["navegacion_principal"] = "Agente"
    app.session_state["resultado"] = {
        "resultados_por_id": {"m1": {"id": "m1", "texto": "Un mensaje"}},
    }
    app.session_state["historial_agente"] = [
        {"role": "assistant", "content": salida["respuesta"], "salida": salida},
        {"role": "assistant", "content": salida["respuesta"], "salida": salida},
    ]
    app.run()
    assert not app.exception
    assert len(app.code) == 2
    assert all(c.value == texto_publicacion(datos) for c in app.code)
    enlaces = app.get("link_button")
    assert len(enlaces) == (0 if plataforma == "mastodon" else 2)
    if plataforma != "mastodon":
        assert all(e.proto.url == enlace_publicacion(datos) for e in enlaces)
    if plataforma in {"facebook", "telegram", "mastodon"}:
        assert len(app.text_input) == 2
        assert len({campo.key for campo in app.text_input}) == 2
    assert any("Publicación preparada ·" in m.value for m in app.markdown)
    if plataforma == "instagram":
        assert any("imagen o video" in c.value for c in app.caption)


def test_ui_avisa_si_x_supera_limite_con_etiquetas():
    app = AppTest.from_string(
        "from src.app.publicacion_redes import render\n"
        "render({'plataforma':'x', 'contenido':'x'*275, 'hashtags':['#Comunidad']})"
    ).run()
    assert not app.exception
    assert any("supera 280" in w.value for w in app.warning)


@pytest.mark.parametrize(
    ("plataforma", "host", "ruta"),
    [
        ("threads", "www.threads.com", "/intent/post"),
        ("bluesky", "bsky.app", "/intent/compose"),
        ("whatsapp", "wa.me", "/"),
        ("mastodon", "comunidad.example", "/share"),
    ],
)
def test_nuevos_editores_precargan_texto_completo(plataforma, host, ruta):
    datos = publicacion(plataforma)
    url = urlparse(enlace_publicacion(datos, servidor="https://comunidad.example/"))
    assert (url.scheme, url.netloc, url.path) == ("https", host, ruta)
    assert parse_qs(url.query) == {"text": [texto_publicacion(datos)]}


@pytest.mark.parametrize("plataforma", ["facebook", "telegram"])
def test_compartir_enlace_no_inventa_url_ni_promete_precarga_de_facebook(plataforma):
    datos = publicacion(plataforma)
    enlace = "https://ejemplo.com/acción?q=IA&tipo=100%25#sección"
    url = urlparse(enlace_publicacion(datos, enlace=enlace))
    params = parse_qs(url.query)
    if plataforma == "facebook":
        assert url.netloc == "www.facebook.com"
        assert url.path == "/sharer/sharer.php"
        assert params == {"u": [enlace]}
    else:
        assert url.netloc == "t.me"
        assert url.path == "/share/url"
        assert params == {"url": [enlace], "text": [texto_publicacion(datos)]}
    assert not urlparse(enlace_publicacion(datos)).query


@pytest.mark.parametrize("valor", [
    "javascript:alert(1)", "https://", "https://user:secret@example.com",
    "https://example.com:bad", "https://exam ple.com", "https://example.com\n/test",
    "https://example.com\\@evil.com", "https://-example.com", "https://example.com:0",
])
def test_rechaza_enlaces_invalidos(valor):
    with pytest.raises(ValueError, match="enlace"):
        validar_url(valor)


@pytest.mark.parametrize("servidor", [
    "", "http://mastodon.social", "https://mastodon.social/@alguien",
    "https://mastodon.social?x=1", "https://mastodon.social/#perfil",
])
def test_mastodon_requiere_el_origen_https_del_usuario(servidor):
    with pytest.raises(ValueError, match="servidor"):
        enlace_publicacion(publicacion("mastodon"), servidor=servidor)


@pytest.mark.parametrize("plataforma", ["facebook", "telegram", "mastodon"])
def test_ui_parametros_independientes_y_errores_visibles(plataforma):
    app = AppTest.from_string(
        "from src.app.publicacion_redes import render\n"
        f"datos = {publicacion(plataforma)!r}\n"
        "render(datos, clave='primero')\n"
        "render(datos, clave='segundo')\n"
    ).run()
    assert not app.exception
    sufijo = "servidor" if plataforma == "mastodon" else "enlace"
    app.text_input(key=f"primero_{sufijo}").set_value("javascript:alert(1)").run()
    assert app.warning
    assert len(app.code) == 2
    assert len(app.get("link_button")) == (0 if plataforma == "mastodon" else 1)
    valor = "https://comunidad.example" if plataforma == "mastodon" else "https://ejemplo.com/post"
    app.text_input(key=f"primero_{sufijo}").set_value(valor).run()
    assert not app.exception
    assert not app.warning
    assert app.text_input(key=f"segundo_{sufijo}").value == ""
    argumentos = {sufijo: valor}
    assert app.get("link_button")[0].proto.url == enlace_publicacion(
        publicacion(plataforma), **argumentos,
    )


@pytest.mark.parametrize(("plataforma", "limite"), [("threads", 500), ("bluesky", 300)])
def test_avisa_sin_recortar_al_superar_el_limite(plataforma, limite):
    datos = publicacion(plataforma)
    datos["contenido"] = "a" * limite
    app = AppTest.from_string(
        "from src.app.publicacion_redes import render\n"
        f"render({datos!r})"
    ).run()
    assert not app.exception
    assert any(f"supera {limite}" in w.value for w in app.warning)
    assert app.code[0].value == texto_publicacion(datos)
    assert parse_qs(urlparse(app.get("link_button")[0].proto.url).query)["text"] == [
        texto_publicacion(datos),
    ]


def test_destinos_coinciden_y_multimedia_sigue_pendiente():
    assert REDES.keys() == NOMBRES_PLATAFORMA.keys()
    for plataforma in ("tiktok", "youtube"):
        with pytest.raises(ValueError, match="no es compatible"):
            enlace_publicacion(publicacion(plataforma))


@pytest.mark.parametrize(("plataforma", "limite"), [("x", 280), ("threads", 500), ("bluesky", 300)])
@pytest.mark.parametrize("exceso", [0, 1])
def test_umbral_incluye_titulo_etiquetas_y_separadores(plataforma, limite, exceso):
    datos = publicacion(plataforma)
    datos["contenido"] = "a"
    resto = len(texto_publicacion(datos)) - 1
    datos["contenido"] = "a" * (limite - resto + exceso)
    assert len(texto_publicacion(datos)) == limite + exceso
    app = AppTest.from_string(
        "from src.app.publicacion_redes import render\n"
        f"render({datos!r})"
    ).run()
    assert not app.exception
    assert bool(app.warning) is bool(exceso)
    assert app.code[0].value == texto_publicacion(datos)
