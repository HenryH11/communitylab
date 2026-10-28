from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from src.app import fuente_agente


PANEL = """
import streamlit as st
from src.app.fuentes_citadas import render

fuentes = {
    f"m-{i}": {
        "id": f"m-{i}", "autor": f"Persona {i}", "canal": "Discord",
        "texto": f"Contenido exclusivo {i}. " + "Texto largo. " * 100,
    }
    for i in range(1200)
}
render({"citas": list(fuentes)}, fuentes, clave="respuesta")
"""


def test_1200_referencias_muestran_solo_10_y_conservan_la_ultima_pagina():
    app = AppTest.from_string(PANEL).run()
    assert not app.exception
    assert len(app.expander) == 10
    assert app.expander[0].label.startswith("m-0 ·")
    assert app.expander[-1].label.startswith("m-9 ·")
    assert app.number_input(key="respuesta_pagina").max == 120
    assert any("1200 fuentes citadas" in c.value for c in app.caption)
    assert all(len(texto.value) <= 183 for texto in app.text)

    app.number_input(key="respuesta_pagina").set_value(120).run()
    assert not app.exception
    assert len(app.expander) == 10
    assert app.expander[0].label.startswith("m-1190 ·")
    assert app.expander[-1].label.startswith("m-1199 ·")
    assert any("1191–1200 de 1200" in c.value for c in app.caption)


def test_busqueda_por_id_autor_canal_o_texto_reinicia_la_pagina():
    app = AppTest.from_string(PANEL).run()
    for consulta in ("m-1199", "Persona 1199", "Contenido exclusivo 1199."):
        app.number_input(key="respuesta_pagina").set_value(120).run()
        app.text_input(key="respuesta_busqueda").set_value(consulta).run()
        assert not app.exception
        assert app.number_input(key="respuesta_pagina").value == 1
        assert len(app.expander) == 1
        assert app.expander[0].label.startswith("m-1199 ·")
        app.text_input(key="respuesta_busqueda").set_value("").run()
    app.text_input(key="respuesta_busqueda").set_value("dIsCoRd").run()
    assert len(app.expander) == 10
    assert app.number_input(key="respuesta_pagina").max == 120


def test_sin_coincidencias_no_muestra_fuentes_ajenas():
    app = AppTest.from_string(PANEL).run()
    app.text_input(key="respuesta_busqueda").set_value("no-existe").run()
    assert not app.exception
    assert not app.expander
    assert not app.number_input
    assert "No hay fuentes citadas" in app.info[0].value


def test_texto_completo_solo_se_renderiza_cuando_se_solicita():
    app = AppTest.from_string(PANEL).run()
    assert all(len(texto.value) <= 183 for texto in app.text)
    app.toggle(key="respuesta_texto_m-0").set_value(True).run()
    assert not app.exception
    completos = [texto.value for texto in app.text if len(texto.value) > 183]
    assert completos == [("Contenido exclusivo 0. " + "Texto largo. " * 100).rstrip()]


def test_referencias_repetidas_ausentes_y_metadatos_nulos():
    app = AppTest.from_string("""
from src.app.fuentes_citadas import render
render(
    {"citas": ["a", "a", "ausente"]},
    {"a": {"autor": None, "canal": None, "texto": "Mensaje conservado"}},
    clave="nulos",
)
""").run()
    assert not app.exception
    assert len(app.expander) == 1
    assert "Autor desconocido" in app.expander[0].label
    assert "2 fuentes citadas" in app.caption[0].value
    assert any("respuesta antigua" in aviso.value for aviso in app.warning)
    assert any("fuente ausente no está disponible" in aviso.value for aviso in app.warning)


def test_copia_conserva_solo_fuentes_citadas_y_no_comparte_objetos():
    from src.app.fuentes_citadas import conservar_fuentes

    fuentes = {c: {"texto": f"Texto {c}", "metadatos": {"valor": "original"}} for c in "abcd"}
    salida = {
        "citas": ["a", "a"],
        "hallazgos": [{"citas": ["b"]}],
        "verificacion": {"afirmaciones": [{"citas": ["c", "ausente"]}]},
        "grupos_preguntas": [{"citas": ["b"]}],
    }
    conservar_fuentes(salida, fuentes)
    fuentes["a"]["texto"] = "Editado"
    fuentes["b"]["metadatos"]["valor"] = "Editado"
    fuentes.clear()
    assert set(salida["fuentes_citadas"]) == {"a", "b", "c"}
    assert salida["fuentes_citadas"]["a"]["texto"] == "Texto a"
    assert salida["fuentes_citadas"]["b"]["metadatos"]["valor"] == "original"


