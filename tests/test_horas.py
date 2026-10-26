from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from src.app.horas import fecha_local, zona_usuario


@pytest.mark.parametrize(("zona", "esperado"), [
    ("America/Bogota", "25/10/2026 08:00 · America/Bogota (UTC-05:00)"),
    ("Asia/Kolkata", "25/10/2026 18:30 · Asia/Kolkata (UTC+05:30)"),
    ("Pacific/Auckland", "26/10/2026 02:00 · Pacific/Auckland (UTC+13:00)"),
    ("UTC", "25/10/2026 13:00 · UTC (UTC+00:00)"),
])
def test_fecha_local_con_zona_y_desfase(zona, esperado):
    assert fecha_local(datetime(2026, 10, 25, 13, tzinfo=timezone.utc), ZoneInfo(zona)) == esperado


def test_cambio_horario_estacional():
    zona = ZoneInfo("America/New_York")
    assert "UTC-04:00" in fecha_local(datetime(2026, 7, 1, tzinfo=timezone.utc), zona)
    assert "UTC-05:00" in fecha_local(datetime(2026, 12, 1, tzinfo=timezone.utc), zona)


def test_no_acepta_fecha_sin_zona():
    with pytest.raises(ValueError, match="zona horaria"):
        fecha_local(datetime(2026, 10, 25), ZoneInfo("UTC"))


@pytest.mark.parametrize("nombre", [None, "America/Bogota", "Zona/Inventada"])
def test_zona_del_navegador_y_fallback_explicito(nombre):
    with patch("src.app.horas.st") as st:
        st.context.timezone = nombre
        assert zona_usuario().key == ("America/Bogota" if nombre == "America/Bogota" else "UTC")
        if nombre == "Zona/Inventada":
            st.warning.assert_called_once()
