from datetime import date
from unittest.mock import Mock, patch

from pydantic import ValidationError
import pytest

from src.agentes import interpretacion
from src.agentes.conversacion import AgenteConversacional, SalidaConversacional
from src.agentes.interpretacion import ErrorInterpretacion, PlanConsulta
from src.app.errores_agente import explicar_error
from src.agentes.plataformas import NOMBRES_PLATAFORMA


EJEMPLO = (
    "hola como estas? podrias hacer un post de linkedin que consideres "
    "los top 5 comentarios de sentimiento positivo?"
)


@pytest.mark.parametrize("valores", [
    {"tipo_detectado": "testimonio", "tipos_detectados": ["pregunta_tecnica"]},
    {"tipos_detectados": ["  "]},
    {"tipos_detectados": ["a" * 251]},
    {"intencion": "conversacion", "respuesta": "Hola", "tipos_detectados": ["testimonio"]},
])
def test_filtros_alternativos_rechazan_planes_ambiguos_o_invalidos(valores):
    with pytest.raises(ValidationError):
        PlanConsulta.model_validate({"intencion": "consulta", **valores})


def test_filtros_alternativos_limpian_espacios_y_duplicados():
    plan = PlanConsulta(
        intencion="consulta",
        tipos_detectados=[" pregunta_tecnica ", "pregunta_tecnica", "pregunta_programa"],
    )
    assert plan.tipos_detectados == ["pregunta_tecnica", "pregunta_programa"]


def mensajes():
    return [
        {
            "id": str(indice), "texto": f"El taller {indice} estuvo excelente",
            "sentimiento": "positivo" if indice % 2 else "muy_positivo",
            "canal": "Discord", "fecha": "2026-10-20T12:00:00Z",
        }
        for indice in range(1, 10)
    ] + [{"id": "negativo", "texto": "El taller estuvo mal", "sentimiento": "negativo"}]


def generador(**kwargs):
    return SalidaConversacional(
        respuesta="Respuesta con evidencia.",
        citas=[m["id"] for m in kwargs["evidencia"]],
    )


@pytest.mark.parametrize("plataforma", list(NOMBRES_PLATAFORMA))
def test_destino_de_texto_llega_del_plan_a_la_publicacion(plataforma):
    from src.agentes.conversacion import BorradorMarketing

    plan = PlanConsulta.model_validate({
        "intencion": "borrador", "plataforma": plataforma,
    })
    generar = Mock(return_value=SalidaConversacional(
        respuesta="Contenido preparado.", citas=["2"],
        borrador=BorradorMarketing.model_validate({
            "plataforma": plataforma, "titulo": "Comunidad",
            "contenido": "Aprendemos juntos.",
            "hashtags": ["#Comunidad", "#Taller", "#Aprendizaje"],
        }),
    ))
    agente = AgenteConversacional(
        mensajes(), interprete=lambda **_: plan, generador=generar,
    )
    salida = agente.consultar(f"Prepara contenido para {plataforma}")
    assert salida["borrador"]["plataforma"] == plataforma
    assert salida["filtros"]["plataforma"] == plataforma
    assert generar.call_args.kwargs["filtros"].plataforma == plataforma


@pytest.mark.parametrize("plataforma", ["tiktok", "youtube", "https://evil.example"])
def test_multimedia_y_destinos_arbitrarios_no_entran_en_el_contrato(plataforma):
    with pytest.raises(ValidationError):
        PlanConsulta.model_validate({"intencion": "borrador", "plataforma": plataforma})


def test_ejemplo_del_usuario_busca_solo_positivos_y_envia_cinco_al_borrador():
    interprete = Mock(return_value=PlanConsulta(
        intencion="borrador", plataforma="linkedin", sentimiento="positivo", cantidad=5,
    ))
    generar = Mock(side_effect=generador)
    agente = AgenteConversacional(mensajes(), interprete=interprete, generador=generar)

    with patch.object(agente, "_buscar", wraps=agente._buscar) as buscar:
        salida = agente.consultar(EJEMPLO)

    assert interprete.call_args.kwargs["consulta"] == EJEMPLO
    assert buscar.call_args.args[0] == ""
    assert salida["modo"] == "borrador"
    assert salida["filtros"]["plataforma"] == "linkedin"
    assert salida["filtros"]["cantidad"] == 5
    assert salida["total_coincidencias"] == 9
    assert len(generar.call_args.kwargs["evidencia"]) == 5
    assert salida["citas"] == ["2", "4", "6", "8", "1"]


