from unittest.mock import patch

import pytest

from src.agentes.configuracion_ia import (
    obtener_pasadas_recuperacion,
)
from src.agentes.errores_ia import ErrorConfiguracionProveedor
from src.agentes.procesamiento import procesar_paquete_entrega


def test_recuperacion_predeterminada(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_PASADAS_RECUPERACION", raising=False)

    with patch("src.agentes.configuracion_ia.load_dotenv"):
        assert obtener_pasadas_recuperacion() == 1


@pytest.mark.parametrize("pasadas", [0, 1, 2, 3])
def test_recuperacion_configurable(monkeypatch, pasadas):
    monkeypatch.setenv("COMMUNITYLAB_PASADAS_RECUPERACION", str(pasadas))

    paquete = {
        "estados": [{"id": "int-1"}],
        "plan": {
            "ciclos": [{"indice": 0, "ids": ["int-1"]}],
            "pendientes": [],
        },
    }

    salida = {
        "resultados": [
            {"id": "int-1", "fallos": [{"reintentable": True}]}
        ],
        "ciclos": [],
        "pendientes": [],
    }

    with (
        patch("src.agentes.configuracion_ia.load_dotenv"),
        patch(
            "src.agentes.procesamiento._ejecutar_ciclos",
            return_value=salida,
        ),
        patch(
            "src.agentes.procesamiento.reprocesar_resultados",
            side_effect=lambda resultado, **kwargs: resultado,
        ) as recuperar,
    ):
        procesar_paquete_entrega(paquete)

    assert recuperar.call_count == pasadas


@pytest.mark.parametrize("valor", ["-1", "4", "abc", "1.5", ""])
def test_recuperacion_invalida(monkeypatch, valor):
    monkeypatch.setenv("COMMUNITYLAB_PASADAS_RECUPERACION", valor)

    with pytest.raises(ErrorConfiguracionProveedor):
        obtener_pasadas_recuperacion()


def test_parametro_explicito_tiene_prioridad(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_PASADAS_RECUPERACION", "3")

    paquete = {
        "estados": [{"id": "int-1"}],
        "plan": {"ciclos": [], "pendientes": []},
    }

    with (
        patch("src.agentes.procesamiento._ejecutar_ciclos") as ejecutar,
        patch("src.agentes.procesamiento.reprocesar_resultados") as recuperar,
    ):
        ejecutar.return_value = {"resultados": [], "ciclos": []}
        procesar_paquete_entrega(paquete, pasadas_recuperacion=0)

    recuperar.assert_not_called()
