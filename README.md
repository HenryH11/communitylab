# 🚀 Proyecto de CommunityLab MotorInteligente - Equipo 39 - PROGRAMA ONE ALURA LATAM GRUPO 10

¡Bienvenidos a **CommunityLab**! Este proyecto es el PMV (Producto Mínimo Viable) desarrollado por el Equipo 39 del Programa ONE G10 con No Country. Es un motor inteligente diseñado para potenciar la interacción y gestión dentro de comunidades de aprendizaje en Latinoamérica, integrando arquitectura en la nube y agentes de inteligencia artificial.

---

## 📁 Estructura general del proyecto

El esqueleto técnico ha sido desplegado bajo los más altos estándares de gobernanza:

* **`.github/flujo de trabajos/`**: Configuraciones de integración y despliegue continuo (CI/CD).
* **`configuracion/`**: Módulos y variables de entorno para inicializar el ecosistema.
* **`src/datos/`**: Gestión, ingesta y almacenamiento de datos semiestructurados.
* **`src/agentes/`**: Lógica central, instrucciones y coordinación de agentes de IA.
* **`src/app/`**: Interfaz de usuario y flujos principales de la aplicación del PMV.
* **`tests/`**: Pruebas unitarias, automatizadas y de integración.

---

## 🛠️ Tecnologías y herramientas (Semana 0)

* **Lenguaje:** Python 3.11+
* **Control de versiones:** Git y GitHub
* **Infraestructura en la nube:** Oracle Cloud Infrastructure (OCI)

## Ingesta y relevancia (aporte de Jhonattan)

Con Python 3.11+, desde la raíz, sin instalar dependencias para este módulo:

```sh
python -m src.datos.ingesta --configuracion configuracion/relevancia.json --fecha-referencia 2026-09-17T12:00:00Z
python -m pytest -v
```

La primera orden genera datos seleccionados y un informe de decisiones en
`salida/datos/`. La fecha fija permite reproducir la demostración; para datos actuales,
indicar otra fecha o quitar `--fecha-referencia` para usar UTC actual.

Consultar el [criterio](docs/criterio_puntuacion_relevancia.md), el
[contrato para IA](docs/contrato_datos_ingesta.md) y el
[avance de Jhonattan](docs/avance_jhonattan_semana1.md). Los pesos y el contrato
se entregan como propuestas para validación del equipo.

---

## 👥 Integrantes del equipo 39 (ONE G10 LATAM)

### 💼 Responsable de proyecto

* **Hernández Godoy Enrique** — *Responsable de proyecto*

### 📊 Analista de datos

* **Benavides Concha Jhonattan Gabriel** — *Analista de datos*
* **Vásquez Gustavo** — *Analista de datos*

### 🧪 Científico de datos

* **Bustinza Arnold** — *Científico de datos*
* **González Portillo Danny de Jesús** — *Científico de datos*
* **Pinto Arthur** — *Científico de datos*

### 💻 Ingeniero de software / Arquitecto de soluciones

* **Aviles Nelson Ramses** — *Ingeniero de software / Arquitecto de soluciones*
* **Peralta Ocampos Sebastián** — *Ingeniero de software / Arquitecto de soluciones*

### ☁️ Ingeniero de nube / DevOps

* **Preda Renato** — *Ingeniero de nube*
* **Soto Marco** — *Ingeniero de nube*

---

## 🛡️ Flujo de Trabajo para el Equipo (Gobernanza)

La rama `main` está **protegida**. No se permiten cambios directos. Para colaborar, sigue estos pasos desde tu terminal:

1. **Clonar el proyecto:** `git clone https://github.com`
2. **Crear una rama de funcionalidad:** `git checkout -b feature/tu-nombre-tarea`
3. **Preparar y guardar los cambios:** `git add .` y `git commit -m "feat: breve descripción"`
4. **Publicar la rama en GitHub:** `git push -u origin feature/tu-nombre-tarea`
5. **Abrir una solicitud de incorporación (Pull Request o PR)** para revisión y aprobación del equipo (requiere al menos una aprobación).
