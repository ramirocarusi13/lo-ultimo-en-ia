"""Genera fotos editoriales con modelos open source, sin servicios pagos.

Orden de preferencia:
  1. ComfyUI (open source) con FLUX.2 [klein] 4B (Black Forest Labs, Apache 2.0).
     ComfyUI corre en esta PC o en cualquier servidor; se usa su API HTTP.
     Dirección configurable con COMFYUI_URL (por defecto http://127.0.0.1:8188).
  2. Si ComfyUI no responde o falla, se usa la foto principal de la nota (con crédito).

Las indicaciones (prompts) las escribe Claude y nunca muestran personas reales
identificables, logos ni texto: así se evitan deepfakes y problemas de derechos.
"""
from __future__ import annotations

import io
import os
import random
import time
import uuid
from pathlib import Path

import requests
from PIL import Image

COMFYUI_URL = (os.getenv("COMFYUI_URL") or "http://127.0.0.1:8188").rstrip("/")
UNET = os.getenv("COMFYUI_UNET") or "flux-2-klein-4b-fp8.safetensors"
# Versión de 4 bits (3,6 GB): la de 16 bits (7,5 GB) no entra junto al modelo en 16 GB de RAM.
TEXT_ENCODER = os.getenv("COMFYUI_TEXT_ENCODER") or "qwen_3_4b_fp4_flux2.safetensors"
VAE = os.getenv("COMFYUI_VAE") or "flux2-vae.safetensors"
# Formato vertical 4:5 como el carrusel (múltiplos de 16). Más chico = más rápido:
# en CPU, 768x960 tarda ~5 min por foto.
WIDTH = int(os.getenv("IMAGE_WIDTH", "768"))
HEIGHT = int(os.getenv("IMAGE_HEIGHT", "960"))
STEPS = int(os.getenv("IMAGE_STEPS", "4"))  # klein distilado: 4 pasos
TIMEOUT = int(os.getenv("COMFYUI_TIMEOUT", "1800"))  # segundos por imagen

STYLE = (
    ", editorial news photography, shot on a full-frame camera with a 50mm lens, natural "
    "cinematic lighting, subtle cyan and violet accents, shallow depth of field, ultra "
    "detailed, photorealistic, magazine quality, no text, no letters, no logos, no watermark"
)


def _workflow(prompt: str, seed: int) -> dict:
    """Flujo de ComfyUI (formato API) de FLUX.2 [klein] 4B distilado, texto a imagen."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": TEXT_ENCODER, "type": "flux2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptyFlux2LatentImage",
              "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
        "7": {"class_type": "Flux2Scheduler", "inputs": {"steps": STEPS, "width": WIDTH, "height": HEIGHT}},
        "8": {"class_type": "CFGGuider",
              "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "cfg": 1.0}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "11": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["10", 0], "guider": ["8", 0], "sampler": ["9", 0],
                          "sigmas": ["7", 0], "latent_image": ["6", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "PreviewImage", "inputs": {"images": ["12", 0]}},
    }


def comfyui_available() -> bool:
    try:
        return requests.get(f"{COMFYUI_URL}/system_stats", timeout=5).ok
    except requests.RequestException:
        return False


def _comfyui(prompt: str, seed: int) -> Image.Image:
    r = requests.post(f"{COMFYUI_URL}/prompt", timeout=30,
                      json={"prompt": _workflow(prompt, seed), "client_id": str(uuid.uuid4())})
    if not r.ok:
        raise RuntimeError(f"ComfyUI rechazó el flujo: {r.text[:500]}")
    prompt_id = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < TIMEOUT:
        time.sleep(2)
        hist = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30).json().get(prompt_id)
        if not hist:
            continue
        status = hist.get("status", {})
        if status.get("status_str") == "error":
            raise RuntimeError(f"ComfyUI falló: {status.get('messages')}")
        for node in hist.get("outputs", {}).values():
            for img in node.get("images", []):
                data = requests.get(f"{COMFYUI_URL}/view", params=img, timeout=60).content
                return Image.open(io.BytesIO(data))
    raise TimeoutError(f"ComfyUI no terminó en {TIMEOUT}s")


def generate(prompt: str, out: Path, seed: int = 0) -> Path | None:
    if not comfyui_available():
        print(f"[imagegen] ComfyUI no responde en {COMFYUI_URL}; se usa la foto de la nota")
        return None
    try:
        t0 = time.time()
        img = _comfyui(prompt + STYLE, seed or random.randint(1, 2**31))
        img.convert("RGB").save(out, "JPEG", quality=95)
        print(f"[imagegen] {out.name} generada con ComfyUI + {UNET} en {time.time() - t0:.0f}s")
        return out
    except Exception as e:
        print(f"[imagegen] falló la generación ({e}); se usa la foto de la nota")
        return None
