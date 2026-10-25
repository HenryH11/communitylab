import pytest

from src.agentes.modelos import AnalisisMensaje
from src.agentes.prompts.analisis import template_analisis, template_analisis_lote
from tests.casos_semanticos_regresion import casos_semanticos


def test_criterios_semanticos_compartidos_por_ambos_modos():
    sistema = template_analisis.messages[0].prompt.template
    assert template_analisis_lote.messages[0].prompt.template == sistema
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


@pytest.mark.parametrize("identificador,texto,esperado", casos_semanticos())
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
