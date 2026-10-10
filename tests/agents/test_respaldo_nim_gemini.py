"""Respaldo NVIDIA NIM -> Gemini: criterios de aceptación acordados con DS.

Data Science publicó invocar_modelo_con_fallback(entrada, *, primario,
respaldo) en src/agentes/modelo_ia.py (feature/DS-Semana3-Nvidia, a989951).
Mientras no esté en la rama, este módulo se omite.

Acordado con DS (6 oct, Arnold):
- Activan el respaldo los fallos operativos de NIM (429, timeout, conexión,
  5xx, clave o configuración ausente) y una salida inutilizable (JSON roto o
  fuera del esquema), después de los reintentos propios de NIM.
- Los errores propios de la entrada no activan el respaldo.
- La traza (proveedor_primario, proveedor_usado, fallback_activado,
  motivo_fallback) va por interacción. Si Gemini responde, no es un fallo.
- Si fallan ambos proveedores, la interacción queda fallida con los motivos de
  ambos guardados de forma segura, y el grafo sigue con los demás mensajes.
- El límite de tiempo es un timeout de NIM: al superarlo se activa Gemini.

Confirmado por DS (8 oct, Arnold):
- Cliente NIM: ChatOpenAI (langchain-openai). Los errores HTTP se reconocen
  por status_code o por .code (aquí se simula status_code).
- La clave o configuración ausente lanza modelo_ia.ErrorConfiguracionProveedor,
  distinto del ValueError de entrada.
- Timeout de 3 s por ahora, configurable con COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS.
- El respaldo ya está conectado al análisis y a la generación por ruta.
"""

from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from langchain_core.exceptions import OutputParserException

from src.agentes import modelo_ia

# skipif en lugar de pytest.skip(): unittest discover también importa este módulo.
pytestmark = pytest.mark.skipif(
    not hasattr(modelo_ia, "invocar_modelo_con_fallback"),
    reason="DS aún no publica invocar_modelo_con_fallback en modelo_ia.py",
)


@pytest.fixture(autouse=True)
def sin_esperas_de_reintento(monkeypatch):
    """Los reintentos de NIM esperan con time.sleep; en pruebas no hace falta."""
    reintentos = pytest.importorskip("src.agentes.reintentos")
    monkeypatch.setattr(reintentos, "_esperar", lambda segundos: None)


# --- Contrato provisional: único bloque a ajustar con la firma definitiva ---

def invocar(entrada, *, primario, respaldo):
    """Firma confirmada por DS; devuelve (resultado, traza)."""
    salida = modelo_ia.invocar_modelo_con_fallback(
        entrada, primario=primario, respaldo=respaldo,
    )
    return salida["resultado"], salida["traza"]


class ErrorHTTP(Exception):
    """Simula los errores HTTP de un cliente compatible con OpenAI."""

    def __init__(self, status_code, mensaje="error simulado"):
        super().__init__(mensaje)
        self.status_code = status_code


class ErrorEntrada(ValueError):
    """Simula un payload inválido detectado al invocar el modelo."""


def error_sin_clave():
    return modelo_ia.ErrorConfiguracionProveedor(f"Falta NVIDIA_API_KEY {SECRETO}")

# --- Fin del contrato provisional ---


SECRETO = "nvapi-secreto-que-no-debe-aparecer"
ENTRADA = {"id": "int-004", "texto": "¿El certificado tiene costo? 👩‍💻"}
RESPUESTA_NIM = {"proveedor": "nvidia_nim", "contenido": "respuesta NIM"}
RESPUESTA_GEMINI = {"proveedor": "gemini", "contenido": "respuesta Gemini"}

FALLOS_NIM = {
    "limite_429": lambda: ErrorHTTP(429, f"Too Many Requests {SECRETO}"),
    "timeout": lambda: TimeoutError(f"sin respuesta {SECRETO}"),
    "conexion": lambda: ConnectionError(f"servicio no disponible {SECRETO}"),
    "error_500": lambda: ErrorHTTP(500),
    "error_503": lambda: ErrorHTTP(503),
    "sin_clave": error_sin_clave,
    # OutputParserException hereda de ValueError: debe distinguirse de ErrorEntrada.
    "json_roto": lambda: OutputParserException(f"Invalid json output: {{'sentim {SECRETO}"),
    "fuera_de_esquema": lambda: OutputParserException("sentimiento: valor no admitido 'feliz'"),
}


