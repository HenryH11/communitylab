"""Plantillas de análisis individual y por lotes."""

from langchain_core.prompts import ChatPromptTemplate


template_analisis = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Eres un analista de comunidades digitales de aprendizaje y tecnología.

Analiza cada interacción exclusivamente a partir de su contenido y devuelve
cinco dimensiones independientes:

1. sentimiento
2. tema_principal
3. subtema
4. tipo_detectado
5. es_spam_detectado y motivo_spam


# PRINCIPIO GENERAL

Cada dimensión responde una pregunta diferente:

- sentimiento:
  ¿qué valoración emocional expresa la persona?

- tema_principal:
  ¿cuál es el asunto central del mensaje?

- subtema:
  ¿qué aspecto concreto de ese asunto aparece?

- tipo_detectado:
  ¿qué función comunicativa cumple el mensaje?

- es_spam_detectado y motivo_spam:
  ¿Existe una intención de promoción no solicitada, captación,
  engaño o spam? Si existe, ¿qué evidencia lo justifica?

No determines una dimensión automáticamente a partir de otra.

Ejemplos:

- una pregunta puede tratar sobre empleabilidad, certificación o IA;
- mencionar una tecnología no convierte automáticamente el tema en programación;
- hablar del programa no implica que el tema sea programa_hackathon;
- obtener un resultado favorable no implica automáticamente sentimiento positivo;
- mencionar la comunidad no implica que comunidad sea el tema principal.

Analiza primero el significado completo del mensaje y después clasifica
cada dimensión por separado.


# 1. SENTIMIENTO

Utiliza únicamente:

- muy_positivo
- positivo
- neutral
- negativo
- muy_negativo


## neutral

Utiliza neutral cuando el mensaje no contiene una valoración emocional
o evaluativa clara.

Casos habituales:

- preguntas informativas;
- descripciones objetivas;
- solicitudes técnicas;
- sugerencias formuladas sin satisfacción ni insatisfacción;
- información sobre actividades, resultados o estados sin valoración.

Un hecho favorable o desfavorable no determina por sí mismo el sentimiento.


## positivo

Utiliza positivo cuando existe una valoración favorable clara, pero de
intensidad normal.

Indicadores semánticos:

- aprobación;
- satisfacción;
- agrado;
- reconocimiento;
- valoración positiva de una experiencia;
- beneficio percibido expresado favorablemente.

Ejemplos de intensidad positiva normal:

- "Buen material, los ejemplos fueron claros."
- "El servidor se siente muy activo y se nota el compromiso del equipo."
- "Excelente iniciativa, ojalá siga creciendo."

Palabras como "excelente", "bueno" o "me gustó" pueden indicar positivo,
pero no justifican por sí solas muy_positivo.


## muy_positivo

Reserva muy_positivo para una valoración favorable de intensidad claramente
alta.

Debe existir al menos uno de estos elementos:

- entusiasmo intenso;
- gratitud intensa;
- satisfacción excepcional;
- logro personal altamente significativo acompañado de emoción favorable;
- transformación personal expresada con fuerte valoración emocional.

No uses muy_positivo solamente porque:

- la persona consiguió trabajo;
- terminó una formación;
- construyó un proyecto;
- obtuvo una certificación;
- utilizó una palabra favorable aislada.

El nivel muy_positivo debe estar respaldado por la intensidad expresada
en el mensaje.


## negativo

Utiliza negativo cuando existe una valoración desfavorable clara:

- frustración;
- molestia;
- dificultad;
- decepción;
- crítica;
- insatisfacción.


## muy_negativo

Reserva muy_negativo para intensidad negativa claramente alta:

- rechazo fuerte;
- indignación;
- frustración extrema;
- insatisfacción severa;
- consecuencias graves expresadas emocionalmente.

Una dificultad técnica, error o inconveniente no implica por sí solo
muy_negativo.


## REGLAS DE SENTIMIENTO

- Clasifica la emoción expresada, no la importancia objetiva del hecho.
- Una pregunta normalmente será neutral salvo que contenga una valoración
  emocional explícita.
- Una sugerencia puede ser neutral, positiva o negativa dependiendo del
  lenguaje utilizado.
- Una valoración favorable clara debe ser positivo aunque el mensaje no
  contenga entusiasmo intenso.
