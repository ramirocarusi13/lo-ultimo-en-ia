"""Arma las 4 imágenes del carrusel con plantillas HTML/CSS y Chromium (Playwright).

HTML/CSS permite tipografías profesionales, degradados, desenfoques y sombras
reales; Chromium saca una captura de 1080x1350 por cada slide.
"""
from __future__ import annotations

import base64
import os
import html
import io
import re
import time
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader
from PIL import Image

from config import BRAND_NAME, COLORS, HANDLE, SIZE

TEMPLATES = Path(__file__).parent / "templates"
UA = {"User-Agent": "Mozilla/5.0 (compatible; news-carousel-bot/1.0)"}
MESES = "ene feb mar abr may jun jul ago sep oct nov dic".split()


def _data_uri(src) -> str:
    """Convierte la foto (ruta o URL) en data URI para que Chromium no dependa de la red."""
    try:
        if src is None:
            raise ValueError("sin foto")
        if str(src).startswith("http"):
            raw = requests.get(str(src), headers=UA, timeout=30).content
        else:
            raw = Path(src).read_bytes()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=92)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        print(f"[render] foto no disponible ({e})")
        return ""


def _marked(text: str, tag: str) -> str:
    """'*palabra*' -> resaltado. Escapa el resto del texto."""
    parts = re.split(r"\*", html.escape(text))
    return "".join(tag.format(p) if i % 2 else p for i, p in enumerate(parts))


def _headline_size(text: str) -> int:
    n = len(text.replace("*", ""))
    return 132 if n <= 45 else 118 if n <= 60 else 104 if n <= 78 else 92


def render_carousel(post: dict, photos: list, credits: list[str], out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    tpl = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False).get_template("carousel.html")

    uris = [_data_uri(p) for p in photos] or [""]
    while len(uris) < 3:
        uris.append(uris[-1])
    creds = (list(credits) + [credits[0] if credits else ""] * 3)[:3]
    t = time.localtime()
    common = dict(c=COLORS, brand=BRAND_NAME, handle=HANDLE,
                  date=f"{t.tm_mday} {MESES[t.tm_mon - 1]} {t.tm_year}")
    same = uris[2] == uris[1]
    hl, bold = '<span class="hl">{}</span>', "<strong>{}</strong>"
    pages = [
        dict(slide="cover", photo=uris[0], credit=creds[0], badge=post.get("badge", ""),
             headline=_marked(post["headline"], hl), headline_size=_headline_size(post["headline"])),
        dict(slide="story", photo=uris[1], credit=creds[1], step="Qué pasó", zoom=1,
             focus="center 30%", text=_marked(post["slides"][0], bold), body_size=44),
        dict(slide="story", photo=uris[2], credit=creds[2], step="Por qué importa",
             zoom=1.25 if same else 1, focus="center 30%", text=_marked(post["slides"][1], bold), body_size=44),
        dict(slide="cta"),
    ]

    paths = []
    with sync_playwright() as pw:
        exe = os.getenv("CHROMIUM_PATH")  # opcional: usar un Chromium ya instalado
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        page = browser.new_page(viewport={"width": SIZE[0], "height": SIZE[1]})
        for i, data in enumerate(pages, 1):
            # el HTML se escribe junto a la plantilla para que encuentre las fuentes
            tmp = TEMPLATES / f"_render_{i}.html"
            tmp.write_text(tpl.render(**common, **data), encoding="utf-8")
            page.goto(tmp.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            p = out_dir / f"slide_{i}.jpg"
            page.screenshot(path=str(p), type="jpeg", quality=92)
            tmp.unlink()
            paths.append(p)
        browser.close()
    return paths