@pytest.mark.parametrize(
    ("consulta", "intencion", "respuesta"),
    [
        ("Hola, ¿cómo estás?", "conversacion", "¡Hola! ¿Qué quieres saber de la comunidad?"),
        ("Gracias, eso era todo", "conversacion", "¡Con gusto!"),
        ("asdf qwer 123", "aclaracion", "No entendí tu petición. ¿Qué quieres consultar?"),
        ("Hazlo como antes", "aclaracion", "¿Qué contenido quieres que adapte?"),
        ("Escribe una API", "fuera_de_alcance", "Puedo analizar mensajes, no programar una API."),
    ],
)
def test_interacciones_sin_busqueda_no_recuperan_datos_ni_generan(
    consulta, intencion, respuesta,
):
    agente = AgenteConversacional(
        [], interprete=lambda **_: PlanConsulta(intencion=intencion, respuesta=respuesta),
    )
    with (
        patch.object(agente, "_buscar") as buscar,
        patch.object(agente, "_generar") as generar,
        patch.object(agente, "_verificar") as verificar,
    ):
        salida = agente.consultar(consulta, modo_verificacion="verificacion_automatica")

    buscar.assert_not_called()
    generar.assert_not_called()
    verificar.assert_not_called()
    assert salida["respuesta"] == respuesta
    assert salida["modo"] == intencion
    assert salida["citas"] == []
    assert salida["borrador"] is None
    assert len(agente.historial) == 2


def test_el_modelo_recibe_contexto_y_puede_quitar_filtros_sin_herencia_forzada():
    interpretar = Mock(side_effect=[
        PlanConsulta(intencion="consulta", terminos=["taller"], sentimiento="negativo"),
        PlanConsulta(intencion="conversacion", respuesta="¡De nada!"),
        PlanConsulta(intencion="consulta", terminos=["taller"]),
    ])
    agente = AgenteConversacional(mensajes(), interprete=interpretar, generador=generador)
    agente.consultar("Los negativos sobre el taller")
    agente.consultar("gracias")
    salida = agente.consultar("Ahora sin filtrar sentimiento", hoy=date(2026, 10, 24))

    argumentos = interpretar.call_args.kwargs
    assert argumentos["hoy"] == date(2026, 10, 24)
    assert argumentos["consulta_anterior"]["sentimiento"] == "negativo"
    assert argumentos["consulta_anterior"]["terminos"] == ["taller"]
    assert argumentos["historial"][-2]["contenido"] == "gracias"
    assert argumentos["vocabulario"]["canal"] == ["Discord"]
    assert salida["filtros"]["sentimiento"] is None
    assert salida["total_coincidencias"] == 10


def test_tema_desconocido_no_se_elimina_para_forzar_coincidencias():
    agente = AgenteConversacional(
        mensajes(),
        interprete=lambda **_: PlanConsulta(intencion="consulta", terminos=["astronomía"]),
    )
    with patch.object(agente, "_generar") as generar:
        salida = agente.consultar("Hola, ¿qué dijeron de astronomía?")

    generar.assert_not_called()
    assert salida["total_coincidencias"] == 0
    assert "astronomia" in salida["respuesta"]


def test_canal_de_origen_es_distinto_de_plataforma_destino():
    agente = AgenteConversacional(
        mensajes(),
        interprete=lambda **_: PlanConsulta(
            intencion="borrador", canal="Discord", plataforma="linkedin", cantidad=2,
        ),
        generador=generador,
    )
    salida = agente.consultar("Post de LinkedIn con dos comentarios de Discord")

    assert salida["total_coincidencias"] == 9
    assert salida["filtros"]["canal"] == "Discord"
    assert len(salida["citas"]) == 2


def test_error_del_interprete_no_activa_reglas_locales_ni_busqueda():
    interpretar = Mock(side_effect=ConnectionError("sin conexión"))
    agente = AgenteConversacional(mensajes(), interprete=interpretar)
    with patch.object(agente, "_buscar") as buscar:
        with pytest.raises(ConnectionError):
            agente.consultar("Python")

    buscar.assert_not_called()
    assert agente.historial == []


