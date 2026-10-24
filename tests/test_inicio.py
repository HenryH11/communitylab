from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from src.app import fuente_agente


RAIZ = Path(__file__).resolve().parents[1]


def _inicio():
    app = AppTest.from_file(str(RAIZ / "src/app/app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    return app


def test_inicio_muestra_recorrido_ejemplos_y_footer_sin_consultar_base(monkeypatch):
    lector = Mock(side_effect=AssertionError("Inicio no debe consultar la base"))
    monkeypatch.setattr(fuente_agente, "leer_base", lector)
    app = _inicio()

    html = " ".join(elemento.proto.body for elemento in app.get("html"))
    for texto in (
        "De lo que se dice.", "Conversación ilustrativa", "Datos de ejemplo",
        "01 / Comprender", "02 / Crear", "03 / Ampliar", "04 / Decidir",
        "Todos los derechos reservados.", "prefers-reduced-motion",
    ):
        assert texto in html
    assert [e.label for e in app.expander] == ["Contacto", "Sobre tus datos"]
    assert "Datos" not in app.radio(key="navegacion_principal").options
    assert "catálogo de nueve" not in html
    assert "Tres formas de empezar" not in html
    assert app.button(key="inicio_catalogo").label == "Explorar el catálogo ↗"
    lector.assert_not_called()


def test_inicio_navega_a_ayuda_sin_perder_estado():
    app = _inicio()
    app.session_state["archivos_usuario"] = {"ejemplo.txt": {"texto": "prueba"}}
    app.button(key="inicio_ayuda").click().run()

    assert not app.exception
    assert app.radio(key="navegacion_principal").value == "Ayuda"
    assert app.session_state["archivos_usuario"] == {
        "ejemplo.txt": {"texto": "prueba"}
    }


def test_inicio_abre_agente_con_navegacion_real(monkeypatch):
    monkeypatch.setattr(
        fuente_agente, "leer_base",
        Mock(side_effect=fuente_agente.FuenteNoDisponible(fuente_agente.NO_CONFIGURADA)),
    )
    app = _inicio()
    app.button(key="inicio_nav_agente").click().run()

    assert not app.exception
    assert app.radio(key="navegacion_principal").value == "Agente"
    assert app.chat_input
    textos = " ".join(elemento.value for elemento in app.markdown)
    assert "Bienvenido. ¿Qué te gustaría descubrir hoy?" in textos
    assert "El archivo aún está vacío" not in textos


def test_inicio_footer_usa_enlaces_discretos_y_portada_con_guia():
    app = _inicio()
    html = " ".join(elemento.proto.body for elemento in app.get("html"))
    html += " ".join(elemento.value for elemento in app.markdown)
    html += " ".join(elemento.value for elemento in app.markdown)
    assert 'class="scroll-cue"' in html
    assert 'class="scroll-cue" aria-hidden="true"' in html
    assert 'href="#inicio-recorrido"' not in html
    assert 'id="inicio-recorrido"' in html
    assert "<small>" not in html
    assert "Fragmentos ilustrativos." not in html
    for pagina in ("Agente", "Análisis", "Plantillas", "Ayuda"):
        assert app.button(key=f"inicio_footer_{pagina}").proto.type == "tertiary"
    app.button(key="inicio_footer_Ayuda").click().run()
    assert not app.exception
    assert app.radio(key="navegacion_principal").value == "Ayuda"


def test_ajustes_actuales_se_aplican_a_la_siguiente_pregunta(monkeypatch):
    from src.agentes.conversacion import AgenteConversacional

    monkeypatch.setattr(
        fuente_agente, "leer_base",
        Mock(side_effect=fuente_agente.FuenteNoDisponible(fuente_agente.NO_CONFIGURADA)),
    )
    consulta = Mock(return_value={
        "respuesta": "Hola, seguimos conversando.",
        "modo": "conversacion",
        "citas": [],
    })
    monkeypatch.setattr(AgenteConversacional, "consultar", consulta)
    app = _inicio()
    app.button(key="inicio_nav_agente").click().run()
    app.radio(key="agente_ajuste").set_value("Manual").run()
    app.number_input(key="agente_temperatura").set_value(0.65).run()
    app.selectbox(key="agente_modelo").set_value("lightning").run()
    app.toggle(key="modo_verificacion").set_value(True).run()
    app.chat_input[0].set_value("Hola").run()

    assert not app.exception
    consulta.assert_called_once_with(
        "Hola", modo_verificacion="verificacion_automatica",
        temperatura=0.65, top_p=0.9, modelo_respuesta="lightning",
    )
