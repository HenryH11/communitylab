# Conjunto Consultable · Semana 5.1, subfase A

Responsable: Data Analyst (Gustavo Vásquez, Jhonattan Benavides). Fecha: 15 de octubre de 2026;
actualizado el 19 de octubre (spam del contrato v1.4 y Autonomous DB).

## Para qué sirve

La Matriz Rectora 3 pide que, en la subfase A (lunes 19 y martes 20 de octubre),
DA defina un "Conjunto Consultable": un JSON limpio que funcione como índice de
la base analítica. Lo usan:

- **DS**: las 3 herramientas del agente en `src/agentes/grafo.py` (conteo y
  agrupación, distribución de sentimiento o temas por canal y búsqueda por ID).
  El agente consulta este índice en lugar de reprocesar el JSON completo en cada
  mensaje del chat, que la Matriz prohíbe.
- **CE**: lo carga en una Autonomous DB de OCI. Marco confirmó el 19 de octubre
  que la base queda lista a más tardar el martes 20 por la mañana. La tabla y la
  forma de carga están por coordinar.

El módulo es `src/datos/conjunto_consultable.py`. No llama a IA, no usa red y no
escribe en OCI: solo transforma una entrega de DS en el índice.

## Formato

```json
{
  "version": "1.1",
  "campos": ["id", "canal", "sentimiento", "tema", "tipo", "contenido_textual", "fecha"],
  "total": 23,
  "total_spam_excluido": 0,
  "registros": [
    {
      "id": "int-001",
      "canal": "#logros-y-empleos",
      "sentimiento": "muy_positivo",
      "tema": "empleabilidad",
      "tipo": "testimonio",
      "contenido_textual": "Comunidad, gracias a este programa conseguí mi primer trabajo…",
      "fecha": "2026-09-10T14:32:00Z"
    }
  ]
}
```

Cómo generarlo:

```powershell
python -m src.datos.conjunto_consultable `
  --entrega <entrega_de_DS.json> `
  --mensajes src/datos/mensajes_comunidad_simulados.json `
  --salida <conjunto_consultable.json>
