"""Pruebas sin red para analizar y transformar canales RSS/Atom de Reddit.

Los ejemplos XML reproducen la estructura Atom de Reddit: espacio de nombres,
autor, contenido HTML e identificadores t1_/t3_. La estructura se confirmó
contra r/webdev y r/programacion reales (ver docs/fuentes_de_datos_acceso.md
y tests/fixtures/prueba_reddit_controlada.json).
"""

from src.datos.ingesta_reddit import (
    comentario_fue_eliminado,
    es_comentario,
    parsear_entradas_atom,
    transformar_entrada,
)

EJEMPLO_PUBLICACIONES = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Publicaciones nuevas</title>
  <entry>
    <author><name>/u/autor_publicacion</name></author>
    <content type="html">&lt;p&gt;Cuerpo de la publicación&lt;/p&gt;</content>
    <id>t3_abc123</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/alguna_publicacion/"/>
    <updated>2026-09-16T09:00:00+00:00</updated>
  </entry>
</feed>
"""

EJEMPLO_COMENTARIOS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Comentarios de: alguna publicación</title>
  <entry>
    <author><name>/u/dev_user_1</name></author>
    <content type="html">&lt;div class="md"&gt;&lt;p&gt;Me sirvió mucho esta herramienta.&lt;/p&gt;&lt;/div&gt;</content>
    <id>t1_def456</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/alguna_publicacion/def456/"/>
    <updated>2026-09-16T09:15:00Z</updated>
  </entry>
  <entry>
    <author><name>/u/dev_user_2</name></author>
    <content type="html">&lt;div class="md"&gt;&lt;p&gt;¿Cómo configuro webpack para esto?&lt;/p&gt;&lt;/div&gt;</content>
    <id>t1_ghi789</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/alguna_publicacion/ghi789/"/>
    <updated>2026-09-16T09:20:00Z</updated>
  </entry>
  <entry>
    <author><name>/u/[deleted]</name></author>
    <content type="html">&lt;div class="md"&gt;&lt;p&gt;[deleted]&lt;/p&gt;&lt;/div&gt;</content>
    <id>t1_jkl000</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/alguna_publicacion/jkl000/"/>
    <updated>2026-09-16T09:25:00Z</updated>
  </entry>
</feed>
"""


def test_parsear_entradas_atom_extrae_publicaciones():
    entradas = parsear_entradas_atom(EJEMPLO_PUBLICACIONES)
    assert len(entradas) == 1
    assert entradas[0]["id_completo"] == "t3_abc123"
    assert entradas[0]["autor"] == "autor_publicacion"
    assert entradas[0]["texto"] == "Cuerpo de la publicación"
    assert not es_comentario(entradas[0])


def test_parsear_entradas_atom_extrae_comentarios():
    entradas = parsear_entradas_atom(EJEMPLO_COMENTARIOS)
    assert len(entradas) == 3
    assert all(es_comentario(e) for e in entradas)
    assert entradas[0]["id_completo"] == "t1_def456"
    assert entradas[0]["autor"] == "dev_user_1"
    assert entradas[0]["texto"] == "Me sirvió mucho esta herramienta."


def test_comentario_fue_eliminado_detecta_borrado():
    entradas = parsear_entradas_atom(EJEMPLO_COMENTARIOS)
    borrado = next(e for e in entradas if e["id_completo"] == "t1_jkl000")
    assert comentario_fue_eliminado(borrado) is True


def test_comentario_normal_no_se_descarta():
    entradas = parsear_entradas_atom(EJEMPLO_COMENTARIOS)
    normal = next(e for e in entradas if e["id_completo"] == "t1_def456")
    assert comentario_fue_eliminado(normal) is False


def test_transformar_entrada_comentario_normal():
    entradas = parsear_entradas_atom(EJEMPLO_COMENTARIOS)
    normal = next(e for e in entradas if e["id_completo"] == "t1_def456")
    resultado = transformar_entrada(normal, "webdev")
    assert resultado["id"] == "reddit-t1_def456"
    assert resultado["autor"] == "dev_user_1"
    assert resultado["canal"] == "r/webdev"
    assert resultado["tipo"] == "comentario"
    assert resultado["fecha"] == "2026-09-16T09:15:00Z"
    assert resultado["idioma"] == "es"  # default actual (r/programacion es hispanohablante)


def test_transformar_entrada_respeta_idioma_explicito():
    entradas = parsear_entradas_atom(EJEMPLO_COMENTARIOS)
    normal = next(e for e in entradas if e["id_completo"] == "t1_def456")
    resultado = transformar_entrada(normal, "webdev", idioma="en")
    assert resultado["idioma"] == "en"


def test_transformar_entrada_detecta_pregunta_tecnica():
    entradas = parsear_entradas_atom(EJEMPLO_COMENTARIOS)
    pregunta = next(e for e in entradas if e["id_completo"] == "t1_ghi789")
    resultado = transformar_entrada(pregunta, "webdev")
    assert resultado["tipo"] == "pregunta_tecnica"


def test_transformar_entrada_sin_autor_usa_placeholder():
    entrada_sin_autor = {"id_completo": "t1_zzz999", "autor": None, "texto": "Hola", "fecha_original": ""}
    resultado = transformar_entrada(entrada_sin_autor, "webdev")
    assert resultado["autor"] == "usuario_eliminado"
