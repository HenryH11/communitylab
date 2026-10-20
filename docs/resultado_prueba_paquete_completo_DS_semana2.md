================================================================================================================================
# El equipo ejecutó una prueba y estos fueron los resultados:

(.venv) PS D:\ALURA\HackatonG39-Semana1> python -B -m pytest tests/integracion/prueba_paquete_completo_datos.py -v -s -p no:cacheprovider
==================================================================== test session starts =====================================================================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- D:\ALURA\HackatonG39-Semana1\.venv\Scripts\python.exe
rootdir: D:\ALURA\HackatonG39-Semana1
plugins: anyio-4.15.1, langsmith-0.14.1
collected 1 item

tests/integracion/prueba_paquete_completo_datos.py::test_paquete_completo_datos_a_ciencia_datos
========================================================================================
PAQUETE RECIBIDO DE DATOS
========================================================================================
Estados recibidos: 23
Ciclos planificados: [(0, 12), (1, 11)]
IDs planificados: 23
IDs pendientes: 0
IDs elegibles para contenido: 14

========================================================================================
EJECUTANDO DATA SCIENCE + GEMINI + LANGGRAPH
========================================================================================

========================================================================================
INTERACCIÓN 1/23: int-001
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Camila Restrepo
Canal: #logros-y-empleos
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: Comunidad, gracias a este programa conseguí mi primer trabajo como analista de datos en menos de 3 meses. El proyecto final de mi portfolio fue clave en la entrevista técnica.
Tipo original: testimonio
Score relevancia: 90
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 20, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: primer trabajo analista de datos
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Camila consigue su primer empleo como analista de datos tras participar en el programa
resumen: Camila consiguió su primer trabajo como analista de datos en un plazo menor a tres meses tras participar en el programa. Según su testimonio, el proyecto final incluido en su portfolio fue clave durante la entrevista técnica.

[linkedin]
titulo: Camila Restrepo alcanza su meta y consigue su primer rol como analista de datos
contenido: Quiero compartir una gran noticia con toda la comunidad. Camila Restrepo consiguió su primer trabajo como analista de datos en menos de tres meses gracias al programa. Durante su proceso, el proyecto final que incluyó en su portfolio fue una herramienta clave para destacar en la entrevista técnica. ¡Muchas felicidades por este gran paso profesional, Camila! #AnalistaDeDatos #Empleabilidad #Portfolio #ComunidadONE
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 2/23: int-002
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Diego Fernández
Canal: #dudas-langgraph
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: Tengo dudas sobre cómo estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. ¿Alguien tiene un ejemplo práctico de router?
Tipo original: pregunta_tecnica
Score relevancia: 80
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 10, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: datos_ia
Subtema: nodos condicionales LangGraph
Tipo detectado: pregunta_tecnica

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['preguntas_frecuentes']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[preguntas_frecuentes]
tema: Tip rápido: nodos condicionales y reintentos en LangGraph
respuesta: Para estructurar un nodo condicional que maneje reintentos según la respuesta de un LLM, se utiliza una función de enrutamiento (router) que evalúael estado actual y decide si el flujo debe ir hacia un nodo de corrección o continuar. Si necesitas un ejemplo preciso, es útil conocer la estructura actual de tu estado y los criterios específicos para determinar cuándo un resultado requiere reintento.

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 3/23: int-003
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Andrés Kuri
Canal: #logros-y-empleos
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: Pasé de no saber programar a construir mi primer modelo de clasificación en 6 semanas, muy agradecido con la comunidad y los mentores.
Tipo original: testimonio
Score relevancia: 75
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 5, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: aprendizaje
Subtema: modelo de clasificación
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Andrés construye su primer modelo de clasificación en seis semanas
resumen: Andrés pasó de no saber programar a construir su primer modelo de clasificación en un periodo de seis semanas. La autora señala que se encuentra muy agradecido con la comunidad y los mentores por este proceso.

