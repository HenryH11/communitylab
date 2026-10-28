# 🚀 CommunityLab — Motor Inteligente de Transformación y Distribución SaaS

> **Producto Mínimo Viable (MVP) — Versión Final de Producción (Semana 5)**
> **Proyecto Oficial de Graduación — Equipo 39 (EnhanceIA Studio - EIAS)**
> *Programa Oficial Oracle Next Education (ONE) G10 - LATAM & No Country*

## Guías para entender el proyecto

- [Manual de lectura del código](docs/manual_lectura_codigo.md): recorridos de
  ejecución, contratos, estado, inventario y laboratorio offline.
- [Razones de arquitectura y tecnologías](docs/razones_arquitectura_tecnologias.md):
  estructura, decisiones, alternativas, compromisos y límites del diseño actual.


---

## 📖 1. Visión del Proyecto y Storytelling de Datos (80% Comercial / 20% Técnico)
**CommunityLab** es una plataforma SaaS de grado industrial especializada en *MarTech* diseñada para resolver la pérdida de capital intelectual, testimonios de éxito y engagement de los usuarios en las comunidades digitales de Latinoamérica (Discord, Slack, Reddit). El sistema opera como una **línea de ensamblaje inteligente**: toma conversaciones orgánicas masivas y caóticas (ruido), las normaliza mediante expresiones regulares y, a través de un grafo dirigido de agentes cognitivos (LangGraph) potenciado por LLMs de frontera, las transforma automáticamente en activos de marketing estructurados con alto potencial de conversión (LinkedIn, Newsletters semanales y repositorios FAQ de soporte).

### 📈 Evolución y Madurez del MVP:
*   **La Refinería de Datos (Data Analysis):** Ingiere lotes masivos de texto, purga etiquetas HTML y calcula un scoring matemático de relevancia sin costo de API, aislando el valor real del ruido orgánico.
*   **El Orquestador Cognitivo (Data Science):** Un grafo asíncrono con enrutamiento híbrido evalúa la taxonomía de los mensajes; si detecta un logro, redacta copys con Few-Shot Learning; si detecta una duda, alimenta los canales educativos.
*   **La Consola de Control (Software Solution & QA):** Una interfaz modular SaaS interactiva con control *Human-in-the-Loop* que permite curar los borradores en caliente antes de su publicación perimetral segura.
*   **La Autopista Cloud (Cloud Engineering):** Conexión bidireccional asíncrona con el Object Storage Always Free de Oracle para persistencia elástica, encapsulada en contenedores herméticos Docker no-root corriendo en OCI Compute.

---

## 🛠 2. Tecnologías y Herramientas (Ecosistema Core)
*   **Lenguaje de Programación:** Python 3.11+
*   **Orquestación de Agentes y Memoria:** LangGraph / LangChain Core / MemorySaver Checkpointer
*   **Motores de Inferencia (Híbridos):** NVIDIA NIM (Nemotron-3.5-Lightning / DeepSeek-V4-Pro)
*   **Mecanismo de Respaldo:** Google Gemini API (Fallback automático ante latencia de red >1.8s)
*   **Interfaz de Usuario (SaaS Frontend):** Streamlit (7 Pestañas reactivas con persistencia de estado)
*   **Infraestructura y Nube:** Oracle Cloud Infrastructure (OCI Object Storage SDK / VCN / Compute Instance)
*   **Aseguramiento de Calidad:** Pytest & Pytest-Asyncio (Suite de regresión semántica con más de 700 casos en verde)
*   **Gobernanza de Código:** Git & GitHub (Estrategia Git Flow Terminal con Conventional Commits)

---

## 👥 3. Estructura General del Equipo (Esquema Organizativo EIAS)

