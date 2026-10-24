# 🚀 Proyecto CommunityLab – Motor Inteligente de Transformación y Distribución para Comunidades Digitales

# CommunityLab

Herramientas para convertir conversaciones de comunidades digitales en datos
analizables y activos estructurados. El flujo combina validación y relevancia
determinista con análisis de lenguaje y enrutamiento por reglas.

Nuestra solución opera como una línea de ensamblaje inteligente: ingiere conversaciones desestructuradas, debates y testimonios orgánicos de canales digitales (ruido), los limpia mediante algoritmos matemáticos de relevancia semántica, y los procesa mediante **Modelos de Lenguaje de Gran Escala (LLMs)** y grafos de decisión dirigidos en **LangGraph** para empaquetarlos automáticamente en activos de marketing de alto impacto (MarTech) y entradas dinámicas de FAQ. La persistencia de los reportes se ejecuta de forma nativa e integral en la capa gratuita Always Free de **Oracle Cloud Infrastructure (OCI) Object Storage**.

---

## 📁 1. Estructura General del Proyecto

El esqueleto arquitectónico del repositorio ha sido desplegado bajo estrictos estándares de gobernanza y separación de dominios:

```text
communitylab/
├── .dockerignore           # Exclusiones de contexto para construcción limpia de contenedores
├── .env.example            # Plantilla maestra para la inyección segura de credenciales y tokens
├── .gitignore              # CRÍTICO: Exclusión de credenciales privadas de Oracle (.oci/, *.pem) y entornos locales.
├── Dockerfile              # Empaquetado industrial multi-stage basado en entorno Linux
├── docker-compose.yml      # Orquestador local automatizado del contenedor de la aplicación
├── README.md               # Documentación e informe técnico institucional del proyecto.
├── requirements.txt        # Dependencias del ecosistema unificado (Streamlit, LangGraph, OCI SDK).
├── configuracion/          # Módulos globales de configuración y entornos locales.
│   └── relevancia.json     # Pesos y parámetros analíticos del algoritmo de selección de datos.
├── docs/                   # Documentación técnica, contratos de datos y especificaciones.
│   ├── arquitectura_general_sistema.md
│   ├── avance_datascience_semana2.md
│   ├── avance_jhonattan_semana1.md
│   ├── contrato_datos_ingesta.md
│   ├── criterio_puntuacion_relevancia.md
│   ├── diagrama_flujo_datos_ingesta.md
│   ├── diagrama_persistencia_oci.md
│   ├── evidencia2_entrega_ciencia_datos_completa.json
│   ├── evidencia_entrega_ciencia_datos_completa.json
│   ├── evidencia_generacion_real.md
│   ├── evidencia_prueba_grafo_3_mensajes.md
│   ├── fuentes_de_datos_acceso.md
│   ├── guia_pruebas.md
│   ├── informe_pruebas_langchain.pdf
│   ├── registro_cambios_y_decisiones.md
│   ├── rendimiento_datos_semana2.md
│   └── resultado_prueba_paquete_completo_DS_semana2.md
├── scripts/                # Herramientas de evaluación analítica y simulaciones de control.
│   ├── apoyo_demostraciones.py
│   ├── demostracion_analisis_sin_contenido.py
│   ├── demostracion_cadena_analisis.py
│   ├── demostracion_grafo_mensaje_unico.py
│   ├── demostracion_lotes_ciencia_datos.py
│   ├── demostracion_nodo_analizador.py
│   ├── evaluar_casos_ambiguos.py
│   ├── evaluar_conjunto_datos.py
│   ├── inspeccionar_estado_agente.py
│   └── probar_oci_storage.py # Prueba manual: consulta el bucket y sube un JSON real.
├── src/                    # Código fuente principal del sistema.
│   ├── agentes/            # Grafos, lógica analítica y prompts de LangGraph (Cerebro IA).
│   │   ├── nodos/          # Nodos enrutadores y generadores de activos MarTech.
│   │   │   ├── nodo_analizador.py
│   │   │   ├── nodo_enrutador.py
│   │   │   └── nodos_generadores.py
│   │   ├── cadenas.py      # Inicialización y configuración de modelos de lenguaje LLM.
│   │   ├── contrato_salida_ciencia_datos.py
│   │   ├── entrega_resultados.py
│   │   ├── estado_agente.py # Definición de la clase tipada del estado global del sistema (AgentState).
│   │   ├── grafo.py        # Orquestador del flujo de agentes secuenciales.
│   │   ├── modelo_ia.py
│   │   └── modelos.py
│   ├── app/                # Interfaz gráfica de usuario y panel de curaduría (Frontend).
│   │   └── app.py          # Andamio gráfico inicial montado en Streamlit.
│   ├── config/             # Conectores e infraestructura cloud.
│   │   └── oci_client.py   # Cliente nativo y seguro para persistencia en Oracle Cloud.
│   └── datos/              # Módulos de ingesta, parseo y limpieza de texto (Analistas).
│       ├── entrega_ia.py
│       ├── ingesta.py
│       ├── ingesta_reddit.py # Pipeline extractor con limpieza por expresiones regulares.
│       ├── mensajes_comunidad_simulados.json # Dataset local con los 23 casos obligatorios del MVP.
│       └── relevancia.py   # Algoritmo matemático de puntuación analítica de mensajes.
└── tests/                  # Lotes de datos JSON de prueba y suite de validación QA.
    ├── agents/             # Pruebas automatizadas sobre nodos y procesamiento de lotes.
    │   ├── test_enrutador.py
    │   ├── test_evaluacion_regresion.py
    │   ├── test_procesamiento_lotes.py
    │   └── test_prompts_generadores.py
    ├── fixtures/           # Sets de datos controlados para simulación de contingencias.
    │   ├── casos_referencia_ia_candidatos.json
    │   └── prueba_reddit_controlada.json
    └── integracion/        # Pruebas cruzadas extremo a extremo (E2E) del pipeline integrado.
        ├── prueba_entrega_resultados_funcional.py
        └── prueba_paquete_completo_datos.py
```

