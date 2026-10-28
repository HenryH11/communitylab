from collections import defaultdict
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from src.agentes.contexto import dividir_evidencia, estimar_tokens, obtener_presupuesto_contexto
from src.agentes.conversacion import (
    AgenteConversacional, GrupoPregunta, SalidaConversacional, _presentar_preguntas, _tokens_prompt,
)
from src.agentes.errores_ia import ErrorConfiguracionProveedor
from src.agentes.interpretacion import PlanConsulta
from src.agentes.prompts.conversacion import prompt_conversacion
from src.agentes.proveedores import gemini, nvidia_nim

pytestmark = pytest.mark.usefixtures("verificacion_analitica_simulada")


@pytest.fixture(autouse=True)
def presupuesto_servidor(monkeypatch):
    monkeypatch.setattr("src.agentes.contexto.load_dotenv", lambda: None)
    monkeypatch.setenv("COMMUNITYLAB_CONTEXTO_TOKENS", "32768")
    monkeypatch.setenv("COMMUNITYLAB_SALIDA_TOKENS", "4096")


@pytest.mark.parametrize("variable,valor", [
    ("COMMUNITYLAB_CONTEXTO_TOKENS", ""),
    ("COMMUNITYLAB_CONTEXTO_TOKENS", "0"),
    ("COMMUNITYLAB_CONTEXTO_TOKENS", "abc"),
    ("COMMUNITYLAB_SALIDA_TOKENS", "-1"),
    ("COMMUNITYLAB_SALIDA_TOKENS", "32768"),
    ("COMMUNITYLAB_SALIDA_TOKENS", "32769"),
])
def test_presupuesto_invalido_no_se_sustituye_silenciosamente(monkeypatch, variable, valor):
    monkeypatch.setenv(variable, valor)
    with pytest.raises(ErrorConfiguracionProveedor):
        obtener_presupuesto_contexto()


