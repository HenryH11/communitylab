"""Contrato DA: excluir ruido antes de IA sin perder opiniones válidas."""

from copy import deepcopy

import pytest

from src.datos.entrega_ia import preparar_paquete_ia


FECHA = "2026-09-17T12:00:00Z"


def mensaje(identificador, texto, **cambios):
    return {
        "id": identificador, "autor": "Ana", "canal": "#dudas", "idioma": "es",
        "tipo": "pregunta_tecnica", "texto": texto, "fecha": FECHA, **cambios,
    }


def preparar(*mensajes):
    datos = {
        "origen_comunidad": "Discord", "periodo_referencia": "Semana_03",
        "interacciones": list(mensajes),
    }
    original = deepcopy(datos)
    paquete = preparar_paquete_ia(datos, fecha_referencia=FECHA, tamano_ciclo=10)
    assert datos == original
    return paquete


@pytest.mark.parametrize("texto,motivo", [
    ("<p> </p>", "texto_vacio"),
    ("https://ejemplo.com www.ejemplo.org", "solo_enlaces"),
    ("[removed]", "contenido_eliminado"),
    ("spam " * 6, "texto_repetitivo"),
    ("compra ahora " * 6, "texto_repetitivo"),
    ("aprovecha esta oferta " * 4, "texto_repetitivo"),
    ("oferta por tiempo limitado " * 3, "texto_repetitivo"),
    ("COMPRA ahora, compra AHORA! " * 3, "texto_repetitivo"),
])
def test_ruido_queda_fuera_de_ambas_poblaciones_y_del_plan(texto, motivo):
    paquete = preparar(mensaje("ruido", texto, tipo="pregunta_programa"))
    assert paquete["completos"]["lotes"][0]["interacciones"] == []
    assert paquete["contenido"]["lotes"][0]["interacciones"] == []
    assert paquete["estados"] == []
    assert paquete["plan"]["ciclos"] == []
    assert paquete["plan"]["pendientes"] == []
    assert paquete["plan"]["ids_contenido"] == []
    evaluacion = paquete["informe"]["lotes"][0]["evaluaciones"][0]
    assert evaluacion["id"] == "ruido"
    assert motivo in evaluacion["motivos_exclusion_sentimiento"]
    assert evaluacion["incluido_sentimiento"] is False
    assert evaluacion["seleccionado"] is False
    assert evaluacion["elegible_faq"] is False


@pytest.mark.parametrize("texto", [
    "Muy mal", "Gracias 😊", "No no no", "muy mal " * 3,
    "¿Cómo funciona este ejemplo de Python? https://ejemplo.com",
    "compra ahora " * 6 + "es el spam que recibí; ¿cómo puedo reportarlo?",
    "Aún no funciona SQL; necesito ayuda con este error 😞",
])
def test_opiniones_y_consultas_permanecen_disponibles_para_analisis(texto):
    paquete = preparar(mensaje("valido", texto, tipo="feedback"))
    assert [estado["id"] for estado in paquete["estados"]] == ["valido"]
    evaluacion = paquete["informe"]["lotes"][0]["evaluaciones"][0]
    assert evaluacion["motivos_exclusion_sentimiento"] == []
    assert paquete["plan"]["pendientes"] == ["valido"]


def test_copia_del_mismo_autor_y_canal_se_excluye_sin_borrar_otras_voces():
    texto = "¿Cómo puedo resolver el error de conexión con OCI?"
    paquete = preparar(
        mensaje("original", texto), mensaje("copia", texto.upper()),
        mensaje("otra-persona", texto, autor="Eva"),
        mensaje("otro-canal", texto, canal="#soporte"),
    )
    assert [e["id"] for e in paquete["estados"]] == ["original", "otra-persona", "otro-canal"]
    copia = paquete["informe"]["lotes"][0]["evaluaciones"][1]
    assert copia["motivos_exclusion_sentimiento"] == ["duplicado"]


def test_pregunta_del_programa_conserva_la_elegibilidad_faq():
    paquete = preparar(mensaje("faq", "¿Cuándo entregan el certificado del programa?", tipo="pregunta_programa"))
    assert paquete["estados"][0]["elegible_faq"] is True
    assert paquete["informe"]["resumen_sentimiento"]["excluidas_calidad"] == 0