---

## 🛠️ 2. Tecnologías y Herramientas (Ecosistema Core)

*   **Lenguaje de Programación:** Python 3.11+
*   **Orquestación de Agentes y LLM:** LangGraph / LangChain Core (Híbrido: NVIDIA NIM APIs + Google Gemini Fallback)
*   **Interfaz de Usuario (UI):** Streamlit (Panel de Curaduría y Aprobación Humana / *Human-in-the-Loop*)
*   **Infraestructura y Nube:** Oracle Cloud Infrastructure (OCI SDK) - Capa Always Free
*   **Gobernanza de Código:** Git & GitHub (Estrategia Git Flow Terminal)

---

## 👥 3. Estructura General del Equipo (Reconfiguración Estratégica)

## Estructura (ง'̀-'́)ง

### 3.1. 💼 Área Project Management (PM) — Dirección y Gestión de Repositorio
*   **Enrique Hernández Godoy (Project Manager):** Administración general del roadmap de 6 semanas, control del checklist del MVP, gobernanza del repositorio, protección de ramas mediante Pull Requests y resolución de incidencias en la línea base.

### 3.2. 📐 Área Sofware Solution (SS) — Arquitectura de Soluciones y Aseguramiento
*   **Nelson Ramses Aviles (Solution Architect):** Modelado conceptual del pipeline completo (E2E), definición analítica de las estructuras fijas de intercambio de datos (Data Contracts) y validación arquitectónica del sistema distribuido.
*   **Eduardo Salvador Martínez Hernández (QA Tester):** Configuración de la suite de pruebas automatizadas, ejecución de validaciones sintácticas bajo `pytest`, control de calidad y auditoría de documentos Markdown.

### 3.3. 🧠 Área Data Science (DS) — Cerebro de Inteligencia ArtificiaL
*   **Arnold Bustinza (Data Scientist):** Diseño técnico de los flujos condicionales de control y orquestación del estado global de memoria (`AgentState`) en el entorno unificado de LangGraph.
*   **Alfrek Arthur Pinto García (Full Stack Developer):** Programación y acoplamiento de las llamadas a los modelos de lenguaje (LLM) y validación de compatibilidad con las salidas del sistema.
*   **Alejandro Alberto Landa (Backend Developer):** Reubicado dinámicamente en esta célula para la asistencia en la integración lógica en Python de los nodos y limpieza de payloads sintácticos.
*   **Danny de Jesús González Portillo (Data Scientist):** Ingeniería y calibración de las plantillas de prompts de entrenamiento corto (*Few-Shot Learning*) y verificación de consistencia en el procesamiento.