[linkedin]
titulo: De cero a mi primer modelo de clasificación en 6 semanas
contenido: Comparto un gran logro personal. Andrés Kuri logró pasar de no saber programar a construir su primer modelo de clasificación en tan solo 6 semanas.Este avance refleja su dedicación y el valioso acompañamiento de los mentores y la comunidad. ¡Felicitaciones por este gran paso! #Programacion #MachineLearning #ComunidadONE #Mentoria
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 4/23: int-004
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Sofía Torres
Canal: #soporte-tecnico
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: ¿El certificado final tiene costo adicional o está incluido en el programa?
Tipo original: comentario
Score relevancia: 37
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 12, 'palabras_clave': 5, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: certificacion
Subtema: costo del certificado
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 5/23: int-005
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Valentina Ríos
Canal: #general
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: El servidor de Discord se siente muy activo, se nota el compromiso del equipo organizador.
Tipo original: comentario
Score relevancia: 35
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 15, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: positivo
Tema principal: comunidad
Subtema: actividad y compromiso
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 6/23: int-006
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Ricardo Mena
Canal: #feedback-programa
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: Sería genial tener más talleres prácticos sobre despliegue de modelos en la nube antes del hackathon.
Tipo original: feedback
Score relevancia: 56
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 30, 'longitud': 16, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: cloud_infraestructura
Subtema: despliegue de modelos
Tipo detectado: feedback

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 7/23: int-007
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Héctor Prado
Canal: #dudas-hackathon
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: ¿Hasta cuándo puedo inscribirme al hackathon si me integro después de la semana 0?
Tipo original: comentario
Score relevancia: 34
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 14, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: programa_hackathon
Subtema: fechas de inscripcion
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 8/23: int-008
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Daniela Uriarte
Canal: #general
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: Buena onda el equipo de mentores, siempre responden rápido en el canal de dudas.
Tipo original: comentario
Score relevancia: 39
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 14, 'palabras_clave': 5, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: positivo
Tema principal: mentoria
Subtema: respuesta de mentores
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 9/23: int-022
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Mariana Souza
Canal: #logros-y-empleos
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: Comunidad, quede seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI que construi en mi portfolio marco toda la diferencia en la entrevista tecnica. Muy agradecida con la comunidad por todo el apoyo!
Tipo original: testimonio
Score relevancia: 95
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 25, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: Desarrolladora Junior de IA
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Mariana Souza es seleccionada como Desarrolladora Junior de IA
resumen: Mariana Souza fue seleccionada para el puesto de Desarrolladora Junior de IA y agradeció el apoyo de la comunidad. Según su testimonio, el proyecto del curso de LangChain y OCI que construyó en su portfolio marcó toda la diferencia en la entrevista técnica.

[linkedin]
titulo: De un proyecto en el portfolio a un nuevo rol como Desarrolladora Junior de IA
contenido: ¡Qué gran noticia nos comparte Mariana Souza! Ha sido seleccionada para el puesto de Desarrolladora Junior de IA. 🚀 Nos cuenta que el proyecto delcurso de LangChain y OCI que sumó a su portfolio marcó toda la diferencia durante su entrevista técnica. Agradecemos su confianza y celebramos su constancia. ¡Mucho éxito en esta nueva etapa profesional! #LangChain #OCI #InteligenciaArtificial #DesarrolloProfesional
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 10/23: int-023
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Lucas Albuquerque
Canal: #dudas-langgraph
Origen: Discord_Grupo_ONE_G10
Idioma: es
Texto: Tengo dudas sobre como estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. Alguien tiene un ejemplo practico de router?
Tipo original: pregunta_tecnica
Score relevancia: 80
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 10, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: datos_ia
Subtema: nodos condicionales LangGraph
Tipo detectado: pregunta_tecnica

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['preguntas_frecuentes']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[preguntas_frecuentes]
tema: Tip Rápido: estructuración de nodos condicionales para reintentos en LangGraph
respuesta: Para implementar un router que maneje reintentos basados en la respuesta de un LLM, debes definir una función condicional que evalúe el estado actual (como el resultado o la validez de la salida) y devuelva el nombre del siguiente nodo a ejecutar, ya sea el nodo de reintento o el siguiente paso del flujo.Como no se especificó la estructura exacta del grafo ni el criterio de validación, se recomienda revisar que el estado contenga la información necesaria para que la función de enrutamiento tome la decisión correcta.

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 11/23: int-009
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Mariana Botero
Canal: #post-lanzamiento-programa
Origen: LinkedIn_ONE_G10
Idioma: es
Texto: Excelente iniciativa, ojalá sigan creciendo este tipo de comunidades en Latinoamérica.
Tipo original: comentario
Score relevancia: 31
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 11, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: positivo
Tema principal: comunidad
Subtema: crecimiento de comunidades
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 12/23: int-010
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Pedro Álvarez
Canal: #post-lanzamiento-programa
Origen: LinkedIn_ONE_G10
Idioma: es
Texto: Interesante propuesta, ¿tienen alguna alianza con empresas para prácticas profesionales?
Tipo original: comentario
Score relevancia: 30
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 10, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: empleabilidad
Subtema: alianzas para practicas
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 13/23: int-011
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Gabriela Núñez
Canal: #historias-egresados
Origen: LinkedIn_ONE_G10
Idioma: es
Texto: El networking que generé en este programa me abrió puertas para colaborar en proyectos open source.
Tipo original: testimonio
Score relevancia: 71
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 16, 'palabras_clave': 5, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: positivo
Tema principal: comunidad
Subtema: networking en proyectos open source
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Gabriela participa en proyectos open source tras generar networking en el programa
resumen: Gabriela colabora en proyectos open source tras haber participado en el programa. La autora señala que el networking generado durante el mismo le abrió puertas para estas colaboraciones.