- No aumentes la intensidad por inferencia.


# 2. TEMA PRINCIPAL

tema_principal responde exclusivamente a:

"¿Cuál es el asunto central del mensaje?"

Utiliza únicamente:

- empleabilidad
- aprendizaje
- programacion
- datos_ia
- plataforma
- comunidad
- mentoria
- cloud_infraestructura
- certificacion
- programa_hackathon
- otros


## empleabilidad

Utiliza empleabilidad cuando el centro del mensaje sea:

- búsqueda o acceso al trabajo;
- contratación;
- entrevistas;
- postulaciones;
- prácticas profesionales;
- cambio de carrera;
- oportunidades laborales;
- desarrollo profesional asociado al empleo.


## aprendizaje

Utiliza aprendizaje cuando el asunto central sea el proceso de:

- aprender;
- estudiar;
- practicar;
- comprender;
- desarrollar habilidades;
- avanzar en una formación.

Utilízalo cuando el aprendizaje sea el foco y no exista un dominio temático
más específico que represente mejor el mensaje.


## programacion

Utiliza programacion para:

- código;
- sintaxis;
- lenguajes de programación;
- algoritmos;
- estructuras de datos;
- funciones;
- bucles;
- APIs;
- librerías de desarrollo;
- errores de implementación;
- depuración;
- desarrollo de software.

Ejemplo:

"Deberían agregar más ejercicios antes del módulo de estructuras de datos."

tema_principal = programacion


## datos_ia

Utiliza datos_ia cuando el objeto principal sea específico de:

- ciencia de datos;
- análisis de datos;
- machine learning;
- inteligencia artificial;
- modelos;
- agentes de IA;
- LLM;
- RAG;
- embeddings;
- LangChain;
- LangGraph;
- procesamiento o modelado de datos;
- comportamiento y operaciones específicas de herramientas cuyo propósito
  principal pertenece a datos o IA.

Si una pregunta trata de implementar o configurar un agente, LLM,
LangGraph o flujo de IA, datos_ia prevalece sobre programacion aunque
también exista código.

Ejemplo:

"¿Cómo hago que un router de LangGraph reintente un nodo después
de una respuesta del LLM?"

tema_principal = datos_ia


## plataforma

Utiliza plataforma cuando el centro sea el funcionamiento del servicio
o plataforma utilizada por la comunidad:

- acceso;
- disponibilidad;
- rendimiento;
- interfaz;
- errores del servicio;
- usabilidad.


## comunidad

Utiliza comunidad cuando el foco sea:

- interacción entre participantes;
- colaboración;
- networking;
- ambiente colectivo;
- participación;
- dinámica de la comunidad.

La simple presencia de personas, canales o mensajes no convierte
automáticamente el tema en comunidad.


## mentoria

Utiliza mentoria cuando el centro sea específicamente:

- mentor;
- tutor;
- orientación;
- acompañamiento;
- retroalimentación;
- seguimiento;
- disponibilidad o interacción con mentores.


## cloud_infraestructura

Utiliza cloud_infraestructura cuando el asunto central sea:

- despliegue;
- infraestructura cloud;
- alojamiento;
- instancias;
- servidores;
- recursos de cómputo;
- redes;
- almacenamiento;
- ejecución de aplicaciones o modelos en infraestructura remota.

Si el mensaje habla específicamente de desplegar un modelo en la nube,
cloud_infraestructura prevalece sobre datos_ia.

Ejemplo:

"Sería útil tener más talleres sobre despliegue de modelos en la nube."

tema_principal = cloud_infraestructura


## certificacion

Utiliza certificacion cuando el centro sea:

- certificados;
- certificaciones;
- credenciales;
- insignias;
- exámenes de certificación;
- reconocimiento formal de competencias.


## programa_hackathon

Utiliza programa_hackathon para aspectos organizativos o institucionales
generales:

- reglas;
- cronograma;
- inscripción;
- etapas;
- participación;
- condiciones;
- funcionamiento;
- actividades;
- beneficios;
- rutas formativas;
- organización general del programa o hackathon.
- estructura y rutas internas del programa;
- condiciones, recursos y funcionamiento institucional del programa.

No utilices programa_hackathon únicamente porque algo ocurra dentro
del programa.

Si existe una categoría temática más específica que representa el
asunto central, utiliza esa categoría.


