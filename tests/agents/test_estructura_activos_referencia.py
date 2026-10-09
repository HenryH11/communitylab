"""Suite rápida: los copies de LinkedIn y FAQ conservan su JSON de punta a punta.

Usa los casos de tests/fixtures/casos_referencia_ia_candidatos.json que el
grafo enruta a linkedin o preguntas_frecuentes. El proveedor se simula con el
JSON de texto que devolvería NVIDIA NIM. Comprueba que ese JSON llega intacto
(campos, tildes, eñes, emojis, comillas y saltos de línea) hasta el contrato
de salida de DS, y que un JSON roto queda como fallo trazable en vez de un
activo alterado. Sin red, sin claves y sin cuota.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.exceptions import OutputParserException

from src.agentes.entrega_resultados import (
    entrega_resultados_a_json,
    preparar_entrega_resultados,
)
from src.agentes.nodos import nodos_generadores

try:  # DS-Semana3 movió los modelos de salida a src/agentes/modelos.py.
    from src.agentes.modelos import PublicacionLinkedIn, SugerenciaPreguntasFrecuentes
except ImportError:
    from src.agentes.nodos.nodos_generadores import (
        PublicacionLinkedIn,
        SugerenciaPreguntasFrecuentes,
    )


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "casos_referencia_ia_candidatos.json"
MODELOS = {"linkedin": PublicacionLinkedIn, "preguntas_frecuentes": SugerenciaPreguntasFrecuentes}
CAMPOS_DS = {"linkedin": {"canal_recomendado": "LinkedIn Oficial"}}


def casos_referencia():
    datos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [c for c in datos["interacciones"] if set(c["rutas"]) & set(MODELOS)]


def respuesta_nim(caso, ruta):
    """JSON de texto como lo devolvería NIM, con caracteres que suelen romperse."""
    if ruta == "linkedin":
        return json.dumps({
            "titulo": f"{caso['autor']}: logro en {caso['tema_principal']} 🎉",
            "contenido": f"«{caso['texto']}»\n¡Felicitaciones! Año de crecimiento, ñandú incluido 👩‍💻",
            "hashtags": ["#AnálisisDeDatos", "#Comunidad", "#PrimerEmpleo"],
        }, ensure_ascii=False)
    return json.dumps({
        "tema": f"¿{caso['tema_principal']}?",
        "respuesta": f"Según los canales oficiales: \"{caso['texto'][:60]}…\"\nConsulta también la guía ✅",
    }, ensure_ascii=False)


def cadena_simulada(texto_nim, modelo):
    """Imita prompt | modelo.with_structured_output(Modelo) con salida de NIM."""
    cadena = MagicMock()
    cadena.invoke.side_effect = lambda *_a, **_k: modelo.model_validate_json(texto_nim)
    return cadena


def ejecutar(caso, generadores):
    estado = {k: v for k, v in caso.items() if k != "justificacion"}
    # El fixture no trae subtema; el contrato de DS lo exige como campo de análisis.
    estado.setdefault("subtema", f"subtema de {caso['tema_principal']}")
    with patch.object(nodos_generadores, "_obtener_generadores", return_value=generadores):
        estado.update(nodos_generadores.generar_activos(estado))
    entrega = preparar_entrega_resultados(
        {"resultados": [estado], "pendientes": [], "ids_pendientes": []}
    )
    return estado, json.loads(entrega_resultados_a_json(entrega))


CASOS = casos_referencia()


@pytest.fixture(autouse=True)
def sin_esperas_de_reintento(monkeypatch):
    """Si existen reintentos con time.sleep (DS-Semana3), no esperar en pruebas."""
    try:
        from src.agentes import reintentos
    except ImportError:
        return
    monkeypatch.setattr(reintentos, "_esperar", lambda segundos: None)


def test_el_fixture_tiene_casos_de_linkedin_y_faq():
    rutas = {r for c in CASOS for r in c["rutas"]}
    assert {"linkedin", "preguntas_frecuentes"} <= rutas
    assert len(CASOS) >= 4


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_copies_de_linkedin_y_faq_llegan_intactos_al_contrato(caso):
    rutas = [r for r in caso["rutas"] if r in MODELOS]
    esperados = {r: json.loads(respuesta_nim(caso, r)) for r in rutas}
    generadores = {
        r: cadena_simulada(respuesta_nim(caso, r), MODELOS.get(r, PublicacionLinkedIn))
        for r in caso["rutas"]
    }
    # Las rutas que no se miden aquí (caso_exito, boletin) no deben estorbar.
    for r in set(caso["rutas"]) - set(MODELOS):
        generadores[r] = MagicMock(invoke=MagicMock(side_effect=RuntimeError("no medido")))

    estado, salida = ejecutar(caso, generadores)

    for ruta, esperado in esperados.items():
        activo = estado["activos_generados"][ruta]
        assert activo == {**esperado, **CAMPOS_DS.get(ruta, {})}
        assert MODELOS[ruta].model_validate(
            {k: activo[k] for k in esperado}
        ).model_dump() == esperado

    texto_salida = json.dumps(salida, ensure_ascii=False)
    for esperado in esperados.values():
        for valor in esperado.values():
            for fragmento in (valor if isinstance(valor, list) else [valor]):
                assert fragmento in texto_salida or json.dumps(fragmento, ensure_ascii=False)[1:-1] in texto_salida


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_json_roto_de_nim_queda_como_fallo_y_no_como_activo_alterado(caso):
    ruta = next(r for r in caso["rutas"] if r in MODELOS)
    roto = respuesta_nim(caso, ruta)[:-12]  # respuesta cortada a mitad de camino
    generadores = {r: MagicMock(invoke=MagicMock(return_value=MagicMock())) for r in caso["rutas"]}
    generadores[ruta] = MagicMock(invoke=MagicMock(
        side_effect=OutputParserException(f"Invalid json output: {roto}")
    ))
    for r in caso["rutas"]:
        if r != ruta:
            generadores[r].invoke.return_value.model_dump.return_value = {"ok": True}

    estado, _ = ejecutar(caso, generadores)

    assert ruta not in estado["activos_generados"]
    fallo = next(f for f in estado["fallos"] if f.get("ruta") == ruta)
    assert fallo["id"] == caso["id"]
    assert fallo["tipo_error"] == "OutputParserException"
