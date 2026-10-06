"""Ensayo NVIDIA con transporte simulado: nunca consume cuota del proveedor."""

from io import BytesIO
import json
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

from scripts import medir_latencia_nvidia_nim as nim


MODELO = next(iter(nim.MODELOS_FREE_ENDPOINT))
ANALISIS = {
    "sentimiento": "neutral", "tema_principal": "datos_ia",
    "subtema": "Python", "tipo_detectado": "pregunta_tecnica",
}


def respuesta(datos=None, final="stop"):
    return {"choices": [{"finish_reason": final, "message": {
        "content": json.dumps(ANALISIS if datos is None else datos),
    }}], "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}}


@pytest.fixture
def archivo(tmp_path):
    datos = {
        "origen_comunidad": "Prueba", "periodo_referencia": "Semana_03",
        "interacciones": [{
            "id": f"nim-{i}", "autor": "Ana", "canal": "#dudas", "idioma": "es",
            "tipo": "pregunta_tecnica", "texto": f"¿Cómo resolver el error {i} en Python? 👩‍💻",
            "fecha": "2026-09-16T12:00:00Z",
        } for i in range(3)],
    }
    ruta = tmp_path / "entrada.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


@pytest.fixture(autouse=True)
def bloquear_red(monkeypatch):
    transporte = MagicMock(side_effect=AssertionError("No debe haber tráfico real"))
    monkeypatch.setattr(nim, "build_opener", transporte)
    return transporte


def test_plan_no_usa_clave_ni_red_y_conserva_entrada(archivo, monkeypatch, capsys):
    original = archivo.read_bytes()
    monkeypatch.setenv("NVIDIA_API_KEY", "clave-no-utilizar")
    dotenv = MagicMock(side_effect=AssertionError("Plan no debe cargar credenciales"))
    monkeypatch.setattr(nim, "load_dotenv", dotenv)
    args = ["--entrada", str(archivo), "--repeticiones", "2"]
    for modelo in nim.MODELOS_FREE_ENDPOINT:
        args += ["--modelo", modelo]
    assert nim.principal(args) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["modo"] == "plan_sin_red"
    assert informe["solicitudes_planificadas"] == 12
    assert informe["ids"] == ["nim-0", "nim-1", "nim-2"]
    assert informe["catalogo_free_endpoint"]["estado_observado"] == "Available"
    assert "resultados" not in informe
    assert archivo.read_bytes() == original


def test_modelo_no_verificado_se_rechaza(archivo):
    with pytest.raises(SystemExit) as error:
        nim.principal(["--entrada", str(archivo), "--modelo", "deepseek-ai/deepseek-v4-pro"])
    assert error.value.code == 2


def test_faq_desde_paquete_real_sin_analisis_previo(archivo, capsys):
    assert nim.principal(["--entrada", str(archivo), "--modelo", MODELO, "--tarea", "faq"]) == 0
    assert json.loads(capsys.readouterr().out)["casos"] == 3


def test_en_vivo_sin_clave_no_envia_solicitudes(archivo, monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setattr(nim, "load_dotenv", lambda *a: None)
    with pytest.raises(SystemExit) as error:
        nim.principal(["--entrada", str(archivo), "--modelo", MODELO, "--en-vivo"])
    assert error.value.code == 2


@pytest.mark.parametrize("malformada", [
    None, [], {}, {"choices": []}, {"choices": [None]},
    {"choices": [{"finish_reason": "stop", "message": {"content": "no-json"}}]},
    respuesta(final="length"), respuesta({**ANALISIS, "campo_extra": "no"}),
    respuesta({**ANALISIS, "sentimiento": "feliz"}), respuesta({"subtema": "Python"}),
])
def test_json_incompleto_o_fuera_de_contrato_se_rechaza(malformada):
    with pytest.raises(nim.RespuestaInvalida):
        nim.validar_respuesta(malformada, nim.AnalisisMensaje)


@pytest.mark.parametrize("sin_razonamiento", [False, True])
def test_transporte_fija_endpoint_y_envia_json_utf8(bloquear_red, sin_razonamiento):
    caso = {"mensajes": [{"role": "user", "content": "¿Qué pasó? 👩‍💻"}]}
    contexto = MagicMock()
    contexto.__enter__.return_value.read.return_value = json.dumps(respuesta()).encode()
    bloquear_red.side_effect = None
    bloquear_red.return_value.open.return_value = contexto
    resultado = nim.solicitar(MODELO, caso, "clave-prueba", 60, 4096, sin_razonamiento)
    peticion = bloquear_red.return_value.open.call_args.args[0]
    assert peticion.full_url == nim.ENDPOINT
    assert peticion.get_header("Authorization") == "Bearer clave-prueba"
    cuerpo = json.loads(peticion.data.decode("utf-8"))
    assert cuerpo["messages"] == caso["mensajes"]
    assert cuerpo["response_format"] == {"type": "json_object"}
    if sin_razonamiento:
        assert cuerpo["chat_template_kwargs"] == {"enable_thinking": False}
    else:
        assert "chat_template_kwargs" not in cuerpo
    assert nim.validar_respuesta(resultado, nim.AnalisisMensaje) == ANALISIS
    assert isinstance(bloquear_red.call_args.args[0], nim.SinRedirecciones)
    assert nim.SinRedirecciones().redirect_request(None, None, 302, None, None, "https://otro") is None


def test_fallos_no_interrumpen_otros_casos_ni_exponen_clave(archivo, monkeypatch, capsys, tmp_path):
    secreto = "clave-que-no-debe-aparecer"
    monkeypatch.setenv("NVIDIA_API_KEY", secreto)
    monkeypatch.setattr(nim, "load_dotenv", lambda *a: None)
    monkeypatch.setattr(nim.Ritmo, "esperar", lambda self: None)

    def proveedor(modelo, caso, *args):
        if caso["id"] == "nim-0":
            raise HTTPError(nim.ENDPOINT, 429, secreto, {}, BytesIO(secreto.encode()))
        if caso["id"] == "nim-1":
            raise TimeoutError(secreto)
        return respuesta()

    monkeypatch.setattr(nim, "solicitar", proveedor)
    salida = tmp_path / "informe.json"
    assert nim.principal([
        "--entrada", str(archivo), "--modelo", MODELO, "--en-vivo",
        "--concurrencia", "2", "--repeticiones", "2", "--salida", str(salida),
    ]) == 1
    contenido = salida.read_text(encoding="utf-8")
    assert secreto not in contenido + capsys.readouterr().out
    reporte = json.loads(contenido)
    assert len(reporte["resultados"]) == 6
    assert reporte["resumen_por_modelo"][MODELO]["respuestas_validas"] == 2
    assert reporte["resumen_por_modelo"][MODELO]["errores"] == 4
    assert {r["repeticion"] for r in reporte["resultados"]} == {1, 2}
    assert reporte["resultados"][0]["error"]["codigo_http"] == 429
    assert reporte["resultados"][2]["uso_reportado_proveedor"]["total_tokens"] == 120


def test_latencia_de_errores_no_mejora_promedio_de_validas():
    registros = [{"modelo": MODELO, "valida": valida, "duracion_solicitud_seg": t}
                 for valida, t in [(True, 2), (True, 4), (False, 0.01)]]
    resumen = nim.resumir(registros, [MODELO], 1.8)[MODELO]
    assert resumen["latencia_validas_seg"]["promedio"] == 3
    assert resumen["latencia_validas_seg"]["p95"] == 4
    assert resumen["validas_sobre_umbral"] == 2
    assert nim.estadisticas([]) is None


def test_ritmo_espacia_inicios_sin_dormir_realmente(monkeypatch):
    reloj = [100.0]
    monkeypatch.setattr(nim.time, "monotonic", lambda: reloj[0])
    monkeypatch.setattr(nim.time, "sleep", lambda t: reloj.__setitem__(0, reloj[0] + t))
    ritmo = nim.Ritmo(1.5)
    ritmo.esperar()
    ritmo.esperar()
    ritmo.esperar()
    assert reloj[0] == 103.0


def test_seleccion_generacion_respeta_elegibilidad():
    def estado(id_, tipo, faq=False):
        return {"id": id_, "tipo_original": tipo, "elegible_faq": faq,
                "texto": "Texto de prueba", "sentimiento": "neutral",
                "tipo_detectado": "", "autor": "Ana", "canal": "#dudas",
                "origen": "Prueba", "idioma": "es"}
    paquete = {
        "estados": [estado("a", "pregunta_tecnica"), estado("b", "pregunta_tecnica"),
                    estado("c", "pregunta_programa", True), estado("d", "pregunta_programa"),
                    estado("e", "testimonio"), estado("f", "testimonio")],
        "plan": {"ids_contenido": ["a", "e"]},
    }
    assert [c["id"] for c in nim.preparar_casos(paquete, "faq")] == ["a", "c"]
    assert [c["id"] for c in nim.preparar_casos(paquete, "linkedin")] == ["e"]
    assert len(nim.preparar_casos(paquete, "analisis")) == 6


def test_informe_no_puede_reemplazar_entrada(archivo):
    original = archivo.read_bytes()
    with pytest.raises(SystemExit) as error:
        nim.principal(["--entrada", str(archivo), "--modelo", MODELO, "--salida", str(archivo)])
    assert error.value.code == 2
    assert archivo.read_bytes() == original


def test_no_se_aplica_opcion_de_razonamiento_de_nemotron_a_deepseek(archivo):
    with pytest.raises(SystemExit) as error:
        nim.principal(["--entrada", str(archivo), "--modelo", "deepseek-ai/deepseek-v4.1-flash",
                       "--sin-razonamiento"])
    assert error.value.code == 2
