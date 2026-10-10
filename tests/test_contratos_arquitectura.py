"""Contratos contra productores reales, sin ejecutar LLM ni Streamlit."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from src.agentes.entrega_resultados import preparar_entrega_resultados
from src.datos.entrega_ia import preparar_paquete_ia

RAIZ = Path(__file__).resolve().parents[1]
CONTRATOS = RAIZ / "docs" / "arquitectura-solucion"


def validador(nombre):
    esquema = json.loads((CONTRATOS / f"contrato-{nombre}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(esquema)
    return Draft202012Validator(esquema, format_checker=FormatChecker())


@pytest.fixture(scope="module")
def paquete():
    datos = json.loads((RAIZ / "src/datos/mensajes_comunidad_simulados.json").read_text(encoding="utf-8"))
    return preparar_paquete_ia(datos, fecha_referencia="2026-09-17T12:00:00Z", tamano_ciclo=20)


def test_entregas_reales_da_y_entrada_publica(paquete):
    for poblacion in ["completos", "contenido"]:
        for lote in paquete[poblacion]["lotes"]:
            validador("intermedio-ingesta").validate(lote)
            entrada = deepcopy(lote)
            for mensaje in entrada["interacciones"]:
                for campo in ["id", "fecha", "idioma"]:
                    del mensaje[campo]
            if entrada["interacciones"]:
                validador("entrada").validate(entrada)


def test_elegibilidad_faq_en_estados_no_en_transporte(paquete):
    elegibles = {e["id"] for e in paquete["estados"] if e["elegible_faq"]}
    assert elegibles == {"int-004", "int-007", "int-010", "int-013", "int-015"}
    assert all(e["tipo_original"] == "pregunta_programa" for e in paquete["estados"] if e["elegible_faq"])
    assert all("elegible_faq" not in m for lote in paquete["completos"]["lotes"] for m in lote["interacciones"])


@pytest.mark.parametrize("campo,valor", [("tipo", "desconocido"), ("fecha", "ayer"), ("fecha", "2026-10-08T12:00:00"), ("id", " id "), ("idioma", ""), ("texto", "")])
def test_intermedio_rechaza_datos_rotos(paquete, campo, valor):
    lote = deepcopy(paquete["completos"]["lotes"][0])
    lote["interacciones"][0][campo] = valor
    with pytest.raises(ValidationError):
        validador("intermedio-ingesta").validate(lote)


def test_intermedio_vacio_es_valido(paquete):
    lote = deepcopy(paquete["completos"]["lotes"][0])
    lote["interacciones"] = []
    validador("intermedio-ingesta").validate(lote)
    with pytest.raises(ValidationError):
        validador("entrada").validate(lote)


def salida_real(resultados=None, pendientes=None):
    pendientes = pendientes or []
    return preparar_entrega_resultados({"resultados": resultados or [], "pendientes": pendientes, "ids_pendientes": [e["id"] for e in pendientes]})


def test_salida_real_vacia_y_pendientes(paquete):
    validador("salida").validate(salida_real())
    validador("salida").validate(salida_real(pendientes=paquete["estados"][:2]))


def test_salida_real_con_error_y_sin_analisis():
    error = {"id": "fallo-1", "errores": ["Timeout"], "fallos": [{"id": "fallo-1", "etapa": "analisis", "tipo_error": "TimeoutError", "mensaje": "Timeout", "reintentable": True}]}
    validador("salida").validate(salida_real([error]))


def test_salida_real_con_activo(paquete):
    estado = deepcopy(paquete["estados"][0])
    estado.update(sentimiento="positivo", tema_principal="comunidad", subtema="colaboracion", tipo_detectado="testimonio", rutas=["linkedin"], activos_generados={"linkedin": {"titulo": "Colaboración", "contenido": "Texto de prueba", "hashtags": ["#ONE", "#Alura", "#Comunidad"]}}, errores=[])
    entrega = salida_real([estado])
    validador("salida").validate(entrega)
    assert entrega["resumen_comunidad"]["total_activos_generados"] == 1
    entrega["interacciones"][0]["elegible_faq"] = "false"
    with pytest.raises(ValidationError):
        validador("salida").validate(entrega)


def test_salida_13_y_campos_obligatorios():
    entrega = salida_real()
    entrega.update(version_contrato="1.3", id_ejecucion=None, ids_reintentables=[])
    entrega["resumen_comunidad"]["total_fallos_reintentables"] = 0
    validador("salida").validate(entrega)
    for campo in ["id_ejecucion", "ids_reintentables"]:
        rota = deepcopy(entrega)
        del rota[campo]
        with pytest.raises(ValidationError):
            validador("salida").validate(rota)
    del entrega["resumen_comunidad"]["total_fallos_reintentables"]
    with pytest.raises(ValidationError):
        validador("salida").validate(entrega)


def test_salida_12_compatible_sin_campos_de_13():
    entrega = salida_real()
    entrega["version_contrato"] = "1.2"
    entrega.pop("id_ejecucion", None)
    entrega.pop("ids_reintentables", None)
    entrega["resumen_comunidad"].pop("total_fallos_reintentables", None)
    validador("salida").validate(entrega)
    for campo, valor in [("id_ejecucion", "ejecucion-1"), ("ids_reintentables", [])]:
        rota = deepcopy(entrega)
        rota[campo] = valor
        with pytest.raises(ValidationError):
            validador("salida").validate(rota)
    entrega["resumen_comunidad"]["total_fallos_reintentables"] = 0
    with pytest.raises(ValidationError):
        validador("salida").validate(entrega)


@pytest.mark.parametrize("campo,valor", [("version_contrato", "9.9"), ("activos", {}), ("fallos", ["timeout"]), ("ids_pendientes", ["a", "a"])])
def test_salida_rechaza_estructura_rota(campo, valor):
    entrega = salida_real()
    entrega[campo] = valor
    with pytest.raises(ValidationError):
        validador("salida").validate(entrega)