@pytest.mark.parametrize("seleccion", ["super", "lightning"])
def test_modelo_elegido_solo_se_envia_a_generacion(seleccion):
    from src.agentes.conversacion import MODELOS_RESPUESTA

    interpretar = Mock(return_value=PlanConsulta(
        intencion="borrador", plataforma="linkedin",
    ))
    agente = AgenteConversacional(mensajes(), interprete=interpretar)
    generar = Mock()
    generar.invoke.return_value = {
        "respuesta": "Listo.", "citas": ["1"],
        "borrador": {
            "plataforma": "linkedin", "titulo": "Título", "contenido": "Contenido",
            "hashtags": ["#a", "#b", "#c"],
        },
    }
    verificar = Mock()
    verificar.invoke.return_value = {
        "afirmaciones": [], "resumen": "Revisión del borrador.",
    }

    def cadena(proveedor, temperatura=None, top_p=None, modelo_id=None):
        return generar

    with (
        patch("src.agentes.conversacion._obtener_cadena", side_effect=cadena) as obtener,
        patch("src.agentes.conversacion._obtener_cadena_verificacion", return_value=verificar) as revision,
        patch("src.agentes.conversacion.obtener_proveedor_generacion", return_value="gemini"),
        patch(
            "src.agentes.conversacion.invocar_modelo_con_fallback",
            side_effect=lambda entrada, primario, respaldo: {"resultado": primario(entrada)},
        ),
    ):
        agente.consultar(
            "Un post", modelo_respuesta=seleccion,
            modo_verificacion="verificacion_automatica",
        )

    assert obtener.call_args.kwargs == {"modelo_id": MODELOS_RESPUESTA[seleccion]}
    assert revision.call_args.args == ("gemini",)
    assert "modelo" not in interpretar.call_args.kwargs


def test_cambio_de_modelo_no_cambia_historial_ni_otras_sesiones():
    from src.agentes.conversacion import MODELOS_RESPUESTA

    interpretar = lambda **_: PlanConsulta(intencion="consulta")
    primero = AgenteConversacional(mensajes(), interprete=interpretar, generador=generador)
    segundo = AgenteConversacional(mensajes(), interprete=interpretar, generador=generador)
    with patch.object(primero, "_generar", wraps=primero._generar) as generar_primero:
        primero.consultar("Resumen", modelo_respuesta="super")
        primero.consultar("Otro resumen", modelo_respuesta="lightning")
    segundo.consultar("Resumen", modelo_respuesta="super")

    assert [c.kwargs["modelo"] for c in generar_primero.call_args_list] == [
        MODELOS_RESPUESTA["super"], MODELOS_RESPUESTA["lightning"],
    ]
    assert len(primero.historial) == 4
    assert len(segundo.historial) == 2


def test_modelo_desconocido_se_rechaza_antes_de_interpretar():
    interpretar = Mock()
    agente = AgenteConversacional([], interprete=interpretar)
    with pytest.raises(ValueError, match="modelo de respuesta"):
        agente.consultar("Hola", modelo_respuesta="inventado")
    interpretar.assert_not_called()


def test_redireccion_preserva_plan_para_retomar_y_no_busca_fuera_de_alcance():
    interpretar = Mock(side_effect=[
        PlanConsulta(intencion="borrador", plataforma="linkedin", sentimiento="positivo"),
        PlanConsulta(
            intencion="fuera_de_alcance",
            respuesta="No puedo programar esa API. ¿Retomamos el post de LinkedIn?",
        ),
        PlanConsulta(intencion="borrador", plataforma="linkedin", sentimiento="positivo"),
    ])
    agente = AgenteConversacional(mensajes(), interprete=interpretar, generador=generador)
    agente.consultar("Un post positivo")
    with patch.object(agente, "_buscar") as buscar:
        salida = agente.consultar("Ahora programa una API")
        buscar.assert_not_called()
    agente.consultar("Sí, retomemos")
    assert "LinkedIn" in salida["respuesta"]
    assert interpretar.call_args.kwargs["consulta_anterior"]["plataforma"] == "linkedin"


