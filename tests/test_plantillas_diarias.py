from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from src.app import plantillas_diarias as diario


AHORA = datetime(2026, 10, 24, 13, tzinfo=timezone.utc)
PLANTILLAS = diario.PLANTILLAS_DIARIAS[:2]


def salida(plataforma="linkedin"):
    return {
        "respuesta": "Contenido con evidencia.", "citas": ["m1"],
        "borrador": {
            "plataforma": plataforma, "titulo": "Comunidad",
            "contenido": "Aprendemos juntos.", "hashtags": ["#IA", "#Datos", "#Comunidad"],
        },
        "verificacion": {"estado": "verificado", "resumen": "Fuentes revisadas."},
    }


def lector():
    return {"registros": [{
        "id": "m1", "contenido_textual": "Aprendemos juntos.", "sentimiento": "positivo",
    }]}


class Memoria(diario.RepositorioCatalogo):
    def __init__(self):
        self._catalogo: diario.CatalogoDiario | None = None
        self.etag = None
        self.escrituras = 0

    @property
    def catalogo(self) -> diario.CatalogoDiario:
        assert self._catalogo is not None
        return self._catalogo

    def leer(self):
        return deepcopy(self._catalogo), self.etag

    def guardar(self, catalogo, etag):
        assert etag == self.etag
        self._catalogo = deepcopy(catalogo)
        self.escrituras += 1
        self.etag = str(self.escrituras)


def fabrica(*respuestas):
    return Mock(side_effect=[
        Mock(consultar=Mock(side_effect=[respuesta])) for respuesta in respuestas
    ])


def ejecutar(repo, *, ahora=AHORA, crear=None, leer=None):
    catalogo = diario.actualizar_catalogo(
        repo, ahora=ahora, plantillas=PLANTILLAS,
        lector=leer or lector, crear_agente=crear or fabrica(salida(), salida("instagram")),
    )
    assert catalogo is not None
    return catalogo


def test_antes_de_las_ocho_no_lee_ni_genera_y_requiere_zona():
    repo = Mock()
    assert diario.actualizar_catalogo(repo, ahora=AHORA - timedelta(seconds=1)) is None
    repo.leer.assert_not_called()
    with pytest.raises(ValueError, match="zona horaria"):
        ejecutar(repo, ahora=AHORA.replace(tzinfo=None))


def test_una_captura_conversaciones_aisladas_idempotencia_y_modo():
    repo = Memoria()
    leer = Mock(side_effect=lector)
    crear = fabrica(salida(), salida("instagram"))
    catalogo = ejecutar(repo, crear=crear, leer=leer)
    assert len(catalogo.entradas) == 2 and not catalogo.fallos
    leer.assert_called_once()
    assert crear.call_count == 2
    assert crear.call_args_list[0].args[0] == crear.call_args_list[1].args[0]
    assert repo.escrituras == 1
    assert catalogo.captura_en == AHORA
    # No llama otra vez a IA/BD ni vuelve a escribir éxitos del mismo día.
    ejecutar(repo, crear=Mock(side_effect=AssertionError), leer=Mock(side_effect=AssertionError))
    assert repo.escrituras == 1


def test_fallo_parcial_conserva_anterior_y_reintento_solo_fallida():
    repo = Memoria()
    ejecutar(repo)
    anterior = deepcopy(repo.catalogo.entradas["instagram"])
    manana = AHORA + timedelta(days=1)
    crear = fabrica(salida(), RuntimeError("No divulgar credenciales"))
    catalogo = ejecutar(repo, ahora=manana, crear=crear)
    assert catalogo.entradas["linkedin"].generado_en == manana
    assert catalogo.entradas["instagram"] == anterior
    assert set(catalogo.fallos) == {"instagram"}
    assert "credenciales" not in catalogo.model_dump_json()
    crear = fabrica(salida("instagram"))
    catalogo = ejecutar(repo, ahora=manana + timedelta(minutes=15), crear=crear)
    assert crear.call_count == 1
    assert not catalogo.fallos
    assert catalogo.entradas["linkedin"].generado_en == manana
    assert catalogo.entradas["instagram"].generado_en > manana
    assert len(catalogo.entradas) == 2


