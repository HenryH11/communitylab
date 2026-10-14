# CommunityLab: frontend local de Streamlit

Rama: `feature/frontend-streamlit-local`. Base consultada el 2026-10-14:
`origin/develop`, commit `8cedef21f574ee7584c86e87052fcea255377f9d`.
El checkout de DA en `communitylab` conserva su rama
`feature/jhonattan-auditoria-semana4`. No se han copiado sus commits exclusivos.

## Referencia visual

[Boceto compartido de Excalidraw](https://excalidraw.com/#json=0Km54u15U234zKdimKLHL,wPlaNd2ZEyzFsf-weUisog).
Se revisaron las nueve vistas del lienzo. Se adaptaron la navegación, el inicio,
el catálogo, la presentación de resultados, la carga, la analítica y la ayuda
a los componentes de Streamlit. La paleta violeta y azul oscuro y los textos
principales siguen la referencia. Es una adaptación funcional, no una copia
exacta de sus dimensiones. La pantalla del agente queda deshabilitada.

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
`local.stdout.log` y `local.stderr.log` dentro del mismo directorio.
Para detenerlo, comprueba primero que ese PID sigue correspondiendo a este
servidor y usa `Stop-Process -Id <PID>`. El cierre de Windows detiene la app.

## Recorrido comprobable

1. En **Carga**, usa el ejemplo del proyecto (23 mensajes), sube un archivo o
   pega un JSON y pulsa su botón de validación.
2. Busca por autor/texto, filtra por canal y lee el mensaje completo.
3. En **Plantillas**, selecciona un formato y genera el borrador simulado.
   Revisa sus mensajes fuente y descarga solo la selección deseada.
4. En **Analítica**, consulta los conteos por tipo, canal, origen y periodo.
5. En **Ayuda**, consulta los formatos y límites. **Agente en vivo** explica
   la integración pendiente y no permite enviar consultas.

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
Los borradores y su selección se conservan al navegar. **Vaciar sesión**
retira los datos en memoria; no borra archivos del equipo.

Los datos se conservan únicamente en la memoria de la sesión Streamlit. La
validación no sustituye todas las reglas futuras de selección y contratos del
pipeline real. Las descargas son explícitas; no hay guardado en la nube.

## Simulación e integración pendiente

Los resultados incluyen `modo: simulado_local`, `generado_por_ia: false` y
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
```

La suite usa `streamlit.testing.v1.AppTest` para la navegación, carga de ejemplo,
filtros, métricas, generación de borradores, selección persistente, errores,
reemplazo de datos y vaciado de sesión. Bloquea conexiones externas y permite
loopback, que necesita asyncio en Windows. Incluye la regresión existente de
limpieza. No ejecuta las pruebas de integración de los proveedores.

Resultado: **76 pruebas y 30 subtests aprobados** con Streamlit 1.65.0,
pandas 2.3.3, Altair 5.5.0 y pytest 9.1.1.

Verificación de navegador: subida del JSON de ejemplo, validación de sus 23
mensajes, rechazo del JSON `{` conservando el lote válido, generación simulada,
lectura del mensaje fuente, descarga JSON y gráficos con 23 mensajes, 15 canales,
8 testimonios y 9 preguntas. Se verificó el inicio en escritorio y a 390 × 844
píxeles, sin desbordamiento horizontal. La descarga probada incluye las marcas
de simulación y no implica una escritura en OCI.