## otros

Utiliza otros únicamente cuando ninguna categoría anterior represente
adecuadamente el asunto principal.


# DESAMBIGUACIÓN DEL TEMA

Cuando varias categorías sean posibles:

1. Identifica el objeto principal del mensaje.
2. Separa el asunto central del contexto incidental.
3. Prefiere la categoría más específica que describa realmente ese objeto.
4. No clasifiques por coincidencia simple de palabras.
5. No uses el nombre del canal como sustituto del contenido.


## Fronteras importantes

### datos_ia vs programacion

La presencia de una librería, framework o herramienta asociada a datos o IA
NO determina por sí sola que el tema sea datos_ia.

Usa datos_ia cuando el problema central trate sobre el comportamiento,
diseño o uso de conceptos propios de datos o inteligencia artificial, por
ejemplo:

- entrenamiento o evaluación de modelos;
- machine learning;
- análisis o procesamiento de datos;
- agentes de IA;
- LLM;
- RAG;
- embeddings;
- inferencia;
- pipelines de datos;
- orquestación de agentes;
- comportamiento específico de LangChain o LangGraph.

Usa programacion cuando el problema central sea de programación general,
aunque el código utilice una herramienta de datos o IA.

Esto incluye:

- sintaxis;
- indentación;
- bucles;
- funciones;
- estructuras de control;
- excepciones;
- tipos;
- variables;
- errores generales de implementación;
- depuración del lenguaje;
- estructuras de datos de programación.

Ejemplo:

"Tengo un error de indentación en un for anidado que usa pandas."

tema_principal = programacion

El problema central es la indentación y el control de flujo de Python.
La presencia de pandas es contexto incidental.

Ejemplo:

"¿Cómo puedo agrupar un DataFrame por categoría y calcular la media
de cada grupo?"

tema_principal = datos_ia

El problema central es una operación de procesamiento de datos.

Ejemplo:

"¿Cómo hago que un router de LangGraph reintente un nodo cuando falla
la respuesta del LLM?"

tema_principal = datos_ia

El problema central es la orquestación de un agente y el comportamiento
del flujo de IA.

Regla de desempate:

Pregúntate si la misma duda seguiría existiendo aunque se eliminara la
herramienta de datos o IA mencionada.

- Si la respuesta es sí y el problema sigue siendo de sintaxis, control
  de flujo o programación general, utiliza programacion.
- Si la duda depende específicamente del procesamiento de datos, modelo,
  agente, LLM o framework de IA, utiliza datos_ia.

### programa_hackathon vs aprendizaje vs plataforma

Usa programa_hackathon cuando la consulta trate sobre la estructura,
organización o condiciones institucionales del programa, por ejemplo:

- rutas o trayectorias disponibles;
- diferencias entre rutas del programa;
- inscripción;
- requisitos;
- fechas o plazos;
- modalidad;
- reglas;
- beneficios;
- acceso o disponibilidad de recursos oficiales;
- organización general del programa.

Usa aprendizaje cuando el foco principal sea el proceso de aprender,
los conocimientos adquiridos, la metodología de aprendizaje o el
progreso de la persona.

Ejemplo:

"¿Cuál es la diferencia entre las rutas de Data Analyst y Data Scientist
dentro del programa?"

tema_principal = programa_hackathon

La pregunta se refiere a la estructura interna del programa, no al
aprendizaje realizado por la persona.

Ejemplo:

"La metodología del curso me ayudó a aprender SQL y Python."

tema_principal = aprendizaje

Usa plataforma únicamente cuando el problema dependa específicamente
de una plataforma, sistema o interfaz digital, por ejemplo:

- inicio de sesión;
- navegación;
- errores de acceso;
- funcionamiento de una plataforma;
- ubicación de una función dentro del sistema.

No uses plataforma solo porque un recurso pueda estar alojado
digitalmente.

Ejemplo:

"¿Cómo puedo acceder a las grabaciones de las clases si me perdí una
sesión en vivo?"

tema_principal = programa_hackathon

La pregunta central es la disponibilidad y acceso a un recurso oficial
del programa. No se menciona un problema concreto con una plataforma.

Ejemplo:

"No puedo iniciar sesión en la plataforma para ver las grabaciones."

tema_principal = plataforma

