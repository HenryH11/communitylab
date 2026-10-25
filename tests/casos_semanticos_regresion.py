"""Expectativas editoriales parciales: no adjudican campos ambiguos."""

import json
from pathlib import Path


# Solo se exige un valor cuando el texto y las definiciones lo respaldan.
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
    "0459": {"tipo_detectado": "testimonio", "tema_principal": "cloud_infraestructura"},
    "0495": {"tipo_detectado": "testimonio", "tema_principal": "certificacion"},
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