def test_presupuesto_reserva_la_salida_y_es_configurable(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_CONTEXTO_TOKENS", "48000")
    monkeypatch.setenv("COMMUNITYLAB_SALIDA_TOKENS", "8000")
    presupuesto = obtener_presupuesto_contexto()
    assert presupuesto.total == 48000
    assert presupuesto.entrada == 40000
    assert presupuesto.salida == 8000


def test_el_plan_publico_no_puede_cambiar_el_presupuesto():
    with pytest.raises(ValidationError):
        PlanConsulta.model_validate({
            "intencion": "consulta", "presupuesto_tokens": 10000000,
        })


def test_fragmentacion_conserva_todo_el_texto_unicode_y_el_orden():
    evidencia = [
        {"id": "a", "texto": "Texto con ñ y 🚀.\n" * 50},
        {"id": "b", "texto": "Fin del segundo registro." * 20},
    ]
    lotes = dividir_evidencia(evidencia, lambda fuentes: estimar_tokens(fuentes) <= 150)
    reconstruidos = defaultdict(str)
    for lote in lotes:
        assert estimar_tokens(lote) <= 150
        for mensaje in lote:
            reconstruidos[mensaje["id"]] += mensaje["texto"]
    assert dict(reconstruidos) == {m["id"]: m["texto"] for m in evidencia}


def test_instrucciones_o_metadatos_que_no_caben_fallan_sin_omitir_datos():
    with pytest.raises(ValueError, match="instrucciones"):
        dividir_evidencia([{"id": "a", "texto": "Texto"}], lambda _: False)
    with pytest.raises(ValueError, match="registro no cabe"):
        dividir_evidencia(
            [{"id": "muy-largo" * 100, "texto": "Texto"}],
            lambda fuentes: estimar_tokens(fuentes) <= 100,
        )


@pytest.mark.parametrize("intencion,plataforma", [
    ("consulta", None), ("borrador", "linkedin"), ("borrador", "x"),
])
def test_todas_las_tareas_procesan_fuentes_completas_por_tokens(intencion, plataforma):
    llamadas = []
    mensajes = [
        {"id": f"m-{i}", "texto": f"Inicio {i}. " + "Evidencia real. " * 120 + f" Final {i}."}
        for i in range(40)
    ]

    def generar(**entrada):
        llamadas.append(entrada)
        salida = {
            "respuesta": "Hallazgos pertinentes.",
            "citas": [m["id"] for m in entrada["evidencia"]],
            "hallazgos": [{
                "afirmacion": "Hallazgos pertinentes.",
                "citas": [m["id"] for m in entrada["evidencia"]],
            }],
        }
        if intencion == "borrador" and entrada["resumen"]["procesamiento"]["etapa"] != "extraccion_parcial":
            salida["borrador"] = {
                "plataforma": plataforma, "titulo": "Una experiencia real",
                "contenido": "La comunidad comparte sus experiencias.",
                "hashtags": ["#Comunidad", "#Datos", "#Aprender"],
            }
        return salida

    agente = AgenteConversacional(
        mensajes, generador=generar,
        interprete=lambda **_: PlanConsulta(intencion=intencion, plataforma=plataforma),
    )
    salida = agente.consultar("Analiza todas las experiencias")
    reconstruidos = defaultdict(str)
    for entrada in llamadas:
        if entrada["resumen"]["procesamiento"]["nivel"] == 0:
            for mensaje in entrada["evidencia"]:
                reconstruidos[mensaje["id"]] += mensaje["texto"]
        # La llamada se hizo antes de guardar el turno actual en el historial.
        with patch.object(agente, "_historial", []):
            estimacion = _tokens_prompt(
                prompt_conversacion,
                agente._entrada_generacion(
                    entrada["consulta"], entrada["resumen"], entrada["evidencia"],
                ),
                SalidaConversacional,
            )
        assert estimacion <= obtener_presupuesto_contexto().entrada
    assert dict(reconstruidos) == {m["id"]: m["texto"] for m in mensajes}
    assert set(salida["citas"]) == {m["id"] for m in mensajes}
    cobertura = salida["resumen"]["procesamiento"]
    assert cobertura["registros_procesados"] == 40
    assert cobertura["cobertura_completa"] is True
    assert cobertura["lotes_fuente"] > 1
    assert cobertura["llamadas_generacion"] == len(llamadas)
    assert cobertura["tokens_entrada_estimados_maximos"] <= cobertura["presupuesto_entrada_tokens"]


def test_un_solo_mensaje_largo_no_pierde_su_final():
    texto = "Inicio. " + "Contenido completo. " * 2000 + "Hecho al final."
    fragmentos = []

    def generar(**entrada):
        for mensaje in entrada["evidencia"]:
            if mensaje["id"] == "largo":
                fragmentos.append(mensaje["texto"])
        return {
            "respuesta": "Síntesis fiel.", "citas": [m["id"] for m in entrada["evidencia"]],
            "hallazgos": [{"afirmacion": "Síntesis fiel.", "citas": [m["id"] for m in entrada["evidencia"]]}],
        }

    agente = AgenteConversacional(
        [{"id": "largo", "texto": texto}], generador=generar,
        interprete=lambda **_: PlanConsulta(intencion="consulta"),
    )
    salida = agente.consultar("Resume todo el mensaje")
    assert "".join(fragmentos) == texto
    assert salida["citas"] == ["largo"]
    assert salida["resumen"]["procesamiento"]["registros_procesados"] == 1


def test_fallo_de_un_lote_no_se_devuelve_como_exito_parcial():
    llamadas = 0

    def generar(**entrada):
        nonlocal llamadas
        llamadas += 1
        if llamadas == 2:
            raise RuntimeError("Falló el segundo lote")
        return {
            "respuesta": "Síntesis.", "citas": [m["id"] for m in entrada["evidencia"]],
            "hallazgos": [{"afirmacion": "Síntesis.", "citas": [m["id"] for m in entrada["evidencia"]]}],
        }

    agente = AgenteConversacional(
        [{"id": str(i), "texto": "Mensaje. " * 500} for i in range(20)],
        generador=generar, interprete=lambda **_: PlanConsulta(intencion="consulta"),
    )
    with pytest.raises(RuntimeError, match="segundo lote"):
        agente.consultar("Resume los mensajes")
    assert agente.historial == []


def test_agrupacion_de_preguntas_consolida_fuentes_entre_lotes():
    def generar(**entrada):
        ids = [m["id"] for m in entrada["evidencia"]]
        return {
            "respuesta": "Preguntas agrupadas.", "citas": ids,
            "grupos_preguntas": [{"duda": "Cómo empezar el proyecto", "citas": ids}],
        }

    mensajes = [{"id": str(i), "texto": "Cómo empezar el proyecto. " * 100} for i in range(30)]
    agente = AgenteConversacional(
        mensajes, generador=generar,
        interprete=lambda **_: PlanConsulta(intencion="consulta", agrupar_preguntas=True),
    )
    salida = agente.consultar("Agrupa las preguntas")
    assert len(salida["grupos_preguntas"]) == 1
    assert set(salida["grupos_preguntas"][0]["citas"]) == {m["id"] for m in mensajes}
    assert "30 mensajes" in salida["respuesta"]
    assert "Fuentes:" not in salida["respuesta"]
    assert "explorador de fuentes" in salida["respuesta"]
    assert salida["resumen"]["procesamiento"]["lotes_fuente"] > 1


@pytest.mark.parametrize("texto", ["Cómo instalar y configurar.", "Cómo instalar y configurar. " * 1600])
def test_varias_dudas_de_un_mensaje_se_conservan_incluso_fragmentado(texto):
    def generar(**entrada):
        fuentes = entrada["evidencia"]
        ids = list(dict.fromkeys(m["id"] for m in fuentes))
        if entrada["resumen"]["procesamiento"]["etapa"] == "extraccion_parcial":
            grupos = [{"duda": "Cómo instalar", "citas": ids},
                      {"duda": "Cómo configurar", "citas": ids}]
        else:
            grupos = [
                {"duda": duda, "citas": [
                    m["id"] for m in fuentes if m["texto"] == duda or m["id"] == "a"
                ]}
                for duda in ("Cómo instalar", "Cómo configurar")
            ]
        return {"respuesta": "Dudas.", "citas": ids, "grupos_preguntas": grupos}

    agente = AgenteConversacional(
        [{"id": "a", "texto": texto}],
        generador=generar,
        interprete=lambda **_: PlanConsulta(intencion="consulta", agrupar_preguntas=True),
    )
    salida = agente.consultar("Agrupa todas las dudas")
    assert [g["citas"] for g in salida["grupos_preguntas"]] == [["a"], ["a"]]
    assert "hay 1 mensajes, agrupados en 2 dudas" in salida["respuesta"]
    assert "Grupos con más de un mensaje: 0" in salida["respuesta"]
    assert salida["respuesta"].count("— 1 mensaje.") == 2
    if len(texto) > 100:
        assert salida["resumen"]["procesamiento"]["lotes_fuente"] > 1


@pytest.mark.parametrize("grupos,ids", [
    ([GrupoPregunta(duda="Una duda", citas=["a", "a"])], {"a"}),
    ([GrupoPregunta(duda="Una duda", citas=["ajena"])], {"a"}),
    ([GrupoPregunta(duda="Una duda", citas=["a"])], {"a", "b"}),
])
def test_grupos_aun_rechazan_duplicados_internos_fuentes_ajenas_y_cobertura_incompleta(grupos, ids):
    with pytest.raises(ValueError):
        _presentar_preguntas(grupos, ids)


def test_sintesis_grandes_se_consolidan_en_mas_de_un_nivel():
    def generar(**entrada):
        nivel = entrada["resumen"]["procesamiento"]["nivel"]
        return {
            "respuesta": "Hallazgo relevante. " * (160 if nivel == 0 else 1),
            "citas": [m["id"] for m in entrada["evidencia"]],
            "hallazgos": [{
                "afirmacion": "Hallazgo relevante. " * (160 if nivel == 0 else 1),
                "citas": [m["id"] for m in entrada["evidencia"]],
            }],
        }

    mensajes = [{"id": str(i), "texto": "Texto completo. " * 250} for i in range(60)]
    agente = AgenteConversacional(
        mensajes, generador=generar,
        interprete=lambda **_: PlanConsulta(intencion="consulta"),
    )
    salida = agente.consultar("Analiza todas las fuentes")
    assert salida["resumen"]["procesamiento"]["niveles_consolidacion"] >= 2
    assert set(salida["citas"]) == {m["id"] for m in mensajes}


def test_no_reducir_el_contexto_falla_sin_bucle_infinito():
    def generar(**entrada):
        return {
            "respuesta": "x" * 50000,
            "citas": [m["id"] for m in entrada["evidencia"]],
            "hallazgos": [{"afirmacion": "x" * 50000, "citas": [m["id"] for m in entrada["evidencia"]]}],
        }

    agente = AgenteConversacional(
        [{"id": "a", "texto": "Original. " * 5000}],
        generador=generar, interprete=lambda **_: PlanConsulta(intencion="consulta"),
    )
    with pytest.raises(ValueError, match="no redujo"):
        agente.consultar("Resume")
    assert agente.historial == []


def test_canales_tipos_y_textos_no_requieren_redactor():
    generar = Mock()
    interpretar = Mock(side_effect=[
        PlanConsulta(intencion="consulta", campos_listado=["canal"]),
        PlanConsulta(intencion="consulta", campos_listado=["tipo", "contenido_textual"]),
    ])
    agente = AgenteConversacional(
        [
            {"id": "a", "texto": "Texto idéntico", "canal": "Discord", "tipo_detectado": "pregunta"},
            {"id": "b", "texto": "Texto idéntico", "canal": "Discord", "tipo_detectado": "pregunta"},
            {"id": "c", "texto": "Otro", "canal": "Telegram", "tipo_detectado": "comentario"},
        ], generador=generar, interprete=interpretar,
    )
    canales = agente.consultar("Lista los canales")
    assert canales["registros"] == [{"canal": "Discord"}, {"canal": "Telegram"}]
    textos = agente.consultar("Lista los tipos y textos")
    assert len(textos["registros"]) == 3
    assert textos["registros"][0] == {"tipo": "pregunta", "contenido_textual": "Texto idéntico"}
    assert textos["citas"] == ["a", "b", "c"]
    generar.assert_not_called()


def test_verificacion_evalua_las_mismas_afirmaciones_en_todos_los_lotes():
    llamadas = []

    def verificar(**entrada):
        llamadas.append(entrada)
        if not entrada["evidencia"]:
            return {"afirmaciones": [
                {"afirmacion": "Un hecho real", "respaldada": False, "citas": []},
            ], "resumen": "Afirmación extraída."}
        assert entrada["afirmaciones_objetivo"] == ["Un hecho real"]
        ids = [m["id"] for m in entrada["evidencia"]]
        return {"afirmaciones": [
            {"afirmacion": "Un hecho real", "respaldada": "final" in ids,
             "citas": ["final"] if "final" in ids else []},
        ], "resumen": "Verificación del lote."}

    agente = AgenteConversacional([], verificador=verificar)
    evidencia = [{"id": str(i), "texto": "Evidencia. " * 1000} for i in range(8)]
    evidencia.append({"id": "final", "texto": "Un hecho real"})
    salida = agente._verificar(
        borrador={"titulo": "Un hecho real", "contenido": "Un hecho real", "hashtags": []},
        evidencia=evidencia,
    )
    assert len(llamadas) > 2
    assert salida.afirmaciones[0].respaldada is True
    assert salida.afirmaciones[0].citas == ["final"]
    reconstruidos = defaultdict(str)
    for llamada in llamadas:
        for mensaje in llamada["evidencia"]:
            reconstruidos[mensaje["id"]] += mensaje["texto"]
    assert dict(reconstruidos) == {m["id"]: m["texto"] for m in evidencia}


@pytest.mark.parametrize("fuente_invalida", [False, True])
def test_verificacion_por_lotes_rechaza_afirmaciones_o_citas_ajenas(fuente_invalida):
    def verificar(**entrada):
        if not entrada["evidencia"]:
            return {"afirmaciones": [
                {"afirmacion": "Un hecho real", "respaldada": False, "citas": []},
            ], "resumen": "Afirmación extraída."}
        return {"afirmaciones": [
            {"afirmacion": "Un hecho real" if fuente_invalida else "Otro hecho",
             "respaldada": True, "citas": ["fuera-del-lote"]},
        ], "resumen": "No fiable."}

    agente = AgenteConversacional([], verificador=verificar)
    with pytest.raises(ValueError, match="fuente ajena|mismas afirmaciones"):
        agente._verificar(
            borrador={"contenido": "Un hecho real"},
            evidencia=[{"id": "a", "texto": "Datos. " * 12000}],
        )


def test_nvidia_recibe_el_maximo_de_tokens_de_salida():
    cliente = Mock()
    with patch.object(nvidia_nim, "obtener_modelo_nvidia", return_value=cliente):
        nvidia_nim.obtener_modelo_nvidia_estructurado(SalidaConversacional, max_tokens=1234)
    assert cliente.bind.call_args.kwargs["max_tokens"] == 1234


def test_gemini_recibe_el_maximo_de_tokens_de_salida(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-simulada")
    gemini.obtener_modelo_gemini.cache_clear()
    try:
        with (
            patch.object(gemini, "load_dotenv"),
            patch.object(gemini, "ChatGoogleGenerativeAI") as cliente,
        ):
            gemini.obtener_modelo_gemini_estructurado(SalidaConversacional, max_tokens=1234)
        assert cliente.call_args.kwargs["max_output_tokens"] == 1234
    finally:
        gemini.obtener_modelo_gemini.cache_clear()


def test_presupuesto_de_salida_llega_al_proveedor_y_al_respaldo(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_SALIDA_TOKENS", "2048")
    cadena = Mock()
    cadena.invoke.return_value = {"respuesta": "Un hecho.", "citas": ["a"]}

    def usar_respaldo(entrada, primario, respaldo):
        primario(entrada)
        return {"resultado": respaldo(entrada)}

    agente = AgenteConversacional(
        [{"id": "a", "texto": "Un hecho."}],
        interprete=lambda **_: PlanConsulta(intencion="consulta"),
    )
    with (
        patch("src.agentes.conversacion._obtener_cadena", return_value=cadena) as obtener,
        patch("src.agentes.conversacion.invocar_modelo_con_fallback", side_effect=usar_respaldo),
    ):
        agente.consultar("Resume", modelo_respuesta="super")
    assert len(obtener.call_args_list) == 2
    assert all(c.kwargs["max_tokens"] == 2048 for c in obtener.call_args_list)


def test_consolidacion_cita_solo_el_hallazgo_elegido_no_todo_su_lote():
    seleccionadas = []

    def generar(**entrada):
        fuentes = entrada["evidencia"]
        if entrada["resumen"]["procesamiento"]["etapa"] == "extraccion_parcial":
            seleccionadas.append(fuentes[0]["id"])
            hallazgos = [
                {"afirmacion": "Un hecho específico", "citas": [fuentes[0]["id"]]},
                {"afirmacion": "Un hecho distinto", "citas": [fuentes[-1]["id"]]},
            ]
        else:
            hallazgos = [{"afirmacion": "Un hecho específico", "citas": [fuentes[0]["id"]]}]
        return {
            "respuesta": "Un hecho específico.", "hallazgos": hallazgos,
            "citas": [m["id"] for m in fuentes],
        }

    mensajes = [{"id": str(i), "texto": "Texto completo. " * 200} for i in range(20)]
    agente = AgenteConversacional(
        mensajes, generador=generar, interprete=lambda **_: PlanConsulta(intencion="consulta"),
    )
    salida = agente.consultar("Analiza el conjunto")
    assert len(seleccionadas) > 1
    assert salida["citas"] == [seleccionadas[0]]
    assert salida["hallazgos"] == [
        {"afirmacion": "Un hecho específico", "citas": [seleccionadas[0]]},
    ]
    assert salida["resumen"]["procesamiento"]["registros_procesados"] == len(mensajes)


@pytest.mark.parametrize("hallazgos", [
    [],
    [{"afirmacion": "Inventado", "citas": ["no-existe"]}],
    [{"afirmacion": "Repetido", "citas": ["0", "0"]}],
])
def test_extraccion_sin_trazabilidad_exacta_se_rechaza(hallazgos):
    agente = AgenteConversacional(
        [{"id": str(i), "texto": "Texto completo. " * 300} for i in range(15)],
        interprete=lambda **_: PlanConsulta(intencion="consulta"),
        generador=lambda **entrada: {
            "respuesta": "Una síntesis.", "citas": [entrada["evidencia"][0]["id"]],
            "hallazgos": hallazgos,
        },
    )
    with pytest.raises(ValueError, match="hallazgos|hallazgo"):
        agente.consultar("Analiza")
    assert agente.historial == []
