# 🚀 Proyecto CommunityLab — Motor Inteligente de Transformación y Distribución para Comunidades Digitales

¡Bienvenidos a **CommunityLab**! Este proyecto es el MVP (Producto Mínimo Viable) desarrollado por el **Equipo 39** para la fase práctica de simulación laboral del programa **Oracle Next Education (ONE) G10 - LATAM**, en conjunto con la plataforma **No Country**.

Nuestra solución opera como una línea de ensamblaje inteligente: ingiere conversaciones desestructuradas, debates y testimonios orgánicos de canales digitales (ruido) y los procesa mediante Modelos de Lenguaje de Gran Escala (LLMs) y grafos de decisión dirigidos en **LangGraph** para empaquetarlos automáticamente en activos de marketing de alto impacto (*MarTech*) y entradas dinámicas de FAQ. La persistencia de los reportes se ejecuta de forma nativa e integral en la capa gratuita **Always Free** de **Oracle Cloud Infrastructure (OCI) Object Storage**.

---

## 📁 1. Estructura General del Proyecto

El esqueleto arquitectónico del repositorio ha sido desplegado bajo estrictos estándares de gobernanza y separación de dominios:

```text
communitylab/
├── .github/workflows/   # Configuraciones de integración y despliegue continuo (CI/CD)
├── config/              # Módulos globales de configuración y entornos locales
├── docs/                # Documentación técnica, contratos de datos y especificaciones
├── src/                 # Código fuente principal del sistema
│   ├── data/            # Módulos de ingesta, parseo y limpieza de texto (Analistas)
│   ├── agents/          # Grafos, lógica analítica y prompts de LangGraph (IA)
│   └── app/             # Interfaz gráfica de usuario y panel de curaduría (Frontend)
├── tests/               # Lotes de datos JSON de prueba y scripts de validación QA
├── .gitignore           # CRÍTICO: Exclusión de credenciales privadas de Oracle y entornos
├── README.md            # Documentación e informe técnico institucional del proyecto
└── requirements.txt     # Dependencias del ecosistema unificado (Streamlit, LangGraph, OCI SDK)
```

---

## 🛠️ 2. Tecnologías y Herramientas (Ecosistema Core)

* **Lenguaje de Programación:** Python 3.11+
* **Orquestación de Agentes y LLM:** LangGraph / LangChain Core
* **Interfaz de Usuario (UI):** Streamlit (Panel de Curaduría y Aprobación Humana)
* **Infraestructura y Nube:** Oracle Cloud Infrastructure (OCI SDK) — Capa Always Free
* **Gobernanza de Código:** Git & GitHub (Estrategia Git Flow)

---

## 👥 3. Estructura General del Equipo (Reconfiguración Estratégica)

La organización interna del equipo fue optimizada por la Dirección de Proyecto para blindar el desarrollo, agrupando a los líderes técnicos y miembros activos en frentes críticos de código Python y reubicando los perfiles de soporte.

### 💼 3.1. Área 1. Dirección, Arquitectura e Interfaz Front-End
* **Enrique Hernández Godoy (Project Manager - Líder General):** Dirección general del roadmap de 6 semanas, control estricto del checklist del MVP, administración de la gobernanza de ramas en GitHub y aseguramiento de la calidad de los entregables de la plataforma.
* **Nelson Ramses Aviles (Solution Architect - Miembro Líder):** Modelado conceptual del pipeline completo (E2E), definición analítica de las estructuras fijas de intercambio de datos (Data Contracts) y validación de la arquitectura de la solución.
* **Sebastián Peralta Ocampos (Software Engineer - Miembro de Soporte):** Encargado de maquetar el cascarón de la interfaz gráfica base en Streamlit (`src/app/app.py`). De momento, sin asignación de lógica interna crítica.
* **Alejandro Alberto Landa (Software Engineer - Miembro de Soporte):** Reubicado en este bloque para asistencia general en documentación y diagramación en la carpeta `docs/`.

