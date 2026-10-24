"""Regresión de la configuración de despliegue; no usa red ni credenciales."""

from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


def test_imagen_multistage_y_usuario_sin_privilegios():
    dockerfile = (RAIZ / "Dockerfile").read_text()
    assert dockerfile.count("\nFROM ") + dockerfile.startswith("FROM ") == 2
    assert "COPY --from=dependencias /opt/venv /opt/venv" in dockerfile
    assert "USER appuser" in dockerfile
    assert "--uid 1000" in dockerfile


def test_imagen_copia_solo_directorios_de_ejecucion():
    lineas = (RAIZ / "Dockerfile").read_text().splitlines()
    copias = [linea for linea in lineas if linea.startswith("COPY ")]
    assert copias == [
        "COPY requirements.txt .",
        "COPY --from=dependencias /opt/venv /opt/venv",
        "COPY src/ ./src/",
        "COPY configuracion/ ./configuracion/",
        "COPY scripts/generar_plantillas_diarias.py ./scripts/generar_plantillas_diarias.py",
    ]


def test_contexto_excluye_credenciales_incluso_anidadas():
    reglas = set((RAIZ / ".dockerignore").read_text().splitlines())
    assert {
        ".env", ".env.*", "**/.env", "**/.env.*",
        "*.pem", "**/*.pem", "*.key", "**/*.key",
        ".oci", "**/.oci", ".ssh", "**/.ssh", "salida",
    } <= reglas


def test_compose_conserva_puerto_y_volumen_sin_elevar_privilegios():
    compose = (RAIZ / "docker-compose.yml").read_text()
    assert '"8501:8501"' in compose
    assert "communitylab-salida:/app/salida" in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:\n      - ALL" in compose
    assert "./salida:/app/salida" not in compose


def test_salud_no_requiere_apis_de_ia_ni_oci():
    dockerfile = (RAIZ / "Dockerfile").read_text()
    assert "http://127.0.0.1:8501/_stcore/health" in dockerfile
    assert 'CMD ["streamlit", "run", "src/app/app.py"]' in dockerfile
