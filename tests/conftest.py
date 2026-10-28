import os
import pytest


# Evita que la suite escriba en salida/logs; las pruebas usan caplog.
os.environ.setdefault("COMMUNITYLAB_LOGS", "0")


@pytest.fixture
def verificacion_analitica_simulada(monkeypatch):
    """Aísla revisión semántica en suites de búsqueda/UI; su contrato se prueba aparte."""
    from src.agentes.conversacion import AgenteConversacional, SalidaVerificacion

    original = AgenteConversacional._invocar_verificacion

    def verificar(self, *, borrador, evidencia, **kwargs):
        if borrador.get("tipo") != "analisis":
            return original(self, borrador=borrador, evidencia=evidencia, **kwargs)
        objetivos = kwargs.get("afirmaciones_objetivo") or ["Hecho simulado del análisis"]
        return SalidaVerificacion.model_validate({
            "afirmaciones": [
                {"afirmacion": objetivo, "respaldada": bool(evidencia),
                 "citas": [evidencia[0]["id"]] if evidencia else []}
                for objetivo in objetivos
            ],
            "resumen": "Revisión simulada para aislar esta prueba.",
        })

    monkeypatch.setattr(AgenteConversacional, "_invocar_verificacion", verificar)
