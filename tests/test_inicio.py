from pathlib import Path
from unittest.mock import Mock
import pytest

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
    assert "Datos" not in app.radio[0].options
    assert "catálogo de nueve" not in html
    assert "Tres formas de empezar" not in html
    assert app.button(key="inicio_catalogo").label == "Explorar el catálogo ↗"
    lector.assert_not_called()


def test_inicio_navega_a_ayuda_sin_perder_estado():
    app = _inicio()
    app.session_state["archivos_usuario"] = {"ejemplo.txt": {"texto": "prueba"}}
    app.button(key="inicio_ayuda").click().run()

    assert not app.exception
    assert app.radio[0].value == "Ayuda"
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
    assert app.radio[0].value == "Agente"
    assert app.session_state["navegacion_principal"] == "Agente"
    assert app.radio[0].key == f"selector_navegacion_{app.session_state['navegacion_revision']}"
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
    assert app.radio[0].value == "Ayuda"


def test_flecha_reaparece_al_volver_arriba_sin_descarte_permanente():
    from src.app.vista_inicio import ANIMACION

    assert "cue.classList.toggle('is-visible', main.scrollTop < 120)" in ANIMACION
    assert "localStorage" not in ANIMACION
    assert "clInicioCueDismissed" not in ANIMACION


def test_inclinaciones_sutiles_solo_en_escritorio_sin_movimiento_reducido():
    from src.app.vista_inicio import ESTILO

    assert "@media(min-width:801px) and (prefers-reduced-motion:no-preference)" in ESTILO
    assert ".cards .card:first-child { rotate: -0.8deg; }" in ESTILO
    assert ".cards .card:last-child { rotate: 0.8deg; }" in ESTILO
    assert "rotate: -0.7deg;" in ESTILO


def test_recorrido_entre_paginas_reutiliza_captura_y_no_pierde_chat(monkeypatch):
    from src.app import vista_plantillas_diarias

    lector = Mock(return_value={"registros": [{
        "id": "m1", "contenido_textual": "Aprendi SQL",
        "tema": "datos_ia", "tipo": "testimonio", "sentimiento": "positivo",
        "canal": "#datos", "fecha": None,
    }]})
    monkeypatch.setattr(fuente_agente, "leer_base", lector)
    monkeypatch.setattr(vista_plantillas_diarias, "leer_catalogo", Mock(return_value=None))
    app = _inicio()
    app.session_state["historial_agente"] = []
    for pagina in ("Agente", "Análisis", "Plantillas", "Ayuda", "Inicio", "Agente"):
        app.radio[0].set_value(pagina).run()
        assert not app.exception
        assert app.radio[0].value == pagina
        assert app.session_state["historial_agente"] == []
    lector.assert_called_once()


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


@pytest.mark.parametrize("boton", ["inicio_nav_agente", "inicio_abrir_agente", "inicio_footer_Agente"])
def test_accesos_inicio_sincronizan_header_y_siguiente_interaccion(monkeypatch, boton):
    monkeypatch.setattr(
        fuente_agente, "leer_base",
        Mock(side_effect=fuente_agente.FuenteNoDisponible(fuente_agente.NO_CONFIGURADA)),
    )
    app = _inicio()
    for _ in range(2):
        app.button(key=boton).click().run()
        assert not app.exception
        assert app.radio[0].value == "Agente"
        assert "navegacion_pendiente" not in app.session_state
        app.toggle(key="modo_verificacion").set_value(True).run()
        assert app.radio[0].value == "Agente"
        assert app.chat_input
        app.radio[0].set_value("Inicio").run()


@pytest.mark.parametrize("error", [
    "La publicación sigue conteniendo afirmaciones sin respaldo tras la corrección factual.",
    "La nueva propuesta sigue repitiendo el título o el contenido anterior.",
])
def test_borrador_rechazado_muestra_error_sin_acciones_de_publicacion(monkeypatch, error):
    from src.agentes.conversacion import AgenteConversacional
    from src.app import publicacion_redes

    monkeypatch.setattr(
        fuente_agente, "leer_base",
        Mock(side_effect=fuente_agente.FuenteNoDisponible(fuente_agente.NO_CONFIGURADA)),
    )
    monkeypatch.setattr(AgenteConversacional, "consultar", Mock(side_effect=ValueError(error)))
    publicar = Mock()
    monkeypatch.setattr(publicacion_redes, "render", publicar)
    app = _inicio()
    app.button(key="inicio_nav_agente").click().run()
    app.toggle(key="modo_verificacion").set_value(True).run()
    app.chat_input[0].set_value("Otra publicación").run()

    for _ in range(2):
        assert not app.exception
        assert error in [aviso.value for aviso in app.warning]
        assert app.session_state["historial_agente"][-1] == {
            "role": "assistant", "error": error,
        }
        publicar.assert_not_called()
        app.run()