```

## Decisiones

### 1. Siete campos, con el nombre de texto actualizado por Cloud

Son los campos estrictos que pide la Matriz: `id, canal, sentimiento, tema,
tipo, contenido_textual, fecha`. `tema` sale de `tema_principal` y `tipo` de
`tipo_detectado`. Cloud confirmó `contenido_textual` en lugar de
`contenido_corto`. Se mantienen los demás nombres de la Matriz para que las
herramientas de DS y la documentación hablen el mismo idioma. No se agregan
`subtema` ni `rutas` hasta que DS los pida: cada campo extra es contrato que hay
que mantener.

### 2. `contenido_textual` = texto completo (nombre confirmado)

- **Por qué el texto original y no un activo generado:** todas las
  interacciones tienen texto, pero no todas tienen activo (un comentario no
  genera LinkedIn). Además, el original es la fuente verificable: la auditoría
  semántica de DA compara contra él.
- **Cambio de alcance:** se elimina el recorte a 160 caracteres para conservar
  la evidencia completa. Se preservan saltos de línea, espacios, tildes y emojis;
  un texto ausente, vacío o de tipo incorrecto se rechaza explícitamente.
- **Almacenamiento:** Marco confirmó el nombre `contenido_textual` al actualizar
  la tabla para CLOB. El JSON, el SQL y el adaptador usan ese nombre.
  No se aplica ninguna migración de tabla aquí; falta la prueba real de integración.
- **Compatibilidad:** se mantienen los siete campos y la versión 1.1. Los
  consumidores no deben asumir que el texto tiene un máximo de 160 caracteres.
  El campo anterior no se acepta en cargas DB: regenerar los documentos antiguos
  y desplegar productores y consumidores coordinadamente con la columna CLOB.
  Solo el importador de archivos propios conserva `contenido_corto` como alias
  de entrada por compatibilidad; no forma parte del contrato DB vigente.
- **Recarga:** los documentos o registros ya recortados no recuperan su contenido;
  hay que reconstruirlos desde la entrega/fuente original y volver a cargarlos.
- Los límites de volumen y de evidencia enviada al modelo del agente permanecen
  independientes: almacenar texto completo no implica enviarlo todo al modelo.

### 3. La `fecha` se une desde el dataset de entrada

El contrato de salida de DS (v1.3, `src/agentes/entrega_resultados.py`) no
incluye `fecha`. La fecha sí está en el dataset de entrada
(`lotes[].interacciones[].fecha`). El módulo la une por `id` con `--mensajes`.

- **Por qué así:** resuelve la subfase A sin modificar `src/agentes`, que es
  de DS, y sin esperar un cambio de contrato.
- **Alternativa:** si DS agrega `fecha` al contrato v1.3, el módulo la toma de
  la entrega y `--mensajes` pasa a ser opcional. La pregunta quedó planteada a
  DS el 15 de octubre.
- **Si falta:** la fecha queda en `null` y el comando informa cuántos registros
  no tienen fecha. Así no se inventa ningún dato.

### 4. Acepta los dos formatos de entrega de DS

- **Contrato v1.3 y v1.4**: campos planos. Es lo que produce el pipeline y lo
  que CE guarda en OCI. La v1.4 agrega `es_spam_detectado` y `motivo_spam`.
- **Paquete de auditoría v1.2**: `entrada`, `datos` y `analisis` anidados. Es
  con lo que se auditaron las corridas de la Semana 4.

Aceptar ambos permite generar el índice hoy, con la entrega auditada (35 activos,
0 alertas), y mañana, con la salida real del pipeline, sin otro código.

### 5. Exclusiones y duplicados

- Las interacciones que Datos excluyó (`datos.excluido_por_data`) no entran en
  el índice: el agente no debe responder sobre spam o ruido como si fuera
  comunidad real. En el contrato v1.3 ya vienen fuera, porque no llegan al
  grafo.
- Desde el contrato v1.4, los mensajes que DS marca con `es_spam_detectado`
  tampoco entran: el resumen de DS ya los deja fuera de la distribución de
  sentimientos, y el índice tiene que dar las mismas cifras. Solo se cuentan en
  `total_spam_excluido` (versión 1.1 del índice). Con la v1.3, que no trae la
  marca, el resultado no cambia y el conteo es 0.
- Si un `id` aparece dos veces, el módulo se detiene con un error en lugar de
  elegir uno. Es el mismo criterio que adoptó el auditor de DA en el #33.

### 6. Salida estable

Los registros se ordenan por `id`. El JSON se escribe en UTF-8 sin escapar
caracteres (`ensure_ascii=False`) y con `indent=4`, igual que las demás salidas
de `src/datos`. Una misma entrega produce siempre el mismo archivo.

## Verificación

- `tests/test_conjunto_consultable.py`:
  - campos y orden;
  - spam de la v1.4 excluido y contado; v1.3 sin cambios;
  - fecha desde el dataset;
  - paquete de auditoría con exclusiones;
  - IDs duplicados;
  - recorte;
  - comando de terminal.
- Suite sobre develop `46f6d41` con este módulo: 464 aprobadas, 0 fallas.
- Con la entrega final de DS (`5162e61`): 23 registros, 0 sin fecha.
  - Sentimiento: 11 neutral, 8 positivo y 4 muy positivo.
  - Tipo: 8 testimonio, 5 pregunta_programa, 4 pregunta_tecnica, 4 comentario
    y 2 feedback.

## Por coordinar

- **DS (Arnold):** confirmar que los 7 campos alcanzan para las 3
  herramientas, y si se agrega `fecha` al contrato v1.3.
- **CE (Renato, Marco):** la tabla de la Autonomous DB, cómo se cargan los
  registros y en qué momento se genera el índice (después de cada
  procesamiento aprobado o a demanda).