### 3.4. 📊 Área Data Analysis (DA) — Ingesta y Procesamiento de Datos
*   **Gustavo Vázquez Serey (Data Analyst):** Desarrollo de pipelines automatizados de transformación de texto crudo, control del manejador de errores de red y curaduría del set de datos simulados locales.
*   **Jhonattan Gabriel Benavides Concha (Data Analyst):** Codificación matemática del algoritmo de puntuación de relevancia semántica, ingesta de lotes de payloads estructurados y control de cuotas de APIs.

### 3.5. ☁️ Área Cloud Engineering (CE) — Infraestructura y Despliegue Cloud
*   **Renato Preda (Cloud Engineer):** Aprovisionamiento y administración de las políticas de seguridad del almacenamiento, control del Bucket OCI y validación de la autenticación cloud.
*   **Marco Soto (Cloud Engineer):** Configuración del entorno de automatización del SDK oficial de Oracle (`oci`), dockerización completa del ecosistema y planeación de la VM Linux de OCI Compute.

*\* (Nota Operativa Administrativa: Los perfiles de Sebastián Peralta y Edward Santiago continuaron inactivos durante las actividades operativas por falta de reporte técnico y comunicación con la Dirección de Proyecto).*

---

## 📋 4. Estado de Control e Hitos Cumplidos (Storytelling del MVP)

### 🏛️ Semana 0 – Fase de Cimientos, Datos y Arquitectura de Sistemas
*   **Hito de Gobernanza:** Inicialización del repositorio remoto con bloqueo y protección de la rama `main`. Creación y publicación de la rama de integración `develop` como el estándar operativo para evitar conflictos de código (*Merge Conflicts*).
*   **Hito de Arquitectura:** Integración del primer Pull Request formal del proyecto elaborado por el arquitecto Nelson Ramses, estableciendo el contrato de datos JSON fijo para la comunicación limpia entre módulos.
*   **Hito de Infraestructura Cloud:** Aprovisionamiento inicial del bucket de Marketing en la consola de Oracle Cloud (Región São Paulo). El nombre vigente confirmado por Cloud es `bkt-communitylab-marketing`. Despliegue seguro de `src/config/test_oci_connection.py` para validar la persistencia asíncrona sin exponer llaves privadas.

### 🧠 Semana 1 – Procesamiento, Filtrado Temático y Estructura IA Core
*   **Hito de Pipeline de Datos (100% Completado):** Sincronización e integración de las ramas de la célula de analistas. Ya residen en `develop` los códigos de limpieza analítica, el calculador matemático de relevancia basado en configuraciones JSON y el set maestro con los 23 casos de prueba del MVP (`mensajes_comunidad_simulados.json`).
*   **Hito de Tolerancia a Fallas QA:** Inyección de scripts extractores robustecidos con técnicas de filtrado por expresiones regulares y control activo de excepciones de red, previniendo caídas del pipeline ante saturaciones de peticiones externas (Error HTTP 429 vía Exponential Backoff).
*   **Hito de Grafo Inteligente Core:** Compilación del andamiaje base del cerebro cognitivo y el flujo secuencial de enrutamiento en `src/agents/grafo.py`, utilizando clases unificadas de memoria para transferir estados de manera transparente.

### ⚡ Semana 2 – Generación de Activos Estructurados, Nubes y UI Base
*   **Hito de Calibración Cognitiva (Few-Shot Learning):** Implementación exitosa de los prompts analíticos parametrizados en `src/agentes/cadenas.py`. El LLM utiliza los casos de uso obligatorios de Mariana Souza y Lucas Albuquerque como base de entrenamiento corto, obligando a la inteligencia artificial a devolver diccionarios JSON estrictamente estructurados bajo las llaves del contrato.
*   **Hito de Cobertura y Pruebas Exitosas (Pytest PASSED):** Ejecución e integración de la suite de pruebas unitarias cruzadas. La terminal de control del backend certifica que el procesamiento de lotes masivos (`entrega_ciencia_datos_completa.json`) se ejecuta con **100% de éxito (PASSED) en un tiempo récord de 74.66 segundos**, validando scores de relevancia y segmentaciones sintácticas sin fugas de memoria.
*   **Hito de Abstracción de Conectores Cloud:** Desarrollo adelantado del script modular `src/config/oci_client.py` por parte de la célula de nube. El conector lee las credenciales del sistema de forma segura mediante `os.getenv`, dejando lista la pasarela asíncrona para que los agentes guarden archivos JSON en OCI.
*   **Hito de Cascarón de UI:** Inicialización limpia del Frontend interactivo en `src/app/app.py` utilizando componentes nativos de Streamlit. El entorno se encuentra aislado de inyecciones inestables de HTML/CSS, preparado para iniciar el sprint de interconexión con los nodos de IA.