@pytest.mark.parametrize(
    "plan",
    [
        {"intencion": "borrador"},
        {"intencion": "consulta", "cantidad": -1},
        {"intencion": "consulta", "cantidad": True},
        {"intencion": "consulta", "cantidad": 1001},
        {"intencion": "consulta", "fecha_desde": "2026-10-24", "fecha_hasta": "2026-10-20"},
        {"intencion": "consulta", "sentimiento": "increíble"},
        {"intencion": "consulta", "terminos": [" "]},
        {"intencion": "consulta", "terminos": ["a" * 121]},
        {"intencion": "consulta", "terminos": ["a"] * 13},
        {"intencion": "conversacion", "respuesta": ""},
        {"intencion": "conversacion", "respuesta": "Hola", "terminos": ["Python"]},
        {"intencion": "consulta", "sql": "SELECT *"},
    ],
)
def test_planes_invalidos_se_rechazan(plan):
    with pytest.raises(ValidationError):
        PlanConsulta.model_validate(plan)


def test_plan_invalido_se_muestra_como_error_y_no_como_consulta_global():
    agente = AgenteConversacional(
        mensajes(), interprete=lambda **_: {"intencion": "conversacion"},
    )
    with patch.object(agente, "_buscar") as buscar:
        with pytest.raises(ErrorInterpretacion) as error:
            agente.consultar("Hola")

    buscar.assert_not_called()
    assert "interpretar" in explicar_error(error.value)
    assert "validation" not in explicar_error(error.value).lower()


@pytest.mark.parametrize("proveedor", ["gemini", "nvidia_nim"])
def test_cadena_interpretacion_usa_esquema_y_temperatura_cero(proveedor):
    interpretacion._obtener_cadena_interpretacion.cache_clear()
    try:
        with (
            patch.object(interpretacion, "obtener_modelo_generacion_estructurado") as modelo,
            patch.object(
                interpretacion, "obtener_modelo_nvidia_interpretacion",
                return_value="nvidia/nemotron-3.5-super-vl-120b-a12b",
            ),
        ):
            interpretacion._obtener_cadena_interpretacion(proveedor)
        assert modelo.call_args.args == (PlanConsulta,)
        assert modelo.call_args.kwargs == {
            "proveedor": proveedor, "ruta": "conversacion", "temperatura": 0.0,
            "modelo": "nvidia/nemotron-3.5-super-vl-120b-a12b" if proveedor == "nvidia_nim" else None,
        }
    finally:
        interpretacion._obtener_cadena_interpretacion.cache_clear()


def test_modelo_interpretacion_es_independiente_del_modelo_redactor(monkeypatch):
    from src.agentes import configuracion_ia

    monkeypatch.setattr(configuracion_ia, "load_dotenv", lambda: None)
    monkeypatch.setenv("COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO", "false")
    monkeypatch.setenv("COMMUNITYLAB_MODELO_NVIDIA", "redactor")
    monkeypatch.delenv("COMMUNITYLAB_MODELO_NVIDIA_INTERPRETACION", raising=False)
    assert configuracion_ia.obtener_modelo_nvidia_interpretacion() == (
        "nvidia/nemotron-3.5-super-vl-120b-a12b"
    )
    monkeypatch.setenv("COMMUNITYLAB_MODELO_NVIDIA_INTERPRETACION", "interprete")
    assert configuracion_ia.obtener_modelo_nvidia_interpretacion() == "interprete"


def test_invocacion_del_interprete_real_serializa_contexto_y_valida_plan():
    cadena = Mock()
    cadena.invoke.return_value = {
        "intencion": "borrador", "plataforma": "linkedin", "cantidad": 5,
        "sentimiento": "positivo",
    }
    with (
        patch.object(interpretacion, "obtener_proveedor_generacion", return_value="gemini"),
        patch.object(interpretacion, "_obtener_cadena_interpretacion", return_value=cadena),
    ):
        plan = interpretacion.interpretar_consulta(
            consulta=EJEMPLO, hoy=date(2026, 10, 24), historial=[],
            consulta_anterior=None, vocabulario={},
        )

    assert plan.terminos == []
    entrada = cadena.invoke.call_args.args[0]
    assert entrada["consulta"] == EJEMPLO
    assert entrada["hoy"] == "2026-10-24"
    assert entrada["consulta_anterior"] == "null"


