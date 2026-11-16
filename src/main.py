"""Pipeline:  noticia en tendencia -> texto -> imágenes -> Instagram.

Flujo con la tarea programada de Claude (usa la suscripción, sin API paga):
  python src/main.py pick              # elige la noticia; deja las notas en work/<id>/story.json
  (Claude escribe work/<id>/draft.json siguiendo prompts/redaccion.md)
  python src/main.py build <id>        # fotos (ComfyUI) + carrusel en posts/<id>/
  python src/main.py skip <id> "motivo"  # descarta la noticia para no volver a evaluarla
  python src/main.py publish           # publica el último post armado (necesita URL pública)

Con ANTHROPIC_API_KEY también existe `generate` (pick + redacción por API + build).
"""
from __future__ import annotations

import json
import os
import sys
import time

import imagegen
from config import POSTS_DIR, ROOT
from news import Article, Story, mark_posted, pick_trending_story
from render import render_carousel

PENDING = POSTS_DIR / "pending.json"
WORK_DIR = ROOT / "work"  # notas completas de los medios: NO se suben al repo

# En Windows la consola no usa UTF-8 por defecto y el emoji del caption rompería el print.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def _dump(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _load_story(post_id: str) -> Story:
    data = json.loads((WORK_DIR / post_id / "story.json").read_text(encoding="utf-8-sig"))
    return Story([Article(**a) for a in data["articles"]])


def pick() -> str | None:
    story = pick_trending_story()
    if not story:
        print("NADA: no hay noticia nueva en tendencia")
        return None
    post_id = time.strftime("%Y%m%d-%H%M")
    _dump(WORK_DIR / post_id / "story.json", {"id": post_id, "articles": [vars(a) for a in story.articles]})
    from writer import notes_text
    (WORK_DIR / post_id / "notas.md").write_text(notes_text(story), encoding="utf-8")
    print(f"PICK {post_id}")
    print(f"Notas: {WORK_DIR / post_id / 'notas.md'}")
    print(f"Escribí el borrador en: {WORK_DIR / post_id / 'draft.json'}")
    return post_id


def skip(post_id: str, reason: str) -> None:
    mark_posted(_load_story(post_id), kind="skip")
    print(f"[main] noticia {post_id} descartada: {reason}")


def build(post_id: str, post: dict | None = None, story: Story | None = None) -> bool:
    from writer import validate

    story = story or _load_story(post_id)
    if post is None:
        post = validate(json.loads((WORK_DIR / post_id / "draft.json").read_text(encoding="utf-8-sig")))
        if post is None:
            mark_posted(story, kind="skip")
            return False
    out = POSTS_DIR / post_id
    out.mkdir(parents=True, exist_ok=True)
    photos, credits = [], []
    # Persona de cada imagen (portada, slide 2, slide 3): foto real con licencia libre.
    people = (post.get("photos") or post.get("people")
              or ([post["person"]] * 2 if post.get("person") else []))
    real = [None] * 3
    if any(people):
        import photos as person_photos
        found, used = {}, {}
        for i, name in enumerate(people[:3]):
            if not name:
                continue
            try:
                found.setdefault(name, person_photos.find_person_photos(name, n=3))
            except Exception as e:
                print(f"[main] no se pudieron buscar fotos de {name}: {e}")
                found[name] = []
            k = used.get(name, 0)
            if k < len(found[name]):  # otra foto distinta si la persona se repite
                real[i] = found[name][k]
                used[name] = k + 1
            print(f"[main] imagen {i + 1}: {name} -> {'foto real' if real[i] else 'sin foto libre'}")
    news_photos = [(a.image, f"Foto: {a.source}") for a in story.articles if a.image]
    for i, prompt in enumerate(post.get("image_prompts", [])):
        dest = out / f"photo_{i + 1}.jpg"
        if i < 3 and real[i]:
            photos.append(person_photos.download(real[i], out / f"real_{i + 1}.jpg"))
            credits.append(real[i]["credit"])
            continue
        if dest.exists():  # rearmado (p. ej. tras corregir el texto): se reusa la foto ya generada
            photos.append(dest)
            credits.append("")
            continue
        img = imagegen.generate(prompt, dest, seed=i + 1)
        if img:
            photos.append(img)
            credits.append("")
        elif i < len(news_photos):  # sin generador: foto de la nota
            photos.append(news_photos[i][0])
            credits.append(news_photos[i][1])
    # Sin créditos sobre las imágenes. Las fotos con licencia CC BY exigen nombrar al
    # autor: va en una línea del caption.
    paths = render_carousel(post, photos, [""] * len(photos), out)
    tags = " ".join("#" + h.lstrip("#").replace(" ", "") for h in post["hashtags"])
    notes = [f"📸 {c}" for c in dict.fromkeys(c for c in credits if c)]
    caption = post["caption"] + ("\n\n" + "\n".join(notes) if notes else "") + f"\n\n{tags}"
    meta = {
        "id": post_id, "post": post, "caption": caption,
        # barras "/" también en Windows: estas rutas se usan para armar URLs
        "slides": [p.relative_to(POSTS_DIR.parent).as_posix() for p in paths],
        "sources": [{"title": a.title, "link": a.link, "source": a.source} for a in story.articles],
    }
    _dump(out / "post.json", meta)
    _dump(PENDING, meta)
    mark_posted(story)
    print(f"[main] post armado en {out}")
    for p in paths:
        print(f"SLIDE {p}")
    print(caption)
    return True


def generate() -> bool:
    """Todo junto, redactando por la API de Anthropic (necesita ANTHROPIC_API_KEY)."""
    from writer import write_post

    post_id = pick()
    if not post_id:
        return False
    story = _load_story(post_id)
    post = write_post(story)
    if not post:
        mark_posted(story, kind="skip")
        return False
    return build(post_id, post, story)


def publish() -> None:
    from publish import publish_carousel

    if not PENDING.exists():
        print("[main] nada pendiente para publicar")
        return
    meta = json.loads(PENDING.read_text(encoding="utf-8-sig"))
    base = os.environ.get("PUBLIC_BASE_URL")
    if not base:  # archivos crudos del repo de GitHub (debe ser público)
        repo, ref = os.environ["GITHUB_REPOSITORY"], os.environ.get("GITHUB_REF_NAME", "main")
        base = f"https://raw.githubusercontent.com/{repo}/{ref}"
    urls = [f"{base.rstrip('/')}/{s}" for s in meta["slides"]]
    permalink = publish_carousel(urls, meta["caption"])
    meta["permalink"] = permalink
    _dump(POSTS_DIR / meta["id"] / "post.json", meta)
    PENDING.unlink()


if __name__ == "__main__":
    args = sys.argv[1:] or ["pick"]
    cmd = args[0]
    if cmd == "pick":
        pick()
    elif cmd == "build":
        sys.exit(0 if build(args[1]) else 2)
    elif cmd == "skip":
        skip(args[1], " ".join(args[2:]) or "sin motivo")
    elif cmd in ("generate", "run"):
        ok = generate()
        if cmd == "run" and ok:
            publish()
    elif cmd == "publish":
        publish()
    else:
        sys.exit(f"comando desconocido: {cmd}")
