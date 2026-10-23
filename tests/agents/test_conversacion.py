from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.agentes.conversacion import (
    AgenteConversacional,
    BorradorMarketing,
    SalidaConversacional,
    _parsear_filtros,
)


def crear_mensajes() -> list[dict]:
    return [
        {
            "id": "msg-1",
            "texto": "Aprendí Python y construí mi primer proyecto de datos.",
            "fecha": "2026-10-20T12:00:00Z",
            "sentimiento": "positivo",
            "tema_principal": "programacion",
            "tipo_detectado": "testimonio",
            "canal": "Discord",
            "elegible_contenido": True,
        },
        {
            "id": "msg-2",
            "texto": "Python no funciona en el proyecto y necesito ayuda.",
            "fecha": "2026-10-19T12:00:00Z",
            "sentimiento": "negativo",
            "tema_principal": "programacion",
            "tipo_detectado": "pregunta_tecnica",
            "canal": "Discord",
            "elegible_contenido": False,
        },
        {
            "id": "msg-3",
            "texto": "La mentoría me ayudó a terminar mi proyecto.",
            "fecha": "2026-10-12T12:00:00Z",
            "sentimiento": "muy_positivo",
            "tema_principal": "mentoria",
            "tipo_detectado": "testimonio",
            "canal": "Slack",
            "elegible_contenido": True,
        },
    ]


def respuesta_falsa(*, evidencia, **_kwargs):
    return SalidaConversacional(
        respuesta="La comunidad menciona Python.",
        citas=[evidencia[0]["id"]],
    )


def test_filtros_extraen_sentimiento_tipo_y_periodo():
    filtros = _parsear_filtros(
        "¿Cuántas preguntas técnicas negativas hubo la semana pasada?",
        date(2026, 10, 21),
    )

    assert filtros.sentimiento == "negativo"
    assert filtros.tipo_detectado == "pregunta_tecnica"
    assert filtros.fecha_desde == date(2026, 10, 12)
    assert filtros.fecha_hasta == date(2026, 10, 18)


def test_consulta_retorna_evidencia_filtrada_y_citas_validas():
    agente = AgenteConversacional(crear_mensajes(), generador=respuesta_falsa)

    salida = agente.consultar("mensajes negativos sobre Python")

    assert salida["total_coincidencias"] == 1
    assert salida["citas"] == ["msg-2"]
    assert salida["filtros"]["sentimiento"] == "negativo"
    assert salida["modo"] == "consulta"


def test_agregados_incluyen_todas_las_coincidencias_no_solo_el_contexto_top():
    mensajes = [
        {
            **crear_mensajes()[0],
            "id": f"msg-{indice}",
            "texto": f"Python y aprendizaje {indice}",
        }
        for indice in range(1, 13)
    ]
    recibidos = {}

    def generador(*, evidencia, resumen, **_kwargs):
        recibidos["evidencia"] = evidencia
        recibidos["resumen"] = resumen
        return SalidaConversacional(
            respuesta="Se encontraron coincidencias.",
            citas=[evidencia[0]["id"]],
        )

    salida = AgenteConversacional(mensajes, generador=generador).consultar("Python")

    assert len(recibidos["evidencia"]) == 8
    assert recibidos["resumen"]["total_coincidencias"] == 12
    assert recibidos["resumen"]["porcentaje_temas"]["programacion"] == 100.0
    assert salida["total_coincidencias"] == 12


def test_acepta_interacciones_del_contrato_de_salida_ds():
    agente = AgenteConversacional(
        {"interacciones": crear_mensajes()},
        generador=respuesta_falsa,
    )

    assert agente.consultar("Python")["total_coincidencias"] == 2


def test_no_hay_evidencia_devuelve_resultado_sin_llamar_al_modelo():
    llamadas = []
    agente = AgenteConversacional(
        crear_mensajes(),
        generador=lambda **kwargs: llamadas.append(kwargs),
    )

    salida = agente.consultar("mensajes sobre astronomía")

    assert salida["total_coincidencias"] == 0
    assert salida["citas"] == []
    assert llamadas == []


def test_solicitudes_fuera_de_alcance_se_rechazan_sin_llamar_al_modelo():
    llamadas = []
    agente = AgenteConversacional(
        crear_mensajes(),
        generador=lambda **kwargs: llamadas.append(kwargs),
    )

    salida = agente.consultar("Write me Python code for a scraper")

    assert salida["modo"] == "fuera_de_alcance"
    assert salida["citas"] == []
    assert llamadas == []