[linkedin]
titulo: De la comunidad a la colaboración abierta: el poder del networking
contenido: Comparto una gran noticia sobre el camino de Gabriela Núñez. Las conexiones y el networking que logró generar a través del programa le abrieron laspuertas para comenzar a colaborar activamente en proyectos open source. Un claro ejemplo de cómo la vinculación dentro de nuestra comunidad impulsa nuevas oportunidades de crecimiento y participación colectiva. #Networking #OpenSource #Colaboracion
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 14/23: int-012
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Felipe Contreras
Canal: #historias-egresados
Origen: LinkedIn_ONE_G10
Idioma: es
Texto: Gracias a este bootcamp cambié de carrera a los 35 años y hoy trabajo en análisis de datos en una fintech.
Tipo original: testimonio
Score relevancia: 80
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 10, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: empleabilidad
Subtema: cambio de carrera en fintech
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Felipe Contreras cambia de carrera y trabaja en análisis de datos
resumen: A los 35 años, Felipe logró cambiar de carrera y actualmente trabaja en análisis de datos en una fintech. Según su testimonio, este resultado ocurrióa través de su participación en el bootcamp.

[linkedin]
titulo: Un nuevo comienzo profesional a los 35 años en el sector fintech
contenido: Quiero compartir una gran noticia. Gracias a este bootcamp, Felipe Contreras logró hacer un cambio de carrera a los 35 años y hoy se encuentra trabajando en análisis de datos en una fintech. ¡Muchas felicidades por este gran paso! #CambioDeCarrera #AnalisisDeDatos #Fintech
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 15/23: int-013
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Javier Fernández
Canal: #formulario-dudas
Origen: Formulario_Feedback_ONE_G10
Idioma: es
Texto: ¿Cómo puedo acceder a las grabaciones de las clases si me perdí una sesión en vivo?
Tipo original: comentario
Score relevancia: 36
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 16, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: programa_hackathon
Subtema: grabaciones de clases en vivo
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 16/23: int-014
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Laura Ocampo
Canal: #formulario-testimonios
Origen: Formulario_Feedback_ONE_G10
Idioma: es
Texto: El acompañamiento del mentor fue clave para entender conceptos de machine learning que antes me costaban mucho.
Tipo original: testimonio
Score relevancia: 72
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 17, 'palabras_clave': 5, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: positivo
Tema principal: mentoria
Subtema: conceptos de machine learning
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Laura comprende conceptos avanzados de machine learning con apoyo de mentoría
resumen: Laura logró comprender conceptos de machine learning que antes le resultaban complejos. Según su testimonio, el acompañamiento del mentor contribuyó a este resultado.

