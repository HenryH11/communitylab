import pytest

from src.agentes.configuracion_ia import (
    obtener_concurrencia_mensajes,
    obtener_concurrencia_lotes_analisis,
)


@pytest.mark.parametrize(
    ("variable", "obtener"),
    [
        (
            "COMMUNITYLAB_CONCURRENCIA_MENSAJES",
            obtener_concurrencia_mensajes,
        ),
        (
            "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS",
            obtener_concurrencia_lotes_analisis,
        ),
    ],
)
def test_concurrencia_predeterminada(monkeypatch, variable, obtener):
    monkeypatch.delenv(variable, raising=False)
    assert obtener() == 1


@pytest.mark.parametrize(
    ("variable", "obtener"),
    [
        (
            "COMMUNITYLAB_CONCURRENCIA_MENSAJES",
            obtener_concurrencia_mensajes,
        ),
        (
            "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS",
            obtener_concurrencia_lotes_analisis,
        ),
    ],
)
def test_concurrencia_doble(monkeypatch, variable, obtener):
    monkeypatch.setenv(variable, "2")
    assert obtener() == 2


@pytest.mark.parametrize(
    ("variable", "obtener"),
    [
        (
            "COMMUNITYLAB_CONCURRENCIA_MENSAJES",
            obtener_concurrencia_mensajes,
        ),
        (
            "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS",
            obtener_concurrencia_lotes_analisis,
        ),
    ],
)
@pytest.mark.parametrize("valor", ["0", "3", "abc", "1.5", ""])
def test_concurrencia_invalida(monkeypatch, variable, obtener, valor):
    monkeypatch.setenv(variable, valor)

    with pytest.raises(ValueError):
        obtener()
