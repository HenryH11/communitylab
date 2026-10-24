"""Aceptación del cliente DB con driver real y conexión simulada, sin red."""

import base64
from copy import deepcopy
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, patch

import pytest

if TYPE_CHECKING:
    from src.config import db_client as db
    from oracledb import Connection
else:
    try:
        from src.config import db_client as db
    except ModuleNotFoundError as error:
        if error.name not in {"oci", "oracledb"}:
            raise
        db = None

pytestmark = pytest.mark.skipif(db is None, reason="requiere OCI y oracledb")


def documento(*ids, version="1.1", spam=1):
    salida = {
        "version": version,
        "campos": list(db.CAMPOS_CONJUNTO),
        "total": len(ids),
        "registros": [
            dict(
                id=i,
                canal="discord",
                sentimiento="positivo",
                tema="aprendizaje",
                tipo="testimonio",
                contenido_textual="Acción, ñ y emoji 🚀",
                fecha="2026-09-10T14:32:00Z",
            )
            for i in ids
        ],
    }
    if version == "1.1":
        salida["total_spam_excluido"] = spam
    return salida


class Conexion:
    """Modelo transaccional limitado; NO interpreta ni valida SQL Oracle."""

    autocommit = False
    transaction_in_progress = False

    def __init__(self, fallar=None):
        self.filas = {}
        self.meta = None
        self.confirmado = ({}, None)
        self.commits = 0
        self.rollbacks = 0
        self.operaciones = []
        self.fallar = fallar

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.confirmado = deepcopy((self.filas, self.meta))
        self.commits += 1

    def rollback(self):
        self.filas, self.meta = deepcopy(self.confirmado)
        self.rollbacks += 1


class Cursor:
    def __init__(self, conexion):
        self.conexion = conexion
        self.resultado = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametros=None):
        con = self.conexion
        con.operaciones.append(sql)
        if con.fallar and con.fallar in sql:
            raise RuntimeError("Fallo simulado")
        if sql.startswith("LOCK TABLE"):
            assert "NOWAIT" in sql
        elif sql == "SELECT id FROM conjunto_consultable":
            self.resultado = [(i,) for i in con.filas]
        elif sql == db._SQL_META:
            con.meta = deepcopy(parametros)
        elif sql == db._SQL_SELECT_TODOS:
            self.resultado = []
            if con.meta is not None:
                meta = tuple(
                    con.meta[c]
                    for c in ("version", "total", "total_spam_excluido")
                )
                self.resultado = [
                    meta + tuple(con.filas[i][c] for c in db.CAMPOS_CONJUNTO)
                    for i in sorted(con.filas)
                ]
                if not self.resultado:
                    self.resultado = [meta + (None,) * 7]
        else:
            raise AssertionError(f"SQL no modelado: {sql}")

    def executemany(self, sql, lote):
        con = self.conexion
        con.operaciones.append(sql)
        if con.fallar and con.fallar in sql:
            # Simula que la primera fila pudo ejecutarse antes de fallar.
            if sql == db._SQL_UPSERT:
                con.filas[lote[0]["id"]] = deepcopy(lote[0])
            raise RuntimeError("Fallo simulado")
        if sql == db._SQL_UPSERT:
            for registro in lote:
                con.filas[registro["id"]] = deepcopy(registro)
        elif sql == "DELETE FROM conjunto_consultable WHERE id = :id":
            for registro in lote:
                del con.filas[registro["id"]]
        else:
            raise AssertionError(f"SQL no modelado: {sql}")

    def setinputsizes(self, **tipos):
        assert tipos == {"contenido_textual": db.oracledb.DB_TYPE_CLOB}
        self.conexion.operaciones.append("BIND CLOB contenido_textual")

    def fetchall(self):
        return self.resultado


@pytest.fixture(autouse=True)
def impedir_red(monkeypatch):
    if db is not None:
        monkeypatch.setattr(
            db.oracledb,
            "connect",
            Mock(
                side_effect=AssertionError("No se permite conectar a DB real")
            ),
        )
        monkeypatch.setattr(
            db,
            "obtener_cliente_secretos",
            Mock(side_effect=AssertionError("No se permite acceder a Vault")),
        )


def cargar(doc, con):
    return db.sincronizar_conjunto(
        doc, conexion=cast("Connection", con), instantanea_completa=True
    )


