"""Flujos de Streamlit, estado de sesión y validación sin acceso a red."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest
from streamlit.testing.v1 import AppTest

from src.app.local import MAX_BYTES, PLANTILLAS, cargar_entrada, ejemplo, simular_plantilla

APP = Path(__file__).resolve().parents[1] / "src/app/app.py"


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    conectar = socket.socket.connect
    def bloquear(sock, direccion):
        # asyncio en Windows usa socketpair sobre loopback para AppTest.
        if isinstance(direccion, tuple) and direccion[0] in {"127.0.0.1", "::1"}:
            return conectar(sock, direccion)
        raise AssertionError("El frontend local no debe abrir conexiones de red")
    monkeypatch.setattr(socket.socket, "connect", bloquear)


@pytest.fixture
def lote():
    return {"origen_comunidad": "Comunidad de prueba", "periodo_referencia": "Semana_01",
            "interacciones": [{"autor": "Ana", "canal": "#general", "tipo": "comentario", "texto": "Una conversación de prueba"}]}


def pulsar(at, etiqueta):
    next(b for b in at.button if b.label == etiqueta).click().run(timeout=30)
    assert not at.exception
    return at


def abrir(at, pagina):
    at.radio(key="pagina").set_value(pagina).run(timeout=30)
    assert not at.exception
    return at


def test_entrada_oficial_multilote_utf8_y_ids(lote):
    mensajes = cargar_entrada(json.dumps(lote).encode("utf-8-sig"))
    assert mensajes[0]["id"] == "local-0001"
    assert lote["interacciones"][0].get("id") is None
    lote2 = deepcopy(lote)
    lote2["interacciones"][0]["id"] = "local-0001"
    assert [m["id"] for m in cargar_entrada(json.dumps({"lotes": [lote, lote2]}))] == ["local-0002", "local-0001"]
    assert len(cargar_entrada(ejemplo())) == 23


@pytest.mark.parametrize("contenido", [b"{", b"[]", b"{}", b"\xff", b'{"lotes": []}', b'{"lotes": [null]}', b'{"lotes": NaN}'])
def test_entradas_invalidas(contenido):
    with pytest.raises(ValueError):
        cargar_entrada(contenido)


def test_limites_vacios_y_duplicados(lote):
    with pytest.raises(ValueError, match="5 MB"):
        cargar_entrada(b" " * (MAX_BYTES + 1))
    lote["interacciones"][0]["id"] = "repetido"
    lote["interacciones"] *= 2
    with pytest.raises(ValueError, match="duplicados"):
        cargar_entrada(json.dumps(lote))
    lote["interacciones"] = [lote["interacciones"][0]]
    lote["interacciones"][0]["texto"] = "  "
    with pytest.raises(ValueError, match="vacío"):
        cargar_entrada(json.dumps(lote))
    lote["interacciones"] = []
    with pytest.raises(ValueError, match="al menos"):
        cargar_entrada(json.dumps(lote))
    lote["interacciones"] = [{"autor": "a", "canal": "c", "tipo": "comentario", "texto": "t"}] * 1001
    with pytest.raises(ValueError, match="1.000"):
        cargar_entrada(json.dumps(lote))


def test_plantillas_son_simulaciones_con_fuentes(lote):
    mensajes = cargar_entrada(ejemplo())
    for plantilla in PLANTILLAS:
        resultado = simular_plantilla(mensajes, plantilla)
        assert resultado["modo"] == "simulado_local"
        assert not resultado["generado_por_ia"] and not resultado["guardado_en_nube"]
        assert resultado["borradores"]
        assert all(set(b["fuentes"]).issubset({m["id"] for m in mensajes}) for b in resultado["borradores"])
    assert simular_plantilla(cargar_entrada(json.dumps(lote)), "Post para LinkedIn")["borradores"] == []


def test_componente_streamlit_se_inicializa():
    at = AppTest.from_file(APP).run(timeout=30)
    assert not at.exception
    assert len(at.get("component_instance")) == 1
    assert at.session_state.estado_local["datos"] == []


def test_eventos_carga_error_simulacion_y_vaciado(lote):
    from src.app.bridge import aplicar_evento, estado_inicial
    estado = aplicar_evento(estado_inicial(), {"id": "1", "accion": "ejemplo"})
    assert len(estado["datos"]) == 23
    resultado = aplicar_evento(estado, {"id": "2", "accion": "simular", "formato": "instagram"})
    assert resultado["resultado"]["plantilla"] == "Post para Instagram"
    assert len(resultado["resultado"]["borradores"]) == 8
    assert not resultado["resultado"]["generado_por_ia"]
    error = aplicar_evento(resultado, {"id": "3", "accion": "cargar", "contenido": "{", "nombre": "invalido.json"})
    assert error["aviso"]["tipo"] == "error" and "columna 2" in error["aviso"]["texto"]
    assert error["datos"] == resultado["datos"] and error["resultado"] == resultado["resultado"]
    reemplazo = aplicar_evento(error, {"id": "4", "accion": "cargar", "contenido": json.dumps(lote), "nombre": "nuevo.json"})
    assert len(reemplazo["datos"]) == 1 and reemplazo["resultado"] is None
    vacio = aplicar_evento(reemplazo, {"id": "5", "accion": "vaciar"})
    assert not vacio["datos"] and vacio["resultado"] is None


def test_eventos_repetidos_y_invalidos_no_se_reprocesan():
    from src.app.bridge import aplicar_evento, estado_inicial
    original = estado_inicial()
    for evento in (None, [], {}, {"id": None}, {"id": "x"*101}):
        assert aplicar_evento(original, evento) == original
    estado = aplicar_evento(original, {"id": "mismo", "accion": "ejemplo"})
    assert aplicar_evento(estado, {"id": "mismo", "accion": "vaciar"}) == estado
    for evento in ({"id": "a", "accion": []}, {"id": "b", "accion": "simular", "formato": []}, {"id": "c", "accion": "cargar", "contenido": None}):
        salida = aplicar_evento(estado, evento)
        assert salida["aviso"]["tipo"] == "error" and salida["datos"] == estado["datos"]


def test_formatos_del_boceto_requieren_datos_y_son_offline():
    from src.app.bridge import FORMATOS, aplicar_evento, estado_inicial
    for i, formato in enumerate(FORMATOS):
        vacio = aplicar_evento(estado_inicial(), {"id": f"v-{i}", "accion": "simular", "formato": formato})
        assert vacio["aviso"]["tipo"] == "error"
        estado = aplicar_evento(estado_inicial(), {"id": "base", "accion": "ejemplo"})
        salida = aplicar_evento(estado, {"id": str(i), "accion": "simular", "formato": formato})
        assert salida["resultado"]["formato"] == formato
        assert not salida["resultado"]["guardado_en_nube"]


def test_vistas_extraidas_del_svg_tienen_geometria_y_textos_originales():
    vistas = json.loads(APP.with_name("frontend").joinpath("design.json").read_text(encoding="utf-8"))
    assert set(vistas) == {"inicio", "plantillas", "resultado", "agente", "analiticas", "ayuda", "datos", "mapa", "estados", "movil_inicio", "movil_resultado"}
    assert all(v["width"] == 1440 and v["height"] == 875 for k,v in vistas.items() if not k.startswith("movil_"))
    assert vistas["inicio"]["elementos"]["cml-00033"] == {"x": 60, "y": 399, "w": 219, "h": 42, "texto": "", "tipo": "rectangle", "font": 14}
    assert "Tu comunidad habla." in vistas["inicio"]["svg"]
    assert "Post para Instagram" in vistas["plantillas"]["svg"]
    assert "Sentimiento de comunidad" in vistas["plantillas"]["svg"]
    assert all("<script" not in v["svg"] and "javascript:" not in v["svg"] for v in vistas.values())


def test_descarga_exporta_solo_seleccion_valida_y_marcas_de_simulacion():
    from src.app.bridge import aplicar_evento, estado_inicial
    from src.app.downloads import registrar_descarga
    estado = aplicar_evento(estado_inicial(), {"id": "base", "accion": "ejemplo"})
    estado = aplicar_evento(estado, {"id": "generar", "accion": "simular", "formato": "instagram"})
    salida = aplicar_evento(estado, {"id": "descarga", "accion": "descargar", "indices": [1, 3]})
    exportacion = salida["exportacion"]
    assert len(exportacion["contenido"]["borradores"]) == 2
    assert exportacion["contenido"]["borradores"][0]["fuentes"] == ["int-003"]
    assert not exportacion["contenido"]["generado_por_ia"] and not exportacion["contenido"]["guardado_en_nube"]
    class Gestor:
        def add(self, contenido, mimetype, coordenadas, **kwargs):
            assert json.loads(contenido)["borradores"] == exportacion["contenido"]["borradores"]
            assert mimetype == "application/json" and kwargs["is_for_static_download"]
            assert kwargs["file_name"] == "communitylab_borradores_simulados.json"
            return "/media/seleccion.json"
    assert registrar_descarga(exportacion, Gestor()) == "/media/seleccion.json"
    for seleccion in ([], [True], [999], [0, 0], [-1], "todos"):
        error = aplicar_evento(estado, {"id": "error", "accion": "descargar", "indices": seleccion})
        assert error["aviso"]["tipo"] == "error" and error["exportacion"] is None
    datos = aplicar_evento(estado, {"id": "datos", "accion": "descargar_datos"})
    assert len(datos["exportacion"]["contenido"]["mensajes"]) == 23
