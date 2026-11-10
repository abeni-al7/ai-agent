"""Split your own voice recording into per-scene clips, using Whisper word timings matched against the script.

  python3 video/align.py my-voice.m4a        -> video/out/voice/S01.wav ... + durations.json + check.txt

Then: node video/record.mjs --timing out/voice/durations.json --out out/run-voice
      node video/build.mjs --run out/run-voice --audio out/voice --out out/wekil-demo-voice.mp4
Each scene's clip starts when that scene starts on screen, so the picture follows your pacing.
"""

import difflib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from script import SCENES  # noqa: E402

MODEL = pathlib.Path.home() / ".cache/whisper-models/ggml-small.en.bin"
OUT = pathlib.Path(__file__).parent / "out" / "voice"


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def words_of(audio: str, tmp: str) -> list[tuple[str, float, float]]:
    wav = f"{tmp}/a.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", audio, "-ar", "16000", "-ac", "1", wav], check=True)
    subprocess.run(["whisper-cli", "-m", str(MODEL), "-f", wav, "-oj", "-ml", "1", "-sow", "-of", f"{tmp}/a", "-np"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    segs = json.loads(pathlib.Path(f"{tmp}/a.json").read_text())["transcription"]
    out = []
    for s in segs:
        w = norm(s["text"])
        if w:
            out.append((w, s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000))
    return out


def main(audio: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        heard = words_of(audio, tmp)
    said = [h[0] for h in heard]
    script_words, owner = [], []
    for i, s in enumerate(SCENES):
        for w in s["say"].split():
            if norm(w):
                script_words.append(norm(w))
                owner.append(i)
    # Map each scene's first word in the script to the matching word in the recording.
    sm = difflib.SequenceMatcher(a=script_words, b=said, autojunk=False)
    script_to_heard = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            script_to_heard[a + k] = b + k
    starts, check = [], []
    for i in range(len(SCENES)):
        idxs = [k for k, o in enumerate(owner) if o == i]
        hit = next((script_to_heard[k] for k in idxs[:12] if k in script_to_heard), None)
        if hit is None:
            check.append(f"{SCENES[i]['id']}: could not find the opening words; placed after the previous scene")
            starts.append(None)
        else:
            starts.append(max(0.0, heard[hit][1] - 0.15))
    for i, s in enumerate(starts):  # fill gaps from neighbours
        if s is None:
            starts[i] = starts[i - 1] + 1 if i else 0.0
    total = heard[-1][2] + 0.6 if heard else 0
    durations = {}
    for i, sc in enumerate(SCENES):
        end = starts[i + 1] if i + 1 < len(SCENES) else total
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", audio, "-ss", f"{starts[i]:.3f}", "-to", f"{end:.3f}",
                        "-ar", "48000", "-ac", "1", str(OUT / f"{sc['id']}.wav")], check=True)
        durations[sc["id"]] = round(end - starts[i], 2)
        print(sc["id"], f"{starts[i]:7.1f}s  {durations[sc['id']]:5.1f}s")
    (OUT / "durations.json").write_text(json.dumps(durations, indent=1))
    (OUT / "check.txt").write_text("\n".join(check) or "All scene openings found.")
    print("\n".join(check) or "All scene openings found.")


if __name__ == "__main__":
    main(sys.argv[1])
