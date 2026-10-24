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
