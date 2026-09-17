# 🚀 Proyecto de CommunityLab MotorInteligente - Equipo 39 - PROGRAMA ONE ALURA LATAM GRUPO 10

¡Bienvenidos a **CommunityLab**! Este proyecto es el MVP (Producto Mínimo Viable) desarrollado por el Equipo 39 del Programa ONE G10 con No Country. Es un motor inteligente diseñado para potenciar la interacción y gestión dentro de comunidades de aprendizaje en Latinoamérica, integrando arquitectura en la nube y agentes de Inteligencia Artificial.

---

## 📁 Estructura General del Proyecto

El esqueleto técnico ha sido desplegado bajo los más altos estándares de gobernanza:

*   **`.github/workflows/`**: Configuraciones de integración y despliegue continuo (CI/CD).
*   **`config/`**: Módulos y variables de entorno para la inicialización del ecosistema.
*   **`src/data/`**: Gestión, ingesta y almacenamiento de datos semiestructurados.
*   **`src/agents/`**: Lógica central, prompts y orquestación de los Agentes de IA.
*   **`src/app/`**: Interfaz de usuario y flujos principales de la aplicación del MVP.
*   **`tests/`**: Pruebas unitarias, automatizadas y de integración de software.

---

## 🛠️ Tecnologías y Herramientas (Semana 0)
*   **Lenguaje:** Python 3.11+
*   **Control de Versiones:** Git & GitHub
*   **Infraestructura Nube:** Oracle Cloud Infrastructure (OCI)

## Ingesta y relevancia (aporte de Jhonattan)

Con Python 3.11+, desde la raíz, sin instalar dependencias para este módulo:

```sh
python -m src.data.ingest --config config/relevancia.json --fecha-referencia 2026-09-17T12:00:00Z
python -m unittest discover -s tests -p "test_*.py" -v
python tests/verificar_transformacion_reddit.py
```

La primera orden genera datos seleccionados y un informe de decisiones en
`output/datos/`. La fecha fija permite reproducir la demo; para datos actuales,
indicar otra fecha o quitar `--fecha-referencia` para usar UTC actual.

Consultar el [criterio](docs/criterio_puntuacion_relevancia.md), el
[contrato para IA](docs/contrato_datos_ingesta.md) y el
[avance de Jhonattan](docs/avance_jhonattan_semana1.md). Los pesos y el contrato
se entregan como propuestas para validación del equipo.

---

## 👥 Miembros del Equipo 39 (ONE G10 LATAM)

### 💼 Project Manager
*   **Hernández Godoy Enrique** - *Project Manager*

### 📊 Data Analyst
*   **Benavides Concha Jhonattan Gabriel** - *Data Analyst*
*   **Vásquez Gustavo** - *Data Analyst*

### 🧪 Data Scientist
*   **Bustinza Arnold** - *Data Scientist*
*   **González Portillo Danny de Jesús** - *Data Scientist*
*   **Pinto Arthur** - *Data Scientist*

### 💻 Software Engineer / Solution Architect
*   **Aviles Nelson Ramses** - *Software Engineer / Solution Architect*
*   **Peralta Ocampos Sebastián** - *Software Engineer / Solution Architect*

### ☁️ Cloud Engineer / DevOps
*   **Preda Renato** - *Cloud Engineer*
*   **Soto Marco** - *Cloud Engineer*

---

## 🛡️ Flujo de Trabajo para el Equipo (Gobernanza)

La rama `main` está **protegida**. No se permiten cambios directos. Para colaborar, sigue estos pasos desde tu terminal:

1. **Clonar el proyecto:** `git clone https://github.com`
2. **Crear una rama de trabajo:** `git checkout -b feature/tu-nombre-tarea`
3. **Guardar cambios locales:** `git add .` y `git commit -m "feat: breve descripción"`
4. **Subir tu rama a GitHub:** `git push -u origin feature/tu-nombre-tarea`
5. **Abrir un Pull Request (PR)** en la web para revisión y aprobación del equipo (requiere 1 aprobación mínima).
