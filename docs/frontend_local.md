# CommunityLab: frontend local de Streamlit

Rama: `feature/frontend-streamlit-local`. Base consultada el 2026-10-14:
`origin/develop`, commit `8cedef21f574ee7584c86e87052fcea255377f9d`.
El frontend se trabaja en el checkout `communitylab_frontend`, separado del
checkout de Datos en `communitylab`. No se han copiado commits exclusivos de
las ramas de auditoría.

## Referencia visual

[Boceto compartido de Excalidraw](https://excalidraw.com/#json=0Km54u15U234zKdimKLHL,wPlaNd2ZEyzFsf-weUisog).
La revisión del 2026-10-14 utiliza los elementos vectoriales originales del
SVG exportado desde el enlace compartido. Se conservan las coordenadas, textos,
colores, tipografía y formas de las nueve vistas de escritorio (1440 × 875),
así como las dos composiciones móviles del boceto. Se escala proporcionalmente
el marco de escritorio al ancho de la ventana.

El componente local `src/app/frontend/` muestra esos elementos y coloca
controles HTML accesibles en los mismos puntos: navegación, catálogo con búsqueda
y categorías, configuración, copia, enlaces a redes, consultas de demostración,
ayuda y selección de JSON. Los controles de revisión local y las descargas están
bajo el marco original para conservar su composición. Las vistas móviles de
inicio y resultado reutilizan las composiciones de los teléfonos del dibujo;
las demás pantallas mantienen sus funciones en una columna.

Las cifras, gráficos, post y respuesta del agente dibujados en el boceto son
ilustrativos. Se conservan sus notas originales y se aclara el modo local. Los
conteos del archivo validado se muestran por separado debajo del panel. El botón
de procesamiento de IA permanece sin activar; la consulta devuelve un aviso de
integración pendiente.

## Arranque en Windows

Desde la raíz de este checkout, con Python 3.12:

```powershell
python -m venv ../.runtime_frontend
../.runtime_frontend/Scripts/python.exe -m pip install -r requirements-frontend.txt
../.runtime_frontend/Scripts/python.exe -m streamlit run src/app/app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
```

URL: <http://127.0.0.1:8501>. Si el puerto está ocupado, elige otro con
`--server.port`. El entorno queda fuera del repositorio. No se requiere `.env`,
claves de API, OCI ni dependencias de los agentes.

El servidor iniciado por este chat se ejecuta en segundo plano. Su PID y puerto
están en `../.runtime_frontend/server.pid` y `server.port`. Sus logs están en
`design.stdout.log` y `design.stderr.log` dentro del mismo directorio.
Para detenerlo, comprueba primero que ese PID sigue correspondiendo a este
servidor y usa `Stop-Process -Id <PID>`. El cierre de Windows detiene la app.

## Aplicación anterior para uso interno

`src/app/ingesta_app.py` recupera sin modificar el código de la antigua
`src/app/app.py` del commit `bfee004` (2026-10-08). La versión anterior queda
disponible con otro nombre; el frontend de Excalidraw continúa en `src/app/app.py`.

| Archivo | Uso | Arranque |
| --- | --- | --- |
| `src/app/app.py` | Frontend de Excalidraw y entrada del despliegue | `streamlit run src/app/app.py` |
| `src/app/ingesta_app.py` | Herramienta interna recuperada | `streamlit run src/app/ingesta_app.py --server.address=127.0.0.1 --server.port=8502` |

El Dockerfile conserva `src/app/app.py` como único comando de arranque. La
aplicación interna no se inicia ni se publica como otra página del frontend;
se ejecuta de forma independiente. El puerto 8502 permite usar ambas a la vez.

La aplicación anterior carga JSON, prepara el paquete de datos, ofrece el
procesamiento explícito con IA y presenta métricas, gráficas y resultados.
Requiere las dependencias completas de `requirements.txt`; el entorno ligero
del frontend no incluye LangGraph ni los SDK de los proveedores. Para no cambiar
ese entorno, puede instalarse en uno separado, fuera del repositorio:

```powershell
python -m venv ../.runtime_ingesta
../.runtime_ingesta/Scripts/python.exe -m pip install -r requirements.txt
../.runtime_ingesta/Scripts/python.exe -m streamlit run src/app/ingesta_app.py --server.address=127.0.0.1 --server.port=8502 --server.headless=true --browser.gatherUsageStats=false
```

La instalación y las llamadas reales de IA no forman parte de la recuperación.
El botón de procesamiento requiere configurar el proveedor y sus credenciales.
Su etiqueta histórica menciona Gemini, pero el proveedor efectivo depende de
la configuración del pipeline. Se conserva también la fecha de referencia fija
`2026-09-17T12:00:00Z` del original; debe revisarse antes de analizar otros periodos.
Esta recuperación no añade un flujo de aprobación o curaduría manual completo
ni conecta la IA con el frontend de Excalidraw.

La recuperación se verificó comparando el archivo con el original de Git y
comprobando su sintaxis. Pasaron diez pruebas de configuración Docker, tolerancia
e inicialización del frontend. Se comprobó además el arranque de ingesta con
AppTest, sustituyendo los módulos de IA por dobles y bloqueando conexiones
externas: aparece la carga de JSON y el arranque no ejecuta el pipeline.
Esta comprobación aislada no valida llamadas reales a los proveedores.

## Recorrido comprobable

1. El menú **DEMO · SIN CUENTAS** permite importar JSON, cargar el ejemplo del
   proyecto (23 mensajes) y consultar el mapa y los estados de la experiencia.
2. En **Datos**, selecciona o arrastra un archivo JSON, o pega JSON en el cuadro
   inferior. Busca por autor/texto, filtra por canal y lee el mensaje completo.
3. En **Plantillas**, usa la búsqueda, las categorías y el orden. El catálogo
   reproduce los seis formatos del boceto: Instagram, LinkedIn, X, sentimiento,
   temas y preguntas. Las vistas de analítica conservan sus gráficos ilustrativos.
4. En **Resultado**, revisa el ejemplo original o usa los controles inferiores
   para generar un borrador simulado con los datos cargados. Copia el contenido,
   abre la red social o descarga una selección. Abrir una red no publica nada.
5. En **Analíticas**, los conteos del archivo validado aparecen bajo la vista del
   boceto y están diferenciados de las cifras ilustrativas de sus gráficos.
6. **Ayuda** contiene las preguntas del diseño y búsqueda. **Agente en vivo**
   reproduce su consulta y respuesta de ejemplo; enviar una consulta muestra
   que la integración real aún no está disponible.

## Validación y estado

Se reutiliza `src/datos/ingesta.py:validar_y_limpiar`; los módulos existentes de
DA, DS y OCI permanecen sin cambios. El adaptador `src/app/local.py` acepta un
lote oficial o un objeto con `lotes`, incluido el dataset del proyecto.
Los campos obligatorios son `origen_comunidad`, `periodo_referencia` y
`interacciones`; cada mensaje requiere `autor`, `canal`, `tipo` y `texto`.

Se rechazan sintaxis JSON incorrecta, codificación distinta de UTF-8, raíces
inválidas, tipos desconocidos, mensajes vacíos tras limpiar, IDs duplicados,
constantes NaN/Infinity, archivos mayores de 5 MB, más de 1.000 mensajes y
textos de más de 50.000 caracteres. Los IDs ausentes se asignan en esta sesión
sin colisionar con los explícitos. No son IDs persistentes del backend.

Un error conserva el lote y resultado válidos anteriores. Cargar un lote
válido nuevo reemplaza los datos y retira los borradores y su selección.
Los borradores y su selección se conservan al navegar dentro de la sesión del componente. **Vaciar sesión**
retira los datos en memoria; no borra archivos del equipo.

Los datos se conservan únicamente en la memoria de la sesión Streamlit. La
validación no sustituye todas las reglas futuras de selección y contratos del
pipeline real. Las descargas son explícitas; no hay guardado en la nube.

## Simulación e integración pendiente

Los borradores descargados incluyen `modo: simulado_local`, `generado_por_ia: false` y
`guardado_en_nube: false`. Las plantillas se construyen por tipo declarado,
con extractos de los mensajes y conteos. No calculan sentimiento, relevancia
semántica, elegibilidad real ni respuestas inventadas para FAQ. No son el
contrato de salida de DS ni deben pasarse directamente al guardado de OCI.

Para integrar posteriormente:

- Sustituir la llamada explícita a `simular_plantilla` por un adaptador que
  utilice `preparar_paquete_ia` y `procesar_paquete_entrega`, y valide la salida.
- Mapear la salida real a los componentes de resultados, diferenciando errores,
  resultados parciales y metadatos de ejecución real.
- Conectar la selección revisada con `guardar_resultado_aprobado`, confirmando
  únicamente los activos cuyo guardado se complete y validando IDs y tipos.
- Implementar la consulta del agente con un contrato acordado por DS.

Ninguno de estos servicios se importa ni se activa por variables de entorno
en este frontend. No se han ejecutado NVIDIA, Gemini ni OCI.

## Pruebas

```powershell
../.runtime_frontend/Scripts/python.exe -m pytest tests/test_frontend_local.py tests/test_tolerancia_app.py tests/test_procesamiento_datos.py -q
node --test tests/test_frontend_interaction.cjs
```

La suite usa `streamlit.testing.v1.AppTest` para comprobar la inicialización del
componente. Comprueba sus acciones del servidor: validación, carga de ejemplo,
generación de borradores, errores, reemplazo de datos, rechazo de acciones
incorrectas, ausencia de procesamiento doble y vaciado de sesión. Comprueba
además la geometría de los activos y la limpieza existente. Bloquea conexiones
externas y permite loopback, que necesita asyncio en Windows. Las interacciones
del componente se prueban en navegador, porque AppTest no ejecuta su JavaScript.
No ejecuta las pruebas de integración de los proveedores.

Resultado: **79 pruebas y 30 subtests aprobados** con Streamlit 1.65.0,
pandas 2.3.3, Altair 5.5.0 y pytest 9.1.1.

Verificación de navegador: subida del JSON de ejemplo, validación de sus 23
mensajes, rechazo del JSON `{` conservando el lote válido, generación simulada,
lectura del mensaje fuente y descarga JSON. Los conteos locales del ejemplo son
23 mensajes, 15 canales, 8 testimonios y 9 preguntas; están separados de los
gráficos ilustrativos originales. Se verificó el inicio en escritorio y a 390 × 844
píxeles, sin desbordamiento horizontal. La descarga probada incluye las marcas
de simulación y no implica una escritura en OCI.


## Fuentes editables del diseño

Los dos archivos exportados están incluidos en `docs/referencias/`:
`Sin título-2026-10-14-0930.excalidraw` y `Sin título-2026-10-14-0930.svg`.
Se conservan los nombres originales de exportación. La escena contiene 676
elementos y su SVG reproduce exactamente las once vistas utilizadas por la app.

`src/app/frontend/design.json` contiene las vistas vectoriales extraídas, por lo
que la app funciona sin leer los originales durante su ejecución. Para regenerarlas después
de editar el boceto, exporta la escena y su SVG correspondientes y ejecuta:

```powershell
../.runtime_frontend/Scripts/python.exe scripts/preparar_boceto_frontend.py 'docs/referencias/Sin título-2026-10-14-0930.excalidraw' 'docs/referencias/Sin título-2026-10-14-0930.svg'
```

`app.js` contiene las interacciones; `style.css` define los controles. No hay
instalación de npm, llamadas externas, tipografías remotas ni dependencias de
frontend obtenidas de CDN. Streamlit sirve el componente en el mismo localhost.

La selección de descarga se valida también en el servidor. La prueba final
exportó siete de ocho borradores, conservando los identificadores fuente y las
marcas de simulación. El archivo se sirve desde la memoria local de Streamlit
mediante su gestor de descargas; no utiliza un enlace Blob ni almacenamiento en
la nube. `src/app/downloads.py` encapsula esa integración para comprobarla al
actualizar Streamlit.

## Respuesta de los botones

Los botones superpuestos cubren la forma completa del boceto, con un mínimo de
44 píxeles para pulsarlos; la navegación ya no depende de acertar sobre las letras.
Las consultas de ejemplo rellenan inmediatamente el campo del agente.
Mientras se procesa una acción local, sus botones muestran el estado ocupado.
Solo la respuesta con el identificador de esa acción los desbloquea. Si no llega
respuesta en 15 segundos, se informa y se permite volver a actuar. Los renders
de Streamlit sin cambios conservan los controles y su foco. El enlace de descarga
preparado se conserva al navegar, sin repetir automáticamente la descarga.

Las pruebas de Node verifican clics repetidos, respuestas anteriores y tardías,
recuperación tras una respuesta ausente y las zonas de pulsación sobre la geometría
real del diseño, incluidas la navegación y las composiciones móviles.
Resultado de esta revisión: **79 pruebas de Python, 30 subtests y cinco pruebas
de Node aprobados**. En navegador se comprobó un clic fuera de las letras del
menú, la superficie lateral de una consulta de ejemplo, el reinicio del campo,
el filtro del catálogo, la generación y descarga de ocho borradores, la ayuda y
la copia en móvil a 390 × 844. El enlace de descarga siguió disponible al navegar.
