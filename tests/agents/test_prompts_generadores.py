from src.agentes.nodos.nodos_generadores import (
    _prompt_boletin,
    _prompt_caso_exito,
    _prompt_linkedin,
    _prompt_preguntas_frecuentes,
)


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

    assert "EJEMPLO DE REFERENCIA" in sistema
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