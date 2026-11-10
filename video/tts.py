"""Kokoro narration per scene -> video/out/audio/<id>.wav + durations.json.

Run with the Python that has kokoro installed:
  ~/Projects/finance_vid/.venv/bin/python video/tts.py [--voice am_michael] [--speed 1.0] [--only S05,S06]
"""

import argparse
import json
import pathlib
import re
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from script import SCENES  # noqa: E402

SR = 24000
OUT = pathlib.Path(__file__).parent / "out" / "audio"
SPOKEN = [(r"\bKYC\b", "K Y C"), (r"\bTIN\b", "tin"), (r"\bOFAC\b", "oh fack"), (r"\bUN\b", "U N"),
          (r"\bGLEIF\b", "gleef"), (r"\bFastAPI\b", "Fast A P I"), (r"\bKYB\b", "K Y B"),
          (r"\bWekil\b", "weh-keel"), (r"\bBole\b", "Boh-lay"), (r"\bTana\b", "Tah-na"), (r"\bNeon\b", "Neon")]


def spoken(text: str) -> str:
    for pat, rep in SPOKEN:
        text = re.sub(pat, rep, text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="am_michael")
    ap.add_argument("--speed", type=float, default=0.97)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    from kokoro import KPipeline

    pipe = KPipeline(lang_code="a")
    OUT.mkdir(parents=True, exist_ok=True)
    durations_file = OUT / "durations.json"
    durations = json.loads(durations_file.read_text()) if durations_file.exists() else {}
    only = set(filter(None, a.only.split(",")))
    for s in SCENES:
        if only and s["id"] not in only:
            continue
        chunks = []
        for _, _, audio in pipe(spoken(s["say"]), voice=a.voice, speed=a.speed, split_pattern=r"(?<=[.!?])\s+"):
            chunks += [audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio), np.zeros(int(SR * 0.28))]
        wav = np.concatenate(chunks[:-1])
        sf.write(OUT / f"{s['id']}.wav", wav, SR)
        durations[s["id"]] = round(len(wav) / SR, 2)
        print(s["id"], durations[s["id"]], "s", flush=True)
    durations_file.write_text(json.dumps(durations, indent=1))
    print("total", round(sum(durations.values()) / 60, 1), "min")


if __name__ == "__main__":
    main()
