from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.app import fuente_agente
from src.app.vista_analiticas import distribucion, filtrar


def captura(**cambios):
    return fuente_agente.Captura(
        mensajes=(
            {"id": "a", "canal": "#datos", "tema_principal": "datos_ia",
             "sentimiento": "positivo", "tipo_detectado": "testimonio"},
            {"id": "b", "canal": "#datos", "tema_principal": "datos_ia",
             "sentimiento": "neutral", "tipo_detectado": "pregunta_tecnica"},
            {"id": "c", "canal": "", "tema_principal": "",
             "sentimiento": "", "tipo_detectado": ""},
        ),
        capturada_en=datetime(2026, 10, 25, 19, tzinfo=timezone.utc),
        **cambios,
    )


def app():
    return AppTest.from_string(
        "from src.app.vista_analiticas import render\nrender()", default_timeout=15,
    )


def test_distribuciones_exactas_con_ausencias():
    for campo in ("canal", "tema_principal", "sentimiento", "tipo_detectado"):
        tabla = distribucion(captura().mensajes, campo)
        assert tabla["Mensajes"].sum() == 3
        assert "Sin clasificar" in tabla["Categoria"].tolist()
    assert distribucion(captura().mensajes, "canal").to_dict("records") == [
        {"Categoria": "#datos", "Mensajes": 2},
        {"Categoria": "Sin clasificar", "Mensajes": 1},
    ]


def test_pantalla_oracle_muestra_conteos_y_actualiza_sin_ia():
    with patch.object(fuente_agente, "obtener_captura", return_value=captura()) as leer:
        pantalla = app().run()
        assert not pantalla.exception
        assert [m.value for m in pantalla.metric] == ["3", "1", "1"]
        assert len(pantalla.dataframe) == 6
        assert not pantalla.error
        assert not any("IA" in c.value or "elegibilidad" in c.value for c in pantalla.caption)
        assert leer.call_args.kwargs["forzar"] is False
        pantalla.button[0].click().run()
        assert leer.call_args.kwargs["forzar"] is True
        assert not pantalla.exception


def test_error_de_conexion_no_se_disfraza_de_cero():
    with patch.object(fuente_agente, "obtener_captura",
                      side_effect=fuente_agente.FuenteNoDisponible("Sin conexion")):
        pantalla = app().run()
    assert not pantalla.exception
    assert pantalla.error[0].value == "Sin conexion"
    assert not pantalla.metric


def test_captura_anterior_se_marca_desactualizada():
    with patch.object(fuente_agente, "obtener_captura",
                      return_value=captura(desactualizada=True, aviso="Lectura fallida")):
        pantalla = app().run()
    assert not pantalla.exception
    assert pantalla.warning[0].value == "Lectura fallida"
    assert pantalla.metric[0].value == "3"


def test_base_vacia_no_inventa_metricas():
    vacia = fuente_agente.Captura((), datetime.now(timezone.utc))
    with patch.object(fuente_agente, "obtener_captura", return_value=vacia):
        pantalla = app().run()
    assert not pantalla.exception
    assert pantalla.info
    assert not pantalla.metric


def test_navegacion_publica_analisis_usa_oracle_sin_procesar_lote():
    ruta = Path(__file__).resolve().parents[1] / "src" / "app" / "app.py"
    with (
        patch.object(fuente_agente, "obtener_captura", return_value=captura()),
        patch("src.app.interfaz.procesar_paquete_entrega") as procesar,
    ):
        pantalla = AppTest.from_file(str(ruta), default_timeout=30)
        pantalla.session_state["navegacion_principal"] = "Análisis"
        pantalla.run()
    assert not pantalla.exception
    assert pantalla.metric[0].value == "3"
    assert len(pantalla.dataframe) == 6
    procesar.assert_not_called()


def test_filtros_interseccion_y_busqueda_por_id():
    mensajes = captura().mensajes
    assert len(filtrar(mensajes, {"canal": ["#datos"], "sentimiento": ["positivo"]})) == 1
    assert filtrar(mensajes, {}, "b")[0]["id"] == "b"
    assert len(filtrar(mensajes, {"canal": ["Sin clasificar"]})) == 1
    assert filtrar(mensajes, {}, "no-existe") == ()


def test_filtros_ui_recalculan_denominador_y_fuentes():
    with patch.object(fuente_agente, "obtener_captura", return_value=captura()):
        pantalla = app().run()
        pantalla.multiselect[1].select("positivo").run()
        assert not pantalla.exception
        assert pantalla.metric[0].value == "1"
        assert pantalla.dataframe[0].value["Porcentaje"].tolist() == [100.0]
        assert pantalla.dataframe[-1].value["id"].tolist() == ["a"]
        pantalla.text_input[0].set_value("no-existe").run()
        assert not pantalla.exception
        assert pantalla.info
        assert not pantalla.metric
