from src.agentes.modelos import (
    PublicacionLinkedIn,
    SugerenciaPreguntasFrecuentes,
)
from src.agentes.prompts.boletin import prompt_boletin as _prompt_boletin
from src.agentes.prompts.caso_exito import prompt_caso_exito as _prompt_caso_exito
from src.agentes.prompts.linkedin import prompt_linkedin as _prompt_linkedin
from src.agentes.prompts.analisis import template_analisis as _template_analisis
from src.agentes.prompts.preguntas_frecuentes import (
    prompt_preguntas_frecuentes as _prompt_preguntas_frecuentes,
)
from src.agentes.trazabilidad_prompts import calcular_hash_prompt
from langchain_core.prompts import ChatPromptTemplate


def _contenido_sistema(prompt, **contexto) -> str:
    mensajes = prompt.format_messages(**contexto)
    contenido = mensajes[0].content
    assert isinstance(contenido, str)
    return contenido


def _contenido_usuario(prompt, **contexto) -> str:
    mensajes = prompt.format_messages(**contexto)
    contenido = mensajes[-1].content
    assert isinstance(contenido, str)
    return contenido


def test_linkedin_incluye_few_shot_y_renderiza_contexto():
    contexto = {
        "autor": "Persona de prueba",
        "tema_principal": "empleabilidad",
        "subtema": "primer empleo",
        "texto": "Conseguí mi primer empleo después de presentar mi proyecto.",
    }

    sistema = _contenido_sistema(_prompt_linkedin, **contexto)
    usuario = _contenido_usuario(_prompt_linkedin, **contexto)

    assert "EJEMPLOS DE REFERENCIA" in sistema
    assert "Andrés Kuri" in sistema
    assert "Mariana Souza" in sistema
    assert "Laura Ocampo" in sistema

    assert "El mensaje original es la única fuente" in sistema
    assert "AGRADECIMIENTO NO ES APOYO" in sistema
    assert "No cierres la publicación con interpretaciones editoriales" in sistema

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

    assert "EJEMPLOS DE REFERENCIA" in sistema
    assert "Andrés Kuri" in sistema
    assert "Mariana Souza" in sistema
    assert "Laura Ocampo" in sistema

    assert "El mensaje original es la única fuente" in sistema
    assert "referencia temporal" in sistema
    assert "otro proceso" in sistema
    assert "Agradecimiento y apoyo son conceptos diferentes" in sistema

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

    assert "EJEMPLOS DE REFERENCIA" in sistema
    assert "PREGUNTA TÉCNICA CONCEPTUAL" in sistema
    assert "PREGUNTA TÉCNICA QUE REQUIERE CONTEXTO" in sistema
    assert "INFORMACIÓN DEL PROGRAMA" in sistema

    assert contexto["tipo_detectado"] in usuario
    assert contexto["subtema"] in usuario
    assert contexto["texto"] in usuario


def test_caso_exito_incluye_few_shot_y_renderiza_contexto():
    contexto = {
        "autor": "Persona de prueba",
        "texto": "Fui seleccionado para un nuevo puesto.",
    }

    sistema = _contenido_sistema(_prompt_caso_exito, **contexto)
    usuario = _contenido_usuario(_prompt_caso_exito, **contexto)

    assert "EJEMPLOS DE REFERENCIA" in sistema
    assert "Mariana Souza" in sistema
    assert "Laura Ocampo" in sistema
    assert "Andrés Kuri" in sistema

    assert "El mensaje original es la única fuente" in sistema
    assert "No conviertas agradecimiento en evidencia de apoyo" in sistema
    assert "No reasignes una duración a otro proceso" in sistema

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

        assert "mensaje original" in sistema
        assert (
            "no inventes" in sistema
            or "inventar" in sistema
            or "información nueva" in sistema
            or "hechos nuevos" in sistema
        )


