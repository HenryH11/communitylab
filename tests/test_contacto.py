from streamlit.testing.v1 import AppTest


def pantalla():
    return AppTest.from_string(
        "from src.app.contacto import render\nrender()", default_timeout=15,
    ).run()


def test_no_anuncia_buzon_no_creado(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_CONTACTO_EMAIL", raising=False)
    app = pantalla()
    assert not app.exception
    assert not app.get("link_button")
    assert "pendiente" in app.markdown[0].value


def test_contacto_activo_abre_cliente_sin_enviar_correo(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_CONTACTO_EMAIL", "contacto@communitylab.lat")
    app = pantalla()
    assert not app.exception
    assert app.get("link_button")[0].proto.url.startswith("mailto:contacto@communitylab.lat?")


def test_correo_invalido_no_crea_enlace(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_CONTACTO_EMAIL", "correo\r\nBcc:otro@example.com")
    app = pantalla()
    assert not app.exception
    assert app.error
    assert not app.get("link_button")
