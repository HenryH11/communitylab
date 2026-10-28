from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock, patch

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
import pytest

from src.agentes import consumo, modelo_ia
from src.agentes.conversacion import SalidaConversacional
from src.agentes.fallback_ia import invocar_modelo_con_fallback
from src.agentes.interpretacion import PlanConsulta
from src.agentes.proveedores import gemini

pytestmark = pytest.mark.usefixtures("verificacion_analitica_simulada")


@pytest.fixture(autouse=True)
def configuracion(monkeypatch):
    monkeypatch.setattr(consumo, "load_dotenv", lambda: None)
    monkeypatch.setattr("src.agentes.contexto.load_dotenv", lambda: None)
    for nombre, valor in {
        "COMMUNITYLAB_MAX_INTENTOS_CONSULTA": 30,
        "COMMUNITYLAB_MAX_TOKENS_CONSULTA": 250000,
        "COMMUNITYLAB_MAX_CONSULTAS_ACTIVAS": 2,
        "COMMUNITYLAB_MAX_INTENTOS_HORA": 0,
        "COMMUNITYLAB_CONTEXTO_TOKENS": 32768,
        "COMMUNITYLAB_SALIDA_TOKENS": 4096,
    }.items():
        monkeypatch.setenv(nombre, str(valor))
    with consumo._lock:
        consumo._intentos_hora.clear()


def reservar():
    consumo.reservar_intento([HumanMessage(content="Una petición")], {}, 4096)


