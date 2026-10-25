from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts import generar_plantillas_diarias as ejecutor


@pytest.mark.parametrize("catalogo,codigo", [
    (None, 0),
    (SimpleNamespace(entradas={"linkedin": object()}, fallos={}), 0),
    (SimpleNamespace(entradas={}, fallos={"linkedin": "Fallo"}), 2),
])
def test_ejecutor_reporta_estado_real_sin_modelos(catalogo, codigo):
    with (
        patch.object(ejecutor, "load_dotenv"),
        patch.object(ejecutor.RepositorioCatalogo, "desde_entorno", return_value=object()),
        patch.object(ejecutor, "actualizar_catalogo", return_value=catalogo) as actualizar,
    ):
        assert ejecutor.principal() == codigo
        actualizar.assert_called_once()


def test_ejecutor_fallo_oci_no_devuelve_exito():
    with (
        patch.object(ejecutor, "load_dotenv"),
        patch.object(ejecutor.RepositorioCatalogo, "desde_entorno",
                     side_effect=RuntimeError("OCI no disponible")),
    ):
        assert ejecutor.principal() == 1