def test_interprete_nvidia_conserva_fallback_a_gemini():
    primario, respaldo = Mock(), Mock()
    primario.invoke.side_effect = ConnectionError("caída")
    respaldo.invoke.return_value = PlanConsulta(intencion="conversacion", respuesta="Hola")
    with (
        patch.object(interpretacion, "obtener_proveedor_generacion", return_value="nvidia_nim"),
        patch.object(
            interpretacion, "_obtener_cadena_interpretacion",
            side_effect=lambda proveedor: primario if proveedor == "nvidia_nim" else respaldo,
        ),
        patch("src.agentes.reintentos.time.sleep"),
    ):
        salida = interpretacion.interpretar_consulta(
            consulta="hola", hoy=date(2026, 10, 24), historial=[],
            consulta_anterior=None, vocabulario={},
        )

    assert salida.intencion == "conversacion"
    primario.invoke.assert_called()
    respaldo.invoke.assert_called_once()


@pytest.mark.parametrize("proveedor", ["gemini", "nvidia_nim"])
@pytest.mark.parametrize("intencion", ["aclaracion", "borrador"])
def test_aclaracion_repetida_se_reinterpreta_con_contexto(proveedor, intencion):
    repetida = "¿Qué texto quieres adaptar?"
    cadena = Mock()
    final = (
        PlanConsulta(intencion="borrador", plataforma="instagram", terminos=["Python"])
        if intencion == "borrador" else PlanConsulta(
            intencion="aclaracion",
            respuesta="Pega aquí el texto de referencia y podré adaptarlo.",
        )
    )
    cadena.invoke.side_effect = [
        PlanConsulta(intencion="aclaracion", respuesta=f"  {repetida.upper()}  "),
        final,
    ]
    historial = [
        {"rol": "usuario", "contenido": "Adapta ese texto"},
        {"rol": "asistente", "contenido": repetida},
    ]
    with (
        patch.object(interpretacion, "obtener_proveedor_generacion", return_value=proveedor),
        patch.object(interpretacion, "_obtener_cadena_interpretacion", return_value=cadena),
    ):
        plan = interpretacion.interpretar_consulta(
            consulta="El de arriba", hoy=date(2026, 10, 24), historial=historial,
            consulta_anterior=None, vocabulario={},
        )
    assert plan == final
    assert cadena.invoke.call_count == 2
    primera, segunda = [llamada.args[0] for llamada in cadena.invoke.call_args_list]
    assert primera["revision"] == ""
    assert "repite una respuesta anterior" in segunda["revision"]
    assert primera["historial"] == segunda["historial"]
    assert primera["consulta"] == segunda["consulta"] == "El de arriba"
    assert historial[-1]["contenido"] == repetida


def test_aclaracion_persistente_falla_sin_bucle_ni_respuesta_prefabricada():
    cadena = Mock()
    cadena.invoke.return_value = PlanConsulta(
        intencion="aclaracion", respuesta="¿Qué texto quieres adaptar?",
    )
    with (
        patch.object(interpretacion, "obtener_proveedor_generacion", return_value="gemini"),
        patch.object(interpretacion, "_obtener_cadena_interpretacion", return_value=cadena),
        pytest.raises(ErrorInterpretacion, match="sin repetir"),
    ):
        interpretacion.interpretar_consulta(
            consulta="Ese", hoy=date(2026, 10, 24),
            historial=[{"rol": "asistente", "contenido": "¿Qué texto quieres adaptar?"}],
            consulta_anterior=None, vocabulario={},
        )
    assert cadena.invoke.call_count == 2


def test_saludo_repetido_no_activa_reintento_de_aclaracion():
    cadena = Mock()
    cadena.invoke.return_value = PlanConsulta(intencion="conversacion", respuesta="Hola")
    with (
        patch.object(interpretacion, "obtener_proveedor_generacion", return_value="gemini"),
        patch.object(interpretacion, "_obtener_cadena_interpretacion", return_value=cadena),
    ):
        plan = interpretacion.interpretar_consulta(
            consulta="Hola", hoy=date(2026, 10, 24),
            historial=[{"rol": "asistente", "contenido": "Hola"}],
            consulta_anterior=None, vocabulario={},
        )
    assert plan.respuesta == "Hola"
    cadena.invoke.assert_called_once()
