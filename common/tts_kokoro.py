"""Offline text-to-speech with Kokoro-82M: one wav per beat plus word timings.

Runs in a Python env that has `kokoro` and `soundfile` (set KOKORO_PY for common/narrate.py):
    $KOKORO_PY common/tts_kokoro.py narration.json out_dir

narration.json: {"voice": "am_michael", "speed": 1.0, "beats": [{"at": 0.5, "text": "..."}, ...]}
Writes out_dir/beat_NN.wav and out_dir/tts.json = [{"file", "duration", "words": [{"w", "ws", "start", "end"}]}].
"""

import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SR = 24000


def main(narration, out):
    cfg = json.load(open(narration))
    voice = cfg.get("voice", "am_michael")
    speed = float(cfg.get("speed", 1.0))
    os.makedirs(out, exist_ok=True)
    pipe = KPipeline(lang_code="a" if voice[0] == "a" else "b", repo_id="hexgrad/Kokoro-82M")
    result = []
    for i, beat in enumerate(cfg["beats"]):
        chunks, words, off = [], [], 0.0
        for r in pipe(beat["say"] if "say" in beat else beat["text"], voice=voice, speed=speed, split_pattern=r"\n+"):
            audio = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
            for tok in r.tokens or []:
                if tok.start_ts is not None and tok.end_ts is not None and tok.text.strip():
                    words.append({"w": tok.text, "ws": tok.whitespace or "", "start": round(off + float(tok.start_ts), 3),
                                  "end": round(off + float(tok.end_ts), 3)})
            chunks.append(audio)
            off += len(audio) / SR
        audio = np.concatenate(chunks).astype(np.float32)
        name = f"beat_{i:02d}.wav"
        sf.write(os.path.join(out, name), audio, SR)
        result.append({"file": name, "duration": round(len(audio) / SR, 3), "words": words})
        print(f"[tts] beat {i}: {len(audio) / SR:5.2f} s  {beat['text'][:60]}", flush=True)
    json.dump(result, open(os.path.join(out, "tts.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
