"""Pipeline:  noticia en tendencia -> texto -> imágenes -> Instagram.

Flujo con la tarea programada de Claude (usa la suscripción, sin API paga):
  python src/main.py pick              # 5 candidatas en work/<id>/candidatos.md
  python src/main.py choose <id> <n>   # lee las notas de la candidata n -> work/<id>/notas.md
  python src/main.py skipc <id> <n> "motivo"  # descarta una candidata
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
from news import Article, Story, mark_posted, top_stories
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


def pick(n: int = 5) -> str | None:
    """Guarda las n mejores candidatas en work/<id>/candidatos.md para elegir una con `choose`."""
    top = top_stories(n)
    if not top:
        print("NADA: no hay noticia nueva en tendencia")
        return None
    post_id = time.strftime("%Y%m%d-%H%M")
    _dump(WORK_DIR / post_id / "candidatos.json",
          [[vars(a) for a in s.articles] for s in top])
    lines = []
    for i, s in enumerate(top, 1):
        age = (time.time() - max(a.published for a in s.articles)) / 3600
        lines.append(f"## {i}. cobertura {s.coverage} medios · hace {age:.1f} h")
        lines += [f"- [{a.source}] {a.title}" for a in s.articles[:5]]
    text = "\n".join(lines)
    (WORK_DIR / post_id / "candidatos.md").write_text(text, encoding="utf-8")
    print(f"CANDIDATOS {post_id}\n{text}")
    print(f"\nElegí una con: python src/main.py choose {post_id} <número>")
    return post_id


def choose(post_id: str, n: int) -> None:
    """Toma la candidata n, lee las notas completas y deja work/<id>/notas.md para redactar."""
    from news import prepare
    from writer import notes_text

    cands = json.loads((WORK_DIR / post_id / "candidatos.json").read_text(encoding="utf-8-sig"))
    story = prepare(Story([Article(**a) for a in cands[n - 1]]))
    _dump(WORK_DIR / post_id / "story.json", {"id": post_id, "articles": [vars(a) for a in story.articles]})
    (WORK_DIR / post_id / "notas.md").write_text(notes_text(story), encoding="utf-8")
    print(f"ELEGIDA {post_id}: {story.articles[0].title}")
    print(f"Notas: {WORK_DIR / post_id / 'notas.md'}")
    print(f"Escribí el borrador en: {WORK_DIR / post_id / 'draft.json'}")


def skip_candidate(post_id: str, n: int, reason: str) -> None:
    """Descarta una candidata sin leer sus notas (para que no vuelva a aparecer)."""
    cands = json.loads((WORK_DIR / post_id / "candidatos.json").read_text(encoding="utf-8-sig"))
    mark_posted(Story([Article(**a) for a in cands[n - 1]]), kind="skip")
    print(f"[main] candidata {n} descartada: {reason}")


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
            if "#" in name:  # "Jensen Huang#2": empezar por la 2.ª foto (no repetir la de otro post)
                name, start = name.split("#", 1)
                used.setdefault(name, int(start) - 1)
            try:
                found.setdefault(name, person_photos.find_person_photos(name, n=4))
            except Exception as e:
                print(f"[main] no se pudieron buscar fotos de {name}: {e}")
                found[name] = []
            k = used.get(name, 0)
            if k < len(found[name]):  # otra foto distinta si la persona se repite
                real[i] = found[name][k]
                used[name] = k + 1
            print(f"[main] imagen {i + 1}: {name} -> {'foto real' if real[i] else 'sin foto libre'}")
    # Nunca se usan las fotos de los medios (contenido ajeno con derechos): solo fotos con
    # licencia libre o ilustraciones propias. Sin ninguna de las dos, el slide va con el fondo
    # de marca.
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
        photos.append(img)  # None -> fondo de marca
        credits.append("")
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

    post_id = pick(1)
    if not post_id:
        return False
    choose(post_id, 1)
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
    elif cmd == "choose":
        choose(args[1], int(args[2]))
    elif cmd == "skipc":
        skip_candidate(args[1], int(args[2]), " ".join(args[3:]) or "sin motivo")
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
