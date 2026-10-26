"""Expectativas editoriales parciales: no adjudican campos ambiguos."""

import json
from pathlib import Path


# Los reportes de fallos son feedback según la frontera editorial acordada.
# 0459 y 0495 eran testimonio en la evaluación anterior: es una readjudicación,
# no una mejora atribuible al modelo.
MUESTRA = {
    "0029": {"tipo_detectado": "feedback", "sentimiento": "muy_negativo"},
    "0065": {"tipo_detectado": "feedback", "sentimiento": "positivo"},
    "0106": {"tipo_detectado": "feedback", "sentimiento": "negativo"},
    "0114": {"tipo_detectado": "pregunta_programa"},
    "0137": {"tipo_detectado": "feedback", "sentimiento": "negativo"},
    "0187": {"tipo_detectado": "feedback", "tema_principal": "aprendizaje"},
    "0197": {"tipo_detectado": "testimonio", "sentimiento": "positivo"},
    "0201": {"tipo_detectado": "feedback", "tema_principal": "plataforma"},
    "0246": {"tipo_detectado": "feedback", "tema_principal": "datos_ia"},
    "0268": {"tipo_detectado": "pregunta_programa", "tema_principal": "programa_hackathon"},
    "0287": {"sentimiento": "negativo"},
    "0326": {"tipo_detectado": "pregunta_programa", "tema_principal": "certificacion"},
    "0369": {"tipo_detectado": "feedback", "sentimiento": "negativo"},
    "0379": {"tipo_detectado": "pregunta_programa", "tema_principal": "programa_hackathon"},
    "0383": {"tipo_detectado": "pregunta_programa", "sentimiento": "positivo"},
    "0403": {"tipo_detectado": "feedback", "tema_principal": "empleabilidad"},
    "0406": {"tipo_detectado": "feedback"},
    "0423": {"tipo_detectado": "pregunta_programa"},
    "0459": {"tipo_detectado": "feedback", "tema_principal": "cloud_infraestructura"},
    "0495": {"tipo_detectado": "feedback", "tema_principal": "certificacion"},
    "0497": {"tipo_detectado": "pregunta_programa"},
    "0511": {"tipo_detectado": "pregunta_programa", "tema_principal": "programa_hackathon"},
    "0513": {"tipo_detectado": "pregunta_programa", "tema_principal": "mentoria"},
    "0514": {"tipo_detectado": "pregunta_programa", "tema_principal": "mentoria"},
    "0517": {"tipo_detectado": "pregunta_programa"},
    "0559": {"tipo_detectado": "testimonio", "tema_principal": "cloud_infraestructura"},
    "0561": {"tipo_detectado": "feedback", "tema_principal": "plataforma"},
}

CONTROLES = [
    ("control_entrega", "¿El programa permite entregar el proyecto en pareja o exige una entrega individual?",
     {"tipo_detectado": "pregunta_programa", "tema_principal": "programa_hackathon"}),
    ("control_volumen", "¿Cómo configuro un volumen persistente para no perder los datos de mi contenedor?",
     {"tipo_detectado": "pregunta_tecnica", "tema_principal": "cloud_infraestructura"}),
    ("control_mentor", "¿Cómo solicito una sesión con mi mentor?",
     {"tipo_detectado": "pregunta_programa", "tema_principal": "mentoria"}),
    ("control_certificacion", "¿Dónde consulto los requisitos para rendir el examen de certificación?",
     {"tipo_detectado": "pregunta_programa", "tema_principal": "certificacion"}),
    ("control_sugerencia", "Me gustó el simulacro de entrevista laboral, pero sugiero otra ronda para practicar las respuestas.",
     {"tipo_detectado": "feedback", "tema_principal": "empleabilidad"}),
    ("control_logro", "Por fin desplegué mi contenedor en el servidor y pude abrirlo desde otra máquina, estoy emocionada.",
     {"tipo_detectado": "testimonio", "tema_principal": "cloud_infraestructura"}),
    ("control_elogio", "Gracias por la explicación, estuvo excelente.",
     {"tipo_detectado": "comentario", "sentimiento": "positivo"}),
    ("control_modelo", "¿Cómo ajusto el umbral de clasificación para recuperar más ejemplos de la clase minoritaria?",
     {"tipo_detectado": "pregunta_tecnica", "tema_principal": "datos_ia"}),
]

IDS_PENDIENTES = {"0106", "0369", "0383", "0403", "0459", "0495", "0513"}

CONTRASTES_PENDIENTES = [
    ("contraste_fallo", "Mi despliegue se interrumpe y tengo que reiniciar el servicio manualmente. ¿Le ocurre a alguien más?",
     {"tipo_detectado": "feedback", "tema_principal": "cloud_infraestructura"}),
    ("contraste_aprendizaje", "Tras perder mi primer despliegue, aprendí a configurar respaldos. Ahora los pruebo cada semana y recuperé mi proyecto sin ayuda.",
     {"tipo_detectado": "testimonio", "tema_principal": "cloud_infraestructura"}),
    ("contraste_confirmacion", "¿Dónde puedo consultar la confirmación de mi reserva del aula?",
     {"tipo_detectado": "pregunta_programa"}),
    ("contraste_correccion", "Las reservas del aula no indican dónde reunirnos; por favor incluyan la ubicación al confirmarlas.",
     {"tipo_detectado": "feedback"}),
]


def casos_semanticos():
    archivo = Path(__file__).resolve().parents[1] / "src" / "datos" / "casos_conciliados_propuestos.json"
    documento = json.loads(archivo.read_text(encoding="utf-8"))
    por_id = {caso["id"]: caso["texto"] for caso in documento["casos"]}
    return [
        (f"syn-eval-{numero}", por_id[f"syn-eval-{numero}"], {**esperado, "es_spam_detectado": False})
        for numero, esperado in MUESTRA.items()
    ] + [
        (identificador, texto, {**esperado, "es_spam_detectado": False})
        for identificador, texto, esperado in CONTROLES
    ]


def casos_pendientes():
    return [
        caso for caso in casos_semanticos()
        if caso[0].removeprefix("syn-eval-") in IDS_PENDIENTES
        or caso[0].startswith("control_")
    ] + [
        (identificador, texto, {**esperado, "es_spam_detectado": False})
        for identificador, texto, esperado in CONTRASTES_PENDIENTES
    ]
