import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from src.agentes.modelos import AnalisisMensaje
from src.agentes.prompts.analisis import template_analisis, template_analisis_lote
from tests.casos_semanticos_regresion import casos_pendientes, casos_semanticos
from tests.casos_spam_regresion import CASOS


RAIZ = Path(__file__).resolve().parents[2]
DOCUMENTO = json.loads(
    (RAIZ / "tests" / "datos_validacion_semantica_nueva.json").read_text(encoding="utf-8")
)


def test_expectativas_congeladas_de_la_ronda_v1():
    contenido = json.dumps(
        DOCUMENTO, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert hashlib.sha256(contenido).hexdigest() == (
        "55e82586c3cede139476637daf902cc0476e3c8222a6232af9fd119efd74cd53"
    )


def test_muestra_nueva_cobertura_y_sin_reutilizar_textos():
    casos = DOCUMENTO["casos"]
    assert len(casos) == 24
    assert len({caso["id"] for caso in casos}) == 24
    assert len({caso["texto"] for caso in casos}) == 24
    assert Counter(caso["grupo"] for caso in casos) == {
        "quejas_y_spam": 8,
        "fallos_y_testimonios": 6,
        "administrativas_y_tecnicas": 6,
        "ambiguos": 4,
    }
    anteriores = {texto.casefold() for _, texto, _ in casos_semanticos() + casos_pendientes() + CASOS}
    fuente = json.loads(
        (RAIZ / "src" / "datos" / "casos_conciliados_propuestos.json").read_text(encoding="utf-8")
    )
    anteriores.update(caso["texto"].casefold() for caso in fuente["casos"])
    prompts = "\n".join(
        mensaje.pretty_repr()
        for plantilla in (template_analisis, template_analisis_lote)
        for mensaje in plantilla.messages
    ).casefold()
    for caso in casos:
        assert caso["texto"].casefold() not in anteriores
        assert caso["texto"].casefold() not in prompts
    assert sum(caso["esperado"]["es_spam_detectado"] == [True] for caso in casos) == 4


@pytest.mark.parametrize("caso", DOCUMENTO["casos"], ids=lambda caso: caso["id"])
def test_expectativas_validas_y_ambiguedad_explicita(caso):
    assert caso["justificacion"].strip()
    esperado = caso["esperado"]
    assert set(esperado) <= {"tipo_detectado", "tema_principal", "es_spam_detectado"}
    assert len(esperado["es_spam_detectado"]) == 1
    for campo, permitidos in esperado.items():
        assert permitidos and len(set(permitidos)) == len(permitidos)
        adaptador = TypeAdapter(AnalisisMensaje.model_fields[campo].annotation)
        for valor in permitidos:
            adaptador.validate_python(valor, strict=True)
    ambiguo = any(len(valores) > 1 for valores in esperado.values())
    assert ambiguo == (caso["grupo"] == "ambiguos")