### 🔬 3.2. Área 2. Cerebro de Inteligencia Artificial (Data Science)
* **Arnold Bustinza (Data Scientist - Miembro Líder):** Diseño técnico de los flujos condicionales de control y el estado global (`AgentState`) en LangGraph para el Sprint de la Semana 1.
* **Danny de Jesús González Portillo (Data Scientist - Miembro Activo):** Evaluación inicial de llamadas de contexto a los modelos de lenguaje, e ingeniería preliminar de plantillas de prompts (*System Prompts*).
* **Alfrek Arthur Pinto García (Full Stack Developer - Miembro Activo):** Validación de compatibilidad entre las interfaces de salida de IA y las capas frontales y de almacenamiento.

### 📊 3.3. Área 3. Ingesta y Procesamiento de Datos (Data Analytics)
* **Gustavo Vásquez (Data Analyst - Miembro Líder):** Desarrollo de pipelines automatizados de transformación de texto crudo y generación de colecciones de datos simulados locales.
* **Jhonattan Gabriel Benavides Concha (Data Analyst - Miembro Activo):** Diseño del algoritmo matemático de puntuación de relevancia comunicacional y parseo de payloads estructurados.
* **Edward Santiago May Restrepo (Backend Developer - Miembro de Soporte):** Reubicado en esta área para soporte secundario no bloqueante en la carga y validación de strings sintéticos.

### ☁️ 3.4. Área 4. Infraestructura y Despliegue en la Nube (Cloud Engineer)
* **Renato Preda (Cloud Engineer - Miembro Líder):** Aprovisionamiento y administración de políticas de seguridad del almacenamiento en Oracle Cloud (OCI).
* **Marco Soto (Cloud Engineer - Miembro Activo):** Configuración del entorno de automatización del SDK de Oracle (`oci`), dockerización del ecosistema y planeación de la VM Linux de OCI Compute.

---

## 📈 4. Estado de Control e Hitos Cumplidos (Semana 0)

Durante la Semana 0 (Fase de Cimientos, Datos y Arquitectura de Sistemas), el equipo alcanzó el **100% de cumplimiento** de las metas planteadas en el cronograma quirúrgico:

* **🟢 Hito de Gobernanza:** Inicialización del repositorio remoto con bloqueo y protección de la rama `main`. Creación y publicación de la rama de integración **`develop`** como el estándar operativo para evitar conflictos de código (*Merge Conflicts*).
* **🟢 Hito de Datos:** Construcción del set de simulación local obligatorio `tests/mock_community_data.json` que contiene los casos fijos de la rúbrica (Mariana Souza y Lucas Albuquerque) y 8 casos alternativos. Como **valor agregado diferencial**, se desarrolló un script de 333 líneas en `src/data/ingesta_reddit.py` con manejo exponencial de errores de red (Error 429) y limpieza de cadenas con expresiones regulares.
* **🟢 Hito de Infraestructura Cloud:** Aprovisionamiento del Bucket Always Free `communitylab-activos-marketing` en la consola de Oracle Cloud (Región São Paulo). Despliegue seguro de `src/config/test_oci_connection.py` para validar la persistencia asíncrona sin exponer llaves privadas.
* **🟢 Hito de Arquitectura:** Integración del primer Pull Request formal del proyecto elaborado por el arquitecto Nelson Ramses, estableciendo el contrato de datos JSON fijo para la comunicación limpia entre módulos.

---

## 🛡️ 5. Flujo de Trabajo Operativo para el Equipo (Gobernanza Git Flow)

La rama `main` (Producción final) y la rama `develop` (Integración de código) están **protegidas**. Está estrictamente prohibido realizar commits directos sobre ellas. Todo miembro del equipo debe trabajar bajo las siguientes directrices terminales:

### Paso 1: Clonar y actualizar el entorno local
```bash
git clone https://github.com
cd communitylab
git checkout develop
git pull origin develop
```

### Paso 2: Crear una rama de tarea (Feature Branch) desde develop
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
Ingresar de forma web al repositorio en GitHub, abre un Pull Request desde tu rama apuntando exclusivamente hacia la rama **`develop`**. Notificae en el canal de Discord. Todo PR requiere la auditoría técnica y aprobación mínima del Project Manager o del Solution Architect antes de fusionarse.