def test_1200_fuentes_repetidas_en_30_respuestas_se_copian_solo_una_vez():
    from src.app.fuentes_citadas import conservar_fuentes

    fuentes = {str(i): {"id": str(i), "texto": "Texto completo " * 100} for i in range(1200)}
    almacen = {}
    salidas: list[dict] = [{"citas": list(fuentes)} for _ in range(30)]
    for salida in salidas:
        conservar_fuentes(salida, fuentes, almacen=almacen)
    assert len(almacen) == 1200
    assert sum(len(versiones) for versiones in almacen.values()) == 1200
    assert len({
        id(fuente) for salida in salidas for fuente in salida["fuentes_citadas"].values()
    }) == 1200
    assert salidas[0]["fuentes_citadas"]["0"] is not fuentes["0"]
    fuentes["0"]["texto"] = "Una versión nueva"
    nueva: dict = {"citas": ["0"]}
    conservar_fuentes(nueva, fuentes, almacen=almacen)
    assert len(almacen["0"]) == 2
    assert salidas[0]["fuentes_citadas"]["0"]["texto"] != nueva["fuentes_citadas"]["0"]["texto"]


def test_cambios_solo_en_metadatos_conservan_version_y_orden_de_claves_no_duplica():
    from src.app.fuentes_citadas import conservar_fuentes

    almacen = {}
    primera: dict = {"citas": ["a"]}
    igual: dict = {"citas": ["a"]}
    distinta: dict = {"citas": ["a"]}
    conservar_fuentes(primera, {"a": {"texto": "Igual", "autor": "Ana"}}, almacen=almacen)
    conservar_fuentes(igual, {"a": {"autor": "Ana", "texto": "Igual"}}, almacen=almacen)
    conservar_fuentes(distinta, {"a": {"texto": "Igual", "autor": "Bea"}}, almacen=almacen)
    assert primera["fuentes_citadas"]["a"] is igual["fuentes_citadas"]["a"]
    assert primera["fuentes_citadas"]["a"] is not distinta["fuentes_citadas"]["a"]
    assert len(almacen["a"]) == 2


def test_panel_no_sustituye_fuentes_historicas_por_datos_actuales():
    app = AppTest.from_string("""
from src.app.fuentes_citadas import render
render(
    {"citas": ["a", "ausente"], "fuentes_citadas": {
        "a": {"texto": "Texto original completo", "autor": "Autora original", "canal": "Discord"},
    }},
    {"a": {"texto": "Texto modificado", "autor": "Otro autor"},
     "ausente": {"texto": "Fuente nueva con ID reutilizado"}},
    clave="historica",
)
""").run()
    assert not app.exception
    assert "Autora original" in app.expander[0].label
    assert app.text[0].value == "Texto original completo"
    assert any("fuente ausente no se conservó" in a.value for a in app.warning)
    assert not any("respuesta antigua" in a.value for a in app.warning)


def test_respuesta_sin_citas_y_paneles_independientes():
    app = AppTest.from_string("""
from src.app.fuentes_citadas import render
render({"citas": []}, {}, clave="vacio")
fuentes = {str(i): {"texto": "Mensaje", "autor": "Ana"} for i in range(21)}
render({"citas": list(fuentes)}, fuentes, clave="uno")
render({"citas": list(fuentes)}, fuentes, clave="dos")
""").run()
    assert not app.exception
    assert "no incluye fuentes" in app.caption[0].value
    app.number_input(key="uno_pagina").set_value(3).run()
    assert not app.exception
    assert app.number_input(key="uno_pagina").value == 3
    assert app.number_input(key="dos_pagina").value == 1
    assert len(app.expander) == 11