[linkedin]
titulo: De la confusión a la claridad en Machine Learning gracias a la mentoría
contenido: Quiero compartir la experiencia de Laura Ocampo, quien nos cuenta que el acompañamiento de su mentor fue clave para entender conceptos de machine learning que antes le costaban mucho. 🚀 Un gran ejemplo de cómo la guía adecuada marca la diferencia en el aprendizaje. #MachineLearning #Mentoria #AprendizajeContinuo #Comunidad
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 17/23: int-015
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Carlos Mena
Canal: #formulario-dudas
Origen: Formulario_Feedback_ONE_G10
Idioma: es
Texto: ¿Cuál es la diferencia entre las rutas de Data Analyst y Data Scientist dentro del programa?
Tipo original: comentario
Score relevancia: 36
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 16, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: programa_hackathon
Subtema: rutas de datos del programa
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 18/23: int-016
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Isabel Quiroga
Canal: #formulario-testimonios
Origen: Formulario_Feedback_ONE_G10
Idioma: es
Texto: Nunca pensé que podría aprender SQL y Python al mismo tiempo, pero la metodología del curso lo hizo posible.
Tipo original: testimonio
Score relevancia: 84
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 19, 'palabras_clave': 15, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: aprendizaje
Subtema: SQL y Python simultáneos
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Isabel aprende SQL y Python simultáneamente mediante la metodología del curso
resumen: Isabel logró aprender SQL y Python al mismo tiempo durante su formación. La autora señala que la metodología del curso hizo posible este aprendizaje,algo que ella misma no pensaba que podría lograr.

[linkedin]
titulo: Dominando SQL y Python en paralelo gracias a la metodología adecuada
contenido: Comparto la experiencia de Isabel Quiroga, quien nos demuestra que aprender dos herramientas clave como SQL y Python al mismo tiempo es posible cuando se cuenta con la metodología correcta. ¡Felicitaciones por este gran avance en tu aprendizaje! #SQL #Python #AprendizajeContinuo
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 19/23: int-017
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Marcos Villalba
Canal: categoria-python
Origen: Alura_Forum_ONE_G10
Idioma: es
Texto: Estoy atascado con un error de indentación en un bucle for anidado con pandas, ¿alguien puede revisar mi código en el tópico que abrí?
Tipo original: pregunta_tecnica
Score relevancia: 75
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 5, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: programacion
Subtema: error de indentación en pandas
Tipo detectado: pregunta_tecnica

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['preguntas_frecuentes']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[preguntas_frecuentes]
tema: Tip rápido: corrección de errores de indentación en bucles con pandas
respuesta: Un error de indentación en Python indica que los espacios o tabulaciones no están alineados correctamente en los bloques de código, como los buclesfor anidados. Para solucionarlo, verifica que cada bloque use consistentemente la misma cantidad de espacios y que no mezcles tabulaciones con espacios. Si necesitas ayuda con el código específico, comparte el fragmento exacto y el mensaje de error completo para revisarlo con precisión.

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 20/23: int-018
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Estefanía Roldán
Canal: categoria-data-science
Origen: Alura_Forum_ONE_G10
Idioma: es
Texto: Terminé la formación de Data Science y ya estoy aplicando lo aprendido en un proyecto real de mi trabajo, el foro fue clave para resolver dudas rápido.
Tipo original: testimonio
Score relevancia: 80
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 10, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: muy_positivo
Tema principal: datos_ia
Subtema: aplicación práctica en trabajo real
Tipo detectado: testimonio

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['caso_exito', 'linkedin']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[caso_exito]
titular: Estefanía aplica lo aprendido en la formación de Data Science en un proyecto real
resumen: Estefanía finalizó la formación de Data Science y ya se encuentra aplicando los conocimientos en un proyecto real de su trabajo. Asimismo, la autora señala que el foro fue clave para resolver dudas de manera rápida durante el proceso.