def test_maximo_intentos_detiene_antes_de_enviar_y_libera_slot(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_CONSULTA", "1")
    enviados = []

    @consumo.limitar_consulta
    def consultar():
        reservar()
        enviados.append(1)
        reservar()
        enviados.append(2)
        return {}

    with pytest.raises(consumo.LimiteConsumo, match="presupuesto"):
        consultar()
    assert enviados == [1]
    assert consumo._activas == 0
    assert consumo._actual.get() is None


def test_presupuesto_total_suma_entrada_y_reserva_y_no_se_reembolsa_un_fallo(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MAX_TOKENS_CONSULTA", "13000")

    @consumo.limitar_consulta
    def consultar():
        reservar()
        reservar()
        with pytest.raises(consumo.LimiteConsumo):
            reservar()
        return {}

    salida = consultar()
    assert salida["consumo"]["intentos_proveedor"] == 2
    assert 12000 < salida["consumo"]["tokens_reservados_estimados"] <= 13000


def test_cuota_horaria_es_compartida_y_expira(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_HORA", "1")

    @consumo.limitar_consulta
    def consultar():
        reservar()
        return {}

    with patch.object(consumo, "monotonic", return_value=100):
        consultar()
        with pytest.raises(consumo.LimiteConsumo, match="horaria"):
            consultar()
    with patch.object(consumo, "monotonic", return_value=3701):
        assert consultar()["consumo"]["intentos_proveedor"] == 1


def test_cuota_horaria_desactivada_no_reutiliza_el_presupuesto_de_otra_consulta():
    @consumo.limitar_consulta
    def consultar():
        reservar()
        return {}

    assert consultar()["consumo"]["intentos_proveedor"] == 1
    assert consultar()["consumo"]["intentos_proveedor"] == 1


def test_concurrencia_rechaza_exceso_y_libera_al_terminar(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MAX_CONSULTAS_ACTIVAS", "1")
    inicio, terminar = Event(), Event()

    @consumo.limitar_consulta
    def consultar():
        inicio.set()
        if not terminar.wait(10):
            raise TimeoutError("La prueba no liberó el worker")
        reservar()
        return {}

    with ThreadPoolExecutor(max_workers=1) as executor:
        tarea = executor.submit(consultar)
        try:
            assert inicio.wait(10)
            with pytest.raises(consumo.LimiteConsumo, match="ocupado"):
                consultar()
        finally:
            terminar.set()
        assert tarea.result(timeout=10)["consumo"]["intentos_proveedor"] == 1
    assert consumo._activas == 0
    assert consultar()["consumo"]["intentos_proveedor"] == 1


@pytest.mark.parametrize("max_intentos", [30, 2])
def test_factory_cuenta_interpretacion_redaccion_y_verificacion_sin_llamadas_reales(monkeypatch, max_intentos):
    from src.agentes.conversacion import AgenteConversacional, SalidaVerificacion
    from src.agentes import conversacion, interpretacion
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_CONSULTA", str(max_intentos))

    def proveedor(esquema, **kwargs):
        assert kwargs["max_tokens"] == 4096

        def responder(_):
            if esquema is PlanConsulta:
                return PlanConsulta(intencion="borrador", plataforma="linkedin")
            if esquema is SalidaConversacional:
                return SalidaConversacional.model_validate({
                    "respuesta": "Listo.", "citas": ["a"],
                    "hallazgos": [{"afirmacion": "Un logro real", "citas": ["a"]}],
                    "borrador": {"plataforma": "linkedin", "titulo": "Un logro real",
                                 "contenido": "Un logro real", "hashtags": ["#a", "#b", "#c"]},
                })
            assert esquema is SalidaVerificacion
            return SalidaVerificacion.model_validate({
                "resumen": "Respaldado.", "afirmaciones": [
                    {"afirmacion": "Un logro real", "respaldada": True, "citas": ["a"]},
                ],
            })
        return RunnableLambda(responder)

    for funcion in (
        conversacion._obtener_cadena, conversacion._obtener_cadena_verificacion,
        interpretacion._obtener_cadena_interpretacion,
    ):
        funcion.cache_clear()
    try:
        with (
            patch.object(modelo_ia, "obtener_modelo_gemini_estructurado", side_effect=proveedor),
            patch.object(conversacion, "obtener_proveedor_generacion", return_value="gemini"),
            patch.object(interpretacion, "obtener_proveedor_generacion", return_value="gemini"),
        ):
            agente = AgenteConversacional([{"id": "a", "texto": "Un logro real"}])
            if max_intentos == 2:
                with pytest.raises(consumo.LimiteConsumo):
                    agente.consultar("Un post", modo_verificacion="verificacion_automatica")
                assert agente.historial == []
                assert agente._ultimo_borrador is None
                assert consumo._activas == 0
                return
            salida = agente.consultar("Un post", modo_verificacion="verificacion_automatica")
        assert salida["consumo"]["intentos_proveedor"] == 3
        assert salida["consumo"]["tokens_reservados_estimados"] > 3 * 4096
    finally:
        for funcion in (
            conversacion._obtener_cadena, conversacion._obtener_cadena_verificacion,
            interpretacion._obtener_cadena_interpretacion,
        ):
            funcion.cache_clear()


def test_reintentos_y_fallback_cuentan_y_no_saltan_el_limite(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MAX_INTENTOS_CONSULTA", "2")
    llamadas = Mock(side_effect=ConnectionError("Proveedor no disponible"))

    def proveedor(*args, **kwargs):
        return RunnableLambda(llamadas)

    @consumo.limitar_consulta
    def consultar():
        cadena = modelo_ia.obtener_modelo_generacion_estructurado(
            SalidaConversacional, proveedor="nvidia_nim", max_tokens=4096,
        )
        invocar_modelo_con_fallback(
            [HumanMessage(content="Consulta")],
            primario=cadena.invoke, respaldo=cadena.invoke,
        )
        return {}

    with (
        patch.object(modelo_ia, "obtener_modelo_nvidia_estructurado", side_effect=proveedor),
        patch("src.agentes.reintentos.obtener_max_intentos_ia", return_value=2),
        patch("src.agentes.reintentos.time.sleep"),
    ):
        with pytest.raises(consumo.LimiteConsumo):
            consultar()
    assert llamadas.call_count == 2
    assert consumo._activas == 0


def test_cliente_gemini_no_hace_reintentos_ocultos_en_consultas(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "prueba")
    gemini.obtener_modelo_gemini.cache_clear()
    try:
        with patch.object(gemini, "ChatGoogleGenerativeAI") as cliente:
            gemini.obtener_modelo_gemini(max_tokens=4096)
            assert cliente.call_args.kwargs["max_retries"] == 0
    finally:
        gemini.obtener_modelo_gemini.cache_clear()


@pytest.mark.parametrize("variable,valor", [
    ("COMMUNITYLAB_MAX_INTENTOS_CONSULTA", "0"),
    ("COMMUNITYLAB_MAX_TOKENS_CONSULTA", "-1"),
    ("COMMUNITYLAB_MAX_CONSULTAS_ACTIVAS", "no"),
    ("COMMUNITYLAB_MAX_INTENTOS_HORA", "-1"),
])
def test_configuracion_invalida_no_se_sustituye_por_defaults(monkeypatch, variable, valor):
    monkeypatch.setenv(variable, valor)
    @consumo.limitar_consulta
    def consultar():
        return {}
    with pytest.raises(consumo.ErrorConfiguracionProveedor):
        consultar()
    assert consumo._activas == 0
