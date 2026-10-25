"""Fuente del agente: captura de la base simulada, archivos del usuario y UI pública."""

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.agentes.conversacion import AgenteConversacional
from src.app import fuente_agente as fuente
from src.app.fuente_agente import (
    CLAVE_CAPTURA,
    ESPERA_REINTENTO,
    VIGENCIA_CAPTURA,
    Captura,
    FuenteNoDisponible,
    adaptar_conjunto,
    combinar,
    leer_archivo_usuario,
    obtener_captura,
)

INICIO = datetime(2026, 5, 1, 12, tzinfo=timezone.utc)


def instantanea(*textos):
    return {
        "version": "1.1",
        "total": len(textos),
        "registros": [
            {
                "id": f"m{numero}",
                "canal": "discord",
                "sentimiento": "positivo",
                "tema": "eventos",
                "tipo": "testimonio",
                "contenido_textual": texto,
                "fecha": INICIO,
            }
            for numero, texto in enumerate(textos, start=1)
        ],
    }


class BaseSimulada:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.lecturas = 0

    def __call__(self):
        self.lecturas += 1
        respuesta = self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def test_adaptar_conjunto_mapea_campos_y_omite_vacios():
    documento = instantanea("Gran meetup", "  ")
    documento["registros"].append(dict(documento["registros"][0]))

    mensajes = adaptar_conjunto(documento)

    assert mensajes == [
        {
            "id": "m1",
            "texto": "Gran meetup",
            "canal": "discord",
            "sentimiento": "positivo",
            "tema_principal": "eventos",
            "tipo_detectado": "testimonio",
            "fecha": "2026-05-01T12:00:00Z",
        }
    ]


def test_captura_se_reutiliza_durante_una_hora_y_luego_se_renueva():
    estado, base = {}, BaseSimulada(instantanea("uno"), instantanea("uno", "dos"))

    primera = obtener_captura(estado, lector=base, ahora=INICIO)
    misma = obtener_captura(
        estado, lector=base, ahora=INICIO + VIGENCIA_CAPTURA - timedelta(seconds=1)
    )
    renovada = obtener_captura(estado, lector=base, ahora=INICIO + VIGENCIA_CAPTURA)

    assert misma is primera
    assert base.lecturas == 2
    assert len(renovada.mensajes) == 2
    assert renovada.capturada_en == INICIO + VIGENCIA_CAPTURA


def test_si_la_base_falla_se_usa_la_captura_previa_sin_reintentar_en_cada_clic():
    estado = {}
    base = BaseSimulada(instantanea("uno"), FuenteNoDisponible(fuente.SIN_CONEXION))
    obtener_captura(estado, lector=base, ahora=INICIO)
    vencida = INICIO + VIGENCIA_CAPTURA

    antigua = obtener_captura(estado, lector=base, ahora=vencida)
    otra_vez = obtener_captura(estado, lector=base, ahora=vencida + timedelta(seconds=30))

    assert antigua.desactualizada and otra_vez.desactualizada
    assert antigua.aviso == fuente.SIN_CONEXION
    assert antigua.capturada_en == INICIO
    assert base.lecturas == 2

    obtener_captura(estado, lector=base, ahora=vencida + ESPERA_REINTENTO)
    assert base.lecturas == 3


def test_sin_captura_previa_el_error_es_amigable_y_se_recuerda():
    estado, base = {}, BaseSimulada(RuntimeError("ORA-12541: TNS no listener"))

    with pytest.raises(FuenteNoDisponible) as error:
        obtener_captura(estado, lector=base, ahora=INICIO)
    with pytest.raises(FuenteNoDisponible):
        obtener_captura(estado, lector=base, ahora=INICIO + timedelta(seconds=10))

    assert str(error.value) == fuente.SIN_CONEXION
    assert "ORA" not in str(error.value)
    assert base.lecturas == 1


def test_instantanea_invalida_se_explica_como_actualizacion():
    with pytest.raises(FuenteNoDisponible, match="actualizando"):
        obtener_captura({}, lector=lambda: {"registros": None}, ahora=INICIO)