def test_fallo_base_no_borra_catalogo_y_se_registra_sin_ejecutar_modelos():
    repo = Memoria()
    ejecutar(repo)
    entradas = deepcopy(repo.catalogo.entradas)
    crear = Mock()
    catalogo = ejecutar(
        repo, ahora=AHORA + timedelta(days=1), crear=crear,
        leer=Mock(side_effect=RuntimeError("DB no disponible")),
    )
    assert catalogo.entradas == entradas
    assert set(catalogo.fallos) == {p.id for p in PLANTILLAS}
    crear.assert_not_called()


@pytest.mark.parametrize("resultado", [
    {"respuesta": "Sin datos.", "citas": [], "borrador": None},
    {"respuesta": "Sin post.", "citas": ["m1"], "borrador": None},
    salida("x"),
])
def test_no_sustituye_version_anterior_por_resultado_invalido(resultado):
    repo = Memoria()
    ejecutar(repo)
    anterior = deepcopy(repo.catalogo.entradas["linkedin"])
    catalogo = ejecutar(
        repo, ahora=AHORA + timedelta(days=1),
        crear=fabrica(resultado, salida("instagram")),
    )
    assert catalogo.entradas["linkedin"] == anterior
    assert "linkedin" in catalogo.fallos


def test_fallo_guardado_o_conflicto_no_se_confirma():
    repo = Memoria()
    ejecutar(repo)
    anterior = deepcopy(repo.catalogo)
    repo.guardar = Mock(side_effect=RuntimeError("conflicto"))
    with pytest.raises(RuntimeError, match="conflicto"):
        ejecutar(repo, ahora=AHORA + timedelta(days=1))
    assert repo.catalogo == anterior


def test_repositorio_usa_un_solo_objeto_y_etag_para_reemplazo():
    repo = Memoria()
    catalogo = ejecutar(repo)
    cliente = Mock()
    cliente.get_object.return_value = SimpleNamespace(
        data=SimpleNamespace(content=catalogo.model_dump_json().encode()),
        headers={"etag": "version-1"},
    )
    oci = diario.RepositorioCatalogo(cliente, "ns", "bucket")
    documento, etag = oci.leer()
    assert documento == catalogo
    assert documento is not None
    oci.guardar(documento, etag)
    kwargs = cliente.put_object.call_args.kwargs
    assert kwargs["object_name"] == diario.OBJETO
    assert kwargs["if_match"] == "version-1"
    assert json.loads(kwargs["put_object_body"])["entradas"]["linkedin"]
    oci.guardar(catalogo, None)
    assert cliente.put_object.call_args.kwargs["if_none_match"] == "*"
    cliente.delete_object.assert_not_called()


@pytest.mark.parametrize(("status", "code", "ausente"), [
    (404, "ObjectNotFound", True), (404, "BucketNotFound", False),
    (403, "NotAuthorized", False), (500, "InternalError", False),
])
def test_solo_objeto_ausente_es_catalogo_vacio(status, code, ausente):
    class ErrorOCI(RuntimeError):
        def __init__(self):
            super().__init__("OCI error")
            self.status, self.code = status, code
    error = ErrorOCI()
    cliente = Mock()
    cliente.get_object.side_effect = error
    repo = diario.RepositorioCatalogo(cliente, "ns", "bucket")
    if ausente:
        assert repo.leer() == (None, None)
    else:
        with pytest.raises(RuntimeError):
            repo.leer()


def test_consulta_analitica_se_guarda_sin_fingir_una_publicacion():
    repo = Memoria()
    resultado = {"respuesta": "Un comentario positivo.", "citas": ["m1"], "borrador": None}
    catalogo = diario.actualizar_catalogo(
        repo, ahora=AHORA, plantillas=(diario.PLANTILLAS_DIARIAS[5],),
        lector=lector, crear_agente=fabrica(resultado),
    )
    assert catalogo is not None
    assert catalogo.entradas["sentimiento"].salida == resultado


