"""Clips de video REALES para los Reels, solo con licencia que permite reutilizarlos.

Fuentes (todas gratis):
  - YouTube con filtro "Creative Commons" (licencia CC BY: se puede reutilizar citando al
    autor). Ojo: la licencia la declara quien sube el video; el agente cazador-videos
    comprueba que el canal sea el autor real (no un resubido de otro).
  - Wikimedia Commons (videos con licencia libre).
  - NASA (dominio público).
Nunca se bajan videos de cuentas de terceros (X/Twitter, TikTok, Instagram) ni de canales
con licencia estándar de YouTube: eso es contenido con derechos.

Uso (lo corre el agente cazador-videos):
  python src/main.py clips <id> "Tesla Optimus robot"     # lista candidatos + miniaturas
  python src/main.py clip <id> <candidato> <escena 1-3> <segundo de inicio>
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import requests

from config import ROOT

WORK_DIR = ROOT / "work"
UA = {"User-Agent": "news-carousel-bot/1.0 (https://github.com/ramirocarusi13/lo-ultimo-en-ia)"}
CC_FILTER = "EgIwAQ%253D%253D"  # filtro "Creative Commons" del buscador de YouTube
CLIP_SECONDS = 14  # se baja un poco más de lo que dura una escena (~8-12 s)
YDL_BASE = {"quiet": True, "no_warnings": True, "remote_components": {"ejs:github"}}


def _ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def _clips_dir(post_id: str) -> Path:
    d = WORK_DIR / post_id / "clips"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- búsqueda
def _youtube(query: str, n: int, max_age_days: int) -> list[dict]:
    import yt_dlp

    url = ("https://www.youtube.com/results?search_query=" + requests.utils.quote(query)
           + "&sp=" + CC_FILTER)
    with yt_dlp.YoutubeDL({**YDL_BASE, "extract_flat": True, "playlistend": n * 2}) as y:
        entries = list(y.extract_info(url, download=False).get("entries") or [])
    out, oldest = [], time.strftime("%Y%m%d", time.localtime(time.time() - max_age_days * 86400))
    for e in entries:
        if len(out) >= n:
            break
        try:
            with yt_dlp.YoutubeDL({**YDL_BASE, "skip_download": True}) as y:
                i = y.extract_info(e["url"], download=False)
        except Exception:
            continue
        lic = i.get("license") or ""
        if "creative commons" not in lic.lower():  # doble control: solo CC
            continue
        if (i.get("upload_date") or "0") < oldest or (i.get("duration") or 0) < 5:
            continue
        out.append({
            "source": "YouTube", "url": i["webpage_url"], "title": i.get("title", ""),
            "channel": i.get("channel") or i.get("uploader") or "",
            "channel_url": i.get("channel_url") or "",
            "verified": bool(i.get("channel_is_verified")),
            "license": "CC BY", "date": i.get("upload_date"), "duration": i.get("duration"),
            "description": (i.get("description") or "")[:400], "thumb": i.get("thumbnail"),
            "credit": f"Video: {i.get('channel') or i.get('uploader')} / YouTube (CC BY)",
        })
    return out


def _commons(query: str, n: int) -> list[dict]:
    from photos import API, OK_LICENSES, _plain

    r = requests.get(API, headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{query} filetype:video", "gsrnamespace": 6, "gsrlimit": 20,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size|mediatype", "iiurlwidth": 640,
    })
    out = []
    for p in r.json().get("query", {}).get("pages", {}).values():
        ii = p["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        lic = _plain(meta.get("LicenseShortName", {}).get("value", ""))
        if not any(lic.lower().startswith(ok) for ok in OK_LICENSES):
            continue
        artist = _plain(meta.get("Artist", {}).get("value", ""))[:40] or "Wikimedia Commons"
        out.append({
            "source": "Wikimedia Commons", "url": ii["url"], "title": p["title"],
            "channel": artist, "license": lic, "date": _plain(meta.get("DateTime", {}).get("value", ""))[:10],
            "duration": float(ii.get("duration") or 0), "thumb": ii.get("thumburl"),
            "description": _plain(meta.get("ImageDescription", {}).get("value", ""))[:400],
            "credit": f"Video: {artist} / Wikimedia Commons ({lic})",
        })
    return out[:n]


def _nasa(query: str, n: int) -> list[dict]:
    r = requests.get("https://images-api.nasa.gov/search", timeout=30,
                     params={"q": query, "media_type": "video"})
    out = []
    for it in r.json().get("collection", {}).get("items", [])[:n]:
        d = it["data"][0]
        thumb = next((l["href"] for l in it.get("links", []) if l.get("render") == "image"), None)
        out.append({
            "source": "NASA", "url": it["href"], "title": d.get("title", ""), "channel": "NASA",
            "license": "dominio público", "date": d.get("date_created", "")[:10], "duration": 0,
            "description": (d.get("description") or "")[:400], "thumb": thumb,
            "credit": "Video: NASA (dominio público)",
        })
    return out


def search(post_id: str, query: str, n: int = 6, max_age_days: int = 60) -> list[dict]:
    """Busca en las 3 fuentes, guarda miniaturas y work/<id>/clips/candidatos.json."""
    found = []
    for name, fn in (("YouTube CC", lambda: _youtube(query, n, max_age_days)),
                     ("Commons", lambda: _commons(query, 3)),
                     ("NASA", lambda: _nasa(query, 3))):
        try:
            found += fn()
        except Exception as e:
            print(f"[clips] {name}: {e}")
    d = _clips_dir(post_id)
    path = d / "candidatos.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    seen = {c["url"] for c in old}
    cands = old + [c for c in found if c["url"] not in seen]
    for i, c in enumerate(cands, 1):
        c["n"] = i
        thumb = d / f"cand_{i}.jpg"
        if c.get("thumb") and not thumb.exists():
            try:
                thumb.write_bytes(requests.get(c["thumb"], headers=UA, timeout=30).content)
            except Exception:
                pass
    path.write_text(json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in cands:
        if c["url"] in {f["url"] for f in found}:
            print(f"[{c['n']}] {c['source']} · {c['license']} · {c['date']} · {c['duration']} s · "
                  f"{c['channel']}{' ✔' if c.get('verified') else ''}\n    {c['title'][:90]}\n    "
                  f"{c['url']}\n    miniatura: {d / ('cand_%d.jpg' % c['n'])}")
    if not found:
        print("[clips] sin videos con licencia libre para esa búsqueda")
    return cands


# ---------------------------------------------------------------- descarga
def take(post_id: str, n: int, scene: int, start: float = 0.0) -> Path:
    """Baja ~14 s del candidato n desde `start` para la escena 1-3 del Reel."""
    d = _clips_dir(post_id)
    cands = json.loads((d / "candidatos.json").read_text(encoding="utf-8"))
    c = next(x for x in cands if x["n"] == n)
    raw = d / f"raw_{n}.mp4"
    out = WORK_DIR / post_id / f"clip_{scene}.mp4"
    end = start + CLIP_SECONDS
    if c["source"] == "YouTube":
        import yt_dlp
        from yt_dlp.utils import download_range_func

        raw.unlink(missing_ok=True)
        opts = {**YDL_BASE, "outtmpl": str(raw.with_suffix(".%(ext)s")),
                "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b",
                "merge_output_format": "mp4", "download_ranges": download_range_func(None, [(start, end)]),
                "force_keyframes_at_cuts": True, "ffmpeg_location": _ffmpeg()}
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([c["url"]])
        src, ss = raw, 0.0
    else:
        url = c["url"]
        if c["source"] == "NASA":  # el href es un índice JSON con los archivos
            files = requests.get(url, timeout=30).json()
            url = next((f for f in files if f.endswith("~mobile.mp4")), None) or \
                next(f for f in files if f.endswith(".mp4"))
        if not raw.exists():
            with requests.get(url.replace("http://", "https://"), headers=UA, stream=True, timeout=120) as r:
                with open(raw, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
        src, ss = raw, start
    subprocess.run([_ffmpeg(), "-y", "-ss", f"{ss:.2f}", "-i", str(src), "-t", str(CLIP_SECONDS),
                    "-an", "-vf", "fps=30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-pix_fmt", "yuv420p", str(out)], check=True, capture_output=True)
    # cuadro de muestra para que el editor de video lo mire
    subprocess.run([_ffmpeg(), "-y", "-ss", "3", "-i", str(out), "-frames:v", "1", "-q:v", "3",
                    str(WORK_DIR / post_id / f"clip_{scene}.jpg")], check=True, capture_output=True)
    sel_path = WORK_DIR / post_id / "clips.json"
    sel = json.loads(sel_path.read_text(encoding="utf-8")) if sel_path.exists() else {}
    sel[str(scene)] = {"file": out.name, "credit": c["credit"], "url": c["url"], "title": c["title"],
                       "start": start}
    sel_path.write_text(json.dumps(sel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"CLIP escena {scene}: {out}  (muestra: {out.with_suffix('.jpg')})")
    return out


def drop(post_id: str, scene: int) -> None:
    """Saca el clip de una escena (vuelve a la foto)."""
    sel_path = WORK_DIR / post_id / "clips.json"
    sel = json.loads(sel_path.read_text(encoding="utf-8")) if sel_path.exists() else {}
    sel.pop(str(scene), None)
    sel_path.write_text(json.dumps(sel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[clips] escena {scene} sin clip")


def selected(post_id: str) -> dict:
    p = WORK_DIR / post_id / "clips.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
