import pytest

from src.agentes.validacion_entrega import validar_resultados


def resultado_valido():
    return {
        "id": "spam-validacion-001",
        "sentimiento": "neutral",
        "tema_principal": "otros",
        "subtema": "Mensaje de prueba",
        "tipo_detectado": "comentario",
        "es_spam_detectado": False,
        "motivo_spam": None,
        "rutas": [],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }


def test_acepta_analisis_con_spam_coherente():
    resultado = resultado_valido()
    resultado["es_spam_detectado"] = True
    resultado["motivo_spam"] = "Captación no solicitada"

    validar_resultados([resultado])


@pytest.mark.parametrize(
    "cambios",
    [
        {"es_spam_detectado": "false"},
        {"es_spam_detectado": True, "motivo_spam": None},
        {"es_spam_detectado": True, "motivo_spam": "   "},
        {"es_spam_detectado": False, "motivo_spam": "Captación"},
    ],
)
def test_rechaza_campos_spam_incoherentes(cambios):
    resultado = resultado_valido()
    resultado.update(cambios)

    with pytest.raises(ValueError):
        validar_resultados([resultado])


@pytest.mark.parametrize(
    "campo",
    ["es_spam_detectado", "motivo_spam"],
)
def test_exige_campos_spam_en_analisis_exitoso(campo):
    resultado = resultado_valido()
    del resultado[campo]

    with pytest.raises(ValueError):
        validar_resultados([resultado])


def test_analisis_fallido_no_requiere_campos_spam():
    resultado = resultado_valido()
    del resultado["es_spam_detectado"]
    del resultado["motivo_spam"]
    resultado["errores"] = ["Error del proveedor"]

    validar_resultados([resultado])


@pytest.mark.parametrize(
    "version_contrato",
    ["1.2", "1.3"],
)
def test_permite_validar_resultados_historicos(
    version_contrato,
):
    resultado = resultado_valido()
    del resultado["es_spam_detectado"]
    del resultado["motivo_spam"]

    validar_resultados(
        [resultado],
        version_contrato=version_contrato,
    )