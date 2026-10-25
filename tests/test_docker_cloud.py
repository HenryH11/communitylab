"""Regresión de la configuración de despliegue; no usa red ni credenciales."""

from pathlib import Path
import re


RAIZ = Path(__file__).resolve().parents[1]


def test_imagen_multistage_y_usuario_sin_privilegios():
    dockerfile = (RAIZ / "Dockerfile.frontend").read_text()
    assert dockerfile.count("\nFROM ") + dockerfile.startswith("FROM ") == 2
    assert "COPY --from=dependencias /opt/venv /opt/venv" in dockerfile
    assert "USER appuser" in dockerfile
    assert "--uid 1000" in dockerfile


def test_imagen_copia_solo_directorios_de_ejecucion():
    lineas = (RAIZ / "Dockerfile.frontend").read_text().splitlines()
    copias = [linea for linea in lineas if linea.startswith("COPY ")]
    assert copias == [
        "COPY requirements.frontend.txt requirements.txt",
        "COPY --from=dependencias /opt/venv /opt/venv",
        "COPY src/__init__.py src/evaluacion.py ./src/",
        "COPY src/agentes/ ./src/agentes/",
        "COPY src/app/ ./src/app/",
        "COPY src/config/ ./src/config/",
        "COPY src/datos/ ./src/datos/",
        "COPY configuracion/ ./configuracion/",
        "COPY .streamlit/ ./.streamlit/",
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
    dockerfile = (RAIZ / "Dockerfile.frontend").read_text()
    assert "http://127.0.0.1:8501/_stcore/health" in dockerfile
    assert 'CMD ["streamlit", "run", "src/app/app.py"]' in dockerfile


def test_compose_separa_entorno_puerto_y_volumen_interno():
    compose = (RAIZ / "docker-compose.yml").read_text()
    marketing, resto = compose.split("  communitylab-ingestor:", 1)
    _, interno = resto.split("  communitylab-interno:", 1)
    assert "env_file:" not in marketing
    assert "DB_USER=" not in marketing
    assert "DB_PASSWORD_SECRET_OCID=" not in marketing
    assert "DB_READ_PASSWORD_SECRET_OCID=" in marketing
    assert 'profiles: ["interno"]' in interno
    assert '["streamlit", "run", "src/app/app_interna.py"]' in interno
    assert '"127.0.0.1:8502:8501"' in interno
    assert "path: .env.interno" in interno
    assert "communitylab-interno-salida:/app/salida" in interno


def test_ingestor_optativo_no_bloquea_marketing_ni_publica_puerto():
    compose = (RAIZ / "docker-compose.yml").read_text()
    marketing, resto = compose.split("  communitylab-ingestor:", 1)
    ingestor, _ = resto.split("  communitylab-interno:", 1)
    assert "depends_on:" not in marketing
    assert "INGESTOR_URL=" not in marketing
    assert 'profiles: ["ingesta"]' in ingestor
    assert 'expose:\n      - "8000"' in ingestor
    assert "ports:" not in ingestor
    assert "DB_PASSWORD_SECRET_OCID=" in ingestor
    assert "DB_READ_PASSWORD_SECRET_OCID=" not in ingestor


def test_backend_especializado_y_dependencias_locales_compatibles():
    backend = (RAIZ / "Dockerfile.backend").read_text()
    assert "COPY src/services/ingest_server.py ./src/services/ingest_server.py" in backend
    assert "COPY src/ ./src/" not in backend
    assert "USER appuser" in backend
    assert "http://127.0.0.1:8000/health" in backend
    assert 'CMD ["python", "src/services/ingest_server.py"]' in backend
    dependencias = (RAIZ / "requirements.txt").read_text()
    assert "-r requirements.frontend.txt" in dependencias
    assert "-r requirements.backend.txt" in dependencias


def test_compose_referencia_archivos_existentes_y_declara_sus_volumenes():
    compose = (RAIZ / "docker-compose.yml").read_text()
    archivos = re.findall(r"^\s+dockerfile:\s+(\S+)$", compose, re.MULTILINE)
    assert len(archivos) == 3
    for archivo in archivos:
        assert (RAIZ / archivo).is_file(), f"Falta el archivo de construcción: {archivo}"
    servicios, declaraciones = compose.split("\nvolumes:\n", 1)
    declaraciones = declaraciones.split("\nnetworks:", 1)[0]
    usados = re.findall(r"^\s+- ([\w-]+):/app/salida$", servicios, re.MULTILINE)
    declarados = re.findall(r"^  ([\w-]+):$", declaraciones, re.MULTILINE)
    assert set(usados) <= set(declarados)


def test_frontend_vm_conserva_entorno_publico_sin_conexion_de_carga():
    local = (RAIZ / "docker-compose.yml").read_text().split("  communitylab-ingestor:", 1)[0]
    frontend = (RAIZ / "docker-compose.frontend.yml").read_text()
    variables = r"^\s+- ([A-Z][A-Z0-9_]*=.*)$"
    assert re.findall(variables, frontend, re.MULTILINE) == re.findall(variables, local, re.MULTILINE)
    assert "INGESTOR_URL" not in frontend
    assert "DB_USER=" not in frontend
    assert "depends_on:" not in frontend
    assert "communitylab-ingestor:" not in frontend
    assert "communitylab-salida:/app/salida" in frontend
    assert "\n  communitylab-salida:" in frontend


def test_backend_vm_exige_bind_explicito_y_entorno_escritor():
    backend = (RAIZ / "docker-compose.backend.yml").read_text()
    assert '${INGESTOR_BIND_IP:?' in backend
    assert '}:8000:8000"' in backend
    assert '"8000:8000"' not in backend
    assert "10.100.65.49" not in backend
    assert "${DB_DSN:?" in backend
    assert "${DB_PASSWORD_SECRET_OCID:?" in backend
    assert "DB_READ_" not in backend
    assert "communitylab-app:" not in backend
    for nombre in ("frontend", "backend"):
        compose = (RAIZ / f"docker-compose.{nombre}.yml").read_text()
        assert "no-new-privileges:true" in compose
        assert "cap_drop:\n      - ALL" in compose
        for archivo in re.findall(r"^\s+dockerfile:\s+(\S+)$", compose, re.MULTILINE):
            assert (RAIZ / archivo).is_file()
