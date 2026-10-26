import json
import logging

import pytest

from tests.integracion import prueba_validacion_semantica_nueva as evaluacion


@pytest.mark.parametrize("modo", ["lote", "individual"])
def test_informe_conserva_tiempos_reintentos_y_fallback_sin_red(
    modo, tmp_path, caplog, monkeypatch
):
    documento = json.loads(evaluacion.ARCHIVO_MUESTRA.read_text(encoding="utf-8"))
    por_id = {caso["id"]: caso for caso in documento["casos"]}

    def analizar(estado):
        esperado = por_id[estado["id"]]["esperado"]
        spam = esperado["es_spam_detectado"][0]
        return {
            "sentimiento": "neutral",
            "tipo_detectado": esperado.get("tipo_detectado", ["comentario"])[0],
            "tema_principal": esperado.get("tema_principal", ["otros"])[0],
            "subtema": "Control simulado",
            "es_spam_detectado": spam,
            "motivo_spam": "Oferta engañosa" if spam else None,
        }

    monkeypatch.setattr(evaluacion, "analizar_mensaje", analizar)
    monkeypatch.setattr(evaluacion, "analizar_lote", lambda estados: [analizar(e) for e in estados])
    monkeypatch.setattr(evaluacion, "obtener_proveedor_analisis", lambda: "simulado")
    monkeypatch.setattr(evaluacion, "obtener_modelo_nvidia_por_tier", lambda _: "simulado")
    caplog.set_level(logging.INFO, logger="communitylab.ciencia_datos")
    logger = logging.getLogger("communitylab.ciencia_datos")
    logger.warning("reintento_programado", extra={
        "evento": "reintento_programado",
        "campos": {
            "id_interaccion": "nuevo-18", "intento": 1,
            "espera_segundos": 0.5, "tipo_error": "TimeoutError",
            "mensaje": "Detalle que no debe persistir",
        },
    })
    logger.info("proveedor_ia_resuelto", extra={
        "evento": "proveedor_ia_resuelto",
        "campos": {"proveedor_usado": "gemini", "fallback_activado": True},
    })
    evaluacion.test_muestra_nueva_sin_ajustar_expectativas(modo, tmp_path, caplog)
    reporte = json.loads((tmp_path / f"validacion_nueva_{modo}.json").read_text(encoding="utf-8"))
    assert len(reporte["llamadas"]) == (3 if modo == "lote" else 24)
    assert all(llamada["segundos"] >= 0 for llamada in reporte["llamadas"])
    assert reporte["resumen"]["concordantes"] == 24
    evento = reporte["eventos_operativos"][0]
    assert evento["evento"] == "reintento_programado"
    assert evento["id_interaccion"] == "nuevo-18"
    assert evento["espera_segundos"] == 0.5
    assert "mensaje" not in evento
    assert reporte["resoluciones_proveedor"][0]["fallback_activado"] is True
