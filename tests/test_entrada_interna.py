import pytest

from src.app.entrada_interna import normalizar_entrada


def test_editoriales_reutiliza_adaptador_sin_etiquetas_propuestas():
    entrada = normalizar_entrada({"casos": [{
        "id": "m1", "texto": "Texto original", "tema_propuesto": "datos_ia",
        "tipo_esperado": "testimonio",
    }]})
    mensaje = entrada["lotes"][0]["interacciones"][0]
    assert mensaje["texto"] == "Texto original"
    assert "tema_propuesto" not in mensaje
    assert "tipo_esperado" not in mensaje
    assert mensaje["fecha"] is None


def test_lote_actual_se_conserva():
    documento = {"interacciones": [{"id": "m1", "texto": "Texto"}]}
    assert normalizar_entrada(documento) is documento


@pytest.mark.parametrize("documento", [
    [], {}, {"lotes": []}, {"interacciones": []},
    {"interacciones": [{"id": "m1", "texto": ""}]},
    {"interacciones": [{"id": "m1", "texto": "a"}, {"id": "m1", "texto": "b"}]},
])
def test_entrada_invalida_falla_explicita(documento):
    with pytest.raises(ValueError):
        normalizar_entrada(documento)
