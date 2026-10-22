# Flujo conversacional de CommunityLab

El MVP del agente en vivo es un flujo Python independiente de Streamlit. Recibe
resultados de Ciencia de Datos ya procesados, permite consultar y filtrar esos
mensajes, y puede generar borradores de marketing basados en evidencia. No
reemplaza el procesamiento por lotes de LangGraph ni publica en redes sociales.

## Flujo

1. Valida la consulta y rechaza solicitudes explícitas de programación o de
   actualidad externa.
2. Extrae filtros conocidos de forma determinista: sentimiento, tipo de
   interacción, período relativo y plataforma para borradores.
3. Busca términos sobre un índice invertido construido una vez al crear la
   instancia. Aplica los filtros antes de elegir hasta ocho mensajes como
   contexto para el modelo.
4. Calcula distribuciones y conteos sobre todas las coincidencias, no solo
   sobre los mensajes incluidos en el contexto acotado.
5. Si hay evidencia, realiza una llamada estructurada al proveedor de
   generación configurado. NVIDIA NIM conserva el fallback existente a Gemini.
6. Valida que las citas correspondan a la evidencia recuperada y, cuando se
   solicitó un borrador, que la salida incluya la plataforma y hashtags
   estructurados.

Las consultas sin coincidencias y las solicitudes fuera del alcance no llaman
al modelo. Las fechas relativas se calculan en UTC; `hoy` permite fijar la fecha
para pruebas reproducibles.

## Uso desde código

```python
from datetime import date

from src.agentes.conversacion import AgenteConversacional

# Se puede pasar la lista `interacciones` del contrato de salida DS o
# directamente el objeto de salida que contiene `interacciones`/`resultados`.
agente = AgenteConversacional(salida_ciencia_datos)
respuesta = agente.consultar(
    "¿Qué mensajes negativos sobre Python hubo la semana pasada?",
    hoy=date(2026, 10, 21),
)
```

El resultado contiene `respuesta`, `citas` (IDs), `total_coincidencias`,
`filtros`, `modo` y, para solicitudes de creación, un `borrador` con plataforma,
título, contenido y hashtags. Las citas permiten a la futura interfaz enlazar
la respuesta con los mensajes cargados; el agente no publica contenido.

Cada instancia conserva un historial acotado en memoria. La instancia debe
pertenecer a una única sesión de usuario y a un único conjunto de datos. No se
crean cuentas, se escriben conversaciones en disco ni se usa una base de datos.
Un adaptador de almacenamiento puede sustituir la fuente de mensajes cuando se
incorpore la base de datos futura.

La búsqueda del MVP es lexical y usa los campos ya clasificados por Ciencia de
Datos; no hace una llamada adicional al modelo para planear la búsqueda, ni usa
embeddings. Está acotada en contexto para reducir tokens, pero todavía no
implementa una política de caché, medición de latencia ni búsqueda semántica.
Los resultados generados son borradores para revisión humana.

## Validación

```powershell
python -m pytest tests/agents/test_conversacion.py -q
```
