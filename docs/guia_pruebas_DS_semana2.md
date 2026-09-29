1. Abrir una terminal en la raíz del proyecto.
2. Crear el entorno si no existe: python -m venv .venv
3. Activarlo en PowerShell: .\.venv\Scripts\Activate.ps1
4. Instalar dependencias: python -m pip install -r requirements.txt
5. Crear/configurar el archivo .env con GEMINI_API_KEY
pegan esto:::: GEMINI_API_KEY="una api aqui, si requieren una pueden crearla o piden una al equipo, sin problema"
6. Ejecutar: python -B -m pytest tests/integracion/prueba_paquete_completo_datos.py -v -s -p no:cacheprovider
7. La prueba procesa el paquete completo recibido de Data y muestra cada resultado de DS.
8. Resultado esperado al final: 23 procesados, 0 pendientes, 0 errores.
9. Pytest debe finalizar con: 1 passed.
