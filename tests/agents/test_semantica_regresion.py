import pytest

from src.agentes.modelos import AnalisisMensaje
from src.agentes.prompts.analisis import template_analisis, template_analisis_lote
from tests.casos_semanticos_regresion import (
    IDS_PENDIENTES,
    casos_pendientes,
    casos_semanticos,
)


def test_criterios_semanticos_compartidos_por_ambos_modos():
    sistema = template_analisis.messages[0].pretty_repr()
    assert template_analisis_lote.messages[0].pretty_repr() == sistema
    for criterio in (
        "Resolver mensajes con varias funciones",
        "Elegir el tema por el objeto de la petición",
        "Elogio seguido de una propuesta concreta de mejora: feedback",
        "Acceso que proporciona el curso: pregunta_programa",
        "Entrevista laboral y rondas de práctica de entrevista: empleabilidad",
        "Contactar o solicitar apoyo de un mentor: mentoria",
        "Una queja no es captación",
    ):
        assert criterio in sistema


def test_muestra_y_controles_tienen_ids_y_textos_unicos():
    casos = casos_semanticos()
    assert len(casos) == 35
    assert len({identificador for identificador, _, _ in casos}) == 35
    assert len({texto for _, texto, _ in casos}) == 35
    assert sum(identificador.startswith("syn-eval-") for identificador, _, _ in casos) == 27


def test_pendientes_conservan_los_siete_casos_y_controles():
    casos = casos_pendientes()
    assert len(casos) == 19
    assert len({identificador for identificador, _, _ in casos}) == 19
    assert {
        identificador.removeprefix("syn-eval-")
        for identificador, _, _ in casos if identificador.startswith("syn-eval-")
    } == IDS_PENDIENTES
    assert sum(i.startswith("control_") for i, _, _ in casos) == 8
    assert sum(i.startswith("contraste_") for i, _, _ in casos) == 4


def test_revision_operativa_es_igual_en_individual_y_lote():
    individual = template_analisis.messages[1].pretty_repr()
    lote = template_analisis_lote.messages[1].pretty_repr()
    marcador = "Revisa cada resultado con este orden de decisión"
    assert individual[individual.index(marcador):] == lote[lote.index(marcador):]
    assert "Un reporte puntual de fallo" in template_analisis.messages[0].pretty_repr()
    assert "sigue siendo feedback" in individual
    assert "logro concreto alcanzado" in individual


def test_reporte_de_fallo_no_se_ejemplifica_como_comentario():
    sistema = template_analisis.messages[0].pretty_repr()
    ejemplo = sistema.split("Ejemplo 4", 1)[1].split("Ejemplo 5", 1)[0]
    assert "fallo de despliegue remoto" in ejemplo
    assert "tipo_detectado: feedback" in ejemplo
    por_id = {identificador: esperado for identificador, _, esperado in casos_pendientes()}
    for numero in ("0106", "0459", "0495"):
        assert por_id[f"syn-eval-{numero}"]["tipo_detectado"] == "feedback"
    assert por_id["control_logro"]["tipo_detectado"] == "testimonio"
    assert por_id["contraste_aprendizaje"]["tipo_detectado"] == "testimonio"


@pytest.mark.parametrize(
    "identificador,texto,esperado",
    casos_semanticos() + [caso for caso in casos_pendientes() if caso[0].startswith("contraste_")],
)
def test_expectativas_parciales_respetan_contrato(identificador, texto, esperado):
    assert identificador and texto.strip()
    assert esperado["es_spam_detectado"] is False
    assert set(esperado) <= {
        "tipo_detectado", "tema_principal", "sentimiento", "es_spam_detectado"
    }
    analisis = AnalisisMensaje.model_validate({
        "sentimiento": "neutral",
        "tema_principal": "otros",
        "subtema": "Control de contrato",
        "tipo_detectado": "comentario",
        "es_spam_detectado": False,
        "motivo_spam": None,
        **esperado,
    })
    assert all(getattr(analisis, campo) == valor for campo, valor in esperado.items())
