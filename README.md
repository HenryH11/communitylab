# 🚀 Proyecto CommunityLab — Motor Inteligente de Transformación y Distribución para Comunidades Digitales

¡Bienvenidos a **CommunityLab**! Este proyecto es el Producto Mínimo Viable (MVP) desarrollado por el equipo **EnhanceIA Studio (EIAS - Equipo 39)** para la fase práctica de simulación laboral del programa **Oracle Next Education (ONE) G10 - LATAM**, en conjunto con la plataforma **No Country**.

Nuestra solución opera como una línea de ensamblaje inteligente: ingiere conversaciones desestructuradas, debates y testimonios orgánicos de canales digitales (ruido), los limpia mediante algoritmos matemáticos de relevancia semántica, y los procesa mediante **Modelos de Lenguaje de Gran Escala (LLMs)** y grafos de decisión dirigidos en **LangGraph** para empaquetarlos automáticamente en activos de marketing de alto impacto (MarTech) y entradas dinámicas de FAQ. La persistencia de los reportes se ejecuta de forma nativa e integral en la capa gratuita Always Free de **Oracle Cloud Infrastructure (OCI) Object Storage**.

---

## 📁 1. Estructura General del Proyecto

El esqueleto arquitectónico del repositorio ha sido desplegado bajo estrictos estándares de gobernanza y separación de dominios:

```text
communitylab/
├── .gitignore               # CRÍTICO: Exclusión de credenciales privadas de Oracle (.oci/, *.pem) y entornos locales.
├── README.md                # Documentación e informe técnico institucional del proyecto.
├── requirements.txt         # Dependencias del ecosistema unificado (Streamlit, LangGraph, OCI SDK).
├── configuracion/           # Módulos globales de configuración y entornos locales.
│   └── relevancia.json      # Pesos y parámetros analíticos del algoritmo de selección de datos.
├── docs/                    # Documentación técnica, contratos de datos y especificaciones.
│   ├── arquitectura_general_sistema.md
│   ├── avance_jhonattan_semana1.md
│   ├── contrato_datos_ingesta.md
│   ├── criterio_puntuacion_relevancia.md
│   └── diagrama_flujo_datos_ingesta.md
├── scripts/                 # Herramientas de evaluación analítica y simulaciones de control.
│   ├── evaluar_casos_ambiguos.py
│   ├── evaluar_conjunto_datos.py
│   └── inspeccionar_estado_agente.py
├── src/                     # Código fuente principal del sistema.
│   ├── agentes/             # Grafos, lógica analítica y prompts de LangGraph (Cerebro IA).
│   │   ├── nodos/           # Nodos enrutadores y generadores de activos MarTech.
│   │   ├── cadenas.py       # Inicialización y configuración de modelos de lenguaje LLM.
│   │   ├── estado_agente.py # Definición de la clase tipada del estado global del sistema.
│   │   └── grafo.py         # Orquestador del flujo de agentes secuenciales.
│   ├── app/                 # Interfaz gráfica de usuario y panel de curaduría (Frontend).
│   │   └── app.py           # Andamio gráfico inicial montado en Streamlit.
│   └── datos/               # Módulos de ingesta, parseo y limpieza de texto (Analistas).
│       ├── ingest.py        # Orquestador modular del flujo de datos de entrada.
│       ├── ingesta_reddit.py# Pipeline extractor con limpieza por expresiones regulares.
│       └── relevancia.py    # Algoritmo matemático de puntuación analítica de mensajes.
└── tests/                   # Lotes de datos JSON de prueba y suite de validación QA.
    ├── agents/              # Pruebas automatizadas sobre nodos y procesamiento de lotes.
    ├── fixtures/            # Sets de datos controlados para simulación de contingencias.
    ├── test_ingest_relevancia.py # Pruebas unitarias de calidad sobre el flujo de ingesta.
    └── test_storage.py      # Pruebas unitarias de conectividad transparente con el OCI Bucket.
```

---

## 🛠️ 2. Tecnologías y Herramientas (Ecosistema Core)

* **Lenguaje de Programación:** Python 3.11+
* **Orquestación de Agentes y LLM:** LangGraph / LangChain Core
* **Interfaz de Usuario (UI):** Streamlit (Panel de Curaduría y Aprobación Humana)
* **Infraestructura y Nube:** Oracle Cloud Infrastructure (OCI SDK) – Capa Always Free
* **Gobernanza de Código:** Git & GitHub (Estrategia Git Flow Terminal)

---

## 👥 3. Estructura General del Equipo (Reconfiguración Estratégica)

La organización interna del equipo fue optimizada equilibradamente por la Dirección de Proyecto para blindar el desarrollo, agrupando a los líderes técnicos en frentes críticos de código Python y reubicando los perfiles de soporte para maximizar el avance del MVP.

### 3.1. Área de Dirección y Gestión de Repositorio (Área PM)
* **Enrique Hernández Godoy (Project Manager - Líder General):** Dirección general del roadmap de 6 semanas, control del checklist del MVP, administración de la gobernanza de ramas en GitHub mediante Pull Requests y resolución de incidencias en la línea base.

