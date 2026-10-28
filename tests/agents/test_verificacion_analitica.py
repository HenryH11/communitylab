from unittest.mock import Mock, patch

import pytest
from langchain_core.runnables import RunnableLambda

from src.agentes import conversacion, interpretacion, modelo_ia
from src.agentes.consumo import LimiteConsumo
from src.agentes.conversacion import AgenteConversacional, SalidaVerificacion
from src.agentes.interpretacion import PlanConsulta


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setattr("src.agentes.contexto.load_dotenv", lambda: None)
    monkeypatch.setattr("src.agentes.consumo.load_dotenv", lambda: None)
    for variable, valor in {
        "COMMUNITYLAB_CONTEXTO_TOKENS": 32768,
        "COMMUNITYLAB_SALIDA_TOKENS": 4096,
        "COMMUNITYLAB_MAX_INTENTOS_CONSULTA": 30,
        "COMMUNITYLAB_MAX_TOKENS_CONSULTA": 250000,
        "COMMUNITYLAB_MAX_CONSULTAS_ACTIVAS": 2,
        "COMMUNITYLAB_MAX_INTENTOS_HORA": 0,
    }.items():
        monkeypatch.setenv(variable, str(valor))


def crear_agente(verificador, respuesta="Una persona terminó un ejercicio.", **plan):
    return AgenteConversacional(
        [{"id": "a", "texto": "Una persona terminó un ejercicio.", "tema_principal": "aprendizaje"}],
        interprete=lambda **_: PlanConsulta(intencion="consulta", **plan),
        generador=lambda **_: {
            "respuesta": respuesta, "citas": ["a"],
            "hallazgos": [{"afirmacion": "Una persona terminó un ejercicio.", "citas": ["a"]}],
        },
        verificador=verificador,
    )


def revision(afirmacion, *, respaldada=True, citas=None, agregado=False):
    return {
        "resumen": "Resultado de revisión.",
        "afirmaciones": [{
            "afirmacion": afirmacion, "respaldada": respaldada,
            "citas": ["a"] if citas is None else citas,
            "respaldo_agregado": agregado,
        }],
    }


@pytest.mark.parametrize("modo", ["prompt_estricto", "verificacion_automatica"])
def test_texto_inventado_con_hallazgos_correctos_se_rechaza(modo):
    def verificar(**entrada):
        candidato = entrada["borrador"]
        assert candidato["respuesta"] == "Todas las personas consiguieron empleo."
        assert candidato["hallazgos_a_comprobar"][0]["afirmacion"] == "Una persona terminó un ejercicio."
        assert entrada["evidencia"][0]["texto"] == "Una persona terminó un ejercicio."
        return {
            "resumen": "El texto contiene una generalización no sustentada.",
            "afirmaciones": [
                {"afirmacion": "Una persona terminó un ejercicio.", "respaldada": True, "citas": ["a"]},
                {"afirmacion": "Todas las personas consiguieron empleo.", "respaldada": False, "citas": []},
            ],
        }

    agente = crear_agente(verificar, "Todas las personas consiguieron empleo.")
    with pytest.raises(ValueError, match="No se pudo comprobar"):
        agente.consultar("Resume resultados", modo_verificacion=modo)
    assert agente.historial == []
    assert agente._ultimo_borrador is None
    assert agente._ultimo_plan is None


def test_respuesta_respaldada_se_guarda_y_expone_revision_obligatoria():
    verificar = Mock(return_value=revision("Una persona terminó un ejercicio."))
    agente = crear_agente(verificar)
    salida = agente.consultar("Resume")
    assert salida["verificacion"]["estado"] == "verificado"
    assert salida["verificacion"]["obligatoria"] is True
    assert salida["verificacion"]["alcance"] == "texto_final_y_hallazgos"
    assert verificar.call_count == 1
    assert len(agente.historial) == 2
    assert verificar.call_args.kwargs["agregados"]["total_coincidencias"] == 1
    assert "mensajes_enviados_al_modelo" not in verificar.call_args.kwargs["agregados"]


