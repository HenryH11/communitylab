from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from langchain_core.runnables import RunnableLambda

from src.agentes import conversacion
from src.agentes.conversacion import AgenteConversacional, BorradorMarketing, GrupoPregunta
from src.agentes.interpretacion import PlanConsulta
from src.app.publicacion_redes import texto_publicacion

pytestmark = pytest.mark.usefixtures("verificacion_analitica_simulada")


def borrador(contenido):
    return {
        "respuesta": "Publicación preparada.", "citas": ["m1"],
        "borrador": {
            "plataforma": "x", "titulo": "Un logro compartido",
            "contenido": contenido, "hashtags": ["#IA", "#Datos", "#Comunidad"],
        },
    }


def agente(generador):
    return AgenteConversacional(
        [{"id": "m1", "texto": "Terminé mi proyecto.", "sentimiento": "positivo"}],
        interprete=lambda **_: PlanConsulta(intencion="borrador", plataforma="x"),
        generador=generador,
    )


def test_esquema_publica_restriccion_de_hashtags_para_el_modelo():
    esquema = BorradorMarketing.model_json_schema()
    assert esquema["properties"]["hashtags"]["items"]["pattern"] == r"^#[^\s#]+$"
    with pytest.raises(ValidationError):
        BorradorMarketing.model_validate(borrador("Texto")["borrador"] | {
            "hashtags": ["IA", "#Datos", "#Comunidad"],
        })


@pytest.mark.parametrize("longitud_final", [279, 280, 281])
def test_x_valida_el_texto_publicable_incluidos_separadores(longitud_final):
    extra = len(texto_publicacion(borrador("x")["borrador"])) - 1
    generar = Mock(side_effect=[borrador("x" * (longitud_final - extra)), borrador("Breve.")])
    salida = agente(generar).consultar("Prepara un post")
    assert generar.call_count == (2 if longitud_final > 280 else 1)
    assert len(texto_publicacion(salida["borrador"])) <= 280


def test_x_no_devuelve_exito_si_la_reescritura_sigue_excediendo():
    generar = Mock(return_value=borrador("x" * 275))
    a = agente(generar)
    with pytest.raises(ValueError, match="280"):
        a.consultar("Prepara un post")
    assert generar.call_count == 2
    assert a.historial == []


def test_faq_recupera_varios_tipos_de_pregunta_y_no_testimonios():
    mensajes = [
        {"id": f"t{i}", "texto": "Muy buena comunidad.", "sentimiento": "muy_positivo",
         "tipo_detectado": "testimonio"} for i in range(10)
    ] + [
        {"id": f"p{i}", "texto": "¿Cómo funciona?", "tipo_detectado": tipo}
        for i, tipo in enumerate(["pregunta_tecnica", "pregunta_programa"] * 5)
    ]
    generar = Mock(side_effect=lambda **k: {
        "respuesta": "Dudas del programa y técnicas; no hay respuestas en las fuentes.",
        "citas": [m["id"] for m in k["evidencia"]],
        "grupos_preguntas": [{
            "duda": "¿Cómo funciona?", "citas": [m["id"] for m in k["evidencia"]],
        }],
    })
    plan = PlanConsulta(
        intencion="consulta", tipos_detectados=["pregunta_tecnica", "pregunta_programa"],
        agrupar_preguntas=True,
    )
    salida = AgenteConversacional(
        mensajes, interprete=lambda **_: plan, generador=generar,
    ).consultar("Identifica preguntas frecuentes")
    assert salida["total_coincidencias"] == 10
    assert set(salida["citas"]) == {f"p{i}" for i in range(10)}
    assert salida["resumen"]["universo_total"] == 20


def test_frecuencias_de_preguntas_se_calculan_sobre_ids_no_sobre_prosa():
    respuesta = conversacion._presentar_preguntas([
        GrupoPregunta(duda="¿Cómo se reintenta?", citas=["a", "b"]),
        GrupoPregunta(duda="¿Cuesta el certificado?", citas=["c"]),
    ], {"a", "b", "c"})
    assert "3 mensajes, agrupados en 2 dudas. Grupos con más de un mensaje: 1." in respuesta
    assert "¿Cómo se reintenta? — 2 mensajes" in respuesta
    assert "¿Cuesta el certificado? — 1 mensaje" in respuesta


@pytest.mark.parametrize("grupos", [
    [GrupoPregunta(duda="¿Una?", citas=["a", "a"])],
    [GrupoPregunta(duda="¿Una?", citas=["a"]), GrupoPregunta(duda="¿Otra?", citas=["a"])],
    [GrupoPregunta(duda="¿Una?", citas=["ajena"])],
    [],
])
def test_grupos_de_preguntas_invalidos_no_se_presentan_como_exito(grupos):
    with pytest.raises(ValueError):
        conversacion._presentar_preguntas(grupos, {"a", "b"})

def test_agregados_distinguen_subconjunto_del_total():
    generar = Mock(return_value={"respuesta": "Un positivo de dos mensajes.", "citas": ["a"]})
    salida = AgenteConversacional(
        [{"id": "a", "texto": "Buen taller.", "sentimiento": "positivo"},
         {"id": "b", "texto": "¿Cuándo empieza?", "sentimiento": "neutral"}],
        interprete=lambda **_: PlanConsulta(intencion="consulta", sentimiento="positivo"),
        generador=generar,
    ).consultar("Resumen positivo")
    assert salida["resumen"]["universo_total"] == 2
    assert salida["resumen"]["total_coincidencias"] == 1


@pytest.mark.parametrize("proveedor", ["nvidia_nim", "gemini"])
def test_verificacion_factual_usa_super_sin_confundir_el_respaldo(monkeypatch, proveedor):
    obtener = Mock(return_value=RunnableLambda(lambda entrada: entrada))
    monkeypatch.setattr(conversacion, "obtener_modelo_generacion_estructurado", obtener)
    conversacion._obtener_cadena_verificacion.cache_clear()
    try:
        conversacion._obtener_cadena_verificacion(proveedor)
        if proveedor == "nvidia_nim":
            assert obtener.call_args.kwargs["modelo"] == conversacion.MODELOS_RESPUESTA["super"]
        else:
            assert obtener.call_args.kwargs["modelo"] is None
    finally:
        conversacion._obtener_cadena_verificacion.cache_clear()
