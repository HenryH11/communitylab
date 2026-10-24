"""Evaluación opt-in con modelos reales y datos simulados. Consume cuota."""

from collections import Counter
from datetime import date
import json
from pathlib import Path
import re

import pytest

from src.agentes.conversacion import AgenteConversacional
from src.agentes.plataformas import texto_publicacion
from src.app.fuente_agente import adaptar_conjunto
from src.app.plantillas_diarias import (
    PLANTILLAS_DIARIAS, PlantillaDiaria, validar_salida_catalogo,
)
from src.datos.conjunto_consultable import construir_conjunto_consultable


@pytest.fixture(scope="module")
def mensajes():
    raiz = Path(__file__).resolve().parents[2]
    entrega = json.loads(
        (raiz / "docs/evidencia2_entrega_ciencia_datos_completa.json").read_text(encoding="utf-8")
    )
    originales = json.loads(
        (raiz / "src/datos/mensajes_comunidad_simulados.json").read_text(encoding="utf-8")
    )
    return adaptar_conjunto(construir_conjunto_consultable(entrega, originales))


@pytest.mark.parametrize("plantilla", PLANTILLAS_DIARIAS, ids=lambda p: p.id)
def test_plantilla_real_cumple_contrato_y_criterios_medibles(
    plantilla: PlantillaDiaria, mensajes, tmp_path,
):
    salida = AgenteConversacional(mensajes).consultar(
        plantilla.prompt, hoy=date(2026, 10, 24),
        modo_verificacion="verificacion_automatica", modelo_respuesta="super",
    )
    (tmp_path / f"{plantilla.id}.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    validar_salida_catalogo(salida)
    assert set(salida["citas"]) <= {m["id"] for m in mensajes}
    if plantilla.plataforma:
        assert salida["borrador"] is not None
        assert salida["borrador"]["plataforma"] == plantilla.plataforma
        assert salida["verificacion"]["estado"] == "verificado"
    if plantilla.id == "x":
        assert len(texto_publicacion(salida["borrador"])) <= 280
    if plantilla.id == "boletin":
        assert salida["respuesta"].startswith("## ")
        assert len(salida["respuesta"].split()) <= 180
        assert salida["filtros"]["sentimiento"] == "positivo"
        assert salida["resumen"]["total_coincidencias"] == 12
        assert salida["resumen"]["universo_total"] == 23
    if plantilla.id == "sentimiento":
        assert salida["resumen"]["distribucion_sentimientos"] == dict(
            Counter(m["sentimiento"] for m in mensajes)
        )
        for conteo in (8, 11, 4):
            assert re.search(rf"\b{conteo}\b", salida["respuesta"])
    if plantilla.id == "temas":
        conteos = Counter(m["tema_principal"] for m in mensajes)
        for tema, total in conteos.items():
            assert re.search(
                rf"{re.escape(tema)}\s*:\s*{total}\b", salida["respuesta"],
            ), f"Falta frecuencia explícita de {tema}: {total}"
    if plantilla.id == "preguntas_frecuentes":
        assert salida["filtros"]["agrupar_preguntas"] is True
        assert set(salida["filtros"]["tipos_detectados"]) == {
            "pregunta_tecnica", "pregunta_programa",
        }
        assert salida["total_coincidencias"] == 9
        assert set(salida["citas"]) == {
            m["id"] for m in mensajes if m["tipo_detectado"].startswith("pregunta_")
        }
        grupos = salida["grupos_preguntas"]
        assert len(grupos) == 8
        assert any(set(g["citas"]) == {"int-002", "int-023"} for g in grupos)
        assert sum(len(g["citas"]) > 1 for g in grupos) == 1
    if plantilla.id == "insight_mejora":
        assert salida["total_coincidencias"] == 0
        assert salida["verificacion"]["estado"] == "sin_evidencia"
        assert salida["borrador"] is None
        assert salida["citas"] == []


def test_mejoras_reales_con_reportes_negativos_sinteticos():
    datos = [
        {"id": "neg-1", "texto": "La plataforma se desconecta y pierdo el progreso. "
         "Sugiero guardado automático.", "sentimiento": "negativo", "tipo_detectado": "feedback"},
        {"id": "neg-2", "texto": "Esperé tres días respuesta a mi duda de Python. "
         "Sugiero horario de consultas.", "sentimiento": "negativo", "tipo_detectado": "feedback"},
    ]
    salida = AgenteConversacional(datos).consultar(
        PLANTILLAS_DIARIAS[7].prompt,
        modo_verificacion="verificacion_automatica", modelo_respuesta="super",
    )
    validar_salida_catalogo(salida)
    assert salida["total_coincidencias"] == 2
    assert set(salida["citas"]) == {"neg-1", "neg-2"}
    assert salida["borrador"] is None


@pytest.mark.parametrize(("titulo", "respaldado"), [
    ("De cero a analista de datos", False),
    ("De no saber programar a conseguir empleo en datos", False),
    ("Primer trabajo como analista de datos", True),
])
def test_verificador_real_detecta_punto_de_partida_no_demostrado(titulo, respaldado):
    from src.agentes.conversacion import BorradorMarketing

    evidencia = [
        {"id": "empleo", "texto": "Conseguí mi primer trabajo como analista de datos."},
    ]
    borrador = BorradorMarketing(
        plataforma="linkedin", titulo=titulo,
        contenido="Una persona consiguió su primer trabajo como analista de datos.",
        hashtags=["#Comunidad", "#Datos", "#Empleabilidad"],
    )
    resultado = AgenteConversacional(evidencia)._verificar(
        borrador=borrador.model_dump(), evidencia=evidencia,
    )
    assert resultado.afirmaciones
    assert all(a.respaldada for a in resultado.afirmaciones) == respaldado