@pytest.mark.parametrize("fallo", ["generacion", "revision", "presupuesto"])
def test_consulta_fallida_no_cambia_plan_ni_contexto_del_siguiente_turno(fallo):
    planes = [
        PlanConsulta(intencion="consulta", campos_listado=["id"]),
        PlanConsulta(intencion="consulta", sentimiento="positivo"),
        PlanConsulta(intencion="consulta", campos_listado=["id"]),
    ]
    interpretar = Mock(side_effect=planes)
    if fallo == "generacion":
        generar = Mock(side_effect=RuntimeError("Fallo de generación"))
        verificar = Mock()
    else:
        generar = Mock(return_value={"respuesta": "Un hecho.", "citas": ["a"]})
        verificar = Mock(
            side_effect=LimiteConsumo("Presupuesto agotado") if fallo == "presupuesto" else None,
            return_value=revision("Un hecho.", respaldada=False),
        )
    agente = AgenteConversacional(
        [{"id": "a", "texto": "Un hecho.", "sentimiento": "positivo"}],
        interprete=interpretar, generador=generar, verificador=verificar,
    )
    agente.consultar("Lista los IDs")
    historial = agente.historial
    with pytest.raises((RuntimeError, ValueError, LimiteConsumo)):
        agente.consultar("Ahora analiza los positivos")
    assert agente.historial == historial
    assert agente._ultimo_plan == planes[0]
    agente.consultar("Otra vez")
    assert interpretar.call_args.kwargs["consulta_anterior"] == planes[0].model_dump(mode="json")
    assert agente._ultimo_plan == planes[2]


@pytest.mark.parametrize("plan", [
    PlanConsulta(intencion="consulta", campos_listado=["id"]),
    PlanConsulta(intencion="consulta", listar_autores=True),
    PlanConsulta(intencion="consulta", canal="Inexistente"),
    PlanConsulta(intencion="consulta"),
])
def test_respuestas_completadas_actualizan_el_plan(plan):
    agente = crear_agente(
        lambda **_: revision("Una persona terminó un ejercicio."),
    )
    agente._interprete = lambda **_: plan
    agente.consultar("Consulta")
    assert agente._ultimo_plan == plan
    assert len(agente.historial) == 2


def test_conteo_correcto_puede_respaldarse_sin_inventar_una_cita():
    def verificar(**entrada):
        assert entrada["agregados"]["distribucion_temas"] == {"aprendizaje": 1}
        return revision("Hay un mensaje de aprendizaje.", citas=[], agregado=True)
    salida = crear_agente(verificar, "Hay un mensaje de aprendizaje.").consultar("Cuenta temas")
    afirmacion = salida["verificacion"]["afirmaciones"][0]
    assert afirmacion["respaldo_agregado"] is True
    assert afirmacion["citas"] == []


@pytest.mark.parametrize("resultado", [
    {"resumen": "Vacío", "afirmaciones": []},
    revision("Hecho", citas=[]),
    revision("Hecho", citas=["inventado"]),
    revision("Hecho", respaldada=False),
])
def test_revision_vacia_no_respaldada_o_con_fuentes_ajenas_no_es_exito(resultado):
    agente = crear_agente(lambda **_: resultado)
    with pytest.raises(ValueError):
        agente.consultar("Resume")
    assert agente.historial == []


@pytest.mark.parametrize("error", [RuntimeError("Fallo de proveedor"), LimiteConsumo("Presupuesto agotado")])
def test_fallo_de_revision_no_guarda_respuesta(error):
    agente = crear_agente(Mock(side_effect=error))
    with pytest.raises(type(error)):
        agente.consultar("Resume")
    assert agente.historial == []


def test_listado_literal_no_invoca_revision():
    verificar = Mock(side_effect=AssertionError("Un listado local no necesita revisión IA"))
    salida = crear_agente(verificar, campos_listado=["tema"]).consultar("Lista temas")
    assert salida["registros"] == [{"tema": "aprendizaje"}]
    verificar.assert_not_called()


def test_agregados_se_mantienen_en_todos_los_lotes_y_no_se_confunden_con_fuentes():
    llamadas = []

    def verificar(**entrada):
        llamadas.append(entrada)
        assert entrada["agregados"]["total_coincidencias"] == 8
        objetivos = entrada.get("afirmaciones_objetivo")
        if not entrada["evidencia"]:
            return {
                "resumen": "Extracción del texto completo.",
                "afirmaciones": [
                    {"afirmacion": "Hay ocho mensajes.", "respaldada": True,
                     "respaldo_agregado": True, "citas": []},
                    {"afirmacion": "Todos encontraron empleo.", "respaldada": False, "citas": []},
                ],
            }
        assert isinstance(objetivos, list)
        assert objetivos == ["Hay ocho mensajes.", "Todos encontraron empleo."]
        return {
            "resumen": "Conteo correcto, logro no respaldado.",
            "afirmaciones": [
                {"afirmacion": objetivos[0], "respaldada": True,
                 "respaldo_agregado": True, "citas": []},
                {"afirmacion": objetivos[1], "respaldada": False, "citas": []},
            ],
        }

    agente = AgenteConversacional([], verificador=verificar)
    with pytest.raises(ValueError, match="No se pudo comprobar"):
        agente._verificar_analisis(
            respuesta="Hay ocho mensajes. Todos encontraron empleo.",
            hallazgos=[],
            evidencia=[{"id": str(i), "texto": "Mensaje sin logros. " * 800} for i in range(8)],
            resumen={"total_coincidencias": 8},
        )
    assert len(llamadas) > 2
    assert sum(len(c["evidencia"]) for c in llamadas) == 8