def test_filtrar_afirmacion_o_duda_conserva_todas_sus_referencias():
    app = AppTest.from_string("""
from src.app.fuentes_citadas import render
fuentes = {str(i): {"texto": "Mensaje", "autor": "Ana"} for i in range(25)}
render(
    {
        "citas": ["0"],
        "verificacion": {"afirmaciones": [
            {"afirmacion": "Un hallazgo", "citas": [str(i) for i in range(22)]},
        ]},
        "grupos_preguntas": [{"duda": "Una pregunta", "citas": ["24"]}],
    },
    fuentes,
    clave="grupos",
)
""").run()
    assert not app.exception
    assert "23 fuentes citadas" in app.caption[0].value
    app.number_input(key="grupos_pagina").set_value(3).run()
    app.selectbox(key="grupos_grupo").select("Afirmación: Un hallazgo").run()
    assert not app.exception
    assert app.number_input(key="grupos_pagina").value == 1
    app.number_input(key="grupos_pagina").set_value(3).run()
    assert len(app.expander) == 2
    assert app.expander[-1].label.startswith("21 ·")
    app.selectbox(key="grupos_grupo").select("Duda: Una pregunta").run()
    assert not app.exception
    assert len(app.expander) == 1
    assert app.expander[0].label.startswith("24 ·")


def test_explorador_filtra_las_fuentes_exactas_del_hallazgo():
    app = AppTest.from_string("""
from src.app.fuentes_citadas import render
render(
    {"citas": ["a", "b"], "hallazgos": [
        {"afirmacion": "Hecho A", "citas": ["a"]},
        {"afirmacion": "Hecho B", "citas": ["b"]},
    ]},
    {"a": {"texto": "Fuente A"}, "b": {"texto": "Fuente B"}},
    clave="hechos",
)
""").run()
    app.selectbox(key="hechos_grupo").select("Hallazgo: Hecho B").run()
    assert not app.exception
    assert len(app.expander) == 1
    assert app.expander[0].label.startswith("b ·")


def test_chat_integra_paginacion_sin_volver_a_consultar_al_modelo(monkeypatch):
    from pathlib import Path
    from src.agentes.conversacion import AgenteConversacional

    registros = [
        {"id": f"m-{i}", "autor": f"Persona {i}", "canal": "Discord",
         "contenido_textual": f"Mensaje {i}", "fecha": None, "sentimiento": "positivo",
         "tema": "aprendizaje", "tipo": "comentario"}
        for i in range(21)
    ]
    monkeypatch.setattr(fuente_agente, "leer_base", lambda: {
        "version": "1.2", "registros": registros, "total": len(registros),
    })
    consultar = Mock(side_effect=AssertionError("Paginar no debe generar otra respuesta"))
    monkeypatch.setattr(AgenteConversacional, "consultar", consultar)
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src" / "app" / "app.py"),
        default_timeout=30,
    )
    app.session_state["navegacion_principal"] = "Agente"
    app.session_state["historial_agente"] = [{
        "role": "assistant", "content": "Respuesta guardada.",
        "salida": {"respuesta": "Respuesta guardada.", "citas": [r["id"] for r in registros]},
    }]
    app.run()
    assert not app.exception
    app.number_input(key="turno_0_fuentes_pagina").set_value(3).run()
    assert not app.exception
    assert any(e.label.startswith("m-20 ·") for e in app.expander)
    assert len(app.session_state["historial_agente"]) == 1
    consultar.assert_not_called()


def test_chat_guarda_fuentes_del_turno_aunque_despues_se_editen_o_desaparezcan(monkeypatch):
    from pathlib import Path
    from src.agentes.conversacion import AgenteConversacional

    mensajes = [{"id": "a", "texto": "Texto al responder", "autor": "Ana"}]
    monkeypatch.setattr(fuente_agente, "leer_base", lambda: {
        "version": "1.2", "registros": [], "total": 0,
    })
    monkeypatch.setattr(fuente_agente, "combinar", lambda *_: mensajes)
    consultar = Mock(return_value={
        "respuesta": "Respuesta guardada.", "citas": ["a"],
        "hallazgos": [{"afirmacion": "Un hecho", "citas": ["a"]}],
    })
    monkeypatch.setattr(AgenteConversacional, "consultar", consultar)
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src" / "app" / "app.py"),
        default_timeout=30,
    )
    app.session_state["navegacion_principal"] = "Agente"
    app.run()
    app.chat_input[0].set_value("Resume").run()
    assert not app.exception
    guardada = app.session_state["historial_agente"][-1]["salida"]["fuentes_citadas"]["a"]
    assert guardada["texto"] == "Texto al responder"
    mensajes[0].update(texto="Texto nuevo", autor="Otro autor")
    app.run()
    assert not app.exception
    assert any("Ana" in e.label for e in app.expander)
    assert any(t.value == "Texto al responder" for t in app.text)
    mensajes.clear()
    app.run()
    assert not app.exception
    assert any(t.value == "Texto al responder" for t in app.text)
    assert not any("no está disponible" in a.value for a in app.warning)
    assert consultar.call_count == 1