@pytest.mark.skipif(
    importlib.util.find_spec("oracledb") is None or importlib.util.find_spec("oci") is None,
    reason="Requiere el cliente de base de datos",
)
@pytest.mark.parametrize(
    ("conexion", "lectura", "esperado"),
    [
        (ValueError("configura un DB_READ_USER distinto"), None, fuente.NO_CONFIGURADA),
        (OSError("timeout"), None, fuente.SIN_CONEXION),
        (None, ValueError("no hay una instantánea publicada con metadatos"), fuente.SIN_PUBLICAR),
        (None, ValueError("la tabla no coincide con el total"), fuente.EN_ACTUALIZACION),
    ],
)
def test_leer_base_traduce_fallos_sin_mencionar_configuracion(
    monkeypatch, conexion, lectura, esperado
):
    from src.config import db_client

    class Conexion:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def abrir():
        if conexion is not None:
            raise conexion
        return Conexion()

    def leer(**_):
        raise lectura

    monkeypatch.setattr(db_client, "obtener_conexion_lectura", abrir)
    monkeypatch.setattr(db_client, "leer_conjunto", leer)

    with pytest.raises(FuenteNoDisponible) as error:
        fuente.leer_base()

    assert str(error.value) == esperado
    assert "DB_" not in str(error.value)


def test_json_sin_estructura_fija_detecta_columna_de_texto_y_metadatos():
    contenido = json.dumps(
        {"comentarios": [
            {"Comment": "Me encantó el taller", "User": "ana", "Platform": "X"},
            {"Comment": "", "User": "luis"},
        ]}
    ).encode()

    mensajes = leer_archivo_usuario("Encuesta Mayo.json", contenido)

    assert mensajes == [
        {"texto": "Me encantó el taller", "autor": "ana", "canal": "X", "id": "encuesta-mayo-1"}
    ]


def test_json_con_lotes_y_lista_de_textos():
    lotes = {"lotes": [{"interacciones": [{"texto": "hola"}]}, {"interacciones": [{"texto": "chao"}]}]}

    assert [m["texto"] for m in leer_archivo_usuario("a.json", json.dumps(lotes).encode())] == [
        "hola",
        "chao",
    ]
    assert leer_archivo_usuario("b.json", b'["uno", " ", "dos"]')[1] == {"texto": "dos", "id": "b-2"}


def test_csv_con_punto_y_coma_y_columna_desconocida_usa_la_mas_larga():
    contenido = "codigo;opinion\n1;El evento fue muy útil para mi equipo\n2;Faltó café\n".encode(
        "utf-8-sig"
    )

    mensajes = leer_archivo_usuario("notas.csv", contenido)

    assert [m["texto"] for m in mensajes] == ["El evento fue muy útil para mi equipo", "Faltó café"]


def test_txt_un_mensaje_por_linea():
    mensajes = leer_archivo_usuario("chat.txt", "uno\n\n dos \n".encode("cp1252"))

    assert mensajes == [{"texto": "uno", "id": "chat-1"}, {"texto": "dos", "id": "chat-2"}]


@pytest.mark.parametrize(
    ("nombre", "contenido", "motivo"),
    [
        ("hoja.xlsx", b"x", "JSON, CSV o TXT"),
        ("roto.json", b"{", "no es un JSON"),
        ("vacio.txt", b"  \n ", "No encontré mensajes"),
        ("grande.txt", b"a" * (fuente.MAX_BYTES_ARCHIVO + 1), "5 MB"),
    ],
    ids=["formato", "json-roto", "vacio", "grande"],
)
def test_archivos_no_validos_se_explican(nombre, contenido, motivo):
    with pytest.raises(ValueError, match=motivo):
        leer_archivo_usuario(nombre, contenido)


def test_combinar_evita_colisiones_de_ids():
    base = [{"id": "notas-1", "texto": "base"}]
    archivos = {
        "notas.txt": [{"id": "notas-1", "texto": "a"}],
        "Notas.csv": [{"id": "notas-1", "texto": "b"}],
    }

    assert [m["id"] for m in combinar(base, archivos)] == ["notas-1", "notas-1-2", "notas-1-3"]


def test_actualizar_datos_conserva_la_conversacion():
    agente = AgenteConversacional([{"id": "a", "texto": "evento genial"}])
    agente._historial.append({"role": "user", "content": "hola"})

    agente.actualizar_datos([{"id": "b", "texto": "taller de python"}])

    assert agente.historial == [{"role": "user", "content": "hola"}]
    assert [m["id"] for m in agente._mensajes] == ["b"]
    assert "python" in agente._indice_invertido
    assert "genial" not in agente._indice_invertido


con_entorno_ui = pytest.mark.skipif(
    any(importlib.util.find_spec(n) is None for n in ("streamlit", "oci", "pandas", "altair")),
    reason="Prueba de UI requiere dependencias de producción",
)
APP = str(Path(__file__).resolve().parents[1] / "src/app/app.py")


