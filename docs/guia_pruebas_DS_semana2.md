# GUÍA ACTUALIZADA DE EJECUCIÓN

1. Abrir una terminal PowerShell en la raíz del proyecto.

2. Crear el entorno virtual si todavía no existe:

python -m venv .venv

3. Activar el entorno virtual:

.\.venv\Scripts\Activate.ps1

4. Instalar las dependencias del proyecto:

python -m pip install -r requirements.txt

5. Crear o configurar el archivo .env en la raíz del proyecto con la API Key de Gemini:

GEMINI_API_KEY="una api aqui"

Si requieren una API Key, pueden crear una propia o solicitar una al equipo, sin problema.


6. Para evitar problemas con tildes y caracteres especiales en Windows, configurar Python en UTF-8:

$env:PYTHONUTF8="1"

7. Ejecutar la prueba completa Data -> Data Science -> contrato de salida:

python -B -m pytest tests\integracion\prueba_entrega_resultados_funcional.py -v -s -p no:cacheprovider

8. La prueba procesa las 23 interacciones recibidas desde Data y ejecuta:

Análisis con Gemini
        ↓
Clasificación semántica
        ↓
LangGraph
        ↓
Enrutamiento
        ↓
Generación de activos
        ↓
Contrato oficial de salida DS

Durante la ejecución puede tomar algunos minutos debido al control de solicitudes implementado para evitar errores 429 de Gemini.

9. Al finalizar se generan los archivos:

output\entrega_ciencia_datos_completa.json
output\resumen_entrega_ciencia_datos.txt

El archivo principal es:

output\entrega_ciencia_datos_completa.json

y contiene el contrato de salida v1.0, incluyendo:

- resumen_comunidad
- interacciones
- activos
- pendientes
- ids_pendientes


RESULTADO ESPERADO

23 interacciones procesadas
0 pendientes
14 interacciones con activos
30 activos generados
0 errores

Pytest debe finalizar con:

1 passed


ACLARACIÓN

Las 14 interacciones con activos corresponden a los mensajes que generaron al menos un activo.

Los 30 activos totales se distribuyen así:

- 8 testimonios -> 24 activos
  - 8 caso_exito
  - 8 boletin / Community Highlight
  - 8 linkedin

- 4 preguntas técnicas -> 4 preguntas_frecuentes

- 2 feedback -> 2 insight_mejora

Total: 30 activos generados.