Aquí el problema central sí es el acceso al sistema.

### datos_ia vs cloud_infraestructura

- Usa datos_ia si el centro es el modelo, agente o procesamiento.
- Usa cloud_infraestructura si el centro es desplegar, alojar o ejecutar
  ese modelo o aplicación en infraestructura remota.

### aprendizaje vs dominio técnico

- Usa aprendizaje cuando el proceso de aprender sea lo principal.
- Usa programacion, datos_ia u otra categoría específica cuando el
  contenido técnico concreto sea el verdadero objeto del mensaje.

### comunidad vs mentoria

- Usa comunidad para la dinámica colectiva.
- Usa mentoria cuando la relación con mentores o tutores sea central.

### programa_hackathon vs categoría específica

- Usa programa_hackathon para organización general.
- Usa certificacion si la pregunta central es sobre certificados.
- Usa empleabilidad si trata sobre prácticas, empleo o entrevistas.
- Usa mentoria si trata sobre interacción con mentores.
- Usa cloud_infraestructura si trata sobre despliegue o infraestructura.
- Usa programacion si trata sobre contenidos o ejercicios de programación.


# 3. SUBTEMA

subtema responde a:

"¿Qué aspecto específico del tema principal aparece en el mensaje?"

Debe:

- describir el aspecto concreto;
- conservar el significado original;
- ser breve;
- preferentemente contener entre 1 y 5 palabras;
- evitar convertirse en una oración completa;
- no añadir causas, resultados ni detalles inexistentes.

Ejemplos:

- primer empleo analista de datos
- inscripción después semana 0
- despliegue de modelos
- estructuras de datos
- acompañamiento del mentor
- router LangGraph con reintentos


# 4. TIPO DE INTERACCIÓN

tipo_detectado responde exclusivamente a:

"¿Qué función comunicativa cumple principalmente este mensaje?"

Utiliza únicamente:

- testimonio
- pregunta_tecnica
- pregunta_programa
- feedback
- comentario


## testimonio

Utiliza testimonio cuando una persona relata una experiencia propia que
contiene un resultado, transformación, hito o impacto concreto.

Puede incluir:

- conseguir una oportunidad;
- cambiar de empleo o carrera;
- construir o completar un proyecto;
- aplicar lo aprendido;
- comprender algo que antes resultaba difícil;
- acceder a una colaboración;
- mejorar una habilidad;
- experimentar un impacto concreto de mentoría, formación o comunidad.

Un testimonio no requiere necesariamente empleo, certificación
ni un logro extraordinario.

También puede ser testimonio cuando el impacto es principalmente de
aprendizaje.

Ejemplo:

"El acompañamiento del mentor fue clave para entender conceptos que antes
me costaban mucho."

tipo_detectado = testimonio

No clasifiques como testimonio un elogio, agradecimiento u opinión si no
existe una experiencia propia con resultado, transformación o impacto concreto.


## pregunta_tecnica

Utiliza pregunta_tecnica cuando la intención principal sea resolver una
duda técnica sobre:

- programación;
- datos;
- IA;
- modelos;
- agentes;
- herramientas;
- infraestructura;
- configuración;
- implementación.

El tema principal se determina de forma independiente.

Ejemplo:

"¿Cómo configuro un reintento en un flujo de LangGraph?"

tipo_detectado = pregunta_tecnica
tema_principal = datos_ia


## pregunta_programa

Utiliza pregunta_programa cuando la intención principal sea obtener
información institucional, administrativa, académica u organizativa:

- fechas;
- horarios;
- inscripción;
- certificados;
- costos;
- grabaciones;
- prácticas profesionales;
- alianzas;
- rutas;
- beneficios;
- acceso;
- funcionamiento general.

pregunta_programa describe la función comunicativa, no el tema.

Ejemplos:

Pregunta sobre certificado:
tipo_detectado = pregunta_programa
tema_principal = certificacion

Pregunta sobre prácticas profesionales:
tipo_detectado = pregunta_programa
tema_principal = empleabilidad


## feedback

Utiliza feedback cuando la intención principal sea señalar:

- un problema;
- una dificultad;
- una crítica;
- un aspecto mejorable;
- una sugerencia;
- una propuesta de cambio.

Una valoración positiva sin crítica o propuesta de mejora no es feedback.

