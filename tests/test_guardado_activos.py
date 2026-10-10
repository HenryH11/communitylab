"""Aceptación del tramo salida DS → aprobación → OCI, sin red ni claves."""

import asyncio
import builtins
import importlib.util
import json
import threading
from copy import deepcopy
from typing import get_args
from unittest.mock import Mock, patch

import pytest

from src.agentes.estado_agente import Ruta
from src.app.guardado import guardar_resultado_aprobado

con_sdk = pytest.mark.skipif(
    importlib.util.find_spec("oci") is None, reason="SDK de OCI no instalado"
)
OPCIONES = {"periodo": "2026-semana-03", "bucket": "bucket-simulado"}


def salida_con_activos(activos=None, identificador="int-022"):
    activos = (
        activos
        if activos is not None
        else {
            "linkedin": {"texto": '¡Aprendí Python! 👩‍💻\n"Gracias"'},
            "boletin": {"texto": "Otro activo aún sin aprobar"},
        }
    )
    return {
        "resultados": [
            {
                "id": identificador,
                "sentimiento": "positivo",
                "tema_principal": "aprendizaje",
                "subtema": "Python",
                "tipo_detectado": "testimonio",
                "rutas": list(activos),
                "activos_generados": activos,
                "errores": [],
                "fallos": [],
            }
        ],
        "pendientes": [],
        "ids_pendientes": [],
    }


@pytest.fixture
def cliente():
    cliente = Mock()
    cliente.put_object.return_value.headers = {"etag": "etag-prueba"}
    return cliente


def guardar(salida, aprobados, cliente, **opciones):
    return asyncio.run(
        guardar_resultado_aprobado(
            salida,
            aprobados=aprobados,
            cliente=cliente,
            namespace="ns-simulado",
            **{**OPCIONES, **opciones},
        )
    )


