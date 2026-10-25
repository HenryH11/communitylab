"""Casos sintéticos compartidos por pruebas estructurales y evaluación real."""

CASOS = [
    ("queja_convocatoria", "Nos convocaron a ayudar sin decir qué había que hacer, fue un desastre. Publiquen las tareas antes de pedir voluntarios.", False),
    ("contactar_mentor", "Ya me harté de escribir a sitios donde nadie responde. cuál es el canal del curso para contactar a mi mentor.", False),
    ("apoyo_companeros", "Ya me cansé de buscar a quién preguntar. el programa tiene algún espacio del grupo para pedir apoyo entre compañeros?", False),
    ("advertencia_fraude", "Cuidado con el mensaje que promete 500 dólares diarios. Es una estafa.", False),
    ("costo_examen", "¿Cuánto cuesta el examen OCI y los servicios cloud?", False),
    ("captacion_ingresos", "Gana 500 dólares diarios sin experiencia. Escríbeme al privado para comenzar.", True),
    ("promocion_no_solicitada", "Olvídense del curso: compren mi mentoría privada, descuento solo hoy. Escríbanme por privado para pagar.", True),
    ("queja_nueva", "Llevo días esperando respuesta del equipo y estoy frustrada. ¿Dónde puedo pedir ayuda con mi inscripción?", False),
    ("denuncia_nueva", "No envíen dinero a quien ofrece certificados por mensaje privado; ese anuncio es fraudulento.", False),
    ("captacion_con_ayuda", "¿Necesitas ayuda con el curso? Págame por privado y te garantizo el certificado sin rendir el examen.", True),
]
