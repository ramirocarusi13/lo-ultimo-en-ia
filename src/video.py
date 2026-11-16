"""Reel de Instagram (9:16, ~25-35 s) a partir de un post ya armado.

Todo gratis y local:
  - voz en off con Piper (TTS de código abierto, corre en CPU en segundos);
  - fondos: las mismas fotos del carrusel (reales de Wikimedia o ilustraciones de ComfyUI)
    con zoom lento (efecto Ken Burns);
  - textos y subtítulos estilo karaoke con la plantilla HTML de la marca (Chromium);
  - ffmpeg une todo en posts/<id>/reel.mp4.

Guion: post["reel_script"] = 3 textos (gancho, qué pasó, por qué importa). Si no está,
se arma con el titular y los 2 textos de los slides.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from PIL import Image

from config import (BRAND_NAME, COLORS, HANDLE, POSTS_DIR, REEL_FPS, REEL_SIZE, REEL_SPEED,
                    REEL_VOICE, VOICES_DIR)
from render import TEMPLATES, _headline_size, _marked

OUTRO = "Sigue a Lo Último en IA para no perderte nada."
GAP = 0.12        # silencio entre oraciones (s)
END_EXTRA = 0.9   # el cierre queda un poco más en pantalla después de la voz
STEPS = ["", "Qué pasó", "Por qué importa"]


def _ffmpeg() -> str:
    exe = os.getenv("FFMPEG") or shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("no se encontró ffmpeg (winget install Gyan.FFmpeg)")
    return exe


def _run(args: list[str]) -> None:
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError("ffmpeg falló:\n" + r.stderr[-2500:])


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("*", "")).strip()


def _script(post: dict) -> list[str]:
    parts = post.get("reel_script")
    if parts and len(parts) >= 3:
        return [p.strip() for p in parts[:3]]
    head = _plain(post["headline"]).capitalize().rstrip(".") + "."
    return [head, post["slides"][0], post["slides"][1]]


# ---------------------------------------------------------------- voz
def _voice():
    from piper import PiperVoice

    model = VOICES_DIR / f"{REEL_VOICE}.onnx"
    if not model.exists():
        subprocess.run([sys.executable, "-m", "piper.download_voices", REEL_VOICE,
                        "--data-dir", str(VOICES_DIR)], check=True)
    return PiperVoice.load(str(model))


def _speak(voice, text: str) -> list[tuple[str, bytes, int]]:
    """Una entrada por oración: (texto con *marcas*, audio int16, sample rate)."""
    from piper import SynthesisConfig

    cfg = SynthesisConfig(length_scale=REEL_SPEED)
    # se separa a mano para conservar los *asteriscos* de cada oración
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if _plain(s)]
    out = []
    for s in sentences:
        chunks = list(voice.synthesize(_plain(s), syn_config=cfg))
        out.append((s, b"".join(c.audio_int16_bytes for c in chunks), chunks[0].sample_rate))
    return out


# ---------------------------------------------------------------- subtítulos
def _chunks(sentence: str, max_words: int = 3, max_chars: int = 18) -> list[str]:
    """Parte una oración en frases de 1-3 palabras, conservando los resaltados *así*."""
    words, hl, tokens = sentence.split(), False, []
    for w in words:
        start = w.startswith("*")
        end = w.rstrip(".,;:!?»”\"").endswith("*") and (len(w.strip("*.,;:!?")) > 0)
        on = hl or start
        clean = w.replace("*", "")
        tokens.append((clean, on))
        if start:
            hl = True
        if end:
            hl = False
    groups, cur = [], []
    for t in tokens:
        if cur and (len(cur) >= max_words or len(" ".join(x for x, _ in cur + [t])) > max_chars):
            groups.append(cur)
            cur = []
        cur.append(t)
        if t[0][-1:] in ",;:" and len(cur) >= 2:  # cortar en las pausas naturales
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return [" ".join(f"*{w}*" if on else w for w, on in g).replace("* *", " ") for g in groups]


# ---------------------------------------------------------------- imágenes
def _background(src: Path | None, out: Path) -> Path:
    """Recorta la foto a 9:16 (al doble de tamaño, para que el zoom no tiemble)."""
    W, H = REEL_SIZE[0] * 2, REEL_SIZE[1] * 2
    if src and src.exists():
        img = Image.open(src).convert("RGB")
        scale = max(W / img.width, H / img.height)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        left = (img.width - W) // 2
        top = int((img.height - H) * 0.3)  # las caras suelen estar en el tercio de arriba
        img = img.crop((left, top, left + W, top + H))
    else:
        img = Image.new("RGB", (W, H), COLORS["bg2"])
    img.save(out, "JPEG", quality=92)
    return out


def _render_layers(pages: list[dict], out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    tpl = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False).get_template("reel.html")
    common = dict(c=COLORS, brand=BRAND_NAME, handle=HANDLE)
    paths = []
    with sync_playwright() as pw:
        exe = os.getenv("CHROMIUM_PATH")
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        page = browser.new_page(viewport={"width": REEL_SIZE[0], "height": REEL_SIZE[1]})
        tmp = TEMPLATES / "_render_reel.html"
        for i, data in enumerate(pages):
            tmp.write_text(tpl.render(**common, **data), encoding="utf-8")
            page.goto(tmp.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            p = out_dir / f"layer_{i:02d}.png"
            page.screenshot(path=str(p), omit_background=data["mode"] != "end")
            paths.append(p)
        tmp.unlink(missing_ok=True)
        browser.close()
    return paths


def _scene_images(out: Path) -> list[Path | None]:
    imgs = []
    for i in range(1, 4):
        cands = [out / f"real_{i}.jpg", out / f"photo_{i}.jpg"]
        imgs.append(next((c for c in cands if c.exists()), None))
    # si falta una, se repite la anterior (con otro encuadre del zoom)
    for i in range(3):
        if imgs[i] is None:
            imgs[i] = next((x for x in imgs if x), None)
    return imgs


# ---------------------------------------------------------------- armado
def make_reel(post_id: str) -> Path:
    out = POSTS_DIR / post_id
    meta = json.loads((out / "post.json").read_text(encoding="utf-8-sig"))
    post = meta["post"]
    tmp = out / "_reel"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()

    # 1. voz en off: escenas 1-3 + cierre
    voice = _voice()
    scenes = [_speak(voice, t) for t in _script(post)] + [_speak(voice, OUTRO)]
    rate = scenes[0][0][2]
    gap = b"\x00\x00" * int(rate * GAP)
    audio, timeline = b"", []   # timeline: por escena, (duración, [(chunk, ini, fin)])
    for k, sentences in enumerate(scenes):
        t0, subs = len(audio) / 2 / rate, []
        for text, pcm, _ in sentences:
            start = len(audio) / 2 / rate
            dur = len(pcm) / 2 / rate
            parts = _chunks(text)
            weights = [len(_plain(p)) + 2 for p in parts]
            acc = start
            for p, w in zip(parts, weights):
                d = dur * w / sum(weights)
                subs.append((p, acc - t0, acc - t0 + d))
                acc += d
            audio += pcm + gap
        if k == len(scenes) - 1:
            audio += b"\x00\x00" * int(rate * END_EXTRA)
        timeline.append((len(audio) / 2 / rate - t0, subs))
    wav = tmp / "voz.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(audio)

    # 2. capas: una por escena (marca + titular o etiqueta), una por subtítulo, y el cierre
    hl = '<span class="hl">{}</span>'
    pages, index = [], []
    for k in range(3):
        if k == 0:
            pages.append(dict(mode="scene", headline=_marked(post["headline"], hl), step="",
                              headline_size=min(_headline_size(post["headline"]), 118),
                              badge=post.get("badge", "")))
        else:
            pages.append(dict(mode="scene", headline="", step=STEPS[k], headline_size=0, badge=""))
        subs = []
        # en la portada ya está el titular grande: sin subtítulos encima para no saturar
        for text, a, b in (timeline[k][1] if k else []):
            subs.append((len(pages), a, b))
            pages.append(dict(mode="sub", text=_marked(text, hl), headline_size=0))
        index.append((len(pages) - len(subs) - 1, subs))
    pages.append(dict(mode="end", headline_size=0))
    layers = _render_layers(pages, tmp)

    # 3. un segmento de video por escena
    ff, fps = _ffmpeg(), REEL_FPS
    imgs = _scene_images(out)
    from clips import WORK_DIR, selected
    clips = selected(post_id)
    segs = []
    for k in range(3):
        dur, _ = timeline[k]
        frames = max(1, round(dur * fps))
        scene_layer, subs = index[k]
        W, H = REEL_SIZE
        clip = clips.get(str(k + 1))
        clip_file = WORK_DIR / post_id / clip["file"] if clip else None
        if clip_file and clip_file.exists():
            # video real (licencia libre), formato noticiero: el clip entero arriba y de fondo
            # el mismo clip ampliado y desenfocado
            args = [ff, "-y", "-stream_loop", "-1", "-i", str(clip_file), "-i", str(layers[scene_layer])]
            f = (f"[0:v]fps={fps},split[a][c];[a]scale={W}:{H}:force_original_aspect_ratio=increase,"
                 f"crop={W}:{H},boxblur=28:2,eq=brightness=-0.12[bg];"
                 f"[c]scale={W}:1000:force_original_aspect_ratio=decrease[fg];"
                 f"[bg][fg]overlay=x=(W-w)/2:y=330,setsar=1[b];[b][1:v]overlay=0:0[v0]")
        else:
            bg = _background(imgs[k], tmp / f"bg_{k}.jpg")
            z = "1+0.10*on/{n}" if k % 2 == 0 else "1.10-0.10*on/{n}"  # acercar / alejar
            args = [ff, "-y", "-i", str(bg), "-i", str(layers[scene_layer])]
            f = (f"[0:v]zoompan=z='{z.format(n=frames)}':x='iw/2-(iw/zoom/2)':y='ih*0.3-(ih/zoom*0.3)'"
                 f":d={frames}:s={W}x{H}:fps={fps},setsar=1[b];[b][1:v]overlay=0:0[v0]")
        for li, _, _ in subs:
            args += ["-i", str(layers[li])]
        for j, (_, a, b) in enumerate(subs):
            f += f";[v{j}][{j + 2}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{j + 1}]"
        seg = tmp / f"seg_{k}.mp4"
        args += ["-filter_complex", f, "-map", f"[v{len(subs)}]", "-frames:v", str(frames),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                 "-r", str(fps), str(seg)]
        _run(args)
        segs.append(seg)

    # cierre: tarjeta de la marca con un zoom mínimo
    dur = timeline[3][0]
    frames = round(dur * fps)
    seg = tmp / "seg_3.mp4"
    _run([ff, "-y", "-i", str(layers[-1]), "-filter_complex",
          f"[0:v]scale={REEL_SIZE[0] * 2}:-1,zoompan=z='1+0.04*on/{frames}':x='iw/2-(iw/zoom/2)'"
          f":y='ih/2-(ih/zoom/2)':d={frames}:s={REEL_SIZE[0]}x{REEL_SIZE[1]}:fps={fps},setsar=1[v]",
          "-map", "[v]", "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(fps), str(seg)])
    segs.append(seg)

    # 4. unir escenas + voz
    lst = tmp / "lista.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), encoding="utf-8")
    reel = out / "reel.mp4"
    _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(wav),
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
          "-shortest", "-movflags", "+faststart", str(reel)])

    # 5. cuadros de muestra para revisar sin abrir el video
    total = sum(d for d, _ in timeline)
    starts = [0.0]
    for d, _ in timeline[:-1]:
        starts.append(starts[-1] + d)
    for k, (s, (d, _)) in enumerate(zip(starts, timeline), 1):
        _run([ff, "-y", "-ss", f"{s + d * 0.6:.2f}", "-i", str(reel), "-frames:v", "1",
              "-q:v", "3", str(out / f"reel_cuadro_{k}.jpg")])
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"[video] reel listo: {reel} ({total:.1f} s)")
    return reel


if __name__ == "__main__":
    make_reel(sys.argv[1])
