from src.app.estilo_agente import informacion_lateral


def test_tarjeta_tiene_control_nativo_accesible_y_texto_escapado():
    html = informacion_lateral("modelo", "Modelo", ["Texto <script>alert(1)</script>"])
    assert "<details" in html and "<summary" in html
    assert 'aria-label="Información de Modelo"' in html
    assert 'aria-describedby="info-modelo"' in html
    assert 'id="info-modelo"' in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "agente-info-derecha" not in html


def test_tarjeta_derecha():
    assert "agente-info-derecha" in informacion_lateral(
        "modo", "Modo", ["Explicación"], derecha=True,
    )