@con_entorno_ui
def test_ui_publica_oculta_datos_y_explica_base_no_disponible(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("COMMUNITYLAB_MODO_INTERNO", raising=False)

    def sin_base():
        raise FuenteNoDisponible(fuente.NO_CONFIGURADA)

    monkeypatch.setattr(fuente, "leer_base", sin_base)
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["navegacion_principal"] = "Agente"
    app.run()

    assert not app.exception
    assert "Datos" not in app.radio[0].options
    aviso = " ".join(i.value for i in app.info)
    assert fuente.NO_CONFIGURADA in aviso
    assert "adjuntar" in aviso


@con_entorno_ui
def test_ui_agente_usa_la_captura_sin_releer_la_base(monkeypatch):
    from streamlit.testing.v1 import AppTest

    lecturas = []

    def base():
        lecturas.append(1)
        return instantanea("Gran meetup")

    monkeypatch.setattr(fuente, "leer_base", base)
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["navegacion_principal"] = "Agente"
    app.run()
    app.run()

    assert not app.exception
    assert len(lecturas) == 1
    assert isinstance(app.session_state[CLAVE_CAPTURA]["captura"], Captura)
    assert "El archivo aún está vacío" not in " ".join(m.value for m in app.markdown)


@con_entorno_ui
def test_ui_permite_saludar_sin_datos_y_conserva_el_chat(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from src.agentes.interpretacion import PlanConsulta

    def sin_base():
        raise FuenteNoDisponible(fuente.NO_CONFIGURADA)

    monkeypatch.setattr(fuente, "leer_base", sin_base)
    monkeypatch.setattr(
        "src.agentes.conversacion.interpretar_consulta",
        lambda **_: PlanConsulta(
            intencion="conversacion", respuesta="¡Hola! ¿Qué te gustaría consultar?",
        ),
    )
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["navegacion_principal"] = "Agente"
    app.run()
    app.chat_input[0].set_value("Hola").run()

    assert not app.exception
    assert len(app.session_state["historial_agente"]) == 2
    assert app.session_state["historial_agente"][1]["salida"]["modo"] == "conversacion"
    assert any("¡Hola!" in bloque.value for bloque in app.markdown)


@con_entorno_ui
def test_ui_controles_compactos_conservan_valores_y_archivos(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(fuente, "leer_base", lambda: instantanea("Gran meetup"))
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["navegacion_principal"] = "Agente"
    app.session_state["archivos_usuario"] = {
        "ejemplo.txt": [{"id": "propio-1", "texto": "Un mensaje"}],
    }
    app.session_state["historial_agente"] = [
        {"role": "user", "content": "Conversación conservada"}
    ]
    app.run()
    assert not app.exception
    assert app.selectbox(key="agente_modelo").value == "super"
    assert not app.slider
    assert any("Equilibrado: claridad" in c.proto.body for c in app.get("html"))
    assert len(app.get("html")) == 3
    assert not any("Equilibrado: claridad" in c.value for c in app.caption)

    app.radio(key="agente_ajuste").set_value("Manual").run()
    assert not app.exception
    app.number_input(key="agente_temperatura").set_value(0.65).run()
    app.radio(key="agente_ajuste").set_value("Estilos").run()
    app.selectbox(key="agente_estilo").set_value("creativo").run()
    assert any("Estilo: Creativo." in c.proto.body for c in app.get("html"))
    app.radio(key="agente_ajuste").set_value("Manual").run()
    assert app.number_input(key="agente_temperatura").value == 0.65
    assert any("Temperatura: 0.65" in c.proto.body for c in app.get("html"))

    app.selectbox(key="agente_modelo").set_value("lightning").run()
    assert any("Seleccionado: Lightning" in c.proto.body for c in app.get("html"))
    app.toggle(key="modo_verificacion").set_value(True).run()
    assert any("Seleccionado: Verificado." in c.proto.body for c in app.get("html"))
    app.button(key="agente_quitar_0").click().run()
    assert not app.exception
    assert app.session_state["archivos_usuario"] == {}
    assert app.selectbox(key="agente_modelo").value == "lightning"
    app.radio[0].set_value("Inicio").run()
    app.radio[0].set_value("Agente").run()
    assert not app.exception
    assert app.selectbox(key="agente_modelo").value == "lightning"
    assert app.number_input(key="agente_temperatura").value == 0.65
    assert app.toggle(key="modo_verificacion").value is True
    assert app.session_state["historial_agente"] == [
        {"role": "user", "content": "Conversación conservada"}
    ]
