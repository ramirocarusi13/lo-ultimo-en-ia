"""Genera las 4 imágenes del carrusel con el estilo de la cuenta."""
from __future__ import annotations

import io
import re
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from config import BLACK, BRAND_NAME, FONTS, GREEN, GREEN_DARK, HANDLE, SIZE, WHITE

W, H = SIZE
UA = {"User-Agent": "Mozilla/5.0 (compatible; news-carousel-bot/1.0)"}


# ---------- fuentes ----------
def anton(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / "Anton-Regular.ttf"), size)


def mont(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / "Montserrat.ttf"), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


# ---------- utilidades ----------
def load_image(src: str | Path | None) -> Image.Image:
    try:
        if src is None:
            raise ValueError
        if str(src).startswith("http"):
            data = requests.get(str(src), headers=UA, timeout=20).content
            img = Image.open(io.BytesIO(data))
        else:
            img = Image.open(src)
        return img.convert("RGB")
    except Exception:
        # sin foto: fondo oscuro con brillo verde
        img = Image.new("RGB", SIZE, (8, 12, 10))
        d = ImageDraw.Draw(img)
        d.ellipse((-300, -200, W + 300, H - 300), fill=(20, 70, 35))
        return img.filter(ImageFilter.GaussianBlur(160))


def cover(img: Image.Image, box: tuple[int, int], zoom: float = 1.0, focus=(0.5, 0.35)) -> Image.Image:
    img = ImageOps.fit(img, (int(box[0] * zoom), int(box[1] * zoom)), Image.LANCZOS, centering=focus)
    if zoom != 1.0:
        left = (img.width - box[0]) // 2
        top = int((img.height - box[1]) * focus[1])
        img = img.crop((left, top, left + box[0], top + box[1]))
    return img


def bottom_gradient(img: Image.Image, start: float, strength: int = 255) -> Image.Image:
    """Oscurece la parte inferior para que el texto se lea."""
    grad = Image.new("L", (1, img.height))
    s = int(img.height * start)
    for y in range(img.height):
        v = 0 if y < s else min(strength, int(strength * ((y - s) / (img.height - s)) ** 0.8 * 1.3))
        grad.putpixel((0, y), v)
    black = Image.new("RGB", img.size, BLACK)
    return Image.composite(black, img, grad.resize(img.size))


def parse_marked(text: str) -> list[tuple[str, bool]]:
    """'EL *CEO* RENUNCIA' -> [('EL', False), ('CEO', True), ('RENUNCIA', False)]"""
    words = []
    for i, chunk in enumerate(re.split(r"\*", text)):
        for w in chunk.split():
            words.append((w, i % 2 == 1))
    return words


def wrap_words(words, font, max_w, draw):
    lines, cur = [], []
    for w in words:
        test = " ".join(x[0] for x in cur + [w])
        if cur and draw.textlength(test, font=font) > max_w:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def draw_marked_block(draw, words, top, max_w, max_h, max_size=118, min_size=60, line_gap=0.98):
    """Titular centrado en Anton, ajustando el tamaño para que entre."""
    size = max_size
    while size >= min_size:
        font = anton(size)
        lines = wrap_words(words, font, max_w, draw)
        lh = int(size * line_gap * 1.12)
        if lh * len(lines) <= max_h:
            break
        size -= 4
    y = top + (max_h - lh * len(lines)) // 2
    space = draw.textlength(" ", font=font)
    for line in lines:
        total = sum(draw.textlength(w, font=font) for w, _ in line) + space * (len(line) - 1)
        x = (W - total) / 2
        for w, hl in line:
            draw.text((x, y), w, font=font, fill=GREEN if hl else WHITE)
            x += draw.textlength(w, font=font) + space
        y += lh
    return y


def wrap_text(text, font, max_w, draw):
    return [" ".join(x[0] for x in l) for l in wrap_words([(w, False) for w in text.split()], font, max_w, draw)]


