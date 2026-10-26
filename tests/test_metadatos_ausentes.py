from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import socket
import sys
from unittest.mock import Mock

import jsonschema
import pytest

from src.agentes.conversacion import AgenteConversacional
from src.agentes.estado_agente import EstadoAgente
from src.agentes.interpretacion import PlanConsulta
from src.agentes.nodos.nodo_analizador import _entrada_analisis
from src.agentes.nodos.nodos_generadores import _contexto
from src.datos.casos_editoriales import adaptar_casos_editoriales, principal
from src.datos.ciclos_transporte import construir_ciclos
from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.metadatos import PREFIJO_AUSENTE, valor_publico


def documento():
    return {"casos": [{
        "id": "sin-autor", "texto": "Necesito otro ejemplo para detectar valores faltantes.",
        "origen": "Sinteticos", "canal": "general", "idioma": "es",
        "tipo_propuesto": "testimonio", "sentimiento_propuesto": "positivo",
    }]}


def test_adaptacion_no_inventa_fechas_ni_importa_etiquetas():
    original = documento()
    copia = deepcopy(original)
    datos = adaptar_casos_editoriales(original)
    mensaje = datos["lotes"][0]["interacciones"][0]
    assert original == copia
    assert mensaje["autor"] == PREFIJO_AUSENTE + "autor"
    assert mensaje["fecha"] is None and mensaje["tipo"] is None
    assert not any(k.endswith("_propuesto") for k in mensaje)
    paquete = preparar_paquete_ia(datos, fecha_referencia="2026-10-24T12:00:00Z")
    assert len(paquete["estados"]) == 1
    evaluacion = paquete["informe"]["lotes"][0]["evaluaciones"][0]
    assert evaluacion["desglose"]["frescura"] == 0
    assert evaluacion["desglose"]["tipo"] == 0
    assert {"sin_fecha", "sin_tipo"} <= set(evaluacion["advertencias"])
    fragmento = construir_ciclos(datos, 20)[0]["contenido"]
    assert fragmento["interacciones"][0]["fecha"] is None
    schema = json.loads((
        Path(__file__).resolve().parents[1] / "docs" / "arquitectura-solucion"
        / "contrato-intermedio-ingesta.schema.json"
    ).read_text(encoding="utf-8"))
    jsonschema.validate(fragmento, schema, format_checker=jsonschema.FormatChecker())


def test_placeholders_no_cruzan_contextos_editoriales(monkeypatch):
    estado: EstadoAgente = {
        "id": "m1", "texto": "Un mensaje real", "autor": PREFIJO_AUSENTE + "autor",
        "canal": PREFIJO_AUSENTE + "canal", "origen": PREFIJO_AUSENTE + "origen",
        "idioma": PREFIJO_AUSENTE + "idioma",
    }
    assert _contexto(estado)["autor"] == ""
    assert _entrada_analisis(estado) == {
        "texto": "Un mensaje real", "canal": "", "origen": "", "idioma": "",
    }
    assert valor_publico("user1") == "user1"
    generar = Mock(return_value={"respuesta": "Un mensaje.", "citas": ["m1"]})
    agente = AgenteConversacional([estado], generador=generar)
    monkeypatch.setattr(
        "src.agentes.conversacion.interpretar_consulta",
        Mock(return_value=PlanConsulta(intencion="consulta")),
    )
    salida = agente.consultar("Resume los mensajes")
    evidencia = generar.call_args.kwargs["evidencia"][0]
    assert evidencia["autor"] == evidencia["canal"] == evidencia["origen"] == ""
    assert salida["citas"] == ["m1"]


def test_fecha_desconocida_no_coincide_con_periodo(monkeypatch):
    monkeypatch.setattr(
        "src.agentes.conversacion.interpretar_consulta",
        Mock(return_value=PlanConsulta(
            intencion="consulta", fecha_desde=date(2026, 10, 1),
        )),
    )
    generar = Mock()
    agente = AgenteConversacional([
        {"id": "m1", "texto": "Aprendi Python", "fecha": None},
    ], generador=generar)
    salida = agente.consultar("Mensajes de octubre")
    assert salida["total_coincidencias"] == 0
    generar.assert_not_called()


