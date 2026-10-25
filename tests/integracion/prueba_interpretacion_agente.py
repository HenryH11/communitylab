"""Evaluación real del intérprete. Consume cuota; se ejecuta explícitamente."""

from datetime import date

import pytest

from src.agentes.interpretacion import interpretar_consulta
from src.agentes.conversacion import AgenteConversacional


VOCABULARIO = {
    "sentimiento": ["positivo", "muy_positivo", "negativo"],
    "tipo_detectado": ["testimonio", "comentario", "pregunta_tecnica"],
    "canal": ["Discord", "Slack"],
}


@pytest.mark.parametrize(
    ("consulta", "esperado"),
    [
        (
            "hola como estas? podrias hacer un post de linkedin que consideres "
            "los top 5 comentarios de sentimiento positivo?",
            ("borrador", [], "positivo", "linkedin", 5),
        ),
        ("Hola, como estas?", ("conversacion", [], None, None, None)),
        ("asdf qwer zzz", ("aclaracion", [], None, None, None)),
        ("kjsdf 928 zxq", ("aclaracion", [], None, None, None)),
        ("Hola, me das los top comentarios?", ("consulta", [], "positivo", None, None)),
        ("Crea un tuit sobre Python", ("borrador", ["python"], None, "x", None)),
        (
            "Hola, crea un post de LinkedIn sobre la clase de SQL",
            ("borrador", ["sql"], None, "linkedin", None),
        ),
        ("dame un resumen de la comunidad", ("consulta", [], None, None, None)),
    ],
    ids=["saludo-post", "saludo", "ruido", "ruido-numeros", "top", "tuit", "sql", "global"],
)
def test_interpretacion_real(consulta, esperado):
    plan = interpretar_consulta(
        consulta=consulta, hoy=date(2026, 10, 24), historial=[],
        consulta_anterior=None, vocabulario=VOCABULARIO,
    )
    assert (
        plan.intencion, [t.lower() for t in plan.terminos],
        plan.sentimiento, plan.plataforma, plan.cantidad,
    ) == esperado
    assert plan.tipo_detectado is None
    assert plan.canal is None
    assert plan.fecha_desde is None and plan.fecha_hasta is None


def test_seguimientos_reales_conservan_tema_y_permiten_quitar_filtros():
    previo = {"intencion": "consulta", "terminos": ["Python"], "sentimiento": "positivo"}
    for consulta, sentimiento in [
        ("y los negativos?", "negativo"),
        ("ahora sin filtrar sentimiento", None),
    ]:
        plan = interpretar_consulta(
            consulta=consulta, hoy=date(2026, 10, 24), historial=[],
            consulta_anterior=previo, vocabulario=VOCABULARIO,
        )
        assert plan.intencion == "consulta"
        assert [t.lower() for t in plan.terminos] == ["python"]
        assert plan.sentimiento == sentimiento
        previo = plan.model_dump(mode="json")


@pytest.mark.parametrize("modelo", ["super", "lightning"])
def test_peticion_real_completa_genera_post_con_cinco_fuentes_validas(modelo):
    textos = [
        "El taller de Python me ayudo a terminar mi proyecto.",
        "La mentoria me ayudo a resolver mis dudas.",
        "Disfrute colaborar con mi equipo.",
        "Me gusto la explicacion sobre analisis de datos.",
        "El ejercicio practico fue muy util.",
        "La comunidad respondio mis preguntas.",
        "Aprendi a organizar mejor mis datos.",
    ]
    datos = [
        {
            "id": f"ejemplo-{i}", "autor": f"Persona {i}", "texto": texto,
            "sentimiento": "positivo", "tipo_detectado": "testimonio",
        }
        for i, texto in enumerate(textos, start=1)
    ]
    datos.append({
        "id": "negativo", "texto": "El taller necesita mas tiempo",
        "sentimiento": "negativo",
    })
    salida = AgenteConversacional(datos).consultar(
        "hola como estas? podrias hacer un post de linkedin que consideres "
        "los top 5 comentarios de sentimiento positivo?",
        modelo_respuesta=modelo,
    )
    assert salida["modo"] == "borrador"
    assert salida["filtros"]["cantidad"] == 5
    assert salida["filtros"]["sentimiento"] == "positivo"
    assert salida["total_coincidencias"] == 7
    assert salida["borrador"] is not None
    assert salida["borrador"]["plataforma"] == "linkedin"
    assert set(salida["citas"]) <= {f"ejemplo-{i}" for i in range(1, 6)}


def test_fuera_de_alcance_real_sugiere_retomar_el_post_sin_buscar():
    plan = interpretar_consulta(
        consulta="Ahora escríbeme una API en Python",
        hoy=date(2026, 10, 24),
        historial=[
            {"rol": "usuario", "contenido": "Crea un post de LinkedIn con testimonios"},
            {"rol": "asistente", "contenido": "Borrador de LinkedIn listo para revisar."},
        ],
        consulta_anterior={
            "intencion": "borrador", "terminos": [], "plataforma": "linkedin",
            "tipo_detectado": "testimonio",
        },
        vocabulario=VOCABULARIO,
    )
    assert plan.intencion == "fuera_de_alcance"
    assert plan.terminos == []
    assert "linkedin" in plan.respuesta.casefold()
    assert plan.plataforma is None


