from unittest.mock import MagicMock, patch

import pytest

from src.agentes.configuracion_ia import (
    MAX_INTENTOS_IA_POR_DEFECTO,
    obtener_max_intentos_ia,
)
from src.agentes.errores_ia import ErrorConfiguracionProveedor
from src.agentes.reintentos import (
    FalloOperacion,
    ejecutar_con_reintentos,
)


def test_reintentos_predeterminados(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_MAX_INTENTOS_IA", raising=False)

    with patch("src.agentes.configuracion_ia.load_dotenv"):
        assert obtener_max_intentos_ia() == MAX_INTENTOS_IA_POR_DEFECTO


def test_reintentos_configurados_por_entorno(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_IA", "2")
    operacion = MagicMock(side_effect=TimeoutError("timeout"))

    with patch("src.agentes.reintentos._esperar"):
        with pytest.raises(FalloOperacion) as fallo:
            ejecutar_con_reintentos(operacion, contexto={"etapa": "prueba"})

    assert fallo.value.intentos == 2
    assert operacion.call_count == 2


def test_parametro_explicito_tiene_prioridad(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_IA", "3")
    operacion = MagicMock(side_effect=TimeoutError("timeout"))

    with patch("src.agentes.reintentos._esperar"):
        with pytest.raises(FalloOperacion) as fallo:
            ejecutar_con_reintentos(
                operacion,
                contexto={"etapa": "prueba"},
                max_intentos=1,
            )

    assert fallo.value.intentos == 1
    assert operacion.call_count == 1


@pytest.mark.parametrize("valor", ["0", "-1", "abc", "1.5"])
def test_rechaza_configuracion_invalida(monkeypatch, valor):
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_IA", valor)

    with pytest.raises(ErrorConfiguracionProveedor):
        obtener_max_intentos_ia()


from src.agentes.configuracion_ia import (
    obtener_esperas_reintentos_ia,
)
from src.agentes.reintentos import calcular_espera


def test_esperas_predeterminadas(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_ESPERA_BASE_IA_SEGUNDOS", raising=False)
    monkeypatch.delenv("COMMUNITYLAB_ESPERA_MAXIMA_IA_SEGUNDOS", raising=False)

    with patch("src.agentes.configuracion_ia.load_dotenv"):
        assert obtener_esperas_reintentos_ia() == (2.0, 30.0)


def test_esperas_configuradas_afectan_backoff(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_ESPERA_BASE_IA_SEGUNDOS", "4")
    monkeypatch.setenv("COMMUNITYLAB_ESPERA_MAXIMA_IA_SEGUNDOS", "10")

    with (
        patch("src.agentes.configuracion_ia.load_dotenv"),
        patch(
            "src.agentes.reintentos.random.uniform",
            side_effect=lambda minimo, maximo: maximo,
        ) as aleatorio,
    ):
        assert calcular_espera(1) == 4.0
        assert calcular_espera(2) == 8.0
        assert calcular_espera(3) == 10.0

    assert [llamada.args for llamada in aleatorio.call_args_list] == [
        (2.0, 4.0),
        (4.0, 8.0),
        (5.0, 10.0),
    ]


@pytest.mark.parametrize(
    ("base", "maxima"),
    [
        ("0", "30"),
        ("-2", "30"),
        ("2", "-1"),
        ("4", "3"),
        ("abc", "10"),
        ("2", "inf"),
        ("nan", "30"),
    ],
)
def test_esperas_invalidas(monkeypatch, base, maxima):
    monkeypatch.setenv("COMMUNITYLAB_ESPERA_BASE_IA_SEGUNDOS", base)
    monkeypatch.setenv("COMMUNITYLAB_ESPERA_MAXIMA_IA_SEGUNDOS", maxima)

    with pytest.raises(ErrorConfiguracionProveedor):
        obtener_esperas_reintentos_ia()