def test_metadatos_reales_se_conservan_y_fecha_real_puntua():
    original = documento()
    original["casos"][0].update(
        autor="user1", fecha="2026-10-24T00:00:00Z", tipo="testimonio",
    )
    datos = adaptar_casos_editoriales(original)
    paquete = preparar_paquete_ia(datos, fecha_referencia="2026-10-24T12:00:00Z")
    assert paquete["estados"][0]["autor"] == "user1"
    assert paquete["estados"][0]["tipo_original"] == "testimonio"
    evaluacion = paquete["informe"]["lotes"][0]["evaluaciones"][0]
    assert evaluacion["desglose"]["frescura"] > 0
    assert evaluacion["desglose"]["tipo"] > 0


@pytest.mark.parametrize("fecha", ["desconocida", "user1", "2026-02-30T00:00:00Z"])
def test_fecha_invalida_no_se_confunde_con_ausencia(fecha):
    original = documento()
    original["casos"][0]["fecha"] = fecha
    with pytest.raises(ValueError, match="fecha"):
        preparar_paquete_ia(
            adaptar_casos_editoriales(original), fecha_referencia="2026-10-24T12:00:00Z",
        )


def test_cli_prepara_600_sin_red_y_sin_analisis(tmp_path, monkeypatch):
    original = documento()
    original["casos"] = [
        {**original["casos"][0], "id": f"caso-{i}", "texto": f"Necesito otro ejemplo de datos para el caso {i}."}
        for i in range(600)
    ]
    entrada = tmp_path / "casos.json"
    entrada.write_text(json.dumps(original), encoding="utf-8")
    salida = tmp_path / "preparados"
    monkeypatch.setattr(sys, "argv", [
        "casos_editoriales", "--entrada", str(entrada), "--salida", str(salida),
        "--fecha-referencia", "2026-10-24T00:00:00Z",
    ])
    sin_red = Mock(side_effect=AssertionError("No se autorizaron conexiones de red"))
    monkeypatch.setattr(socket.socket, "connect", sin_red)
    monkeypatch.setattr(socket.socket, "connect_ex", sin_red)
    monkeypatch.setattr(socket, "getaddrinfo", sin_red)
    principal()
    paquete = json.loads((salida / "paquete_preparado.json").read_text(encoding="utf-8"))
    resumen = json.loads((salida / "resumen.json").read_text(encoding="utf-8"))
    assert resumen["total"] == resumen["incluidas_analisis"] == 600
    assert resumen["ciclos"] == 30 and resumen["pendientes"] == []
    assert resumen["capa_2_ejecutada"] is False
    assert all(e["tipo_original"] is None for e in paquete["estados"])
    assert not any("sentimiento" in e for e in paquete["estados"])
    sin_red.assert_not_called()
    with pytest.raises(FileExistsError):
        principal()


def test_dataset_editorial_del_proyecto_prepara_los_600_sin_etiquetas_propuestas():
    ruta = Path(__file__).resolve().parents[1] / "src" / "datos" / "casos_conciliados_propuestos.json"
    original = json.loads(ruta.read_text(encoding="utf-8"))
    assert original["usar_para_resultados_oficiales"] is False
    assert len(original["casos"]) == 600
    assert all(c["naturaleza"] == "sintetico" for c in original["casos"])
    entrada = adaptar_casos_editoriales(original)
    paquete = preparar_paquete_ia(entrada, fecha_referencia="2026-10-24T00:00:00Z")
    assert len(paquete["estados"]) == 600
    assert len(paquete["plan"]["ciclos"]) == 30
    assert paquete["plan"]["pendientes"] == []
    assert [(e["id"], e["texto"]) for e in paquete["estados"]] == [
        (c["id"], c["texto"]) for c in original["casos"]
    ]
    assert all(e["tipo_original"] is None and "sentimiento" not in e for e in paquete["estados"])