def test_roundtrip_contrato_11_unicode_null_sin_mutar():
    doc = documento("int-002", "int-001", spam=3)
    doc["registros"][0]["fecha"] = None
    original = deepcopy(doc)
    con = Conexion()
    assert cargar(doc, con)["sincronizados"] == 2
    esperado = deepcopy(doc)
    esperado["registros"].sort(key=lambda r: r["id"])
    assert db.leer_conjunto(conexion=cast("Connection", con)) == esperado
    assert doc == original
    assert con.commits == 1


def test_roundtrip_version_10():
    doc, con = documento("int-001", version="1.0"), Conexion()
    cargar(doc, con)
    assert db.leer_conjunto(conexion=cast("Connection", con)) == doc


@pytest.mark.parametrize("longitud", [161, 4001, 32768, 50000])
def test_texto_completo_se_carga_con_bind_clob_y_llega_al_agente(longitud):
    from src.app.fuente_agente import adaptar_conjunto

    texto = "  Inicio 🚀\n" + "á" * longitud + "\nFinal intacto.  "
    doc, con = documento("int-001"), Conexion()
    doc["registros"][0]["contenido_textual"] = texto
    cargar(doc, con)
    assert con.operaciones.index("BIND CLOB contenido_textual") < con.operaciones.index(db._SQL_UPSERT)
    leido = db.leer_conjunto(conexion=cast("Connection", con))
    assert leido["registros"][0]["contenido_textual"] == texto
    assert adaptar_conjunto(leido)[0]["texto"] == texto


@pytest.mark.parametrize("inyectada", [True, False])
def test_clob_se_materializa_antes_de_cerrar_cursor_y_conexion(inyectada):
    texto = "Inicio\n" + "Experiencia íntegra 🚀 " * 3000 + "\nFinal."
    conexion = Mock()
    cursor = Mock()
    conexion.__enter__ = Mock(return_value=conexion)
    conexion.__exit__ = Mock(return_value=False)
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    conexion.cursor.return_value = cursor
    abierto = {"valor": True}
    def cerrar(*_):
        abierto["valor"] = False
    cursor.__exit__.side_effect = cerrar
    lob = Mock(spec=db.oracledb.LOB)
    def leer():
        assert abierto["valor"], "El CLOB se leyó después de cerrar el cursor"
        return texto
    lob.read.side_effect = leer
    registro = documento("int-001")["registros"][0]
    registro["contenido_textual"] = lob
    cursor.fetchall.return_value = [
        ("1.1", 1, 0) + tuple(registro[c] for c in db.CAMPOS_CONJUNTO),
    ]
    with patch.object(db, "obtener_conexion_lectura", return_value=conexion):
        resultado = db.leer_conjunto(
            conexion=cast("Connection", conexion) if inyectada else None,
        )
    lob.read.assert_called_once_with()
    assert resultado["registros"][0]["contenido_textual"] == texto
    assert not abierto["valor"]


def test_fallo_clob_se_propaga_sin_convertirlo_en_texto_vacio():
    cursor = Mock()
    lob = Mock(spec=db.oracledb.LOB)
    lob.read.side_effect = RuntimeError("Fallo de lectura")
    cursor.fetchall.return_value = [("1.1", 1, 0, "id", "canal", "positivo", "tema", "tipo", lob, None)]
    with pytest.raises(RuntimeError, match="Fallo de lectura"):
        db._leer_filas_con_texto(cursor)


def test_lectura_rechaza_lob_binario():
    cursor = Mock()
    lob = Mock(spec=db.oracledb.LOB)
    lob.read.return_value = b"datos binarios"
    cursor.fetchall.return_value = [("1.1", 1, 0, "id", "canal", "positivo", "tema", "tipo", lob, None)]
    with pytest.raises(ValueError, match="no binario"):
        db._leer_filas_con_texto(cursor)


def test_retira_id_que_ya_no_esta_sin_duplicar():
    con = Conexion()
    cargar(documento("int-001", "int-002"), con)
    doc = documento("int-001", spam=2)
    doc["registros"][0]["tema"] = "tema actualizado"
    assert cargar(doc, con)["retirados"] == 1
    assert db.leer_conjunto(conexion=cast("Connection", con)) == doc
    assert cargar(doc, con)["retirados"] == 0
    assert db.leer_conjunto(conexion=cast("Connection", con))["total"] == 1


def test_instantanea_vacia_confirmada_conserva_spam():
    con = Conexion()
    cargar(documento("int-001"), con)
    doc = documento(spam=8)
    assert cargar(doc, con)["retirados"] == 1
    assert db.leer_conjunto(conexion=cast("Connection", con)) == doc