Para medir el análisis actual con Gemini, de forma explícita:

## 🔄 Semana 3 y 4 – Enrutamiento Condicional, Curaduría Human-in-the-Loop y Contenedores
*   **Hito de Enrutamiento Dinámico (Semana 3):** Ensamblaje de la función enrutadora `routing_conditional_edge` en LangGraph para automatizar la bifurcación del flujo analítico hacia el nodo especializado correspondiente basándose en la intención sintáctica del payload de entrada.
*   **Hito de Intervención Humana (Semana 4):** Integración de componentes reactivos `st.text_area` en la interfaz gráfica. Esto rompe la automatización rígida del pipeline al habilitar una ventana de edición y curaduría para que el operador valide o altere los copys MarTech antes de su persistencia cloud.
*   **Hito de Empaquetado Industrial (Semana 4):** Construcción y validación del entorno reproducible multiplataforma mediante archivos `Dockerfile` y `docker-compose.yml`, aislando librerías nativas y mitigando deudas técnicas de despliegue en staging.

---

## 🔀 5. Flujo de Trabajo Operativo para el Equipo (Gobernanza Git Flow)

Para mantener una línea base libre de regresiones y asegurar una auditoría de código limpia ante los evaluadores del programa, la dirección técnica impuso las siguientes directrices terminales de control:
*   **Uso de conventional commits:** Cada confirmación de código en el servidor debe seguir la nomenclatura tipada internacional estándar (ej. `feat(ia):`, `fix(data):`, `docs(readme):`).
*   **Integración por Pull Requests:** Está estrictamente prohibido realizar inserciones directas (*Push*) sobre la rama de producción `main` o la rama de integración común `develop`. Los cambios se someten obligatoriamente a revisión por pares abriendo un Pull Request desde ramas locales de tarea (`feature/nombre-miembro-tarea`).

---

## 🔐 6. Guía Maestra de Configuración y Variables de Entorno

El sistema requiere el aprovisionamiento de un archivo local `.env` en la raíz de la carpeta de trabajo. Las llaves se leen dinámicamente en caliente a través del sistema operativo, quedando prohibida su escritura explícita en texto plano:

```ini
# ==============================================================================
# CAPA COGNITIVA - INTELIGENCIA ARTIFICIAL (NVIDIA NIM & GEMINI FALLBACK)
# ==============================================================================
NVIDIA_API_KEY=nvapi-R3g...       # Token maestro de autenticación para el catálogo de modelos de NVIDIA
GEMINI_API_KEY=AIzaSyA...       # API Key de respaldo institucional para la suite de contingencia de Google

# ==============================================================================
# INFRAESTRUCTURA DE ORACLE CLOUD (OCI OBJECT STORAGE CONFIGURATION)
# ==============================================================================
OCI_USER_OCID=ocid1.user.oc1..aaaaaaaaxxx...    # Identificador único de usuario en la consola de Oracle
OCI_TENANCY_OCID=ocid1.tenancy.oc1..aaaaaaayyy... # OCID de la raíz de la organización del inquilino OCI
OCI_REGION=sa-saopaulo-1                          # Código geográfico de la región del centro de datos destino
OCI_FINGERPRINT=aa:bb:cc:dd:ee:ff:11:22...        # Huella digital vinculada a la clave pública de API registrada
OCI_KEY_FILE_PATH=./.oci/oci_api_key.pem         # Ruta local hacia el archivo físico de llave privada de firma
OCI_BUCKET_NAME=bkt-communitylab-marketing        # Nombre exacto del bucket confirmado por Cloud
```

---

## 🐳 7. Despliegue Automatizado Mediante Contenedores (Docker)

Para ejecutar de manera aislada todo el ecosistema SaaS y el pipeline de Ciencia de Datos en un servidor local o instancia de OCI Compute, ejecute la siguiente secuencia en su terminal:

1. **Poblar las variables reales:**
   ```bash
   cp .env.example .env
   nano .env # Proceda a rellenar las llaves OCI y tokens de IA requeridos
   ```

2. **Lanzar la construcción y ejecución en segundo plano:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verificar estado de puertos:**
   Abra su navegador web e ingrese a la dirección local predeterminada: `http://localhost:8501`. Asegúrese de abrir el puerto perimetral correspondientemente en las tablas de listas de seguridad de la red VCN de Oracle Cloud si está desplegando en producción.

## 🌀 5. Flujo de Trabajo Operativo para el Equipo (Gobernanza Git Flow)

El modo en vivo requiere `GEMINI_API_KEY` en un `.env` local y consume cuota.
Los snapshots actuales son referencias históricas, no etiquetas validadas por
anotadores independientes.

## Documentación (•̀ᴗ•́)و


Los [contratos JSON de arquitectura](docs/arquitectura-solucion/README.md) definen
la entrada pública, los lotes de ingesta DA → DS y la salida operativa de DS.
La rama de Semana 4 incorpora el contrato v1.4, manteniendo compatibilidad
con v1.2 y v1.3, pendiente de aprobación formal de SS/QA.

La implementación de detección semántica de spam, sus reglas de enrutamiento
y las pruebas realizadas se documentan en el
[informe técnico de Semana 4](docs/avance_datascience_semana4_spam.md).
Los comandos de validación están disponibles en la
[guía de ejecución y pruebas](docs/guia_pruebas.md).


### Paso 2: Crear una rama de tarea (Feature Branch) desde develop
```bash
git checkout -b feature/nombre_subequipo_tarea
# Ejemplo: git checkout -b feature/grafo-ia-ds o feature/streamlit-ui-ss
```

### Paso 3: Confirmar cambios bajo Conventional Commits
Queda prohibido el uso de mensajes genéricos. Cada confirmación debe seguir el estándar internacional:
*   `feat(ia):` para nuevos nodos o lógicas del grafo.
*   `feat(ui):` para componentes interactivos de Streamlit.
*   `fix(data):` para correcciones en scripts de ingesta o limpieza.

```bash
git add .
git commit -m "feat(ia): implementar tecnicas few-shot en nodos de redaccion"
git push origin feature/nombre_subequipo_tarea
```

### Paso 4: Cierre y Fusión (Pull Request)
El desarrollador abrirá el Pull Request en la interfaz web de GitHub apuntando exclusivamente hacia la rama `develop`. Ningún PR se fusionará sin la revisión cruzada de otra célula técnica y la confirmación de que las pruebas unitarias locales corren en verde.

## 🔐 6. Guía Maestra de Configuración y Variables de Entorno

El sistema requiere el aprovisionamiento de un archivo local `.env` en la raíz de la carpeta de trabajo para la lectura dinámica de tokens en caliente a través del sistema operativo:

```ini
# ==============================================================================
# CAPA COGNITIVA - INTELIGENCIA ARTIFICIAL (NVIDIA NIM & GEMINI FALLBACK)
# ==============================================================================
NVIDIA_API_KEY=nvapi-R3g...       # Token maestro de autenticación para el catálogo de modelos de NVIDIA
GEMINI_API_KEY=AIzaSyA...       # API Key de respaldo institucional para la suite de contingencia de Google

# ==============================================================================
# INFRAESTRUCTURA DE ORACLE CLOUD (OCI OBJECT STORAGE CONFIGURATION)
# ==============================================================================
OCI_USER_OCID=ocid1.user.oc1..aaaaaaaaxxx...    # Identificador único de usuario en la consola de Oracle
OCI_TENANCY_OCID=ocid1.tenancy.oc1..aaaaaaayyy... # OCID de la raíz de la organización del inquilino OCI
OCI_REGION=sa-saopaulo-1                          # Código geográfico de la región del centro de datos destino
OCI_FINGERPRINT=aa:bb:cc:dd:ee:ff:11:22...        # Huella digital vinculada a la clave pública de API registrada
OCI_KEY_FILE_PATH=./.oci/oci_api_key.pem         # Ruta local hacia el archivo físico de llave privada de firma
OCI_BUCKET_NAME=bkt-communitylab-marketing        # Nombre exacto del bucket confirmado por Cloud
```