def test_historial_pagina_10_turnos_con_errores_migra_fuentes_y_vuelve_a_recientes(monkeypatch):
    from pathlib import Path
    from src.agentes.conversacion import AgenteConversacional

    monkeypatch.setattr(fuente_agente, "leer_base", lambda: {
        "version": "1.2", "registros": [], "total": 0,
    })
    consultar = Mock(return_value={"respuesta": "Respuesta nueva", "citas": []})
    monkeypatch.setattr(AgenteConversacional, "consultar", consultar)
    historial = []
    for i in range(25):
        historial.extend([
            {"role": "user", "content": f"Pregunta {i}"},
            {"role": "assistant", "content": f"Respuesta {i}", "salida": {
                "citas": ["a"], "fuentes_citadas": {
                    "a": {"texto": "Texto histórico", "autor": "Ana"},
                },
            }},
        ])
    historial[45] = {"role": "assistant", "error": "Fallo del turno 22"}
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src" / "app" / "app.py"),
        default_timeout=30,
    )
    app.session_state["navegacion_principal"] = "Agente"
    app.session_state["historial_agente"] = historial
    app.run()
    assert not app.exception
    assert len(app.chat_message) == 20
    assert app.number_input(key="pagina_historial_agente").max == 3
    assert any("Turnos 16–25 de 25" in c.value for c in app.caption)
    assert any(a.value == "Fallo del turno 22" for a in app.warning)
    almacen = app.session_state["fuentes_agente_versionadas"]
    assert len(almacen["a"]) == 1
    guardado = app.session_state["historial_agente"]
    assert guardado[1]["salida"]["fuentes_citadas"]["a"] is guardado[3]["salida"]["fuentes_citadas"]["a"]
    app.number_input(key="pagina_historial_agente").set_value(3).run()
    assert not app.exception
    assert len(app.chat_message) == 10
    assert any("Turnos 1–5 de 25" in c.value for c in app.caption)
    assert any(e.label.startswith("a · Ana") for e in app.expander)
    assert any(m.value == "Pregunta 0" for m in app.markdown)
    assert not any(m.value == "Pregunta 24" for m in app.markdown)
    assert len(app.session_state["historial_agente"]) == 50
    consultar.assert_not_called()
    app.chat_input[0].set_value("Nueva consulta desde página antigua").run()
    assert not app.exception
    assert app.number_input(key="pagina_historial_agente").value == 1
    assert len(app.chat_message) == 20
    assert any("Turnos 17–26 de 26" in c.value for c in app.caption)
    assert len(app.session_state["historial_agente"]) == 52
    assert consultar.call_count == 1
    app.run()
    assert not app.exception
    assert len(app.chat_message) == 20


def test_chat_muestra_revision_analitica_obligatoria_aunque_selector_este_desactivado(monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(fuente_agente, "leer_base", lambda: {
        "version": "1.2", "registros": [], "total": 0,
    })
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src" / "app" / "app.py"),
        default_timeout=30,
    )
    app.session_state["navegacion_principal"] = "Agente"
    app.session_state["historial_agente"] = [{
        "role": "assistant", "content": "Hay cero mensajes.",
        "modo_verificacion": "prompt_estricto",
        "salida": {
            "respuesta": "Hay cero mensajes.", "citas": [],
            "verificacion": {
                "estado": "verificado", "obligatoria": True,
                "resumen": "El conteo coincide con los agregados.",
                "afirmaciones": [{
                    "afirmacion": "Hay cero mensajes.", "respaldada": True,
                    "citas": [], "respaldo_agregado": True,
                }],
            },
        },
    }]
    app.run()
    assert not app.exception
    assert any(e.label == "Verificación y fuentes" for e in app.expander)
    assert any("Estado: verificado" in c.value for c in app.caption)
    assert any("agregados calculados" in c.value for c in app.caption)