[linkedin]
titulo: De la formación de Data Science al impacto en proyectos reales
contenido: Quiero compartirles que Estefanía Roldán terminó la formación de Data Science y ya está aplicando todo lo aprendido directamente en un proyecto real de su trabajo. En su proceso, el foro fue una herramienta clave para resolver dudas de manera ágil. 🚀 ¡Felicitaciones por llevar la teoría a la práctica tanrápido! #DataScience #FormacionYAccion #ComunidadONE
canal_recomendado: LinkedIn Oficial

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 21/23: int-019
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Joaquín Beltrán
Canal: subcategoria-javascript
Origen: Alura_Forum_ONE_G10
Idioma: es
Texto: Buen material el de la última clase de funciones asíncronas, muy claro con los ejemplos.
Tipo original: comentario
Score relevancia: 35
Incluido sentimiento: True
Elegible contenido: False
Desglose relevancia: {'tipo': 10, 'longitud': 15, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: positivo
Tema principal: programacion
Subtema: funciones asíncronas en JavaScript
Tipo detectado: comentario

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 22/23: int-020
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Lucía Paredes
Canal: categoria-programacion-basica
Origen: Alura_Forum_ONE_G10
Idioma: es
Texto: Sugiero agregar más ejercicios prácticos antes de pasar al módulo de estructuras de datos, se siente un salto grande.
Tipo original: feedback
Score relevancia: 64
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 30, 'longitud': 19, 'palabras_clave': 5, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: programacion
Subtema: ejercicios prácticos de estructuras
Tipo detectado: feedback

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: []

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------
Ninguno

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
INTERACCIÓN 23/23: int-021
========================================================================================
ENTRADA RECIBIDA DE DATOS
----------------------------------------------------------------------------------------
Autor: Tomás Ibáñez
Canal: categoria-front-end
Origen: Alura_Forum_ONE_G10
Idioma: es
Texto: ¿Cuál es la diferencia práctica entre usar Grid y Flexbox para un layout de dashboard? En el tópico nadie me respondió todavía.
Tipo original: pregunta_tecnica
Score relevancia: 70
Incluido sentimiento: True
Elegible contenido: True
Desglose relevancia: {'tipo': 40, 'longitud': 20, 'palabras_clave': 0, 'frescura': 10}

RESULTADO DATA SCIENCE
----------------------------------------------------------------------------------------
Sentimiento: neutral
Tema principal: programacion
Subtema: Grid versus Flexbox
Tipo detectado: pregunta_tecnica

ENRUTAMIENTO LANGGRAPH
----------------------------------------------------------------------------------------
Rutas: ['preguntas_frecuentes']

ACTIVOS GENERADOS
----------------------------------------------------------------------------------------

[preguntas_frecuentes]
tema: Diferencia práctica entre Grid y Flexbox para layouts
respuesta: Flexbox está diseñado principalmente para distribuciones unidimensionales (en una sola fila o columna a la vez), lo que lo hace ideal para alinear elementos dentro de barras de navegación o componentes individuales. CSS Grid, en cambio, está pensado para layouts bidimensionales (filas y columnas simultáneamente), facilitando la estructura general o esqueleto de un dashboard. Para darte una recomendación más precisa sobre cuál usar en tu caso, sería útil conocerla disposición específica de los paneles que deseas lograr.

ERRORES
----------------------------------------------------------------------------------------
[]

========================================================================================
RESUMEN FINAL DATA -> DATA SCIENCE
========================================================================================
Estados recibidos de Datos: 23
Estados procesados por DS: 23
Estados pendientes: 0
Elegibles para contenido: 14
Con activos generados: 12
Con errores: 0

Distribución de sentimientos: {'muy_positivo': 6, 'neutral': 11, 'positivo': 6}
Distribución de temas: {'empleabilidad': 4, 'datos_ia': 3, 'aprendizaje': 2, 'certificacion': 1, 'comunidad': 3, 'cloud_infraestructura': 1, 'programa_hackathon': 3, 'mentoria': 2, 'programacion': 4}
Tipos detectados: {'testimonio': 8, 'pregunta_tecnica': 4, 'comentario': 9, 'feedback': 2}
Rutas ejecutadas: {'caso_exito': 8, 'linkedin': 8, 'preguntas_frecuentes': 4}
Activos generados: {'caso_exito': 8, 'linkedin': 8, 'preguntas_frecuentes': 4}
IDs con activos: ['int-001', 'int-002', 'int-003', 'int-022', 'int-023', 'int-011', 'int-012', 'int-014', 'int-016', 'int-017', 'int-018', 'int-021']
PASSED

====================================================================== warnings summary ======================================================================
.venv\Lib\site-packages\google\genai\types.py:42
  D:\ALURA\HackatonG39-Semana1\.venv\Lib\site-packages\google\genai\types.py:42: DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removalin Python 3.17
    VersionedUnionType = Union[builtin_types.UnionType, _UnionGenericAlias]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================================================== 1 passed, 1 warning in 37.06s ================================================================
