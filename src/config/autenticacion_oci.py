"""Seleccion explícita de identidad OCI para VM o perfil local."""

import os
from pathlib import Path

import oci.config
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner


def configuracion_cliente() -> dict:
    modo = os.getenv("OCI_AUTH_MODE", "instance_principal").strip()
    if modo == "instance_principal":
        return {
            "config": {},
            "signer": InstancePrincipalsSecurityTokenSigner(),
            "timeout": (5, 20),
        }
    if modo != "api_key":
        raise ValueError("OCI_AUTH_MODE debe ser instance_principal o api_key")
    archivo = os.getenv("OCI_CONFIG_FILE", "").strip()
    if not archivo:
        directorio = os.getenv("OCI_CONFIG_DIR", "~/.oci").strip()
        archivo = str(Path(directorio).expanduser() / "config")
    perfil = os.getenv("OCI_PROFILE", "DEFAULT").strip()
    if not perfil:
        raise ValueError("OCI_PROFILE no puede estar vacio")
    config = oci.config.from_file(
        file_location=str(Path(archivo).expanduser()), profile_name=perfil,
    )
    oci.config.validate_config(config)
    return {"config": config, "timeout": (5, 20)}
