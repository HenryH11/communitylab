import pytest

from src.app.errores_agente import explicar_error


class _ErrorHttp(Exception):
    def __init__(self, codigo: int):
        super().__init__(f"HTTP {codigo}")
        self.status_code = codigo


class APIConnectionError(Exception):
    pass


def _envuelto(causa: Exception) -> Exception:
    try:
        raise causa
    except Exception as interno:
        try:
            raise RuntimeError("fallo del proveedor") from interno
        except RuntimeError as externo:
            return externo


@pytest.mark.parametrize(
    ("error", "fragmento"),
    [
        (_ErrorHttp(404), "no está disponible"),
        (_ErrorHttp(401), "rechazó el acceso"),
        (_ErrorHttp(429), "límite de uso"),
        (_ErrorHttp(503), "tiene problemas"),
        (APIConnectionError(), "No hay conexión"),
        (ConnectionError(), "fuente de datos"),
        (TimeoutError(), "No hay conexión"),
        (_envuelto(_ErrorHttp(404)), "no está disponible"),
        (RuntimeError("boom"), "problema inesperado"),
    ],
)
def test_errores_se_explican_en_lenguaje_claro(error, fragmento):
    assert fragmento in explicar_error(error)


def test_errores_de_validacion_se_muestran_tal_cual():
    assert explicar_error(ValueError("Escribe una consulta.")) == "Escribe una consulta."


@pytest.mark.parametrize(
    "error",
    [_ErrorHttp(404), _ErrorHttp(403), APIConnectionError(), RuntimeError("x")],
)
def test_errores_no_mencionan_codigo_ni_configuracion(error):
    mensaje = explicar_error(error).lower()
    for prohibido in (".env", "api key", "logs", ".py", "variable", "nvidia", "jsonl"):
        assert prohibido not in mensaje
