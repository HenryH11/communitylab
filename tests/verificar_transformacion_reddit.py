"""Pruebas rapidas (sin red) del parseo y transformacion de feeds RSS de Reddit.

Ejecutar (desde la raiz del repo): python tests/verificar_transformacion_reddit.py

Los fixtures de XML replican la estructura real de los feeds Atom de Reddit
(namespace, author/name, content HTML, id con fullname t1_/t3_) — confirmada
contra r/webdev real en desarrollo (ver docs/fuentes_de_datos_acceso.md y el
snapshot de evidencia en tests/fixtures/prueba_reddit_controlada.json).
"""

import sys
from pathlib import Path

# src/data no es un paquete instalable (sin __init__.py/setup.py); se agrega
# su ruta a sys.path para poder importar ingesta_reddit.py directamente.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "data"))

from ingesta_reddit import (  # noqa: E402
    comentario_fue_eliminado,
    es_comentario,
    parsear_entradas_atom,
    transformar_entrada,
)

FIXTURE_POSTS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>New posts</title>
  <entry>
    <author><name>/u/autor_post</name></author>
    <content type="html">&lt;p&gt;Cuerpo del post&lt;/p&gt;</content>
    <id>t3_abc123</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/algun_post/"/>
    <updated>2026-09-16T09:00:00+00:00</updated>
  </entry>
</feed>
"""

FIXTURE_COMENTARIOS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Comments on: algun post</title>
  <entry>
    <author><name>/u/dev_user_1</name></author>
    <content type="html">&lt;div class="md"&gt;&lt;p&gt;Me sirvio mucho este framework.&lt;/p&gt;&lt;/div&gt;</content>
    <id>t1_def456</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/algun_post/def456/"/>
    <updated>2026-09-16T09:15:00Z</updated>
  </entry>
  <entry>
    <author><name>/u/dev_user_2</name></author>
    <content type="html">&lt;div class="md"&gt;&lt;p&gt;Como configuro webpack para esto?&lt;/p&gt;&lt;/div&gt;</content>
    <id>t1_ghi789</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/algun_post/ghi789/"/>
    <updated>2026-09-16T09:20:00Z</updated>
  </entry>
  <entry>
    <author><name>/u/[deleted]</name></author>
    <content type="html">&lt;div class="md"&gt;&lt;p&gt;[deleted]&lt;/p&gt;&lt;/div&gt;</content>
    <id>t1_jkl000</id>
    <link href="https://www.reddit.com/r/webdev/comments/abc123/algun_post/jkl000/"/>
    <updated>2026-09-16T09:25:00Z</updated>
  </entry>
</feed>
"""


def test_parsear_entradas_atom_extrae_posts():
    entradas = parsear_entradas_atom(FIXTURE_POSTS)
    assert len(entradas) == 1
    assert entradas[0]["fullname"] == "t3_abc123"
    assert entradas[0]["autor"] == "autor_post"
    assert entradas[0]["texto"] == "Cuerpo del post"
    assert not es_comentario(entradas[0])


def test_parsear_entradas_atom_extrae_comentarios():
    entradas = parsear_entradas_atom(FIXTURE_COMENTARIOS)
    assert len(entradas) == 3
    assert all(es_comentario(e) for e in entradas)
    assert entradas[0]["fullname"] == "t1_def456"
    assert entradas[0]["autor"] == "dev_user_1"
    assert entradas[0]["texto"] == "Me sirvio mucho este framework."


def test_comentario_fue_eliminado_detecta_borrado():
    entradas = parsear_entradas_atom(FIXTURE_COMENTARIOS)
    borrado = next(e for e in entradas if e["fullname"] == "t1_jkl000")
    assert comentario_fue_eliminado(borrado) is True


def test_comentario_normal_no_se_descarta():
    entradas = parsear_entradas_atom(FIXTURE_COMENTARIOS)
    normal = next(e for e in entradas if e["fullname"] == "t1_def456")
    assert comentario_fue_eliminado(normal) is False


def test_transformar_entrada_comentario_normal():
    entradas = parsear_entradas_atom(FIXTURE_COMENTARIOS)
    normal = next(e for e in entradas if e["fullname"] == "t1_def456")
    resultado = transformar_entrada(normal, "webdev")
    assert resultado["id"] == "reddit-t1_def456"
    assert resultado["autor"] == "dev_user_1"
    assert resultado["canal"] == "r/webdev"
    assert resultado["tipo"] == "comentario"
    assert resultado["fecha"] == "2026-09-16T09:15:00Z"
    assert resultado["idioma"] == "es"  # default actual (r/programacion es hispanohablante)


def test_transformar_entrada_respeta_idioma_explicito():
    entradas = parsear_entradas_atom(FIXTURE_COMENTARIOS)
    normal = next(e for e in entradas if e["fullname"] == "t1_def456")
    resultado = transformar_entrada(normal, "webdev", idioma="en")
    assert resultado["idioma"] == "en"


def test_transformar_entrada_detecta_pregunta_tecnica():
    entradas = parsear_entradas_atom(FIXTURE_COMENTARIOS)
    pregunta = next(e for e in entradas if e["fullname"] == "t1_ghi789")
    resultado = transformar_entrada(pregunta, "webdev")
    assert resultado["tipo"] == "pregunta_tecnica"


def test_transformar_entrada_sin_autor_usa_placeholder():
    entrada_sin_autor = {"fullname": "t1_zzz999", "autor": None, "texto": "Hola", "fecha_raw": ""}
    resultado = transformar_entrada(entrada_sin_autor, "webdev")
    assert resultado["autor"] == "usuario_eliminado"


if __name__ == "__main__":
    test_parsear_entradas_atom_extrae_posts()
    test_parsear_entradas_atom_extrae_comentarios()
    test_comentario_fue_eliminado_detecta_borrado()
    test_comentario_normal_no_se_descarta()
    test_transformar_entrada_comentario_normal()
    test_transformar_entrada_respeta_idioma_explicito()
    test_transformar_entrada_detecta_pregunta_tecnica()
    test_transformar_entrada_sin_autor_usa_placeholder()
    print("OK: todas las pruebas de parseo/transformacion RSS pasaron.")