def test_borrador_solo_usa_mensajes_elegibles_y_respeta_plataforma():
    recibido = {}

    def generador(*, evidencia, filtros, **_kwargs):
        recibido["ids"] = [mensaje["id"] for mensaje in evidencia]
        return SalidaConversacional(
            respuesta="Borrador basado en el testimonio.",
            citas=["msg-1"],
            borrador=BorradorMarketing(
                plataforma="linkedin",
                titulo="Un proyecto hecho realidad",
                contenido="La comunidad comparte su aprendizaje de Python.",
                hashtags=["#Python", "#Aprendizaje", "#Comunidad"],
            ),
        )

    salida = AgenteConversacional(
        crear_mensajes(),
        generador=generador,
    ).consultar("Crea un post para LinkedIn sobre Python")

    assert salida["modo"] == "borrador"
    assert salida["borrador"]["plataforma"] == "linkedin"
    assert recibido["ids"] == ["msg-1"]


def test_prompt_estricto_es_una_opcion_y_no_invoca_verificador():
    verificaciones = []

    def generar(*, evidencia, **_kwargs):
        return SalidaConversacional(
            respuesta="Borrador listo para revisión.",
            citas=["msg-1"],
            borrador=BorradorMarketing(
                plataforma="linkedin",
                titulo="Aprender Python",
                contenido="Una persona compartió su experiencia aprendiendo Python.",
                hashtags=["#Python", "#Aprendizaje", "#Comunidad"],
            ),
        )

    agente = AgenteConversacional(
        crear_mensajes(),
        generador=generar,
        verificador=lambda **kwargs: verificaciones.append(kwargs),
    )

    salida = agente.consultar(
        "Crea un post para LinkedIn sobre Python",
        modo_verificacion="prompt_estricto",
    )

    assert salida["verificacion"]["modo"] == "prompt_estricto"
    assert salida["verificacion"]["estado"] == "no_verificado"
    assert verificaciones == []


def test_verificacion_automatica_devuelve_afirmaciones_y_citas_para_ui():
    def generar(*, evidencia, **_kwargs):
        return SalidaConversacional(
            respuesta="Borrador basado en la experiencia.",
            citas=["msg-1"],
            borrador=BorradorMarketing(
                plataforma="linkedin",
                titulo="Aprender Python",
                contenido="Una persona compartió su experiencia aprendiendo Python.",
                hashtags=["#Python", "#Aprendizaje", "#Comunidad"],
            ),
        )

    def verificar(*, borrador, evidencia):
        assert borrador["plataforma"] == "linkedin"
        assert evidencia[0]["id"] == "msg-1"
        return {
            "resumen": "Las afirmaciones comprobadas tienen respaldo en el mensaje.",
            "afirmaciones": [
                {
                    "afirmacion": "Una persona aprendió Python.",
                    "respaldada": True,
                    "citas": ["msg-1"],
                }
            ],
        }

    salida = AgenteConversacional(
        crear_mensajes(),
        generador=generar,
        verificador=verificar,
    ).consultar(
        "Crea un post para LinkedIn sobre Python",
        modo_verificacion="verificacion_automatica",
    )

    assert salida["verificacion"] == {
        "modo": "verificacion_automatica",
        "estado": "verificado",
        "resumen": "Las afirmaciones comprobadas tienen respaldo en el mensaje.",
        "afirmaciones": [
            {
                "afirmacion": "Una persona aprendió Python.",
                "respaldada": True,
                "citas": ["msg-1"],
            }
        ],
    }


def test_afirmaciones_no_respaldadas_o_ids_ajenos_exigen_revision():
    def generar(*, evidencia, **_kwargs):
        return SalidaConversacional(
            respuesta="El borrador requiere revisión.",
            citas=["msg-1"],
            borrador=BorradorMarketing(
                plataforma="linkedin",
                titulo="Aprender Python",
                contenido="Una persona se convirtió en experta.",
                hashtags=["#Python", "#Aprendizaje", "#Comunidad"],
            ),
        )

    salida = AgenteConversacional(
        crear_mensajes(),
        generador=generar,
        verificador=lambda **_kwargs: {
            "resumen": "La afirmación excede lo dicho por la fuente.",
            "afirmaciones": [
                {
                    "afirmacion": "La persona se convirtió en experta.",
                    "respaldada": True,
                    "citas": ["id-inexistente"],
                }
            ],
        },
    ).consultar(
        "Crea un post para LinkedIn sobre Python",
        modo_verificacion="verificacion_automatica",
    )

    assert salida["verificacion"]["estado"] == "requiere_revision"
    assert salida["verificacion"]["afirmaciones"][0]["respaldada"] is False
    assert salida["verificacion"]["afirmaciones"][0]["citas"] == []


