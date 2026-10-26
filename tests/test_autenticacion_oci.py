from unittest.mock import Mock, patch

import pytest

from src.config.autenticacion_oci import configuracion_cliente
from src.config import db_client, oci_client


def test_vm_conserva_instance_principals(monkeypatch):
    monkeypatch.delenv("OCI_AUTH_MODE", raising=False)
    with patch("src.config.autenticacion_oci.InstancePrincipalsSecurityTokenSigner") as signer:
        parametros = configuracion_cliente()
    assert parametros == {"config": {}, "signer": signer.return_value, "timeout": (5, 20)}


def test_perfil_local_explicito_no_consulta_identidad_vm(monkeypatch):
    monkeypatch.setenv("OCI_AUTH_MODE", "api_key")
    monkeypatch.setenv("OCI_CONFIG_FILE", r"C:\seguro\oci\config")
    monkeypatch.setenv("OCI_PROFILE", "COMMUNITYLAB_READ")
    config = {"region": "region-prueba"}
    with (
        patch("src.config.autenticacion_oci.oci.config.from_file", return_value=config) as cargar,
        patch("src.config.autenticacion_oci.oci.config.validate_config") as validar,
        patch("src.config.autenticacion_oci.InstancePrincipalsSecurityTokenSigner") as signer,
    ):
        assert configuracion_cliente() == {"config": config, "timeout": (5, 20)}
    cargar.assert_called_once_with(
        file_location=r"C:\seguro\oci\config", profile_name="COMMUNITYLAB_READ",
    )
    validar.assert_called_once_with(config)
    signer.assert_not_called()


def test_directorio_y_perfil_predeterminados(monkeypatch):
    monkeypatch.setenv("OCI_AUTH_MODE", "api_key")
    monkeypatch.setenv("OCI_CONFIG_DIR", r"C:\perfil")
    monkeypatch.delenv("OCI_CONFIG_FILE", raising=False)
    monkeypatch.delenv("OCI_PROFILE", raising=False)
    with (
        patch("src.config.autenticacion_oci.oci.config.from_file", return_value={}) as cargar,
        patch("src.config.autenticacion_oci.oci.config.validate_config"),
    ):
        configuracion_cliente()
    cargar.assert_called_once_with(file_location=r"C:\perfil\config", profile_name="DEFAULT")


def test_perfil_invalido_no_hace_fallback(monkeypatch):
    monkeypatch.setenv("OCI_AUTH_MODE", "api_key")
    with (
        patch("src.config.autenticacion_oci.oci.config.from_file", side_effect=FileNotFoundError),
        patch("src.config.autenticacion_oci.InstancePrincipalsSecurityTokenSigner") as signer,
        pytest.raises(FileNotFoundError),
    ):
        configuracion_cliente()
    signer.assert_not_called()


def test_modo_desconocido_es_error(monkeypatch):
    monkeypatch.setenv("OCI_AUTH_MODE", "automatico")
    with pytest.raises(ValueError, match="OCI_AUTH_MODE"):
        configuracion_cliente()


@pytest.mark.parametrize("modulo,fabrica,funcion", [
    (db_client, "SecretsClient", "obtener_cliente_secretos"),
    (oci_client, "ObjectStorageClient", "obtener_cliente"),
])
def test_ambos_clientes_usan_configuracion_seleccionada(modulo, fabrica, funcion):
    obtener = getattr(modulo, funcion)
    obtener.cache_clear()
    cliente = Mock()
    cliente.get_namespace.return_value.data = "namespace"
    try:
        with (
            patch.object(modulo, "configuracion_cliente", return_value={"config": {"region": "prueba"}}),
            patch.object(modulo, fabrica, return_value=cliente) as crear,
        ):
            obtener()
        crear.assert_called_once_with(config={"region": "prueba"})
    finally:
        obtener.cache_clear()
