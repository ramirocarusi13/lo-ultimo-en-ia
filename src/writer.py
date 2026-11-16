"""Claude redacta el carrusel en español a partir de las notas originales."""
from __future__ import annotations

import json

import anthropic

from config import BRAND_NAME, CLAUDE_MODEL, HANDLE
from news import Story

SCHEMA = {
    "type": "object",
    "properties": {
        "skip": {"type": "boolean"},
        "skip_reason": {"type": "string"},
        "headline": {"type": "string"},
        "badge": {"type": "string"},
        "slides": {"type": "array", "items": {"type": "string"}},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "image_prompts": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["skip", "skip_reason", "headline", "badge", "slides", "caption", "hashtags", "image_prompts"],
    "additionalProperties": False,
}

SYSTEM = f"""Sos el editor de "{BRAND_NAME}" ({HANDLE}), una cuenta de Instagram en español
que cuenta noticias de inteligencia artificial de forma simple y directa.

Con las notas que te paso armás un carrusel de 4 imágenes:
- headline: titular de portada, MAYÚSCULAS, 6 a 12 palabras, impactante pero fiel a los hechos.
  Encerrá entre *asteriscos* 2 a 4 palabras clave para resaltarlas en color
  (ej: "EL *CEO DE NVIDIA* RENUNCIA DESPUÉS DE *33 AÑOS*").
- badge: nombre corto de la empresa/producto protagonista (máx 10 caracteres, ej "NVIDIA",
  "OpenAI") o "" si no hay uno claro.
- slides: exactamente 2 textos (uno por imagen interior), 30 a 45 palabras cada uno, en
  oraciones completas. El primero explica qué pasó; el segundo, el contexto o por qué importa.
  Encerrá entre *asteriscos* 1 o 2 frases clave de cada texto para mostrarlas en negrita.
- caption: texto del post, 80 a 150 palabras. Empezá con un emoji 🚨 y la noticia en una línea,
  después 2 o 3 párrafos cortos, cerrá con una pregunta para generar comentarios y la línea
  "Fuente: <medios>". Sin hashtags dentro del caption.
- hashtags: 8 a 12 hashtags relevantes, sin el símbolo #.
- image_prompts: exactamente 3 descripciones EN INGLÉS de fotos para generar con IA
  (portada, imagen 2, imagen 3), 25 a 45 palabras cada una. Escenas editoriales
  concretas y fotográficas que representen la noticia: objetos, lugares, manos,
  pantallas, laboratorios, servidores, siluetas o personas genéricas de espaldas.
  PROHIBIDO: personas reales o reconocibles (nunca nombres propios de personas),
  logos, marcas, texto o letras en la imagen. Variá encuadre entre las 3.

Reglas:
- Usá SOLO datos presentes en las notas. No inventes cifras, citas ni detalles.
- Si las notas se contradicen, quedate con lo que confirman varias y aclaralo como "según ...".
- Si la noticia es un rumor sin confirmar, acusa a una persona de un delito o conducta
  privada sin pruebas sólidas, o no trata de IA/tecnología, devolvé skip=true con el motivo.
- Español neutro latinoamericano, tono cercano, sin clickbait engañoso."""


def write_post(story: Story) -> dict | None:
    notes = []
    for i, a in enumerate(story.articles, 1):
        body = a.text or a.summary
        notes.append(f"### Nota {i} — {a.source}\nTítulo: {a.title}\nURL: {a.link}\n\n{body}")

    client = anthropic.Anthropic()
    # Si el modelo rechaza la consulta, el servidor reintenta con otro modelo.
    resp = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": "\n\n".join(notes)}],
    )
    if resp.stop_reason == "refusal":
        print("[writer] Claude rechazó la noticia; se saltea")
        return None
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    if data["skip"]:
        print(f"[writer] saltada: {data['skip_reason']}")
        return None
    data["slides"] = data["slides"][:2]
    data["image_prompts"] = data["image_prompts"][:3]
    return data