@pytest.mark.parametrize("respuesta", [
    "Falta el titular.", "## Titular\n\n" + "palabra " * 180,
])
def test_boletin_invalido_no_se_publica_como_exito(respuesta):
    repo = Memoria()
    resultado = {"respuesta": respuesta, "citas": ["m1"], "borrador": None}
    catalogo = diario.actualizar_catalogo(
        repo, ahora=AHORA, plantillas=(diario.PLANTILLAS_DIARIAS[3],),
        lector=lector, crear_agente=fabrica(resultado),
    )
    assert catalogo is not None
    assert "boletin" in catalogo.fallos
    assert not catalogo.entradas


def test_plantilla_analitica_no_guarda_borrador_de_red_social():
    repo = Memoria()
    catalogo = diario.actualizar_catalogo(
        repo, ahora=AHORA, plantillas=(diario.PLANTILLAS_DIARIAS[5],),
        lector=lector, crear_agente=fabrica(salida()),
    )
    assert catalogo is not None
    assert "sentimiento" in catalogo.fallos

def sin_evidencia():
    return {
        "respuesta": "No hay mensajes negativos en esta captura.",
        "citas": [], "borrador": None, "total_coincidencias": 0,
        "modo": "consulta",
        "verificacion": {
            "estado": "sin_evidencia", "resumen": "Sin coincidencias.",
        },
    }


def test_ausencia_explicita_se_guarda_y_se_relee_sin_fabricar_citas():
    repo = Memoria()
    resultado = sin_evidencia()
    catalogo = diario.actualizar_catalogo(
        repo, ahora=AHORA, plantillas=(diario.PLANTILLAS_DIARIAS[7],),
        lector=lector, crear_agente=fabrica(resultado),
    )
    assert catalogo is not None
    assert not catalogo.fallos
    assert catalogo.entradas["insight_mejora"].salida == resultado
    cliente = Mock()
    cliente.get_object.return_value = SimpleNamespace(
        data=SimpleNamespace(content=catalogo.model_dump_json().encode()),
        headers={"etag": "v1"},
    )
    assert diario.RepositorioCatalogo(cliente, "ns", "bucket").leer()[0] == catalogo


@pytest.mark.parametrize("cambio", [
    {"total_coincidencias": 2}, {"citas": ["m1"]}, {"modo": "conversacion"},
    {"borrador": salida()["borrador"]},
])
def test_ausencia_no_permite_resultados_contradictorios(cambio):
    resultado = sin_evidencia() | cambio
    repo = Memoria()
    catalogo = diario.actualizar_catalogo(
        repo, ahora=AHORA, plantillas=(diario.PLANTILLAS_DIARIAS[7],),
        lector=lector, crear_agente=fabrica(resultado),
    )
    assert catalogo is not None
    assert "insight_mejora" in catalogo.fallos
    assert not catalogo.entradas


def test_ausencia_sustituye_plantilla_previa_sin_dejar_contenido_obsoleto():
    repo = Memoria()
    ejecutar(repo)
    resultado = sin_evidencia() | {"modo": "borrador"}
    catalogo = ejecutar(
        repo, ahora=AHORA + timedelta(days=1),
        crear=fabrica(resultado, salida("instagram")),
    )
    assert not catalogo.fallos
    assert catalogo.entradas["linkedin"].salida == resultado
    assert catalogo.entradas["linkedin"].generado_en == AHORA + timedelta(days=1)