```text
                     ┌─────────────────────────────────────────────────────────┐
                     │              💼 PROJECT MANAGEMENT (PM)                 │
                     ├─────────────────────────────────────────────────────────┤
                     │         [🇲🇽] Enrique Hernández Godoy (Líder PM)         │
                     └────────────────────────────┬────────────────────────────┘
                                                  │
         ┌────────────────────────┬───────────────┼───────────────┬────────────────────────┐
         ▼                        ▼               ▼               ▼                        ▼
 ┌──────────────┐         ┌──────────────┐┌──────────────┐┌──────────────┐         ┌──────────────┐
 │ 📐 SOFTWARE  │         │ 📊 DATA      ││ 🧠 DATA      ││ 💻 BACKEND / │         │ ☁️ CLOUD      │
 │   SOLUTION   │         │   ANALYSIS   ││   SCIENCE    ││  QA TESTER   │         │ ENGINEERING  │
 ├──────────────┤         ├──────────────┤├──────────────┤├──────────────┤         ├──────────────┤
 │ [🇲🇽] Nelson  │         │ [🇨🇱] Gustavo  ││ [🇵🇪] Arnold  ││ [🇲🇽] Eduardo  │         │ [🇵🇾] Renato  │
 │      Ramses  │         │      Vásquez ││      Bustinza││      Salvador│         │      Preda   │
 │      Aviles  │         │      Serey   ││      (Líder) ││      Martínez │         │      (Líder) │
 └──────────────┘         ├──────────────┤├──────────────┤├──────────────┤         ├──────────────┤
                          │ [🇨🇴] Jhonattan││ [🇨🇴] Alfrek   ││ [🇨🇱] Alejandro│         │ [🇨🇱] Marco   │
                          │      Gabriel ││      Arthur  ││      Alberto │         │      Soto    │
                          │      Benavide││      Pinto   ││      Landa   │         └──────────────┘
                          └──────────────┘└──────────────┘└──────────────┘
```

### 📋 Desglose de Funciones de Ingeniería de Software:
*   **💼 Célula de Project Management (PM):** Dirección del roadmap de 6 semanas, control estricto del checklist del MVP, administración de las Branch Protection Rules en GitHub y gobernanza de entregables institucionales.
*   **📐 Célula de Software Solution (SS):** Modelado conceptual del pipeline unificado E2E, definición técnica de contratos JSON fijos, aprobación técnica de Pull Requests y diseño de la consola SaaS modular en Streamlit.
*   **📊 Célula de Data Analysis (DA):** Desarrollo del pipeline de extracción de 333 líneas con expresiones regulares, sanitización de strings, normalización de UTF-8 contra Mojibake y diseño analítico del score de relevancia.
*   **🧠 Célula de Data Science (DS):** Configuración del grafo de LangGraph, control de transiciones lógicas del diccionario `AgentState`, ingeniería de prompts Few-Shot e inyección de la memoria persistente local.
*   **💻 Célula de Backend & QA Tester (BE/QA):** Cobertura masiva de la suite automatizada bajo Pytest, validaciones sintácticas cruzadas en servidor y mantenimiento del control de regresión semántica.
*   **☁️ Célula de Cloud Engineering (CE):** Aprovisionamiento cloud, políticas de seguridad perimetral de la VCN, enlace nativo asíncrono con el OCI Object Storage SDK y dockerización multi-stage bajo usuario no-root.

---

## 📁 4. Arquitectura Física del Repositorio (`develop3`)
El esqueleto arquitectónico del repositorio se encuentra desplegado bajo estrictos estándares de desacoplamiento y modularidad absoluta:

