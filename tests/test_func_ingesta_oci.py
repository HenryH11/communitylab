"""Regresiones de carga acumulativa: driver real, DB simulada, sin red."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from test_db_client import Conexion, cargar, db, documento, impedir_red

pytestmark = [
    pytest.mark.skipif(db is None, reason="requiere OCI y oracledb"),
    pytest.mark.usefixtures("impedir_red"),
]


def test_lotes_a_b_repetir_b_conserva_textos_completos():
    raiz = Path(__file__).parent / "fixtures" / "ingesta_ce"
    a = json.loads((raiz / "lote-a.json").read_text(encoding="utf-8"))
    b = json.loads((raiz / "lote-b.json").read_text(encoding="utf-8"))
    originales, con = deepcopy((a, b)), Conexion()
    assert cargar(a, con)["total"] == 2
    assert cargar(b, con)["total"] == 4
    repetido = cargar(b, con)
    assert repetido["repetido"] is True
    assert repetido["insertados"] == repetido["retirados"] == 0
    assert repetido["total"] == 4
    assert (a, b) == originales
    for registro in a["registros"] + b["registros"]:
        assert con.filas[registro["id"]] == registro
    assert len(con.cargas) == 2
    assert con.meta["total"] == 4
    assert not any("DELETE" in sql for sql in con.operaciones)


@pytest.mark.parametrize("largo", [161, 4001, 40000])
def test_texto_clob_no_se_recorta(largo):
    doc, con = documento("clob-001", spam=0), Conexion()
    texto = "ñ🚀\n" * largo
    doc["registros"][0]["contenido_textual"] = texto
    cargar(doc, con)
    assert con.filas["clob-001"]["contenido_textual"] == texto


@pytest.mark.parametrize("valor", ["", None, 160])
def test_contenido_no_textual_o_vacio_se_rechaza(valor):
    doc, con = documento("a", spam=0), Conexion()
    doc["registros"][0]["contenido_textual"] = valor
    with pytest.raises(ValueError, match="contenido_textual"):
        cargar(doc, con)
    assert not con.operaciones


def test_reintento_con_otro_orden_no_suma_spam():
    doc, con = documento("a", "b", spam=3), Conexion()
    cargar(doc, con)
    doc["registros"].reverse()
    resultado = cargar(doc, con)
    assert resultado["repetido"] is True
    assert resultado["total_spam_excluido"] == 3
    assert len(con.cargas) == 1


def test_id_existente_distinto_rechaza_todo_y_revierte():
    con = Conexion()
    cargar(documento("a", spam=1), con)
    anterior = deepcopy((con.filas, con.meta, con.cargas))
    otro = documento("b", "a", spam=2)
    otro["registros"][1]["contenido_textual"] = "No sobrescribir"
    with pytest.raises(ValueError, match="conflicto"):
        cargar(otro, con)
    assert (con.filas, con.meta, con.cargas) == anterior
    assert con.commits == 1
    assert con.rollbacks == 1


def test_solapamiento_sin_recibo_con_spam_requiere_conciliacion():
    con = Conexion()
    cargar(documento("a", spam=1), con)
    anterior = deepcopy((con.filas, con.meta, con.cargas))
    with pytest.raises(ValueError, match="conciliación"):
        cargar(documento("a", "b", spam=2), con)
    assert (con.filas, con.meta, con.cargas) == anterior


def test_solapamiento_identico_sin_spam_no_duplica_filas():
    con = Conexion()
    cargar(documento("a", spam=0), con)
    resultado = cargar(documento("a", "b", spam=0), con)
    assert resultado["total"] == 2
    assert resultado["insertados"] == 1
    assert resultado["total_spam_excluido"] == 0


def test_tabla_con_filas_sin_meta_no_adivina_contadores():
    con = Conexion()
    con.filas["a"] = documento("a")["registros"][0]
    con.commit()
    with pytest.raises(ValueError, match="sin metadatos"):
        cargar(documento("b"), con)
    assert set(con.filas) == {"a"}


def test_meta_total_incoherente_impide_carga():
    con = Conexion()
    cargar(documento("a"), con)
    con.meta["total"] = 90
    with pytest.raises(ValueError, match="metadatos"):
        cargar(documento("b"), con)
    assert set(con.filas) == {"a"}


def test_lector_publico_no_expone_api_de_escritura():
    from src.config import db_client

    assert not hasattr(db_client, "sincronizar_conjunto")
    assert not hasattr(db_client, "_SQL_UPSERT")


def test_lote_vacio_no_purga_registros():
    con = Conexion()
    cargar(documento("a", spam=0), con)
    resultado = cargar(documento(spam=0), con)
    assert resultado["total"] == 1
    assert resultado["retirados"] == 0


def test_fallo_al_guardar_recibo_revierte_y_reintento_funciona():
    con = Conexion(fallar="INSERT INTO conjunto_consultable_cargas")
    with pytest.raises(RuntimeError):
        cargar(documento("a", spam=2), con)
    assert con.filas == con.cargas == {}
    assert con.meta is None
    con.fallar = None
    resultado = cargar(documento("a", spam=2), con)
    assert resultado["total_spam_excluido"] == 2


def test_recibo_sin_filas_no_confirma_guardado_falso():
    con = Conexion()
    doc = documento("a", spam=0)
    con.cargas[db._huella_lote(doc, db._preparar_lote(doc))] = {}
    con.commit()
    with pytest.raises(ValueError, match="recibo"):
        cargar(doc, con)
    assert con.filas == {}