@pytest.mark.parametrize("consulta", ["dale", "algo nuevo, no lo mismo", "más cercano"])
def test_seguimiento_editorial_real_no_repite_el_menu(consulta):
    plan = interpretar_consulta(
        consulta=consulta, hoy=date(2026, 10, 24),
        historial=[
            {"rol": "usuario", "contenido": "Un post para Instagram sobre Python"},
            {"rol": "asistente", "contenido": (
                "Publicación para Instagram preparada: aprender Python con proyectos. "
                "Puedo darle otro enfoque más cercano."
            )},
        ],
        consulta_anterior={
            "intencion": "borrador", "terminos": ["Python"], "plataforma": "instagram",
        },
        vocabulario=VOCABULARIO,
    )
    assert plan.intencion == "borrador"
    assert plan.plataforma == "instagram"
    assert [t.casefold() for t in plan.terminos] == ["python"]
    assert plan.nueva_version == (consulta != "más cercano")


def test_redaccion_real_aporta_otro_enfoque_sin_pegar_el_testimonio():
    texto = (
        "En el taller aprendí a limpiar datos con Python. Antes revisaba cada "
        "fila a mano y ahora uso un script para encontrar valores faltantes."
    )
    agente = AgenteConversacional([
        {"id": "ficticio-1", "autor": "Persona de prueba", "texto": texto,
         "sentimiento": "positivo", "tipo_detectado": "testimonio"},
    ])
    primera = agente.consultar(
        "Crea una publicación para Instagram basada en este testimonio de Python. "
        "No copies el comentario: dale una apertura y un enfoque propios."
    )
    segunda = agente.consultar("Algo nuevo, no lo mismo; usa otro enfoque.")
    for salida in (primera, segunda):
        assert salida["modo"] == "borrador"
        assert salida["borrador"] is not None
        assert salida["borrador"]["plataforma"] == "instagram"
        assert salida["citas"] == ["ficticio-1"]
        assert texto.casefold() not in salida["borrador"]["contenido"].casefold()
    assert primera["borrador"]["contenido"] != segunda["borrador"]["contenido"]
    assert primera["borrador"]["titulo"] != segunda["borrador"]["titulo"]


@pytest.mark.parametrize(
    "textos",
    [
        [
            "En el taller aprendí a detectar valores faltantes con un script de Python.",
            "Con Python identifiqué filas duplicadas en mi archivo de gastos.",
        ],
        [
            "La explicación de Python fue rápida. Necesito otro ejemplo de valores faltantes.",
        ],
    ],
    ids=["aprendizajes-sin-beneficios-medidos", "dificultad-sin-exito"],
)
def test_redaccion_editorial_real_conserva_hechos_y_atribuciones(textos):
    datos = [
        {
            "id": f"editorial-{i}", "autor": f"Persona ficticia {i}",
            "texto": texto, "tema_principal": "Python",
            "sentimiento": "positivo" if len(textos) > 1 else "negativo",
            "tipo_detectado": "testimonio",
        }
        for i, texto in enumerate(textos, start=1)
    ]
    salida = AgenteConversacional(datos).consultar(
        "Prepara una publicación sobria para Instagram sobre estos mensajes de Python. "
        "Dale una apertura propia y mantén la atribución de cada experiencia.",
        modo_verificacion="verificacion_automatica",
        modelo_respuesta="super",
    )
    assert salida["modo"] == "borrador"
    assert salida["borrador"]["plataforma"] == "instagram"
    assert set(salida["citas"]) == {dato["id"] for dato in datos}
    assert salida["verificacion"]["estado"] == "verificado", {
        "borrador": salida["borrador"], "verificacion": salida["verificacion"],
    }
    afirmaciones = salida["verificacion"]["afirmaciones"]
    assert afirmaciones
    for afirmacion in afirmaciones:
        assert afirmacion["respaldada"]
        assert afirmacion["citas"]
        assert set(afirmacion["citas"]) <= set(salida["citas"])


@pytest.mark.parametrize("inventar_resultados", [False, True], ids=["invitacion", "beneficios-inventados"])
def test_verificacion_editorial_real_no_confunde_invitacion_con_beneficio(inventar_resultados):
    contenido = (
        "Marta cuenta que identificó filas duplicadas con Python. "
        "Si te ocurre algo similar, cuéntanos qué parte te gustaría explorar."
    )
    if inventar_resultados:
        contenido += " Ahora ahorra dos horas al día. Ya adaptamos las clases."
    resultado = AgenteConversacional([])._verificar(
        borrador={
            "plataforma": "instagram", "titulo": "Marta identifica duplicados",
            "contenido": contenido, "hashtags": ["#Python", "#Datos", "#Aprendizaje"],
        },
        evidencia=[{
            "id": "verificacion-editorial", "autor": "Marta",
            "texto": "Con Python identifiqué filas duplicadas en mi archivo.",
        }],
    )
    assert resultado.afirmaciones
    if inventar_resultados:
        sin_respaldo = " ".join(
            afirmacion.afirmacion.casefold()
            for afirmacion in resultado.afirmaciones if not afirmacion.respaldada
        )
        assert "horas" in sin_respaldo, resultado
        assert "clases" in sin_respaldo, resultado
    else:
        assert all(afirmacion.respaldada for afirmacion in resultado.afirmaciones), resultado
        assert all(
            afirmacion.citas == ["verificacion-editorial"]
            for afirmacion in resultado.afirmaciones
        )
