"""Tolerancia del conector OCI ante activos del grafo y payloads anómalos.

Sin red ni credenciales: el cliente de Object Storage se simula. Complementa
test_persistencia_oci.py (Cloud) con los casos que llegarán al conectarlo al
cierre del grafo en Semana 3.
"""

import ast
import json
from pathlib import Path
from typing import get_args
from unittest.mock import Mock

import pytest

from src.agentes.estado_agente import Ruta

# skipif en lugar de importorskip(): unittest discover también importa este módulo.
try:
    import oci
    from src.config.oci_client import RUTAS_ACTIVO, nombre_objeto_activo, subir_json
except ImportError:
    oci = None
    RUTAS_ACTIVO = frozenset()

pytestmark = pytest.mark.skipif(oci is None, reason="SDK de OCI no instalado")


RAIZ = Path(__file__).resolve().parents[1]
PERIODO = "2026-semana-03"


def cliente_simulado():
    cliente = Mock()
    cliente.put_object.return_value.headers = {"etag": "etag-prueba"}
    return cliente


@pytest.mark.parametrize("ruta", sorted(RUTAS_ACTIVO))
def test_rutas_admitidas_generan_clave_estable(ruta):
    assert nombre_objeto_activo("int-004", ruta, PERIODO) == f"assets/{PERIODO}/{ruta}/int-004.json"


@pytest.mark.xfail(strict=True, raises=ValueError, reason=(
    "El grafo genera la ruta insight_mejora (estado_agente.Ruta), pero "
    "oci_client.RUTAS_ACTIVO no la admite: esos activos no se podrán guardar (CE)"
))
def test_toda_ruta_del_grafo_tiene_destino_en_el_bucket():
    for ruta in get_args(Ruta):
        nombre_objeto_activo("int-006", ruta, PERIODO)


@pytest.mark.parametrize("identificador", [
    "../otro", "a/b", "a\\b", "", " ", "int 004", "int-004\n", None, 4,
])
def test_identificador_anomalo_se_rechaza_antes_de_subir(identificador):
    with pytest.raises(ValueError):
        nombre_objeto_activo(identificador, "linkedin", PERIODO)


@pytest.mark.parametrize("documento", [
    {"texto": "\ud800"},
    {"puntaje": float("inf")},
    {"puntaje": float("nan")},
    {"fecha": object()},
])
def test_documento_no_serializable_no_llega_al_bucket(documento):
    cliente = cliente_simulado()
    with pytest.raises((TypeError, ValueError)):
        subir_json(documento, "assets/prueba.json", cliente=cliente, namespace="ns")
    cliente.put_object.assert_not_called()


@pytest.mark.parametrize("nombre", ["", "   ", "/assets/x.json", None])
def test_nombre_de_objeto_invalido_no_llega_al_bucket(nombre):
    cliente = cliente_simulado()
    with pytest.raises(ValueError):
        subir_json({"id": "int-004"}, nombre, cliente=cliente, namespace="ns")
    cliente.put_object.assert_not_called()


def test_activo_de_ciencia_de_datos_se_sube_intacto_en_utf8():
    activo = {
        "id_interaccion": "int-004", "tipo": "preguntas_frecuentes",
        "contenido": {
            "tema": "Certificación",
            "respuesta": "Confírmalo en los canales oficiales del programa. ✅",
        },
    }
    cliente = cliente_simulado()
    nombre = nombre_objeto_activo(activo["id_interaccion"], activo["tipo"], PERIODO)
    resultado = subir_json(activo, nombre, cliente=cliente, namespace="ns", bucket="bucket-prueba")
    cuerpo = cliente.put_object.call_args.kwargs["put_object_body"]
    assert json.loads(cuerpo.decode("utf-8")) == activo
    assert "✅".encode("utf-8") in cuerpo
    assert resultado["object_name"] == nombre


@pytest.mark.parametrize("estado_http", [429, 500, 503])
def test_error_del_servicio_se_propaga_sin_confirmar_guardado(estado_http):
    cliente = cliente_simulado()
    cliente.put_object.side_effect = oci.exceptions.ServiceError(
        estado_http, "Simulado", {}, "error simulado del servicio",
    )
    with pytest.raises(oci.exceptions.ServiceError) as error:
        subir_json({"id": "int-004"}, "assets/x.json", cliente=cliente, namespace="ns")
    assert error.value.status == estado_http


def test_timeout_del_cliente_se_propaga():
    cliente = cliente_simulado()
    cliente.put_object.side_effect = TimeoutError("sin respuesta del bucket")
    with pytest.raises(TimeoutError):
        subir_json({"id": "int-004"}, "assets/x.json", cliente=cliente, namespace="ns")


def test_persistencia_no_usa_comandos_del_sistema_operativo():
    """Regla del PM (Semana 3): nada de os.system ni subprocess en src/config/."""
    prohibidos = []
    for archivo in (RAIZ / "src" / "config").rglob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, (ast.Import, ast.ImportFrom)):
                modulos = [a.name for a in nodo.names] + [getattr(nodo, "module", None) or ""]
                if any(m.split(".")[0] == "subprocess" for m in modulos):
                    prohibidos.append(f"{archivo.name}: import subprocess")
            if (isinstance(nodo, ast.Attribute) and nodo.attr in {"system", "popen"}
                    and isinstance(nodo.value, ast.Name) and nodo.value.id == "os"):
                prohibidos.append(f"{archivo.name}: os.{nodo.attr}")
    assert prohibidos == []