def test_sin_aprobacion_no_importa_oci_ni_sube(monkeypatch, cliente):
    original = builtins.__import__

    def impedir_oci(nombre, *args, **kwargs):
        if (
            nombre == "oci"
            or nombre.startswith("oci.")
            or nombre == "src.config.oci_client"
        ):
            pytest.fail("Una selección vacía no debe necesitar OCI")
        return original(nombre, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", impedir_oci)
    informe = guardar(salida_con_activos(), [], cliente)
    assert informe["guardados"] == informe["fallidos"] == []
    assert len(informe["omitidos"]) == 2
    cliente.put_object.assert_not_called()


@pytest.mark.parametrize(
    "aprobados",
    [
        None,
        True,
        "todos",
        [("otro-id", "linkedin")],
        [("int-022", "ruta-inexistente")],
        [("int-022",)],
        [(1, "linkedin")],
    ],
)
def test_aprobacion_invalida_no_sube(aprobados, cliente):
    with pytest.raises(ValueError):
        guardar(salida_con_activos(), aprobados, cliente)
    cliente.put_object.assert_not_called()


@con_sdk
def test_solo_guarda_seleccion_y_conserva_json_utf8(cliente):
    salida = salida_con_activos()
    original = deepcopy(salida)
    informe = guardar(salida, [("int-022", "linkedin")], cliente)
    cliente.put_object.assert_called_once()
    parametros = cliente.put_object.call_args.kwargs
    assert json.loads(parametros["put_object_body"].decode("utf-8")) == {
        "id_interaccion": "int-022",
        "tipo": "linkedin",
        "contenido": original["resultados"][0]["activos_generados"][
            "linkedin"
        ],
    }
    assert "👩‍💻".encode("utf-8") in parametros["put_object_body"]
    assert parametros["bucket_name"] == "bucket-simulado"
    assert informe["guardados"][0]["etag"] == "etag-prueba"
    assert informe["omitidos"] == [
        {"id_interaccion": "int-022", "tipo": "boletin"}
    ]
    assert informe["fallidos"] == []
    assert salida == original


@con_sdk
@pytest.mark.parametrize("ruta", get_args(Ruta))
def test_admite_todos_los_tipos_de_ds(ruta, cliente):
    informe = guardar(
        salida_con_activos({ruta: {"texto": "válido"}}),
        [("int-022", ruta)],
        cliente,
    )
    assert informe["guardados"][0]["tipo"] == ruta
    assert informe["fallidos"] == []


@con_sdk
@pytest.mark.parametrize(
    "contenido",
    [
        {"texto": "\ud800"},
        {"valor": float("nan")},
        {"valor": float("inf")},
        {"valor": object()},
        None,
    ],
)
def test_valida_todo_el_lote_antes_de_la_primera_subida(contenido, cliente):
    salida = salida_con_activos(
        {"linkedin": {"texto": "válido"}, "boletin": contenido}
    )
    with pytest.raises((ValueError, TypeError)):
        guardar(
            salida, [("int-022", "linkedin"), ("int-022", "boletin")], cliente
        )
    cliente.put_object.assert_not_called()


@con_sdk
@pytest.mark.parametrize(
    "identificador,periodo",
    [
        ("../otro", "semana-03"),
        ("int-022", "../otro"),
        ("int-022", ""),
    ],
)
def test_identidad_y_periodo_no_admiten_rutas_arbitrarias(
    identificador, periodo, cliente
):
    with pytest.raises(ValueError):
        guardar(
            salida_con_activos(identificador=identificador),
            [(identificador, "linkedin")],
            cliente,
            periodo=periodo,
        )
    cliente.put_object.assert_not_called()


@con_sdk
@pytest.mark.parametrize("estado", [429, 500, 503])
def test_fallo_parcial_no_confirma_guardado_y_permite_reintento(
    estado, cliente
):
    import oci

    respuesta = Mock(headers={"etag": "correcto"})
    cliente.put_object.side_effect = [
        oci.exceptions.ServiceError(
            estado, "Simulado", {}, "secreto-no-publicar"
        ),
        respuesta,
    ]
    salida = salida_con_activos()
    informe = guardar(
        salida, [("int-022", "linkedin"), ("int-022", "boletin")], cliente
    )
    assert [a["tipo"] for a in informe["guardados"]] == ["boletin"]
    assert [a["tipo"] for a in informe["fallidos"]] == ["linkedin"]
    assert informe["fallidos"][0]["estado_http"] == estado
    assert "secreto-no-publicar" not in json.dumps(informe)

    cliente.reset_mock()
    cliente.put_object.side_effect = None
    reintento = guardar(
        salida,
        [(a["id_interaccion"], a["tipo"]) for a in informe["fallidos"]],
        cliente,
    )
    cliente.put_object.assert_called_once()
    assert (
        reintento["guardados"][0]["object_name"]
        == informe["fallidos"][0]["object_name"]
    )
    assert reintento["fallidos"] == []


@con_sdk
def test_timeout_no_confirma_guardado(cliente):
    cliente.put_object.side_effect = TimeoutError("detalle privado")
    informe = guardar(salida_con_activos(), [("int-022", "linkedin")], cliente)
    assert informe["guardados"] == []
    assert informe["fallidos"][0]["tipo_error"] == "TimeoutError"
    assert "detalle privado" not in json.dumps(informe)


@con_sdk
def test_sdk_se_ejecuta_fuera_del_hilo_del_bucle(cliente):
    hilo_principal = threading.get_ident()
    hilos = []

    def subir(**kwargs):
        hilos.append(threading.get_ident())
        return Mock(headers={"etag": "ok"})

    cliente.put_object.side_effect = subir
    guardar(salida_con_activos(), [("int-022", "linkedin")], cliente)
    assert len(hilos) == 1
    assert hilos[0] != hilo_principal


@con_sdk
def test_delega_autenticacion_sin_acoplarse_a_perfil_o_instance_principals():
    with patch(
        "src.config.oci_client.subir_json", return_value={"etag": "ok"}
    ) as subir:
        informe = asyncio.run(
            guardar_resultado_aprobado(
                salida_con_activos(),
                aprobados=[("int-022", "linkedin")],
                **OPCIONES,
            )
        )
    subir.assert_called_once()
    assert set(subir.call_args.kwargs) == {"cliente", "namespace", "bucket"}
    assert informe["fallidos"] == []


@con_sdk
def test_grafo_real_entrega_activos_y_solo_se_guarda_lo_aprobado(cliente):
    from src.agentes.procesamiento import procesar_paquete_entrega
    from src.agentes.nodos import nodos_generadores

    ids = ["int-022", "int-002", "int-008"]
    paquete = {
        "estados": [{"id": i, "texto": "Mensaje simulado"} for i in ids],
        "plan": {
            "ids_contenido": ids[:2],
            "pendientes": [],
            "ciclos": [{"indice": 1, "ids": ids}],
        },
    }
    analisis = [
        {
            "sentimiento": "positivo",
            "tema_principal": "aprendizaje",
            "subtema": "Python",
            "tipo_detectado": tipo,
        }
        for tipo in ("testimonio", "pregunta_tecnica", "comentario")
    ]
    generadores = {}
    for ruta in get_args(Ruta):
        cadena = Mock()
        cadena.invoke.return_value.model_dump.return_value = {
            "texto": "Contenido ✅"
        }
        generadores[ruta] = cadena

    with patch(
        "src.agentes.grafo.analizar_lote", return_value=analisis
    ), patch.object(
        nodos_generadores, "_obtener_generadores", return_value=generadores
    ):
        salida = procesar_paquete_entrega(paquete)

    assert salida["resultados_por_id"]["int-008"]["activos_generados"] == {}
    cliente.put_object.assert_not_called()
    informe = guardar(
        salida,
        [("int-022", "linkedin"), ("int-002", "preguntas_frecuentes")],
        cliente,
    )
    assert len(informe["guardados"]) == cliente.put_object.call_count == 2
    assert len(informe["omitidos"]) == 2
    assert informe["fallidos"] == []
    assert {a["id_interaccion"] for a in informe["guardados"]} == {
        "int-022",
        "int-002",
    }
