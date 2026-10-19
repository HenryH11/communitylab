from src.agentes.nodos.nodos_generadores import (
    _prompt_boletin,
    _prompt_caso_exito,
    _prompt_linkedin,
    _prompt_preguntas_frecuentes,
)
from src.agentes.trazabilidad_prompts import calcular_hash_prompt
from langchain_core.prompts import ChatPromptTemplate


def _contenido_sistema(prompt, **contexto):
    mensajes = prompt.format_messages(**contexto)
    return mensajes[0].content


def _contenido_usuario(prompt, **contexto):
    mensajes = prompt.format_messages(**contexto)
    return mensajes[-1].content


def test_linkedin_incluye_few_shot_y_renderiza_contexto():
    contexto = {
        "autor": "Persona de prueba",
        "tema_principal": "empleabilidad",
        "subtema": "primer empleo",
        "texto": "Conseguí mi primer empleo después de presentar mi proyecto.",
    }

    sistema = _contenido_sistema(_prompt_linkedin, **contexto)
    usuario = _contenido_usuario(_prompt_linkedin, **contexto)

    assert "EJEMPLO DE REFERENCIA" in sistema
    assert "Mariana Souza" in sistema
    assert "LangChain" in sistema
    assert "OCI" in sistema

    assert contexto["autor"] in usuario
    assert contexto["tema_principal"] in usuario
    assert contexto["subtema"] in usuario
    assert contexto["texto"] in usuario


def test_boletin_incluye_few_shot_y_renderiza_contexto():
    contexto = {
        "autor": "Persona de prueba",
        "tema_principal": "empleabilidad",
        "subtema": "nueva oportunidad profesional",
        "texto": "Fui seleccionado para una nueva oportunidad profesional.",
    }

    sistema = _contenido_sistema(_prompt_boletin, **contexto)
    usuario = _contenido_usuario(_prompt_boletin, **contexto)

    assert "EJEMPLO DE REFERENCIA" in sistema
    assert "Mariana Souza" in sistema
    assert "Community Highlight" in sistema
    assert "Logro de la comunidad" in sistema

    assert contexto["autor"] in usuario
    assert contexto["tema_principal"] in usuario
    assert contexto["subtema"] in usuario
    assert contexto["texto"] in usuario


def test_preguntas_frecuentes_incluye_few_shot_y_renderiza_contexto():
    contexto = {
        "tipo_detectado": "pregunta_tecnica",
        "subtema": "enrutamiento condicional",
        "texto": "¿Cómo puedo elegir el siguiente nodo según el estado?",
    }
    sistema = _contenido_sistema(
        _prompt_preguntas_frecuentes,
        **contexto,
    )
    usuario = _contenido_usuario(
        _prompt_preguntas_frecuentes,
        **contexto,
    )

    assert "EJEMPLO TÉCNICO" in sistema
    assert "EJEMPLO DE PROGRAMA" in sistema
    assert "Tipo de pregunta: pregunta_tecnica" in usuario
    assert "LangGraph" in sistema
    assert "enrutamiento" in sistema.lower()

    assert contexto["subtema"] in usuario
    assert contexto["texto"] in usuario


def test_caso_exito_incluye_few_shot_y_renderiza_contexto():
    contexto = {
        "autor": "Persona de prueba",
        "texto": "Fui seleccionado para un nuevo puesto.",
    }

    sistema = _contenido_sistema(_prompt_caso_exito, **contexto)
    usuario = _contenido_usuario(_prompt_caso_exito, **contexto)

    assert "EJEMPLO DE REFERENCIA" in sistema
    assert "Mariana Souza" in sistema
    assert "según su testimonio" in sistema.lower()

    assert contexto["autor"] in usuario
    assert contexto["texto"] in usuario


def test_prompts_contienen_reglas_contra_informacion_inventada():
    contextos = (
        (
            _prompt_linkedin,
            {
                "autor": "A",
                "tema_principal": "empleabilidad",
                "subtema": "empleo",
                "texto": "Texto de prueba",
            },
        ),
        (
            _prompt_boletin,
            {
                "autor": "A",
                "tema_principal": "empleabilidad",
                "subtema": "empleo",
                "texto": "Texto de prueba",
            },
        ),
        (
            _prompt_caso_exito,
            {
                "autor": "A",
                "texto": "Texto de prueba",
            },
        ),
    )

    for prompt, contexto in contextos:
        sistema = _contenido_sistema(prompt, **contexto).lower()
        assert "no inventes" in sistema

def test_pregunta_programa_faq_prohibe_inventar_informacion_institucional():
    contexto = {
        "tipo_detectado": "pregunta_programa",
        "subtema": "costo del certificado",
        "texto": "¿El certificado final tiene costo adicional o está incluido en el programa?",
    }

    sistema = _contenido_sistema(
        _prompt_preguntas_frecuentes,
        **contexto,
    )

    usuario = _contenido_usuario(
        _prompt_preguntas_frecuentes,
        **contexto,
    )

    assert "pregunta_programa" in sistema
    assert "NO inventes precios, fechas, condiciones, beneficios" in sistema
    assert "fuente oficial del programa" in sistema
    assert "posterior validación humana" in sistema
    assert "Tipo de pregunta: pregunta_programa" in usuario
    assert "costo del certificado" in usuario


def test_hash_prompt_es_determinista_y_cambia_con_la_plantilla():
    prompt_original = ChatPromptTemplate.from_messages(
        [("system", "Clasifica el mensaje con cuidado.")]
    )
    prompt_modificado = ChatPromptTemplate.from_messages(
        [("system", "Clasifica el mensaje con cuidado y precisión.")]
    )

    huella_original = calcular_hash_prompt(prompt_original)

    assert huella_original == calcular_hash_prompt(prompt_original)
    assert huella_original != calcular_hash_prompt(prompt_modificado)