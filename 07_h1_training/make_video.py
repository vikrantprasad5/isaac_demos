"""Build video 7 from the recorded clips: training montage + tests of the final policy.

    python3 07_h1_training/make_video.py

Needs 07_h1_training/clips/*.mp4 (record_all.sh) and training_curve.json (parsed from the training log).
Writes videos/raw/07_h1_training.mp4 and videos/edited/07_h1_training.mp4 (stage panel + captions).
"""

import json
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
from common import annotate

CLIPS = os.path.join(HERE, "clips")
FONT_BOLD = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"
ACCENT = (255, 196, 0)
TOTAL_ROUNDS = 2000
TRAIN_MINUTES = 33  # wall-clock time of the whole run on one RTX 5070

CURVE = json.load(open(os.path.join(HERE, "training_curve.json")))


def stage(c):
    row = CURVE[str(c)]
    minutes = c / TOTAL_ROUNDS * TRAIN_MINUTES
    when = "before any training" if c == 0 else f"after {minutes:.0f} min of training" if minutes >= 1 else "after 1 min of training"
    return [
        (f"Training round {c + 1 if c == TOTAL_ROUNDS - 1 else c} / {TOTAL_ROUNDS}", True),
        (when, False),
        (f"Stays up: {min(row['eplen'] / 50, 20):.1f} s of 20 s", False),
    ]


# (clip, seconds used, skip from start, panel lines)
SEGMENTS = [
    ("grid_0000", 4.0, 0.0, stage(0)),
    ("grid_0050", 5.0, 0.0, stage(50)),
    ("grid_0150", 5.0, 0.0, stage(150)),
    ("grid_0400", 5.0, 0.0, stage(400)),
    ("grid_1000", 5.0, 0.0, stage(1000)),
    ("grid_1999", 6.0, 0.0, stage(1999)),
    ("ice", 6.0, 0.0, [("Test: slippery floor", True), ("friction 0.2", False)]),
    ("heavy", 6.0, 0.0, [("Test: heavy load", True), ("+15 kg on the torso", False)]),
    ("push", 7.0, 0.0, [("Test: shoves", True), ("random push every 2-3 s", False)]),
    ("combo", 7.0, 0.0, [("Test: all at once", True), ("slippery + heavy + shoves", False)]),
    ("stairs", 10.0, 0.0, [("Test: stairs", True), ("up a 1 m stair pyramid", False)]),
]


def panel(lines, path):
    img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    big = ImageFont.truetype(FONT_BOLD, 44)
    small = ImageFont.truetype(FONT_REGULAR, 34)
    pad, gap = 28, 12
    sizes = [(draw.textlength(t, font=big if b else small), 50 if b else 40) for t, b in lines]
    w = max(s[0] for s in sizes) + 2 * pad
    h = sum(s[1] for s in sizes) + gap * (len(lines) - 1) + 2 * pad
    x0, y0 = 1920 - 40 - w, 40
    draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=18, fill=(10, 14, 22, 200))
    y = y0 + pad
    for (text, bold), (_, lh) in zip(lines, sizes):
        draw.text((x0 + pad, y), text, font=big if bold else small, fill=ACCENT if bold else (235, 238, 245))
        y += lh + gap
    img.save(path)


def run(cmd):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + cmd, check=True)


def build(out_mp4, overlay):
    tmp = os.path.join(HERE, "_parts")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    parts = []
    for k, (name, dur, skip, lines) in enumerate(SEGMENTS):
        src = os.path.join(CLIPS, f"{name}.mp4")
        part = os.path.join(tmp, f"{k:02d}.mp4")
        fade = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.25}:d=0.25"
        if overlay:
            png = os.path.join(tmp, f"{k:02d}.png")
            panel(lines, png)
            run(["-ss", str(skip), "-t", str(dur), "-i", src, "-i", png, "-filter_complex",
                 f"[0:v][1:v]overlay=0:0,{fade},fps=50,format=yuv420p", "-c:v", "libx264", "-crf", "18", part])
        else:
            run(["-ss", str(skip), "-t", str(dur), "-i", src, "-vf", f"{fade},fps=50,format=yuv420p",
                 "-c:v", "libx264", "-crf", "18", part])
        parts.append(part)
    listing = os.path.join(tmp, "list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    run(["-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", "-movflags", "+faststart", out_mp4])
    shutil.rmtree(tmp)


def main():
    videos = os.path.join(ROOT, "videos")
    raw = os.path.join(videos, "raw", "07_h1_training.mp4")
    build(raw, overlay=False)
    staged = os.path.join(HERE, "_staged.mp4")
    build(staged, overlay=True)
    annotate.main(os.path.join(HERE, "captions.json"), staged, os.path.join(videos, "edited", "07_h1_training.mp4"))
    os.remove(staged)
    print("wrote", raw, "and captioned copy")


if __name__ == "__main__":
    main()
