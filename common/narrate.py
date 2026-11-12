"""Add an AI voice-over (offline Kokoro TTS) and word-timed captions in a bottom band to a demo video.

    python3 common/narrate.py 08_dynamics/narration_math.json videos/edited/08a_dynamics_math.mp4 videos/narrated/08a_dynamics_math.mp4

narration.json:
    {"voice": "am_michael", "speed": 1.0,
     "beats": [{"at": 0.5, "text": "Sentence(s) spoken from 0.5 s of the source video."}, ...]}

Each beat starts at its `at` time in the source video. If the previous beat is still speaking then, the video
freezes on that frame until the narrator catches up, so speech always matches the picture. The source picture is
scaled into the top of the frame and the captions sit in a band underneath, so they never cover the video.
TTS runs in the env named by KOKORO_PY (default: the jetbot_ramp reels env that has kokoro installed).
"""

import hashlib
import json
import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KOKORO_PY = os.environ.get("KOKORO_PY", os.path.expanduser("~/jetbot_ramp/reels/.tts/bin/python"))
SR = 24000
GAP = 0.35        # silence between beats
TAIL = 1.0        # keep the last frame this long after the last word
W, H = 1920, 1080
VW, VH = 1664, 936  # picture size; band of H - VH px below for captions
BG = "0E1726"
MAX_CHARS = 62


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def tts(narration, work):
    key = hashlib.sha1(open(narration, "rb").read()).hexdigest()
    stamp = os.path.join(work, "key.txt")
    if not (os.path.exists(stamp) and open(stamp).read() == key):
        os.makedirs(work, exist_ok=True)
        run([KOKORO_PY, os.path.join(HERE, "tts_kokoro.py"), narration, work])
        open(stamp, "w").write(key)
    return json.load(open(os.path.join(work, "tts.json")))


def read_wav(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def schedule(beats, clips, src_len):
    """Returns per-beat output start times and the freezes [(source_time, seconds)]."""
    offset, prev_end, starts, freezes = 0.0, -1e9, [], []
    for beat, clip in zip(beats, clips):
        want = beat["at"] + offset
        if prev_end + GAP > want:
            d = prev_end + GAP - want
            freezes.append((beat["at"], d))
            offset += d
            want += d
        starts.append(want)
        prev_end = want + clip["duration"]
    end_out = src_len + offset
    if prev_end + TAIL > end_out:
        freezes.append((src_len, prev_end + TAIL - end_out))
    return starts, freezes


def chunks(words):
    """Split word tokens into caption lines: break at sentence ends, or before MAX_CHARS."""
    lines, cur = [], []

    def text(ws):
        return "".join(w["w"] + w["ws"] for w in ws).strip()

    for w in words:
        if cur and len(text(cur + [w])) > MAX_CHARS:
            # prefer breaking after a comma/colon inside the current line
            cut = max((i for i, x in enumerate(cur[:-1]) if x["w"] in ",:;"), default=None)
            if cut is not None and cut > len(cur) // 3:
                lines.append(cur[: cut + 1])
                cur = cur[cut + 1:]
            else:
                lines.append(cur)
                cur = []
        cur.append(w)
        if w["w"] in ".?!":
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return [(text(l), l[0]["start"], l[-1]["end"]) for l in lines if text(l)]


def ass_time(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def write_ass(path, events):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Ubuntu,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,60,60,{(H - VH) // 2 - 22},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w") as f:
        f.write(head)
        for text, a, b in events:
            f.write(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Cap,,0,0,0,,{text}\n")


def main(narration, src, dst):
    cfg = json.load(open(narration))
    beats = cfg["beats"]
    work = os.path.join(os.path.dirname(os.path.abspath(narration)), "_tts_" + os.path.splitext(os.path.basename(narration))[0])
    clips = tts(narration, work)
    src_len = duration(src)
    starts, freezes = schedule(beats, clips, src_len)
    total = src_len + sum(d for _, d in freezes)
    for t, d in freezes:
        print(f"[narrate] freeze {d:4.1f} s at {t:5.1f} s", flush=True)

    # audio track
    audio = np.zeros(int((total + 0.5) * SR), np.float32)
    events = []
    for s, clip in zip(starts, clips):
        a = read_wav(os.path.join(work, clip["file"]))
        i = int(s * SR)
        audio[i:i + len(a)] += a
        for text, a0, a1 in chunks(clip["words"]):
            events.append([text, s + a0, s + a1 + 0.25])
    for k in range(len(events) - 1):  # no overlapping captions
        events[k][2] = min(events[k][2], events[k + 1][1])
    wav_path = os.path.join(work, "voice.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    ass_path = os.path.join(work, "captions.ass")
    write_ass(ass_path, events)

    # video: freezes, then picture in the top of the frame, captions in the band below
    cuts = sorted(freezes)
    parts, filters, t0 = [], [], 0.0
    for k, (t, d) in enumerate(cuts + [(src_len, 0.0)]):
        if t > t0 + 1e-3 or d > 0:
            tt = max(t, t0 + 1.0 / 30)
            pad = f",tpad=stop_mode=clone:stop_duration={d:.3f}" if d > 0 else ""
            filters.append(f"[0:v]trim=start={t0:.3f}:end={tt:.3f},setpts=PTS-STARTPTS{pad}[s{k}]")
            parts.append(f"[s{k}]")
            t0 = tt
    filters.append(f"{''.join(parts)}concat=n={len(parts)}:v=1:a=0[cat]")
    filters.append(f"[cat]scale={VW}:{VH},pad={W}:{H}:{(W - VW) // 2}:0:color=0x{BG},"
                   f"subtitles='{ass_path}':fontsdir=/usr/share/fonts/truetype/ubuntu[v]")
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-i", wav_path, "-filter_complex", ";".join(filters),
         "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", "30",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", dst])
    print(f"[narrate] wrote {dst}: {duration(dst):.1f} s (source {src_len:.1f} s)", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
