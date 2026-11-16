"""Redacción del carrusel en español.

Flujo normal: la redacta Claude en una tarea programada de la app de Claude (con la
suscripción), siguiendo prompts/redaccion.md, y la guarda en work/<id>/draft.json.
Opcional: con ANTHROPIC_API_KEY, `main.py generate` la redacta por la API (pago).
"""
from __future__ import annotations

import json

from config import CLAUDE_MODEL, ROOT
from news import Story

RULES_FILE = ROOT / "prompts" / "redaccion.md"
SYSTEM = RULES_FILE.read_text(encoding="utf-8")

SCHEMA = {
    "type": "object",
    "properties": {
        "skip": {"type": "boolean"},
        "skip_reason": {"type": "string"},
        "confidence": {"type": "string", "enum": ["alta", "media", "baja"]},
        "headline": {"type": "string"},
        "badge": {"type": "string"},
        "photos": {"type": "array", "items": {"type": "string"}},
        "slides": {"type": "array", "items": {"type": "string"}},
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "image_prompts": {"type": "array", "items": {"type": "string"}},
        "reel_script": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["skip", "skip_reason", "confidence", "headline", "badge", "photos", "slides", "caption", "hashtags",
                 "image_prompts", "reel_script"],
    "additionalProperties": False,
}


def notes_text(story: Story) -> str:
    notes = []
    for i, a in enumerate(story.articles, 1):
        body = a.text or a.summary
        notes.append(f"### Nota {i} — {a.source}\nTítulo: {a.title}\nURL: {a.link}\n\n{body}")
    return "\n\n".join(notes)


def validate(data: dict) -> dict | None:
    """Revisa un borrador; devuelve el post listo o None si hay que saltear la noticia."""
    optional = ("confidence", "photos", "reel_script")  # borradores viejos pueden no tenerlos
    missing = [k for k in SCHEMA["required"] if k not in data and k not in optional]
    if missing:
        raise ValueError(f"faltan claves en el borrador: {missing}")
    if data["skip"]:
        print(f"[writer] saltada: {data['skip_reason']}")
        return None
    if data.get("confidence") == "baja":  # verificación: nunca publicar algo poco confirmado
        print("[writer] saltada: confianza baja (el hecho central no está bien confirmado)")
        return None
    data["hashtags"] = data["hashtags"][:5]  # límite de Instagram
    if len(data["slides"]) < 2 or not data["headline"].strip():
        raise ValueError("el borrador necesita headline y 2 slides")
    data["slides"] = data["slides"][:2]
    data["image_prompts"] = data["image_prompts"][:3]
    return data


def write_post(story: Story) -> dict | None:
    """Redacción por la API de Anthropic (solo si hay ANTHROPIC_API_KEY)."""
    import anthropic

    client = anthropic.Anthropic()
    # Si el modelo rechaza la consulta, el servidor reintenta con otro modelo.
    resp = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": notes_text(story)}],
    )
    if resp.stop_reason == "refusal":
        print("[writer] Claude rechazó la noticia; se saltea")
        return None
    return validate(json.loads(next(b.text for b in resp.content if b.type == "text")))