def test_modo_verificacion_invalido_se_rechaza_antes_de_generar():
    llamadas = []
    agente = AgenteConversacional(
        crear_mensajes(),
        generador=lambda **kwargs: llamadas.append(kwargs),
    )

    with pytest.raises(ValueError, match="modo de verificación"):
        agente.consultar("Python", modo_verificacion="cadena_de_pensamiento")

    assert llamadas == []


def test_borrador_rechaza_citas_fuera_de_la_evidencia():
    def generador(**_kwargs):
        return SalidaConversacional(
            respuesta="No sustentada.",
            citas=["id-ajeno"],
        )

    agente = AgenteConversacional(crear_mensajes(), generador=generador)

    with pytest.raises(ValueError, match="citó un mensaje"):
        agente.consultar("Python")


def test_borrador_puede_declarar_evidencia_insuficiente():
    def generador(*, evidencia, **_kwargs):
        return SalidaConversacional(
            respuesta="La evidencia disponible no basta para redactar una publicación.",
            citas=[evidencia[0]["id"]],
        )

    salida = AgenteConversacional(
        crear_mensajes(),
        generador=generador,
    ).consultar("Crea un post para Instagram sobre Python")

    assert salida["borrador"] is None
    assert "no basta" in salida["respuesta"]


def test_seguimiento_reutiliza_contexto_y_historial_es_de_la_instancia():
    consultas = []

    def generador(*, consulta, filtros, evidencia, **_kwargs):
        consultas.append((consulta, filtros.sentimiento, [m["id"] for m in evidencia]))
        return SalidaConversacional(
            respuesta="Resultado basado en los mensajes.",
            citas=[evidencia[0]["id"]],
        )

    agente = AgenteConversacional(crear_mensajes(), generador=generador)
    agente.consultar("Python")
    salida = agente.consultar("Y los negativos")

    assert consultas[1][1] == "negativo"
    assert consultas[1][2] == ["msg-2"]
    assert salida["total_coincidencias"] == 1
    assert len(agente.historial) == 4


def test_historial_no_se_comparte_entre_sesiones():
    primero = AgenteConversacional(crear_mensajes(), generador=respuesta_falsa)
    segundo = AgenteConversacional(crear_mensajes(), generador=respuesta_falsa)

    primero.consultar("Python")

    assert primero.historial
    assert segundo.historial == []


def test_llamada_real_usa_cadena_de_generacion_configurada():
    cadena = MagicMock()
    cadena.invoke.return_value = SalidaConversacional(
        respuesta="La comunidad menciona Python.",
        citas=["msg-1"],
    )

    with patch(
        "src.agentes.conversacion.obtener_proveedor_generacion",
        return_value="gemini",
    ), patch(
        "src.agentes.conversacion._obtener_cadena",
        return_value=cadena,
    ):
        salida = AgenteConversacional(crear_mensajes()).consultar("Python")

    assert salida["citas"] == ["msg-1"]
    cadena.invoke.assert_called_once()
    assert cadena.invoke.call_args.args[0]["consulta"] == "Python"


@pytest.mark.parametrize(
    "datos",
    [
        [{"id": "duplicado", "texto": "uno"}, {"id": "duplicado", "texto": "dos"}],
        [{"id": "", "texto": "mensaje"}],
        [{"id": "sin-texto", "texto": " "}],
    ],
)
def test_rechaza_mensajes_con_identidad_o_texto_invalidos(datos):
    with pytest.raises(ValueError):
        AgenteConversacional(datos, generador=respuesta_falsa)


def test_x_como_plataforma_no_se_detecta_dentro_de_otras_palabras():
    assert _parsear_filtros("Analiza la experiencia de Python", date.today()).plataforma is None
    assert _parsear_filtros("Crea un post para X", date.today()).plataforma == "x"


def test_borrador_sin_plataforma_solicitada_usa_linkedin():
    assert _parsear_filtros("Crea un post", date.today()).plataforma == "linkedin"