@pytest.mark.parametrize("confirmacion", [False, None, 1, "true"])
def test_no_escribe_sin_confirmacion_exacta(confirmacion):
    con = Conexion()
    with pytest.raises(ValueError, match="instantanea_completa"):
        db.sincronizar_conjunto(
            documento(), conexion=cast("Connection", con), instantanea_completa=confirmacion
        )
    assert con.operaciones == []


@pytest.mark.parametrize(
    "cambio",
    [
        {"total": 23},
        {"total": True},
        {"total": -1},
        {"version": "9.0"},
        {"campos": ["id"]},
        {"total_spam_excluido": -1},
        {"total_spam_excluido": True},
        {"total_spam_excluido": "2"},
        {"registros": "no es lista"},
    ],
)
def test_documento_invalido_no_abre_conexion(cambio):
    doc = documento("int-001")
    doc.update(cambio)
    with patch.object(db, "obtener_conexion") as abrir:
        with pytest.raises((ValueError, TypeError)):
            db.sincronizar_conjunto(doc, instantanea_completa=True)
        abrir.assert_not_called()


def test_11_exige_contador_y_no_admite_duplicados():
    doc = documento("int-001")
    del doc["total_spam_excluido"]
    with pytest.raises(ValueError):
        cargar(doc, Conexion())
    with pytest.raises(ValueError, match="duplicados"):
        cargar(documento("int-001", "int-001"), Conexion())


@pytest.mark.parametrize(
    "cambio",
    [
        {"id": "../otro"},
        {"id": "int-1' OR 1=1"},
        {"contenido_textual": ""},
        {"contenido_textual": " \t\n"},
        {"contenido_textual": None},
        {"tema": 8},
        {"canal": []},
        {"fecha": "2026-02-30T00:00:00Z"},
        {"fecha": "2026-01-01T00:00:00+03:00"},
        {"fecha": 8},
        {"extra": "no debe perderse silenciosamente"},
        {"contenido_textual": "\ud800"},
    ],
)
def test_registro_invalido_se_rechaza_antes_de_sql(cambio):
    doc, con = documento("int-001"), Conexion()
    doc["registros"][0].update(cambio)
    with pytest.raises((ValueError, TypeError, UnicodeError)):
        cargar(doc, con)
    assert con.operaciones == []


def test_rechaza_campo_faltante():
    doc = documento("int-001")
    del doc["registros"][0]["fecha"]
    with pytest.raises(ValueError):
        cargar(doc, Conexion())


def test_contrato_y_sql_usan_nombre_confirmado_sin_alias_legacy():
    assert "contenido_textual" in db.CAMPOS_CONJUNTO
    assert "contenido_corto" not in db.CAMPOS_CONJUNTO
    assert ":contenido_textual" in db._SQL_UPSERT
    assert "d.contenido_textual" in db._SQL_SELECT_TODOS
    doc, con = documento("int-001"), Conexion()
    registro = doc["registros"][0]
    registro["contenido_corto"] = registro.pop("contenido_textual")
    with pytest.raises(ValueError, match="7 campos"):
        cargar(doc, con)
    assert not con.operaciones


@pytest.mark.parametrize("campo", ["canal", "sentimiento", "tema", "tipo"])
@pytest.mark.parametrize("valor", [None, "", " \t\n", 7, []])
def test_columnas_not_null_se_validan_en_todo_el_lote(campo, valor):
    doc = documento("int-001", "int-002")
    doc["registros"][1][campo] = valor
    original, con = deepcopy(doc), Conexion()
    with pytest.raises(ValueError, match=campo):
        cargar(doc, con)
    assert doc == original
    assert con.operaciones == []
    assert con.commits == con.rollbacks == 0
    with patch.object(db, "obtener_conexion") as abrir:
        with pytest.raises(ValueError, match=campo):
            db.sincronizar_conjunto(doc, instantanea_completa=True)
        abrir.assert_not_called()


def test_columnas_requeridas_conservan_texto_y_fecha_null():
    doc, con = documento("int-001"), Conexion()
    doc["registros"][0].update(
        canal="  comunidad 🚀  ",
        sentimiento="positivo",
        tema="acción y formación",
        tipo="testimonio",
        fecha=None,
    )
    original = deepcopy(doc)
    cargar(doc, con)
    assert db.leer_conjunto(conexion=cast("Connection", con)) == original
    assert doc == original


@pytest.mark.parametrize(
    "etapa",
    [
        "LOCK TABLE",
        "MERGE INTO conjunto_consultable destino",
        "DELETE FROM",
        "MERGE INTO conjunto_consultable_meta",
    ],
)
def test_error_revierte_filas_y_metadatos(etapa):
    con = Conexion()
    anterior = documento("int-001", "int-002")
    cargar(anterior, con)
    con.fallar = etapa
    with pytest.raises(RuntimeError):
        cargar(documento("int-003", spam=9), con)
    con.fallar = None
    assert db.leer_conjunto(conexion=cast("Connection", con)) == anterior
    assert con.commits == 1
    assert con.rollbacks == 1


