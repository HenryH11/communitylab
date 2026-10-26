from unittest.mock import Mock

import json
import pytest

from scripts import comprobar_cloud_lectura as diagnostico


@pytest.mark.parametrize("fallo", [None, "oracle", "bucket"])
def test_diagnostico_solo_lee_y_reporta_fallos(monkeypatch, capsys, fallo):
    monkeypatch.setattr(diagnostico, "load_dotenv", Mock())
    leer = Mock(return_value={"total": 600, "version": "1.1"})
    cliente = Mock()
    cliente.list_objects.return_value.data.objects = []
    cliente.list_objects.return_value.data.next_start_with = None
    if fallo == "oracle":
        leer.side_effect = ValueError("texto sensible que no debe mostrarse")
    if fallo == "bucket":
        cliente.list_objects.side_effect = RuntimeError("credencial sensible")
    monkeypatch.setattr(diagnostico.db_client, "leer_conjunto", leer)
    monkeypatch.setattr(diagnostico.oci_client, "obtener_cliente", Mock(return_value=(cliente, "ns")))

    assert diagnostico.principal() == int(fallo is not None)
    captura = capsys.readouterr()
    salida = json.loads(captura.out)
    assert salida["oracle"]["estado"] == ("error" if fallo == "oracle" else "accesible")
    assert salida["bucket"]["estado"] == ("error" if fallo == "bucket" else "accesible")
    assert "sensible" not in captura.out + captura.err
    assert cliente.list_objects.call_args.kwargs["prefix"] == "plantillas/"
    assert cliente.list_objects.call_args.kwargs["limit"] == 5
    cliente.put_object.assert_not_called()
    cliente.delete_object.assert_not_called()
