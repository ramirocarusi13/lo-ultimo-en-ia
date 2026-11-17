"""Voz natural en español con Chatterbox Multilingual (Resemble AI, licencia MIT).

Se corre con el Python de .venv-tts (tiene PyTorch):
  .venv-tts\\Scripts\\python.exe src\\tts_natural.py <trabajo.json>
trabajo.json = {"sentences": [...], "out_dir": "..."} -> out_dir/tts_000.wav, tts_001.wav, ...

Timbre: imita la grabación voices/referencia.wav (10-20 s, una sola persona hablando claro,
sin música). Usá SOLO una grabación de alguien que dio su permiso (vos, o una locutora que
aceptó). Si no existe, usa voices/referencia_base.wav (generada con una voz libre de Piper).
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICES = ROOT / "voices"
EXAGGERATION = 0.55  # expresividad (0.5 = neutra; más alto = más enfática)
CFG_WEIGHT = 0.4     # más bajo = ritmo más natural y algo más rápido


def reference() -> Path | None:
    for name in ("referencia.wav", "referencia_base.wav"):
        p = VOICES / name
        if p.exists():
            return p
    return None


def main(job_path: str) -> None:
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    job = json.loads(Path(job_path).read_text(encoding="utf-8-sig"))
    out_dir = Path(job["out_dir"])
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    ref = reference()
    for i, text in enumerate(job["sentences"]):
        kw = dict(language_id="es", exaggeration=EXAGGERATION, cfg_weight=CFG_WEIGHT)
        if ref:
            kw["audio_prompt_path"] = str(ref)
        wav = model.generate(text, **kw)  # tensor float [1, n] a model.sr Hz
        pcm = (wav.squeeze(0).clamp(-1, 1) * 32767).to(torch.int16).numpy().tobytes()
        with wave.open(str(out_dir / f"tts_{i:03d}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(model.sr)
            w.writeframes(pcm)
        print(f"[tts] {i + 1}/{len(job['sentences'])}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
