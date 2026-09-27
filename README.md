# 🚀 Proyecto CommunityLab — Motor Inteligente de Transformación y Distribución para Comunidades Digitales

¡Bienvenidos a **CommunityLab**! Este proyecto es el producto mínimo viable desarrollado por el Equipo 39 del Programa ONE G10 con No Country. Es un motor inteligente diseñado para potenciar la interacción y gestión dentro de comunidades de aprendizaje en Latinoamérica mediante agentes de inteligencia artificial y servicios en la nube.

La solución ingiere conversaciones, debates y testimonios de comunidades digitales; los analiza con LangGraph y LangChain para generar materiales de difusión y preguntas frecuentes. El repositorio también incluye un panel inicial de curaduría en Streamlit y dependencias para OCI Object Storage.

---

## 📁 Estructura general del proyecto

El esqueleto arquitectónico del repositorio ha sido desplegado bajo estrictos estándares de gobernanza y separación de dominios:

* **`.github/workflows/`**: Configuraciones de integración y despliegue continuo (CI/CD).
* **`configuracion/`**: Módulos y variables de entorno para inicializar el ecosistema.
* **`src/datos/`**: Gestión, ingesta y almacenamiento de datos semiestructurados.
* **`src/agentes/`**: Lógica central, instrucciones y coordinación de agentes de IA.
* **`src/app/`**: Interfaz inicial de usuario y panel de curaduría.
* **`tests/`**: Pruebas unitarias, automatizadas y de integración.
* **`scripts/`**: Demostraciones y herramientas de evaluación.
* **`docs/`**: Documentación técnica, contratos y guías del proyecto.

---

## 🛠️ Tecnologías y herramientas

* **Lenguaje:** Python 3.11+
* **Control de versiones:** Git y GitHub
* **Infraestructura en la nube:** Oracle Cloud Infrastructure (OCI)

* **Orquestación de agentes y modelos de lenguaje:** LangGraph / LangChain Core
* **Interfaz de usuario:** Streamlit (panel de curaduría y aprobación humana)
* **Almacenamiento en la nube:** OCI Object Storage
* **Gobernanza de código:** Git y GitHub (Git Flow)

---

## 👥 3. Estructura General del Equipo (Reconfiguración Estratégica)

La organización interna del equipo distribuye el trabajo entre dirección, arquitectura, IA, datos e infraestructura.

### 💼 3.1. Área 1. Dirección, Arquitectura e Interfaz Front-End

* **Enrique Hernández Godoy (responsable de proyecto):** Dirección del plan de seis semanas, seguimiento de la lista de verificación del producto mínimo viable, gobernanza de ramas en GitHub y calidad de los entregables.
* **Nelson Ramses Aviles (arquitecto de soluciones):** Modelado del flujo integral, definición de los contratos de datos y validación de la arquitectura.
* **Sebastián Peralta Ocampos (ingeniero de software):** Desarrollo inicial de la interfaz en Streamlit (`src/app/app.py`).
* **Alejandro Alberto Landa (ingeniero de software):** Apoyo en documentación y diagramas de `docs/`.

### 🔬 3.2. Área 2. Cerebro de Inteligencia Artificial (Data Science)

* **Arnold Bustinza (científico de datos):** Diseño de flujos condicionales y del estado global (`EstadoAgente`) en LangGraph.
* **Danny de Jesús González Portillo (científico de datos):** Evaluación de llamadas a modelos de lenguaje y diseño inicial de instrucciones.
* **Alfrek Arthur Pinto García (desarrollador de pila completa):** Validación de compatibilidad entre las salidas de IA, la interfaz y el almacenamiento.

### 📊 3.3. Área 3. Ingesta y Procesamiento de Datos (Data Analytics)

* **Gustavo Vásquez (analista de datos):** Desarrollo de flujos de transformación de texto y generación de datos simulados.
* **Jhonattan Gabriel Benavides Concha (analista de datos):** Diseño de la puntuación de relevancia y análisis de cargas estructuradas.
* **Edward Santiago May Restrepo (desarrollador de sistemas):** Apoyo en la carga y validación de datos sintéticos.

### ☁️ 3.4. Área 4. Infraestructura y Despliegue en la Nube

* **Renato Preda (ingeniero de nube):** Aprovisionamiento y administración de políticas de seguridad en Oracle Cloud Infrastructure (OCI).
* **Marco Soto (ingeniero de nube):** Configuración del SDK de Oracle (`oci`), creación de contenedores y planeación de máquinas virtuales Linux en OCI Compute.

---

## 📈 4. Estado de Control e Hitos Cumplidos (Semana 0)

Durante la Semana 0 (cimientos, datos y arquitectura), el equipo completó las metas establecidas:

* **Gobernanza:** Protección de `main` y creación de `develop` como rama de integración.
* **Datos:** Conjunto simulado de 23 interacciones en `src/datos/mensajes_comunidad_simulados.json` y herramienta opcional de ingesta Reddit en `src/datos/ingesta_reddit.py`.
* **Nube:** Bucket `communitylab-activos-marketing` en OCI Object Storage. La utilidad `tests/test_storage.py` permite comprobar manualmente la conexión y realizar una carga de prueba.
* **Arquitectura:** Contrato de datos JSON para la comunicación entre módulos.

---

## 🛡️ 5. Flujo de Trabajo Operativo para el Equipo (Gobernanza Git Flow)

Las ramas `main` (producción) y `develop` (integración) están protegidas. No se permiten commits directos; cada integrante debe seguir estos pasos:

### Paso 1: Clonar y actualizar el entorno local

```bash
git clone https://github.com/HenryH11/communitylab.git
cd communitylab
git checkout develop
git pull origin develop
```

### Paso 2: Crear una rama de trabajo desde develop

```bash
git checkout -b feature/nombre_subequipo_tarea
# Ejemplo: feature/grafo-ia-ds o feature/streamlit-ui-ss
```

### Paso 3: Guardar y registrar cambios de forma local

```bash
git add .
git commit -m "feat: breve descripción técnica del cambio implementado"
```

### Paso 4: Publicar la rama en el servidor de GitHub

```bash
git push -u origin feature/nombre_subequipo_tarea
```

### Paso 5: Abrir un Pull Request (PR)

Abre un PR desde tu rama hacia **`develop`** y avisa al equipo. Antes de fusionarse, requiere revisión técnica y aprobación del responsable de proyecto o del arquitecto de soluciones.

---

## Ingesta y relevancia de Datos

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