def proveedores(error_primario=None, error_respaldo=None):
    primario = MagicMock(name="nvidia_nim")
    if error_primario is None:
        primario.return_value = RESPUESTA_NIM
    else:
        primario.side_effect = error_primario
    respaldo = MagicMock(name="gemini")
    if error_respaldo is None:
        respaldo.return_value = RESPUESTA_GEMINI
    else:
        respaldo.side_effect = error_respaldo
    return primario, respaldo


def test_nim_disponible_responde_sin_tocar_gemini():
    primario, respaldo = proveedores()
    resultado, traza = invocar(deepcopy(ENTRADA), primario=primario, respaldo=respaldo)
    assert resultado == RESPUESTA_NIM
    respaldo.assert_not_called()
    assert traza["proveedor_primario"] == "nvidia_nim"
    assert traza["proveedor_usado"] == "nvidia_nim"
    assert traza["fallback_activado"] is False
    assert not traza.get("motivo_fallback")


@pytest.mark.parametrize("caso", sorted(FALLOS_NIM))
def test_fallo_de_nim_activa_gemini_con_trazabilidad(caso):
    primario, respaldo = proveedores(FALLOS_NIM[caso]())
    resultado, traza = invocar(deepcopy(ENTRADA), primario=primario, respaldo=respaldo)
    assert resultado == RESPUESTA_GEMINI
    assert primario.call_count >= 1  # admite los reintentos propios de NIM
    respaldo.assert_called_once()
    assert traza["proveedor_primario"] == "nvidia_nim"
    assert traza["proveedor_usado"] == "gemini"
    assert traza["fallback_activado"] is True
    assert isinstance(traza["motivo_fallback"], str) and traza["motivo_fallback"].strip()


@pytest.mark.parametrize("caso", sorted(FALLOS_NIM))
def test_respaldo_exitoso_no_se_registra_como_fallo(caso):
    primario, respaldo = proveedores(FALLOS_NIM[caso]())
    _, traza = invocar(deepcopy(ENTRADA), primario=primario, respaldo=respaldo)
    assert not traza.get("fallos")
    assert not traza.get("errores")


@pytest.mark.parametrize("caso", sorted(FALLOS_NIM))
def test_gemini_recibe_la_misma_entrada_sin_alterar(caso):
    primario, respaldo = proveedores(FALLOS_NIM[caso]())
    entrada = deepcopy(ENTRADA)
    invocar(entrada, primario=primario, respaldo=respaldo)
    assert entrada == ENTRADA
    assert respaldo.call_args == primario.call_args


@pytest.mark.parametrize("caso", sorted(FALLOS_NIM))
def test_traza_no_expone_la_clave_ni_el_mensaje_del_proveedor(caso):
    primario, respaldo = proveedores(FALLOS_NIM[caso]())
    _, traza = invocar(deepcopy(ENTRADA), primario=primario, respaldo=respaldo)
    assert SECRETO not in repr(traza)


@pytest.mark.parametrize("error", [
    ErrorEntrada("payload inválido: falta texto"),
    ErrorEntrada("payload inválido: texto no es str"),
])
def test_error_de_entrada_no_activa_gemini(error):
    primario, respaldo = proveedores(error)
    with pytest.raises(ErrorEntrada):
        invocar(deepcopy(ENTRADA), primario=primario, respaldo=respaldo)
    respaldo.assert_not_called()


@pytest.mark.parametrize("caso", ["limite_429", "timeout", "json_roto"])
def test_si_fallan_ambos_proveedores_el_error_no_expone_secretos(caso):
    error_gemini = ErrorHTTP(503, f"Gemini no disponible {SECRETO}")
    primario, respaldo = proveedores(FALLOS_NIM[caso](), error_gemini)
    with pytest.raises(Exception) as error:
        invocar(deepcopy(ENTRADA), primario=primario, respaldo=respaldo)
    respaldo.assert_called_once()
    assert SECRETO not in str(error.value)
    assert SECRETO not in repr(getattr(error.value, "traza", None))
