"""Genera fotos editoriales con modelos open source.

Orden de preferencia:
  1. FLUX.1 [schnell] (Black Forest Labs, licencia Apache 2.0) vía Hugging Face
     Inference Providers. Necesita la variable HF_TOKEN (cuenta gratis con créditos
     mensuales). Modelo configurable con IMAGE_MODEL.
  2. Si no hay token o falla, se usa la foto principal de la nota (con crédito).

Las indicaciones (prompts) las escribe Claude y nunca muestran personas reales
identificables, logos ni texto: así se evitan deepfakes y problemas de derechos.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image

MODEL = os.getenv("IMAGE_MODEL") or "black-forest-labs/FLUX.1-schnell"

STYLE = (
    ", editorial news photography, shot on a full-frame camera with a 50mm lens, natural "
    "cinematic lighting, subtle cyan and violet accents, shallow depth of field, ultra "
    "detailed, photorealistic, magazine quality, no text, no letters, no logos, no watermark"
)


def generate(prompt: str, out: Path, seed: int = 0) -> Path | None:
    token = os.getenv("HF_TOKEN")
    if not token:
        return None
    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(token=token)
        img: Image.Image = client.text_to_image(
            prompt + STYLE, model=MODEL, width=1088, height=1360, seed=seed,
        )
        img.convert("RGB").save(out, "JPEG", quality=95)
        print(f"[imagegen] {out.name} generada con {MODEL}")
        return out
    except Exception as e:
        print(f"[imagegen] falló la generación ({e}); se usa la foto de la nota")
        return None


def to_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")