```text
communitylab-develop3/
├── .dockerignore       # Exclusión de contextos locales para optimizar la compilación de imágenes Docker.
├── .env.example        # Plantilla maestra de variables de entorno e infraestructura secreta.
├── .gitignore          # Exclusión terminal de entornos virtuales, llaves criptográficas .pem y tokens.
├── Dockerfile.backend  # Contenedor optimizado para el backend de agentes y el orquestador cognitivo.
├── Dockerfile.frontend # Contenedor multi-stage para la interfaz gráfica reactiva en Streamlit.
├── README.md           # Informe técnico institucional maestro de producción (Storytelling de Datos).
├── docker-compose.yml  # Orquestador maestro de la suite multi-contenedor para producción en OCI Compute.
├── requirements.txt    # Archivo máster de dependencias congeladas y auditadas del sistema.
├── configuracion/
│   └── relevancia.json # Pesos fijos analíticos para el cálculo numérico de prioridad de mensajes.
├── docs/               # Manuales operativos, bitácoras de regresión y especificaciones sintácticas.
│   ├── arquitectura-solucion/
│   │   ├── contrato-entrada.schema.json  # Esquema contractual estricto para interacciones de entrada.
│   │   ├── contrato-salida.schema.json   # JSON Schema unificado que valida las llaves MarTech de salida.
│   │   └── diagrama-e2e-communitylab.md  # Diagrama conceptual de bloques de la infraestructura global.
│   └── avance_datascience_semana2.md     # Registro de ingeniería de los nodos generadores y LangGraph core.
│   ├── arquitectura_general_sistema.md # Especificación técnica del pipeline de datos extremo a extremo (E2E).
│   ├── avance_datascience_semana4_spam.md # Registro y calibración del nodo clasificador y enrutador de spam.
│   ├── avance_jhonattan_semana1.md     # Bitácora analítica de la carga masiva y unificación del dataset base.
│   ├── benchmark_calibracion_casos_ambiguos.json # Set de datos de holdout para evaluar el comportamiento del LLM.
│   ├── conjunto_consultable.md         # Documentación del índice analítico y el conector de base de datos.
│   ├── contrato_datos_ingesta.md       # Reglas sintácticas originales de la célula de análisis de datos.
│   ├── criterio_puntuacion_relevancia.md # Fórmulas matemáticas aplicadas para el cálculo del Relevance Score.
│   ├── diagrama_flujo_datos_ingesta.md # Flujo detallado del pipeline de extracción y limpiador de strings.
│   ├── diagrama_persistencia_oci.md    # Mapeo de la conexión segura asíncrona con el Object Storage.
│   ├── docker_cloud_semana4.md         # Especificaciones de infraestructura y manual de containerización.
│   ├── evaluacion_proveedores_semana3.md # Pruebas comparativas de latencia entre Gemini y NVIDIA NIM.
│   ├── evidencia2_entrega_ciencia_datos_completa.json # Consolidado de 23 interacciones reales del MVP.
│   ├── evidencia_holdout_proveedores_semana3.json # Muestra de control para la certificación del Green Cert de QA.
│   ├── huellas_saneamiento_semana5.md  # Registro de purga de comentarios de depuración y refactorización.
│   ├── informe_evaluacion_concurrencia_semana5.md # Métricas de rendimiento ante ráfagas de procesamiento masivo.
│   ├── informe_pruebas_langchain.pdf   # Certificado estático de las pruebas unitarias y de estrés del grafo.
│   ├── ingesta_lotes_retenidos_ce.md   # Registro de auditoría sobre payloads corruptos interceptados.
│   ├── integracion_frontend_semana5_1.md # Bitácora de acoplamiento de las 7 pestañas reactivas en Streamlit.
│   ├── manual_lectura_codigo.md        # Guía para desarrolladores sobre la lógica de la suite de software.
│   └── registro_cambios_y_decisiones.md # Registro de gobernanza de la Dirección de Proyecto.
├── scripts/            # Herramientas auxiliares de simulación, calibración y benchmarking.
│   ├── agente_en_vivo.py               # Herramienta de pruebas del chat conversacional en terminal local.
│   ├── auditoria_consistencia.py       # Script que valida la estabilidad de las salidas estructuradas del LLM.
│   ├── benchmark_concurrencia_calidad.py # Emulador de peticiones simultáneas para evaluar el Rate Limiting.
│   ├── medir_latencia_nvidia_nim.py    # Módulo de telemetría para evaluar tiempos de respuesta de los endpoints.
│   └── probar_oci_storage.py           # Script de testing de conectividad con las variables de entorno de Oracle.
├── src/                # Código fuente principal de la aplicación.
│   ├── agentes/        # Orquestación de Inteligencia Artificial (LangGraph Core).
│   │   ├── nodos/      # Funciones lógicas encargadas de bifurcar y redactar activos MarTech.
│   │   │   ├── nodo_analizador.py      # Nodo que extrae taxonomía y clasifica sentimiento.
│   │   │   ├── nodo_enrutador.py       # Lógica que evalúa las variables del AgentState.
│   │   │   └── nodos_generadores.py    # Componentes que redactan los contenidos especializados.
│   │   ├── proveedores/# Conectores oficiales a las APIs (nvidia_nim.py y gemini.py).
│   │   ├── prompts/    # Plantillas e ingeniería de prompts parametrizados (linkedin.py, boletin.py).
│   │   ├── cadenas.py  # Configuración e instanciación de los modelos y llaves criptográficas.
│   │   └── grafo.py    # Orquestador maestro del flujo y de los bordes condicionales del agente.
│   ├── app/            # Interfaz Gráfica de Usuario (Frontend SaaS).
│   │   ├── assets/     # Recursos vectoriales de redes sociales para la suite de marketing.
│   │   ├── app.py      # Inicializador y lógica de las 7 pestañas de la UI.
│   │   └── interfaz.py # Componentes gráficos comunes y estilos de Streamlit.
│   ├── config/         # Parámetros globales e infraestructura cloud.
│   │   ├── oci_client.py   # Cliente nativo que invoca el SDK oficial de Oracle Cloud Storage.
│   │   └── db_client.py    # Conector e indexador del "Conjunto Consultable" de datos.
│   └── datos/          # Ingesta, parseo y limpieza de datos (Data Analysis).
│       ├── ingest.py   # Orquestador del flujo de entrada y telemetría de procesamiento.
│       ├── ingesta_reddit.py # Extractor robusto con algoritmos de Exponential Backoff.
│       └── relevancia.py     # Algoritmo cuantitativo para el cálculo numérico del score.
└── tests/              # Suite automatizada de aseguramiento de calidad (Pytest).
    ├── agents/
    │   ├── test_mojibake_cp1252.py     # Validador de codificación UTF-8 para caracteres latinos.
    │   ├── test_tolerancia_fallas.py   # Certifica la resiliencia ante payloads malformados o vacíos.
    │   └── test_validacion_semantica_nueva.py # Suite de regresión que blinda las respuestas de la IA.
    └── test_persistencia_oci.py        # Pruebas unitarias de conectividad transparente con el Bucket.

---

## 📈 5. Estado de Control e Hitos Cumplidos (Storytelling del MVP)

### 🏢 Semana 0 — Fase de Cimientos, Datos y Arquitectura de Sistemas
*   **Hito de Gobernanza:** Inicialización del repositorio remoto con Branch Protection Rules. Bloqueo estricto de la rama `main` y apertura de la rama común de integración `develop3` bajo Conventional Commits.
*   **Hito de Contratos:** Diseño del modelado de bloques conceptual E2E y firma de los contratos JSON de entrada y salida para asegurar la interoperabilidad sintáctica entre células.
*   **Hito Cloud Base:** Aprovisionamiento del compartimento Always Free en la consola de Oracle Cloud Infrastructure. Creación exitosa del Bucket elástico `communitylab-activos-marketing` en la región de São Paulo.

### 🏢 Semana 1 — Procesamiento, Filtrado Temático y Estructura IA Core
*   **Hito de Pipeline de Datos:** Sincronización e integración de las ramas de datos bajo la dirección del PM. Consolidación del dataset maestro local con los 23 casos reales del MVP y el pipeline extractor `ingesta_reddit.py` (333 líneas) con Exponential Backoff para mitigar el Error HTTP 429.
*   **Hito de Scoring Analítico:** Implementación del script matemático `relevancia.py` que consume los pesos de `config/relevancia.json` para priorizar los mejores momentos de la comunidad de forma automatizada y sin costo de API.
*   **Hito Cognitivo Base:** Compilación del esqueleto del grafo dirigido en LangGraph acoplado a la clase tipada `AgentState`, asegurando la transferencia de estados en memoria de manera transparente.

### 🏢 Semana 2 — Generación de Activos Estructurados, Nubes y UI Base
*   **Hito de Prompt Engineering:** Implementación exitosa de los prompts analíticos parametrizados utilizando técnicas avanzadas de *Few-Shot Learning*. Inyección de los casos reales del PDF (Mariana Souza para MarTech corporativo y Lucas Albuquerque para canales FAQ), moldeando la voz de marca sin alucinaciones.
*   **Hito Frontend Inicial:** Inicialización limpia del cascarón gráfico de Streamlit en `src/app/app.py`. Diseño del layout interactivo preparado para la inyección asíncrona de datos desde el backend.
*   **Hito QA Green Cert:** Ejecución e integración de la suite de pruebas unitarias cruzadas en servidor. El procesamiento de los lotes masivos arrojó un estatus unificado **PASSED en un tiempo récord de 74.66 segundos**.

### 🏢 Semana 3 — Enrutamiento Condicional, Inferencia Híbrida y Persistencia
*   **Hito de Innovación Multimodelo:** Integración del catálogo de inferencia gratuita de NVIDIA NIM. Configuración de un enrutamiento híbrido cognitivo (*Hybrid-Model Routing*) que utiliza *Nemotron-3.5-Lightning* para decisiones del ruteador condicional y *DeepSeek-V4-Pro* para copywriting de alta fidelidad.
*   **Hito de Resiliencia Fallback:** Acoplamiento de un mecanismo de conmutación en caliente (*Fallback*) hacia la API de Google Gemini dentro de `fallback_ia.py` que redirige el tráfico automáticamente si la latencia de NVIDIA NIM supera los 1.8 segundos.
*   **Hito de Persistencia Cloud:** Enlace directo del SDK oficial de Oracle (`oci_client.py`) al nodo de cierre del grafo de agentes, logrando que cada lote aprobado por marketing se guarde de forma invisible en el Object Storage de São Paulo.

### 🏢 Semana 4 — Panel de Curaduría Humana, Portabilidad y Seguridad
*   **Hito Human-in-the-Loop:** Intercepción de los payloads del LLM mediante componentes `st.text_area` en Streamlit, permitiendo al equipo de marketing editar los copys antes de guardarlos. Se acopló un validador contractual que bloquea el envío si la edición humana rompe el JSON Schema del negocio.
*   **Hito DevOps Multi-Stage:** Construcción de una arquitectura multi-contenedor optimizada mediante Dockerfiles independientes para Frontend y Backend bajo la política de privilegios mínimos (usuario no-root).
*   **Hito de Resguardo Criptográfico:** Quedó estrictamente prohibido el almacenamiento de claves en texto plano. Las credenciales de producción son inyectadas en caliente directamente en la memoria del contenedor Docker a través del entorno seguro de la OCI Compute Instance.

### 🏢 Semana 5 — Motor Colectivo, Evaluación de Regresión y Despliegue SaaS
*   **Hito del Motor Colectivo:** Implementación de la arquitectura de generación por lotes desarticulados de Arnold, habilitando tres modalidades editoriales a partir de un único análisis de datos: Individual, Agrupado (post sintético unificado basado en múltiples IDs) y Mixto.

## 🛠 6. Flujo de Trabajo Operativo para el Equipo (Gobernanza Git Flow)

Para mantener una línea base libre de regresiones sintácticas y asegurar una auditoría de código limpia ante los evaluadores del programa, la dirección técnica impuso las siguientes directrices terminales de control:

### 🔹 1. Uso de Conventional Commits
Cada confirmación de código en el servidor local o remoto debe seguir la nomenclatura tipada internacional:
*   `feat(modulo):` Para nuevos desarrollos o nodos lógicos del grafo.
*   `fix(modulo):` Para correcciones de bugs, excepciones o saneamiento de strings.
*   `docs(modulo):` Para actualizaciones de README, especificaciones o manuales de arquitectura.
*   `chore(modulo):` Para tareas de mantenimiento, dependencias o congelamiento de ramas.

### 🔹 2. Integración por Pull Requests (PR)
Está estrictamente prohibido realizar inserciones directas (`git push`) sobre la rama de producción protegida `main` o sobre la rama común de integración `develop3`. Los cambios se someten obligatoriamente a revisión por pares abriendo un Pull Request desde ramas locales de tarea utilizando la siguiente estructura semántica de ramas:
*   `feature/nombre_subequipo_tarea` (Ejemplo: `feature/grafo-ia-ds` o `feature/streamlit-ui-ss`).
*   `hotfix/nombre_error_critico` (Ejemplo: `hotfix/mojibake-utf8-da`).

---

## 🔐 7. Guía Maestra de Configuración y Variables de Entorno

El sistema requiere el aprovisionamiento de un archivo local `.env` en la raíz de la carpeta de trabajo. Las llaves son leídas dinámicamente en caliente a través del sistema operativo, quedando prohibida su escritura explícita en texto plano dentro del código:

```env
# ==============================================================================
# I. CAPA COGNITIVA - INTELIGENCIA ARTIFICIAL (NVIDIA NIM & GEMINI FALLBACK)
# ==============================================================================
NVIDIA_API_KEY=nvapi-k4g...      # Token maestro de autenticación para el catálogo de NVIDIA NIM.
GEMINI_API_KEY=AIzaSyD...       # API Key de respaldo institucional para la suite de contingencia.

