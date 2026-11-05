"""Build video 5 from the 120 fps frames: real time (every 4th frame) + 4x slow-motion replay of the slip.

    python3 05_hand_grasp/make_video.py

Writes videos/raw/05_hand_grasp.mp4 and videos/edited/05_hand_grasp.mp4 (squeeze meter + captions).
"""

import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
from common import annotate

FRAMES = os.path.join(HERE, "frames")
CAPTURE_FPS = 120
SLOW = (11.5, 12.35)  # seconds of the take replayed at 4x slow motion
SQUEEZE_FULL = 0.8
RELAX = (7.0, 13.0)
FONT_BOLD = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"
ACCENT = (255, 196, 0)


def smooth(t, t0, t1):
    s = min(max((t - t0) / (t1 - t0), 0.0), 1.0)
    return s * s * (3 - 2 * s)


def squeeze_fraction(t):
    return 1.0 if t < RELAX[0] else 0.01 ** smooth(t, *RELAX)


def sequence():
    """(source frame index, take time, is_slow) for every output frame at 30 fps."""
    n = len(os.listdir(FRAMES))
    out = [(i, i / CAPTURE_FPS, False) for i in range(0, n, 4)]
    out += [(i, i / CAPTURE_FPS, True) for i in range(int(SLOW[0] * CAPTURE_FPS), int(SLOW[1] * CAPTURE_FPS))]
    return out


def draw_meter(img, frac, slow):
    draw = ImageDraw.Draw(img, "RGBA")
    x0, y0, w, h = 1560, 300, 120, 520
    label = ImageFont.truetype(FONT_BOLD, 34)
    value = ImageFont.truetype(FONT_BOLD, 44)
    draw.rounded_rectangle((x0 - 50, y0 - 120, x0 + w + 110, y0 + h + 110), radius=18, fill=(10, 14, 22, 190))
    draw.text((x0 + w / 2, y0 - 70), "Squeeze", font=label, fill=(255, 255, 255), anchor="mm")
    draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=10, outline=(200, 205, 215), width=3)
    fill_h = max(int((h - 12) * frac), 2)
    color = ACCENT if frac > 0.05 else (224, 57, 62)
    draw.rounded_rectangle((x0 + 6, y0 + h - 6 - fill_h, x0 + w - 6, y0 + h - 6), radius=6, fill=color)
    pct = f"{frac * 100:.0f}%" if frac >= 0.1 else f"{frac * 100:.1f}%"
    draw.text((x0 + w / 2, y0 + h + 55), pct, font=value, fill=color, anchor="mm")
    if slow:
        tag = ImageFont.truetype(FONT_BOLD, 40)
        draw.rounded_rectangle((1580, 40, 1880, 110), radius=12, fill=(224, 57, 62, 230))
        draw.text((1730, 75), "4x SLOW", font=tag, fill=(255, 255, 255), anchor="mm")


def build(out_mp4, overlay):
    tmp = os.path.join(HERE, "_seq")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for k, (i, t, slow) in enumerate(sequence()):
        src = os.path.join(FRAMES, f"{i:05d}.png")
        dst = os.path.join(tmp, f"{k:05d}.png")
        if overlay:
            img = Image.open(src).convert("RGB")
            draw_meter(img, squeeze_fraction(t), slow)
            img.save(dst)
        else:
            os.symlink(src, dst)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-framerate", "30", "-i", os.path.join(tmp, "%05d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out_mp4],
        check=True,
    )
    shutil.rmtree(tmp)


def main():
    videos = os.path.join(ROOT, "videos")
    raw = os.path.join(videos, "raw", "05_hand_grasp.mp4")
    build(raw, overlay=False)
    metered = os.path.join(HERE, "_metered.mp4")
    build(metered, overlay=True)
    annotate.main(os.path.join(HERE, "captions.json"), metered, os.path.join(videos, "edited", "05_hand_grasp.mp4"))
    os.remove(metered)
    print("wrote", raw, "and captioned copy")


if __name__ == "__main__":
    main()
