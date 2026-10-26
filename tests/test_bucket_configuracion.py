from pathlib import Path
from unittest.mock import Mock

from scripts import probar_oci_storage
from src.config.oci_client import BUCKET_PREDETERMINADO


def test_ejemplo_y_cliente_coinciden_con_bucket_confirmado():
    raiz = Path(__file__).resolve().parents[1]
    assert BUCKET_PREDETERMINADO == "bkt-communitylab-marketing"
    assert f"OCI_BUCKET_NAME={BUCKET_PREDETERMINADO}" in (
        raiz / ".env.example"
    ).read_text(encoding="utf-8").splitlines()


def test_script_usa_bucket_confirmado_y_respeta_variable(monkeypatch):
    cliente = Mock()
    monkeypatch.setattr(probar_oci_storage, "get_oci_client", Mock(return_value=(cliente, "ns")))
    mostrar = Mock()
    subir = Mock()
    monkeypatch.setattr(probar_oci_storage, "display_bucket_info", mostrar)
    monkeypatch.setattr(probar_oci_storage, "upload_object", subir)
    monkeypatch.delenv("OCI_BUCKET_NAME", raising=False)
    assert probar_oci_storage.main() == 0
    assert mostrar.call_args.args[2] == BUCKET_PREDETERMINADO
    assert subir.call_args.args[2] == BUCKET_PREDETERMINADO
    monkeypatch.setenv("OCI_BUCKET_NAME", "bucket-pruebas")
    assert probar_oci_storage.main() == 0
    assert mostrar.call_args.args[2] == "bucket-pruebas"
    assert subir.call_args.args[2] == "bucket-pruebas"