def test_pregunta_programa_faq_prohibe_inventar_informacion_institucional():
    contexto = {
        "tipo_detectado": "pregunta_programa",
        "subtema": "costo del certificado",
        "texto": (
            "¿El certificado final tiene costo adicional "
            "o está incluido en el programa?"
        ),
    }

    sistema = _contenido_sistema(
        _prompt_preguntas_frecuentes,
        **contexto,
    ).lower()

    usuario = _contenido_usuario(
        _prompt_preguntas_frecuentes,
        **contexto,
    )

    assert "pregunta_programa" in sistema
    assert "no utilices conocimiento general" in sistema
    assert "no inventes:" in sistema
    assert "precios" in sistema
    assert "fechas" in sistema
    assert "políticas" in sistema
    assert "información oficial vigente del programa" in sistema

    assert contexto["tipo_detectado"] in usuario
    assert contexto["texto"] in usuario


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


def test_faq_usa_respuestas_finales_y_no_metainstrucciones():
    contexto = {
        "tipo_detectado": "pregunta_programa",
        "subtema": "informacion del programa",
        "texto": "¿Dónde puedo confirmar esta información?",
    }

    sistema = _contenido_sistema(
        _prompt_preguntas_frecuentes,
        **contexto,
    )

    assert "listo para curaduría o publicación" in sistema
    assert "notas internas" in sistema
    assert "instrucciones para otro redactor" in sistema

    assert "Una redacción breve que indique" not in sistema
    assert "Una explicación breve centrada" not in sistema


def test_prompt_analisis_considera_impactos_concretos_como_testimonio():
    contexto = {
        "origen": "Comunidad",
        "canal": "#general",
        "idioma": "es",
        "texto": "Apliqué lo aprendido en una situación real.",
    }

    sistema = _contenido_sistema(
        _template_analisis,
        **contexto,
    )

    assert "no requiere necesariamente empleo" in sistema
    assert "aplicar lo aprendido" in sistema
    assert "comprender algo que antes" in sistema
    assert "acceder a una colaboración" in sistema


def test_caso_exito_entrega_contenido_final_sin_notas_internas():
    contexto = {
        "autor": "Persona de prueba",
        "texto": "Conseguí una oportunidad para colaborar en un proyecto.",
    }

    sistema = _contenido_sistema(
        _prompt_caso_exito,
        **contexto,
    )

    assert "directamente publicable" in sistema
    assert "notas internas" in sistema.lower()

    assert "Un texto de 2 a 3 frases que indique" not in sistema
    assert "No se especifica el tipo de proyectos" not in sistema
    assert "No se menciona ningún logro adicional" not in sistema


def test_faq_publica_no_hace_referencia_a_la_pregunta():
    contexto = {
        "tipo_detectado": "pregunta_programa",
        "subtema": "costo del certificado",
        "texto": "¿El certificado tiene algún costo?",
    }

    sistema = _contenido_sistema(
        _prompt_preguntas_frecuentes,
        **contexto,
    ).lower()

    assert (
        "la faq debe funcionar independientemente "
        "de la conversación que la originó"
    ) in sistema

    assert '"la pregunta"' in sistema
    assert '"el mensaje original"' in sistema
    assert '"la información proporcionada"' in sistema

    assert "no explicar ausencias" in sistema


def test_linkedin_normaliza_hashtags_con_numeral():
    publicacion = PublicacionLinkedIn(
        titulo="Aprendizaje de clasificación",
        contenido="Contenido de prueba.",
        hashtags=[
            "Aprendizaje",
            "#Python",
            "ModeloDeClasificacion",
        ],
    )

    assert publicacion.hashtags == [
        "#Aprendizaje",
        "#Python",
        "#ModeloDeClasificacion",
    ]


def test_faq_elimina_repeticiones_accidentales():
    faq = SugerenciaPreguntasFrecuentes(
        tema="Fecha de inscripción",
        respuesta=(
            "Consulta la información oficial para verificar si las "
            "integraciones posteriores posteriores posteriores "
            "después de la semana 0 son permitidas."
        ),
    )

    assert "posteriores posteriores" not in faq.respuesta
    assert (
        "integraciones posteriores después de la semana 0"
        in faq.respuesta
    )


