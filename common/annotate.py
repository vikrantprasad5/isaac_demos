"""Burn captions into a demo video.

Captions are rendered as transparent PNG cards (Pillow) and overlaid with
ffmpeg, fading in and out. Usage:

    python3 common/annotate.py 01_follow_target/captions.json videos/01_follow_target.mp4 videos/01_follow_target_captioned.mp4

captions.json:
    {"badge": "Topic 3 - Robot Kinematics", "position": "bottom",  # or "top"
     "captions": [{"start": 0, "end": 3.5, "title": "...", "body": "..."}, ...]}
"""

import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FONT_BOLD = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"
FADE = 0.4
ACCENT = (255, 196, 0, 255)


def wrap(draw, text, font, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def caption_card(title, body, path, position="bottom"):
    """Lower-third card: accent bar, bold title, wrapped body text."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(FONT_BOLD, 52)
    body_font = ImageFont.truetype(FONT_REGULAR, 38)
    pad, margin, max_text = 36, 80, 1400
    body_lines = wrap(draw, body, body_font, max_text) if body else []
    title_h = 62
    body_h = 50 * len(body_lines)
    box_h = pad * 2 + title_h + (14 + body_h if body_lines else 0)
    text_w = max([draw.textlength(title, font=title_font)] + [draw.textlength(l, font=body_font) for l in body_lines])
    box_w = int(text_w) + pad * 2 + 14
    x0 = margin
    if position == "top":
        y0 = 130
        y1 = y0 + box_h
    else:
        y1 = H - margin
        y0 = y1 - box_h
    draw.rounded_rectangle((x0, y0, x0 + box_w, y1), radius=18, fill=(10, 14, 22, 200))
    draw.rounded_rectangle((x0, y0, x0 + 10, y1), radius=5, fill=ACCENT)
    tx = x0 + pad + 14
    draw.text((tx, y0 + pad), title, font=title_font, fill=(255, 255, 255, 255))
    y = y0 + pad + title_h + 14
    for line in body_lines:
        draw.text((tx, y), line, font=body_font, fill=(220, 226, 235, 255))
        y += 50
    img.save(path)


def badge_card(text, path):
    """Small persistent label, top-left."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_BOLD, 30)
    pad = 16
    w = int(draw.textlength(text, font=font)) + pad * 2
    draw.rounded_rectangle((40, 40, 40 + w, 40 + 30 + pad * 2), radius=12, fill=(10, 14, 22, 170))
    draw.text((40 + pad, 40 + pad - 2), text, font=font, fill=ACCENT)
    img.save(path)


def main(spec_path, in_mp4, out_mp4):
    spec = json.load(open(spec_path))
    tmp = tempfile.mkdtemp(prefix="captions_")
    inputs, filters, last = ["-i", in_mp4], [], "[0:v]"
    cards = []
    if spec.get("badge"):
        path = os.path.join(tmp, "badge.png")
        badge_card(spec["badge"], path)
        cards.append((path, 0.0, None))
    for i, cap in enumerate(spec["captions"]):
        path = os.path.join(tmp, f"cap{i:02d}.png")
        caption_card(cap["title"], cap.get("body", ""), path, spec.get("position", "bottom"))
        cards.append((path, float(cap["start"]), float(cap["end"])))

    for i, (path, start, end) in enumerate(cards, start=1):
        inputs += ["-loop", "1", "-i", path]
        if end is None:
            filters.append(f"[{i}:v]format=rgba[c{i}]")
            enable = ""
        else:
            fade_in = f"fade=t=in:st={start}:d={FADE}:alpha=1"
            fade_out = f"fade=t=out:st={end - FADE}:d={FADE}:alpha=1"
            filters.append(f"[{i}:v]format=rgba,{fade_in},{fade_out}[c{i}]")
            enable = f":enable='between(t,{start},{end})'"
        out = f"[v{i}]"
        filters.append(f"{last}[c{i}]overlay=0:0:shortest=1{enable}{out}")
        last = out

    cmd = [
        "ffmpeg", "-loglevel", "error", "-y", *inputs,
        "-filter_complex", ";".join(filters), "-map", last,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "slow", "-movflags", "+faststart",
        out_mp4,
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