# ==============================================================================
# II. INFRAESTRUCTURA EN ORACLE CLOUD (OCI OBJECT STORAGE CONFIGURATION)
# ==============================================================================
OCI_USER_OCID=ocid1.user.oc1..aaaaaaaa...     # Identificador único de usuario en la consola de Oracle.
OCI_TENANCY_OCID=ocid1.tenancy.oc1..aaaaaaaa...  # OCID de la raíz de la organización del inquilino.
OCI_REGION=sa-saopaulo-1                         # Código geográfico de la región del centro de datos.
OCI_FINGERPRINT=aa:bb:cc:dd:ee:ff:11:22...      # Huella digital vinculada a la clave pública de API.
OCI_KEY_FILE_PATH=./config/oci_api_key.pem       # Ruta local hacia el archivo físico de llave privada.
OCI_BUCKET_NAME=bucket-communitylab-marketing   # Nombre exacto del bucket elástico confirmado por Cloud.
```

---

## 🐳 8. Despliegue Automatizado mediante Contenedores (Docker)

Para ejecutar de manera aislada todo el ecosistema SaaS y el pipeline de Ciencia de Datos en un servidor local o en vuestra instancia de OCI Compute, ejecute la siguiente secuencia en su terminal:

### Paso 1: Poblar las variables reales
```bash
cp .env.example .env
nano .env # Proceda a rellenar las llaves OCI y tokens de IA requeridos
```

### Paso 2: Lanzar la construcción y ejecución en segundo plano
```bash
docker-compose up --build -d
```

### Paso 3: Verificar estado de puertos
Abra su navegador web e ingrese a la dirección local predeterminada: `http://localhost:8501`. Asegúrese de abrir el puerto perimetral correspondiente en las tablas de listas de seguridad de la red VCN de Oracle Cloud si está desplegando en producción.

---

## ⚖️ 9. Licencia y Derechos de Autor
Este software se distribuye como propiedad intelectual protegida de **EnhanceIA Studio (EIAS)** bajo los lineamientos de simulación laboral avanzada de la Generación 10 de Oracle Next Education y No Country, optimizado para su uso comercial exclusivo por equipos de MarTech de Latinoamérica.

---

## 🌐 Dirección de Producción SaaS
Visite el entorno web oficial interactivo en vivo: [https://communitylab.lat](https://communitylab.lat)