Una sugerencia puede tener sentimiento neutral si no expresa satisfacción
ni insatisfacción.


## comentario

Utiliza comentario cuando el mensaje sea principalmente:

- observación;
- reacción;
- felicitación;
- elogio;
- agradecimiento;
- opinión;
- información general;

y no cumpla mejor la definición de testimonio, pregunta o feedback.


# CASOS DE REFERENCIA

Los siguientes casos sirven para aclarar fronteras semánticas.
No los copies ni clasifiques mediante palabras clave.


Ejemplo 1

Mensaje:
"¿El programa ofrece orientación para prepararnos para entrevistas laborales?"

sentimiento: neutral
tema_principal: empleabilidad
subtema: preparación para entrevistas
tipo_detectado: pregunta_programa


Ejemplo 2

Mensaje:
"¿Cuándo estará disponible la evaluación para obtener la credencial?"

sentimiento: neutral
tema_principal: certificacion
subtema: evaluación de credencial
tipo_detectado: pregunta_programa


Ejemplo 3

Mensaje:
"¿Cómo hago que un router de LangGraph reintente un nodo cuando falla
la respuesta del LLM?"

sentimiento: neutral
tema_principal: datos_ia
subtema: reintentos en LangGraph
tipo_detectado: pregunta_tecnica


Ejemplo 4

Mensaje:
"Mi aplicación funciona localmente pero falla al desplegarla en una
instancia remota."

sentimiento: neutral
tema_principal: cloud_infraestructura
subtema: fallo de despliegue remoto
tipo_detectado: comentario


Ejemplo 5

Mensaje:
"El servidor está muy activo y se nota el compromiso del equipo."

sentimiento: positivo
tema_principal: comunidad
subtema: actividad de la comunidad
tipo_detectado: comentario


Ejemplo 6

Mensaje:
"Excelente iniciativa, ojalá este tipo de comunidades siga creciendo."

sentimiento: positivo
tema_principal: comunidad
subtema: crecimiento de la comunidad
tipo_detectado: comentario


Ejemplo 7

Mensaje:
"El acompañamiento del mentor fue clave para entender conceptos que
antes me costaban."

sentimiento: positivo
tema_principal: mentoria
subtema: comprensión con mentoría
tipo_detectado: testimonio


Ejemplo 8

Mensaje:
"Me gustó mucho la orientación del mentor."

sentimiento: positivo
tema_principal: mentoria
subtema: orientación del mentor
tipo_detectado: comentario


Ejemplo 9

Mensaje:
"Sería genial tener más talleres sobre despliegue de modelos en la nube."

sentimiento: neutral
tema_principal: cloud_infraestructura
subtema: talleres de despliegue
tipo_detectado: feedback


Ejemplo 10

Mensaje:
"Sugiero agregar ejercicios antes del módulo de estructuras de datos."

sentimiento: neutral
tema_principal: programacion
subtema: ejercicios de estructuras de datos
tipo_detectado: feedback


# METADATOS

También recibirás:

- origen
- canal
- idioma

Estos campos proporcionan contexto, pero no constituyen evidencia semántica
suficiente para modificar la clasificación del mensaje.

No infieras intención, sentimiento o tema únicamente por el canal,
la plataforma de origen o el idioma.

# DETECCIÓN SEMÁNTICA DE SPAM

La detección de spam es independiente del sentimiento,
tema, subtema y tipo_detectado.

Devuelve siempre:
- es_spam_detectado: true o false
- motivo_spam: explicación breve o null

Marca es_spam_detectado = true cuando exista evidencia
semántica de promoción no solicitada, captación,
engaño, oferta dudosa o comportamiento equivalente.

Ejemplo de spam:
"¡Gana 500 dólares diarios sin experiencia!
Escríbeme por privado para comenzar."

No clasifiques como spam únicamente por mencionar:
- dinero, dólares o salarios;
- precios de certificaciones;
- costos de servicios cloud;
- oportunidades laborales;
- fraudes o estafas.

Ejemplos legítimos:
- Un estudiante advierte a otros sobre una estafa y cita su mensaje.
- Una persona cuenta que consiguió empleo y menciona su salario.
- Un estudiante pregunta cuánto cuesta un examen de certificación.
- Una persona explica cómo identificar una oferta fraudulenta.

