"""Pipeline completo:  noticias en tendencia -> texto (Claude) -> imágenes -> Instagram.

Uso:
  python src/main.py generate     # elige noticia, redacta y genera imágenes en posts/<id>/
  python src/main.py publish      # publica el último post generado (necesita URL pública)
  python src/main.py run          # generate + publish (si las imágenes ya son públicas)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import imagegen
from config import POSTS_DIR
from news import Story, mark_posted, pick_trending_story
from render import render_carousel
from writer import write_post

PENDING = POSTS_DIR / "pending.json"

# En Windows la consola no usa UTF-8 por defecto y el emoji del caption rompería el print.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def generate() -> bool:
    story = pick_trending_story()
    if not story:
        return False
    post = write_post(story)
    if not post:
        mark_posted(story)  # no volver a evaluarla
        return False
    post_id = time.strftime("%Y%m%d-%H%M")
    out = POSTS_DIR / post_id
    out.mkdir(parents=True, exist_ok=True)
    photos, credits = [], []
    news_photos = [(a.image, f"Foto: {a.source}") for a in story.articles if a.image]
    for i, prompt in enumerate(post.get("image_prompts", [])):
        img = imagegen.generate(prompt, out / f"photo_{i + 1}.jpg", seed=i + 1)
        if img:
            photos.append(img)
            credits.append("Imagen generada con IA")
        elif i < len(news_photos):  # sin generador: foto de la nota
            photos.append(news_photos[i][0])
            credits.append(news_photos[i][1])
    paths = render_carousel(post, photos, credits, out)
    tags = " ".join("#" + h.lstrip("#").replace(" ", "") for h in post["hashtags"])
    caption = f"{post['caption']}\n\n{tags}"
    meta = {
        "id": post_id, "post": post, "caption": caption,
        # barras "/" también en Windows: estas rutas se usan para armar URLs
        "slides": [p.relative_to(POSTS_DIR.parent).as_posix() for p in paths],
        "sources": [{"title": a.title, "link": a.link, "source": a.source} for a in story.articles],
    }
    (out / "post.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    PENDING.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    mark_posted(story)
    print(f"[main] post generado en {out}")
    print(caption)
    return True


def publish() -> None:
    from publish import publish_carousel

    if not PENDING.exists():
        print("[main] nada pendiente para publicar")
        return
    meta = json.loads(PENDING.read_text(encoding="utf-8"))
    base = os.environ.get("PUBLIC_BASE_URL")
    if not base:  # en GitHub Actions: archivos crudos del repo (debe ser público)
        repo, ref = os.environ["GITHUB_REPOSITORY"], os.environ.get("GITHUB_REF_NAME", "main")
        base = f"https://raw.githubusercontent.com/{repo}/{ref}"
    urls = [f"{base.rstrip('/')}/{s}" for s in meta["slides"]]
    permalink = publish_carousel(urls, meta["caption"])
    meta["permalink"] = permalink
    (POSTS_DIR / meta["id"] / "post.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    PENDING.unlink()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "generate"
    if cmd in ("generate", "run"):
        ok = generate()
        if cmd == "run" and ok:
            publish()
    elif cmd == "publish":
        publish()
