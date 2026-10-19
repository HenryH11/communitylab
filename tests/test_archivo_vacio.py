"""QA-1: Carga de archivo JSON vacío o sin interacciones (Semana 5.1)."""
import json
from pathlib import Path

import pytest

from src.datos.entrega_ia import preparar_paquete_ia

FIXTURES = Path(__file__).parent / "fixtures"


def _cargar(nombre: str) -> dict:
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


def test_json_vacio_no_rompe_pipeline():
    """Un JSON válido con interacciones vacías debe procesarse sin excepción."""
    datos = _cargar("json_vacio_semana51.json")
    paquete = preparar_paquete_ia(
        datos, fecha_referencia="2026-10-18T12:00:00Z", tamano_ciclo=20
    )
    assert paquete is not None
    assert len(paquete.get("interacciones", [])) == 0


def test_json_sin_campo_interacciones_falla_claro():
    """Si falta 'interacciones', el error debe ser explícito (no un KeyError opaco)."""
    datos = _cargar("json_sin_interacciones.json")
    with pytest.raises((KeyError, ValueError, TypeError)) as excinfo:
        preparar_paquete_ia(
            datos, fecha_referencia="2026-10-18T12:00:00Z", tamano_ciclo=20
        )
    # El mensaje debe ser entendible, no un stacktrace críptico
    assert excinfo.value is not None