### 3.2. Área de Arquitectura de Soluciones y Aseguramiento (Área SS)
* **Nelson Ramses Aviles (Solution Architect - Líder Técnico):** Modelado conceptual del pipeline completo (E2E), definición analítica de las estructuras fijas de intercambio de datos (Data Contracts) y validación arquitectónica del sistema distribuido.
* **Eduardo Salvador Martínez Hernández (QA Tester):** Configuración de la suite de pruebas automáticas, ejecución de validaciones sintácticas bajo pytest, control de calidad y auditoría de documentos Markdown.

### 3.3. Área de Cerebro de Inteligencia Artificial (Área DS)
* **Arnold Bustinza (Data Scientist - Líder Técnico):** Diseño técnico de los flujos condicionales de control y orquestación del estado global de memoria (`EstadoAgente`) en el entorno unificado de LangGraph.
* **Alfrek Arthur Pinto García (Full Stack Developer):** Programación y acoplamiento de las llamadas a los modelos de lenguaje (LLM) y validación de compatibilidad con las salidas del sistema.
* **Alejandro Alberto Landa (Backend Developer):** Reubicado dinámicamente en esta célula para la asistencia en la integración lógica en Python de los nodos y limpieza de payloads sintácticos.
* **Danny de Jesús González Portillo (Data Scientist):** Ingeniería y calibración de las plantillas de prompts de entrenamiento corto (Few-Shot Learning) y verificación de consistencia en el procesamiento.

### 3.4. Área de Ingesta y Procesamiento de Datos (Área DA)
* **Gustavo Vásquez Serey (Data Analyst - Líder Técnico):** Desarrollo de pipelines automatizados de transformación de texto crudo, control del manejador de errores de red y curaduría del set de datos simulados locales.
* **Jhonattan Gabriel Benavides Concha (Data Analyst):** Codificación matemática del algoritmo de puntuación de relevancia semántica, ingestión de lotes de payloads estructurados y control de cuotas de APIs.

### 3.5. Área de Infraestructura y Despliegue Cloud (Área CE)
* **Renato Preda (Cloud Engineer - Líder Técnico):** Aprovisionamiento y administración de las políticas de seguridad del almacenamiento, control del Bucket OCI y validación de la autenticación cloud.
* **Marco Soto (Cloud Engineer):** Configuración del entorno de automatización del SDK oficial de Oracle (`oci`), dockerización completa del ecosistema y planeación de la VM Linux de OCI Compute.

*(Nota Operativa Administrativa: Los perfiles de Sebastián Peralta y Edward Santiago continuan declarados como miembros de soporte (inactivos) de las actividades operativas por falta de reporte técnico).*

---

## 📈 4. Estado de Control e Hitos Cumplidos

### Semana 0 (Fase de Cimientos, Datos y Arquitectura de Sistemas)
* **Hito de Gobernanza:** Inicialización del repositorio remoto con bloqueo y protección de la rama `main`. Creación y publicación de la rama de integración `develop` como el estándar operativo para evitar conflictos de código (`Merge Conflicts`).
* **Hito de Arquitectura:** Integración del primer Pull Request formal del proyecto elaborado por el arquitecto Nelson Ramses, estableciendo el contrato de datos JSON fijo para la comunicación limpia entre módulos.
* **Hito de Infraestructura Cloud:** Aprovisionamiento del Bucket Always Free `communitylab-activos-marketing` en la consola de Oracle Cloud (Región São Paulo). Despliegue seguro de `src/config/test_oci_connection.py` para validar la persistencia asíncrona sin exponer llaves privadas.

### Semana 1 (Procesamiento, Filtrado Temático y Estructura IA Core) — ESTADO ACTUAL
* **Hito de Pipeline de Datos (100% Completado):** Sincronización e integración de las ramas de la célula de analistas. Ya residen en `develop` los códigos de limpieza analítica, el calculador matemático de relevancia basado en configuraciones JSON y el set maestro con los 23 casos del MVP.
* **Hito de Tolerancia a Fallas QA:** Inyección de scripts extractores robustecidos con técnicas de filtrado por expresiones regulares y control activo de excepciones de red, previniendo caídas del pipeline ante saturaciones de peticiones externas (Error 429).
* **Estado de Integración de IA:** El andamiaje del cerebro cognitivo y el flujo secuencial de enrutamiento han sido correctamente unificados en `src/agentes/grafo.py`. La autopista lógica está abierta.

---

## 🛡️ 5. Flujo de Trabajo Operativo para el Equipo (Gobernanza Git Flow)

La rama `main` (Producción final) y la rama `develop` (Integración de código) están protegidas. Está estrictamente prohibido realizar commits directos sobre ellas. Todo miembro del equipo debe trabajar bajo las siguientes directrices terminales:

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
# Ejemplo: git checkout -b feature/grafo-ia-ds o feature/streamlit-ui-ss
```