def test_boletin_preserva_comparadores_y_precision_cuantitativa():
    contexto = {
        "autor": "Persona de prueba",
        "tema_principal": "empleabilidad",
        "subtema": "primer empleo",
        "tipo_detectado": "testimonio",
        "texto": "Conseguí mi primer trabajo en menos de 3 meses.",
    }

    sistema = _contenido_sistema(
        _prompt_boletin,
        **contexto,
    ).lower()

    assert "fidelidad cuantitativa" in sistema
    assert "menos de" in sistema
    assert "más de" in sistema
    assert "al menos" in sistema
    assert "no elimines ni modifiques calificadores" in sistema
    assert "consiguió su primer trabajo en menos de 3 meses" in sistema


def test_analisis_distingue_estructura_programa_de_aprendizaje_y_plataforma():
    contexto = {
        "origen": "Comunidad",
        "canal": "#general",
        "idioma": "es",
        "texto": "¿Cuál es la diferencia entre las rutas del programa?",
    }

    sistema = _contenido_sistema(
        _template_analisis,
        **contexto,
    ).lower()

    assert "programa_hackathon vs aprendizaje vs plataforma" in sistema
    assert "rutas o trayectorias disponibles" in sistema
    assert "tema_principal = programa_hackathon" in sistema
    assert "no uses plataforma solo porque un recurso pueda estar alojado" in sistema
    assert "tema_principal = plataforma" in sistema


def test_faq_programa_no_completa_vacios_con_conocimiento_general():
    contexto = {
        "tipo_detectado": "pregunta_programa",
        "subtema": "diferencias entre rutas",
        "texto": (
            "¿Cuál es la diferencia entre las rutas de "
            "Data Analyst y Data Scientist dentro del programa?"
        ),
    }

    sistema = _contenido_sistema(
        _prompt_preguntas_frecuentes,
        **contexto,
    ).lower()

    sistema_normalizado = " ".join(sistema.split())

    assert "conocimiento general" in sistema_normalizado
    assert "información oficial vigente del programa" in sistema_normalizado
    assert "objetivos de una ruta" in sistema_normalizado
    assert "profundidad de los contenidos" in sistema_normalizado
    assert "diferencias entre trayectorias" in sistema_normalizado
    assert (
        "diferencias entre rutas data analyst y data scientist"
        in sistema_normalizado
    )
    assert (
        "las diferencias entre las rutas de data analyst y data scientist "
        "deben confirmarse"
        in sistema_normalizado
    )


def test_boletin_preserva_grado_y_modalidad_del_mensaje():
    contexto = {
        "autor": "Persona de prueba",
        "tema_principal": "empleabilidad",
        "subtema": "networking",
        "texto": (
            "El networking me abrió puertas para colaborar "
            "en proyectos open source."
        ),
    }

    sistema = _contenido_sistema(
        _prompt_boletin,
        **contexto,
    ).lower()

    sistema_normalizado = " ".join(sistema.split())

    assert "fidelidad de grado y modalidad" in sistema_normalizado
    assert "me abrió puertas para colaborar" in sistema_normalizado
    assert "me permitió colaborar" in sistema_normalizado
    assert "nunca pensé que podría aprenderlo" in sistema_normalizado
    assert "consideraba imposible aprenderlo" in sistema_normalizado
    assert "no aumentar" in sistema_normalizado


def test_faq_tecnica_prioriza_precision_terminologica():
    contexto = {
        "tipo_detectado": "pregunta_tecnica",
        "subtema": "diferencia entre Grid y Flexbox",
        "texto": (
            "¿Cuál es la diferencia práctica entre usar Grid y Flexbox "
            "para un layout de dashboard?"
        ),
    }

    sistema = _contenido_sistema(
        _prompt_preguntas_frecuentes,
        **contexto,
    ).lower()

    sistema_normalizado = " ".join(sistema.split())

    assert "precisión terminológica" in sistema_normalizado
    assert "layout no equivale necesariamente a tabla" in sistema_normalizado
    assert "distribuciones unidimensionales" in sistema_normalizado
    assert "organizar elementos en filas y columnas" in sistema_normalizado
    assert "controlar ambas dimensiones" in sistema_normalizado