# ---------- logo ----------
def make_logo(size: int = 200) -> Image.Image:
    s = size * 4  # supersampling
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, s - 1, s - 1), fill=(0, 0, 0, 255))
    ring = int(s * 0.035)
    d.ellipse((ring, ring, s - ring, s - ring), outline=GREEN_DARK, width=ring)
    f = anton(int(s * 0.46))
    tw = d.textlength("IA", font=f)
    d.text(((s - tw) / 2, s * 0.14), "IA", font=f, fill=WHITE)
    # flecha de "lo último"
    d.line([(s * 0.30, s * 0.70), (s * 0.48, s * 0.60), (s * 0.58, s * 0.66), (s * 0.74, s * 0.52)],
           fill=GREEN, width=int(s * 0.035), joint="curve")
    d.polygon([(s * 0.78, s * 0.48), (s * 0.70, s * 0.50), (s * 0.76, s * 0.57)], fill=GREEN)
    f2 = mont(int(s * 0.075), "Black")
    t = "LO ÚLTIMO"
    tw = d.textlength(t, font=f2)
    d.text(((s - tw) / 2, s * 0.76), t, font=f2, fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def paste_handle_pill(img: Image.Image):
    """Etiqueta arriba a la derecha: logo + nombre + @usuario (como marca de agua)."""
    d = ImageDraw.Draw(img)
    logo = make_logo(96)
    f1, f2 = mont(30, "ExtraBold"), mont(24, "Medium")
    tw = max(d.textlength(BRAND_NAME, font=f1), d.textlength(HANDLE, font=f2))
    x0 = W - int(tw) - 96 - 60
    y0 = 36
    img.paste(logo, (x0, y0), logo)
    for txt, f, dy in ((BRAND_NAME, f1, 14), (HANDLE, f2, 52)):
        d.text((x0 + 110 + 2, y0 + dy + 2), txt, font=f, fill=(0, 0, 0))
        d.text((x0 + 110, y0 + dy), txt, font=f, fill=WHITE)


def credit(img, text):
    d = ImageDraw.Draw(img)
    f = mont(20, "Medium")
    d.text((W - 30 - d.textlength(text, font=f), H - 40), text, font=f, fill=(170, 170, 170))


# ---------- slides ----------
def slide_cover(photo, headline: str, badge: str, photo_credit: str) -> Image.Image:
    img = Image.new("RGB", SIZE, BLACK)
    ph_h = int(H * 0.60)
    ph = bottom_gradient(cover(photo, (W, ph_h)), 0.55)
    img.paste(ph, (0, 0))
    d = ImageDraw.Draw(img)

    if badge:
        r = 190
        cx, cy = 20 + r - 60, int(ph_h * 0.42)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GREEN_DARK)
        size = 92
        while size > 30 and d.textlength(badge.upper(), font=anton(size)) > r * 1.45:
            size -= 4
        f = anton(size)
        tw = d.textlength(badge.upper(), font=f)
        d.text((cx - tw / 2 + 20, cy - size * 0.62), badge.upper(), font=f, fill=WHITE)

    # línea con el logo al centro
    ly = ph_h - 10
    logo = make_logo(84)
    d.line([(40, ly), (W / 2 - 60, ly)], fill=(200, 200, 200), width=3)
    d.line([(W / 2 + 60, ly), (W - 40, ly)], fill=(200, 200, 200), width=3)
    img.paste(logo, (W // 2 - 42, ly - 42), logo)

    end_y = draw_marked_block(d, parse_marked(headline), ly + 55, W - 110, H - ly - 200)
    f = mont(36, "Bold")
    t = "Desliza para VER  →"
    d.text(((W - d.textlength(t, font=f)) / 2, max(end_y + 25, H - 110)), t, font=f, fill=WHITE)
    credit(img, photo_credit)
    return img


def slide_story(photo, text: str, photo_credit: str, zoom=1.0, focus=(0.5, 0.3)) -> Image.Image:
    img = bottom_gradient(cover(photo, SIZE, zoom, focus), 0.45)
    d = ImageDraw.Draw(img)
    paste_handle_pill(img)
    size = 44
    while True:
        f = mont(size, "SemiBold")
        lines = wrap_text(text, f, W - 100, d)
        lh = int(size * 1.28)
        if len(lines) * lh < H * 0.30 or size <= 32:
            break
        size -= 2
    y = H - 90 - len(lines) * lh
    for line in lines:
        d.text((50, y), line, font=f, fill=WHITE)
        y += lh
    credit(img, photo_credit)
    return img


def slide_cta() -> Image.Image:
    img = Image.new("RGB", SIZE, BLACK)
    d = ImageDraw.Draw(img)
    # tarjeta de perfil
    x0, y0, x1, y1 = 70, 70, W - 70, 660
    d.rounded_rectangle((x0, y0, x1, y1), radius=60, outline=WHITE, width=14, fill=(5, 5, 5))
    f = mont(46, "Bold")
    d.text((x0 + 60, y0 + 60), "←", font=f, fill=WHITE)
    d.text((x0 + 150, y0 + 58), HANDLE.lstrip("@"), font=f, fill=WHITE)
    for i in range(3):
        d.ellipse((x1 - 70, y0 + 62 + i * 18, x1 - 60, y0 + 72 + i * 18), fill=WHITE)

    logo = make_logo(210)
    img.paste(logo, (x0 + 50, y0 + 170), logo)
    fb = mont(34, "ExtraBold")
    d.text((x0 + 300, y0 + 190), "INTELIGENCIA ARTIFICIAL •", font=fb, fill=WHITE)
    d.text((x0 + 300, y0 + 232), "Noticias y tendencias", font=fb, fill=WHITE)
    fm = mont(30, "Medium")
    d.text((x0 + 300, y0 + 300), "Lo nuevo de la IA, todos los días", font=fm, fill=(200, 200, 200))
    bio = ["Noticias de IA en español", "Explicado simple, sin vueltas", "Activá las notificaciones"]
    for i, b in enumerate(bio):
        by = y0 + 410 + i * 46
        d.ellipse((x0 + 64, by + 13, x0 + 80, by + 29), fill=GREEN)
        d.text((x0 + 100, y0 + 410 + i * 46), b, font=fm, fill=WHITE)
    # botón
    bx0, by0, bx1, by1 = x1 - 330, y0 + 420, x1 - 50, y0 + 500
    d.rounded_rectangle((bx0 + 4, by0 + 8, bx1 + 4, by1 + 8), radius=40, fill=(20, 80, 40))
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=40, fill=(76, 175, 80))
    ft = mont(38, "Bold")
    t = "Síguenos"
    d.text(((bx0 + bx1 - d.textlength(t, font=ft)) / 2, by0 + 16), t, font=ft, fill=WHITE)

    draw_marked_block(d, parse_marked("SI TE GUSTAN LAS NOTICIAS DE *IA* EN *TENDENCIA* ESTA PÁGINA ES PARA TI"),
                      720, W - 130, 580, max_size=130)
    return img


def render_carousel(post: dict, photos: list, credits: list[str], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    imgs = [load_image(p) for p in photos] or [load_image(None)]
    p1 = imgs[0]
    p2 = imgs[1] if len(imgs) > 1 else imgs[0]
    p3 = imgs[2] if len(imgs) > 2 else (imgs[1] if len(imgs) > 1 else imgs[0])
    c = credits + [credits[0] if credits else ""] * 3
    zoom3 = 1.0 if p3 is not p2 else 1.35  # misma foto: otro encuadre
    slides = [
        slide_cover(p1, post["headline"], post.get("badge", ""), c[0]),
        slide_story(p2, post["slides"][0], c[1 if len(imgs) > 1 else 0]),
        slide_story(p3, post["slides"][1], c[min(2, len(imgs) - 1)], zoom=zoom3, focus=(0.5, 0.25)),
        slide_cta(),
    ]
    paths = []
    for i, s in enumerate(slides, 1):
        p = out_dir / f"slide_{i}.jpg"
        s.save(p, "JPEG", quality=92)
        paths.append(p)
    return paths