@pytest.mark.parametrize("atributo", ["autocommit", "transaction_in_progress"])
def test_no_confirma_trabajo_ajeno(atributo):
    con = Conexion()
    setattr(con, atributo, True)
    with pytest.raises(ValueError, match="conexión exclusiva"):
        cargar(documento("int-001"), con)
    assert con.commits == con.rollbacks == 0
    assert con.operaciones == []


def test_lectura_no_modifica_ni_hace_commit():
    con = Conexion()
    cargar(documento("int-001"), con)
    con.operaciones.clear()
    db.leer_conjunto(conexion=cast("Connection", con))
    assert con.operaciones == [db._SQL_SELECT_TODOS]
    assert con.commits == 1


def test_lectura_sin_publicacion_o_con_total_inconsistente_falla():
    con = Conexion()
    with pytest.raises(ValueError, match="metadatos"):
        db.leer_conjunto(conexion=cast("Connection", con))
    cargar(documento("int-001"), con)
    assert con.meta is not None
    con.meta["total"] = 3
    with pytest.raises(ValueError, match="total"):
        db.leer_conjunto(conexion=cast("Connection", con))


def test_conexiones_propias_separadas(monkeypatch):
    con = Conexion()
    with patch.object(db, "obtener_conexion", return_value=con) as abrir:
        db.sincronizar_conjunto(
            documento("int-001"), instantanea_completa=True
        )
        abrir.assert_called_once_with()
    with patch.object(
        db, "obtener_conexion_lectura", return_value=con
    ) as abrir:
        assert db.leer_conjunto()["total"] == 1
        abrir.assert_called_once_with()


@pytest.mark.parametrize(
    "usuario,secreto",
    [
        ("", ""),
        ("lector", ""),
        ("agent_communitylab", "secret-reader"),
    ],
)
def test_lector_no_reutiliza_credenciales_escritor(
    monkeypatch, usuario, secreto
):
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.setenv("DB_READ_USER", usuario)
    monkeypatch.setenv("DB_READ_PASSWORD_SECRET_OCID", secreto)
    with pytest.raises(ValueError):
        db.obtener_conexion_lectura()


def test_lector_usa_su_usuario_y_secreto(monkeypatch):
    monkeypatch.setenv("DB_READ_USER", "agent_lector")
    monkeypatch.setenv("DB_READ_PASSWORD_SECRET_OCID", "secret-reader")
    monkeypatch.setenv("DB_READ_DSN", "dsn-reader")
    with patch.object(db, "obtener_conexion") as abrir:
        db.obtener_conexion_lectura()
        abrir.assert_called_once_with(
            usuario="agent_lector",
            dsn="dsn-reader",
            ocid_secreto="secret-reader",
        )


def test_password_se_conserva_exacta_y_no_se_imprime():
    cliente = Mock()
    cliente.get_secret_bundle.return_value.data.secret_bundle_content.content = base64.b64encode(
        b" password ficticia "
    ).decode()
    assert (
        db.obtener_secreto_vault("secret-test", cliente=cliente)
        == " password ficticia "
    )


def test_conexion_inyecta_password_sin_normalizar():
    cliente = Mock()
    cliente.get_secret_bundle.return_value.data.secret_bundle_content.content = base64.b64encode(
        b" ficticia "
    ).decode()
    db.oracledb.connect.side_effect = None
    db.obtener_conexion(
        usuario="cargador",
        dsn="dsn-simulado",
        ocid_secreto="secret-test",
        cliente_secretos=cliente,
    )
    db.oracledb.connect.assert_called_once_with(
        user="cargador", password=" ficticia ", dsn="dsn-simulado"
    )


def test_documento_real_generado_por_da():
    from src.datos.conjunto_consultable import construir_conjunto_consultable

    entrega = {
        "interacciones": [
            dict(
                id="int-001",
                canal="discord",
                texto="Acción 🚀",
                sentimiento="positivo",
                tema_principal="comunidad",
                tipo_detectado="testimonio",
            ),
            dict(id="int-002", es_spam_detectado=True),
        ]
    }
    doc = construir_conjunto_consultable(entrega)
    con = Conexion()
    cargar(doc, con)
    assert db.leer_conjunto(conexion=cast("Connection", con)) == doc