def test_revision_por_lotes_combina_conteo_autorizado_y_hecho_en_ultima_fuente():
    def verificar(**entrada):
        ids = {m["id"] for m in entrada["evidencia"]}
        return {
            "resumen": "Conteo y hecho revisados.",
            "afirmaciones": [
                {"afirmacion": "Hay nueve mensajes.", "respaldada": True,
                 "respaldo_agregado": True, "citas": []},
                {"afirmacion": "Una persona terminó un ejercicio.",
                 "respaldada": "final" in ids, "citas": ["final"] if "final" in ids else []},
            ],
        }

    agente = AgenteConversacional([], verificador=verificar)
    salida = agente._verificar_analisis(
        respuesta="Hay nueve mensajes. Una persona terminó un ejercicio.",
        hallazgos=[],
        evidencia=[
            *[{"id": str(i), "texto": "Un mensaje. " * 1200} for i in range(8)],
            {"id": "final", "texto": "Una persona terminó un ejercicio."},
        ],
        resumen={"total_coincidencias": 9},
    )
    assert salida["estado"] == "verificado"
    assert salida["afirmaciones"][0]["respaldo_agregado"] is True
    assert salida["afirmaciones"][1]["citas"] == ["final"]


def test_el_prompt_exige_examinar_texto_y_no_tratar_hallazgos_como_evidencia():
    from src.agentes.prompts.verificacion import prompt_verificacion
    texto = str(prompt_verificacion.format_messages(
        borrador='{"tipo": "analisis", "respuesta": "Texto final", "hallazgos_a_comprobar": []}',
        evidencia="[]",
    ))
    assert "TODA la respuesta final" in texto
    assert "NUNCA evidencia autorizada" in texto
    assert "no restrinjas la revisión a los hallazgos" in texto


@pytest.mark.parametrize("limite", [3, 2])
def test_revision_analitica_real_pasa_por_el_mismo_contador_de_consumo(monkeypatch, limite):
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_CONSULTA", str(limite))
    factories = [
        interpretacion._obtener_cadena_interpretacion,
        conversacion._obtener_cadena, conversacion._obtener_cadena_verificacion,
    ]
    for factory in factories:
        factory.cache_clear()

    def proveedor(esquema, **kwargs):
        def responder(entrada):
            if esquema is PlanConsulta:
                return {"intencion": "consulta"}
            if esquema is SalidaVerificacion:
                contenido = str(entrada)
                assert "hallazgos_a_comprobar" in contenido
                assert "total_coincidencias" in contenido
                return revision("Una persona terminó un ejercicio.")
            return {
                "respuesta": "Una persona terminó un ejercicio.", "citas": ["a"],
                "hallazgos": [{"afirmacion": "Una persona terminó un ejercicio.", "citas": ["a"]}],
            }
        return RunnableLambda(responder)

    try:
        with (
            patch.object(modelo_ia, "obtener_modelo_gemini_estructurado", side_effect=proveedor),
            patch.object(conversacion, "obtener_proveedor_generacion", return_value="gemini"),
            patch.object(interpretacion, "obtener_proveedor_generacion", return_value="gemini"),
        ):
            agente = AgenteConversacional([{"id": "a", "texto": "Una persona terminó un ejercicio."}])
            if limite == 2:
                with pytest.raises(LimiteConsumo):
                    agente.consultar("Resume")
                assert agente.historial == []
            else:
                salida = agente.consultar("Resume")
                assert salida["consumo"]["intentos_proveedor"] == 3
                assert salida["verificacion"]["obligatoria"] is True
    finally:
        for factory in factories:
            factory.cache_clear()