Evalúa la intención y el contexto completo del mensaje.

Una queja no es captación. Distingue lo que la persona HACE en su mensaje de
lo que relata que otras personas hicieron. Mencionar una convocatoria, pedir
el contacto de un mentor o buscar apoyo entre compañeros no ofrece ni
promociona un servicio. Frustración, crítica y falta de organización no son
evidencia de spam, aunque el tono sea muy negativo.
Para marcar true identifica una oferta, promoción no solicitada, captación o
engaño realizado por el emisor; el motivo debe señalar esa evidencia concreta.
No inventes una intención comercial a partir de una petición de ayuda.

Contrastes de quejas legítimas (es_spam_detectado=false, motivo_spam=null):
- "Nos convocaron a ayudar sin decir qué había que hacer, fue un desastre. Publiquen las tareas antes de pedir voluntarios."
  Relata una convocatoria y pide mejorarla; no está captando voluntarios.
- "Ya me harté de escribir a sitios donde nadie responde. cuál es el canal del curso para contactar a mi mentor."
  Solicita un canal de soporte; no promueve sitios externos.
- "Ya me cansé de buscar a quién preguntar. el programa tiene algún espacio del grupo para pedir apoyo entre compañeros?"
  Pregunta por apoyo disponible; no vende ni recluta.
- "Cuidado con el mensaje que promete 500 dólares diarios. Es una estafa."
  Es una advertencia CONTRA una oferta, no una oferta del emisor. Devuelve
  false y null aunque cite cantidades o palabras usadas por un estafador.

En cambio, "Olvídense del curso: compren mi mentoría privada, descuento solo
hoy. Escríbanme por privado para pagar." sí es promoción no solicitada y
captación comercial. Mantén es_spam_detectado=true con un motivo concreto.
No conviertas estos contrastes en una lista blanca de palabras: una solicitud
de ayuda puede ser spam si además incluye una oferta engañosa o captación real.

Si es_spam_detectado = true:
- motivo_spam debe explicar brevemente la evidencia.
- No inventes motivos que el texto no sustente.

Si es_spam_detectado = false:
- motivo_spam debe ser null.

No crees una categoría de sentimiento llamada spam.
No utilices tipo_detectado como sustituto de esta señal.
Comprobación final obligatoria: si el mensaje denuncia, rechaza o advierte
contra una oferta ajena sin ofrecerla al lector, es_spam_detectado=false.
No escribas motivos contradictorios como "promueve advertencia sobre estafa":
advertir contra un engaño no es promoverlo.

Los ejemplos antiguos del prompt pueden mostrar solo las
cinco dimensiones originales. Independientemente de ello,
la respuesta final debe incluir siempre los seis campos:
sentimiento, tema_principal, subtema, tipo_detectado,
es_spam_detectado y motivo_spam.

# VERIFICACIÓN FINAL

Antes de responder, comprueba mentalmente:

1. ¿El sentimiento refleja una valoración realmente expresada?
2. ¿La intensidad está justificada y no exagerada?
3. ¿El tema representa el objeto central y no un elemento contextual?
4. ¿Elegí datos_ia, programacion o cloud_infraestructura según el objeto real?
5. ¿El subtema es breve y no introduce información?
6. ¿El tipo_detectado describe la función comunicativa principal?
7. ¿Estoy distinguiendo una experiencia con impacto concreto de un simple elogio?
8. ¿La detección de spam considera la intención completa
   y el motivo_spam es consistente con es_spam_detectado?

No inventes información y no utilices una dimensión para deducir
automáticamente otra.
            """,
        ),
        (
            "user",
            """
Analiza la siguiente interacción:

Origen: {origen}
Canal: {canal}
Idioma: {idioma}

Mensaje:
{texto}
            """,
        ),
    ]
)


template_analisis_lote = ChatPromptTemplate.from_messages(
    [
        template_analisis.messages[0],
        (
            "user",
            """
Analiza cada mensaje del siguiente JSON de forma independiente.

Devuelve exactamente un resultado por mensaje y conserva su `id`
sin modificarlo.

No mezcles información entre interacciones.
No omitas IDs.
No inventes IDs.
No utilices la clasificación de un mensaje para influir en otro.

Mensajes:
{mensajes_json}
            """,
        ),
    ]
)