def test_vista_muestra_ausencia_sin_fuentes_ni_botones_de_publicacion(monkeypatch):
    from src.app import vista_plantillas_diarias as vista

    catalogo = diario.CatalogoDiario(
        intentado_en=AHORA,
        entradas={"insight_mejora": diario.EntradaDiaria(
            nombre="Mejoras", prompt="Analiza", generado_en=AHORA,
            salida=sin_evidencia(),
        )},
    )
    monkeypatch.setattr(vista, "leer_catalogo", Mock(return_value=catalogo))
    app = AppTest.from_string(
        "from src.app.vista_plantillas_diarias import render\nrender()"
    ).run()
    assert not app.exception
    assert any("Sin evidencia para esta plantilla" in i.value for i in app.info)
    assert not any(c.value.startswith("Fuentes:") for c in app.caption)
    assert not app.get("link_button")


APP = str(Path(__file__).resolve().parents[1] / "src" / "app" / "app.py")


def test_vista_publica_lee_oci_sin_lote_ni_generacion(monkeypatch):
    from src.app import vista_plantillas_diarias as vista

    repo = Memoria()
    ejecutar(repo, ahora=AHORA - timedelta(days=2))
    repo.catalogo.fallos["instagram"] = "No se pudo renovar."
    monkeypatch.delenv("COMMUNITYLAB_MODO_INTERNO", raising=False)
    monkeypatch.setattr(vista, "leer_catalogo", Mock(return_value=repo.catalogo))
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["navegacion_principal"] = "Plantillas"
    app.run()
    assert not app.exception
    assert any("Contenido anterior" in w.value for w in app.warning)
    assert any("No se pudo renovar" in w.value for w in app.warning)
    assert len(app.get("link_button")) == 2
    assert not app.text_area
    assert not any(b.label == "Guardar aprobados en OCI" for b in app.button)


@pytest.mark.parametrize("error", [False, True])
def test_vista_distingue_ausencia_y_fallo_oci(monkeypatch, error):
    from src.app import vista_plantillas_diarias as vista

    lector_ui = Mock(side_effect=RuntimeError("SDK") if error else None, return_value=None)
    monkeypatch.setattr(vista, "leer_catalogo", lector_ui)
    app = AppTest.from_string(
        "from src.app.vista_plantillas_diarias import render\nrender()"
    ).run()
    assert not app.exception
    if error:
        assert app.error and not app.info
    else:
        assert any("primer catálogo" in i.value for i in app.info)


@pytest.mark.parametrize(("fallos", "codigo"), [({}, 0), ({"linkedin": "Pendiente"}, 2)])
def test_ejecutor_informa_estado_real_sin_tocar_cloud(monkeypatch, fallos, codigo):
    from scripts import generar_plantillas_diarias as cli

    repo = Mock()
    monkeypatch.setattr(cli, "load_dotenv", Mock())
    monkeypatch.setattr(cli.RepositorioCatalogo, "desde_entorno", Mock(return_value=repo))
    catalogo = diario.CatalogoDiario(intentado_en=AHORA, fallos=fallos)
    actualizar = Mock(return_value=catalogo)
    monkeypatch.setattr(cli, "actualizar_catalogo", actualizar)
    assert cli.principal() == codigo
    actualizar.assert_called_once_with(repo)


def test_ejecutor_no_confirma_fallos_de_escritura(monkeypatch):
    from scripts import generar_plantillas_diarias as cli

    monkeypatch.setattr(cli, "load_dotenv", Mock())
    monkeypatch.setattr(cli.RepositorioCatalogo, "desde_entorno", Mock())
    monkeypatch.setattr(cli, "actualizar_catalogo", Mock(side_effect=RuntimeError("fallo")))
    assert cli.principal() == 1


def test_repositorio_no_oculta_catalogo_corrupto():
    cliente = Mock()
    repo = diario.RepositorioCatalogo(cliente, "ns", "bucket")
    cliente.get_object.return_value = SimpleNamespace(
        data=SimpleNamespace(content=b'{"version":9}'), headers={"etag": "v1"},
    )
    with pytest.raises(ValueError):
        repo.leer()
    cliente.get_object.return_value = SimpleNamespace(
        data=SimpleNamespace(content=b'{}'), headers={},
    )
    with pytest.raises(ValueError, match="ETag"):
        repo.leer()
