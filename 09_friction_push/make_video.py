"""Build video 9: rough vs smooth push side by side, with the live push force (effort) underneath.

    ./run.sh 09_friction_push/record.py --take rough
    ./run.sh 09_friction_push/record.py --take smooth
    ./run.sh 09_friction_push/make_video.py   # -> videos/raw/09_friction_push.mp4, videos/edited/09_friction_push.mp4
"""

import json
import os
import shutil
import subprocess
from multiprocessing import Pool

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FPS = 30
W, H = 1920, 1080
HOLD = 3.0  # seconds to hold the last frame with the summary
for f in ("Ubuntu-R.ttf", "Ubuntu-B.ttf"):
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/ubuntu/" + f)
plt.rcParams.update({"font.family": ["Ubuntu", "DejaVu Sans"], "mathtext.fontset": "cm"})

BG, PANEL = "#0E1726", "#1B2333"
WHITE, SOFT, MUTED = "#FFFFFF", "#C9D1DD", "#8793A6"
YELLOW, RED, BLUE, GREEN = "#FFC400", "#E0393E", "#4F9FD1", "#2EAD5B"
TAKES = {
    "rough": dict(label="Rough surface", mu=r"$\mu_s = 1.0,\ \mu_k = 0.6$", color=RED),
    "smooth": dict(label="Smooth surface", mu=r"$\mu_s = 0.04,\ \mu_k = 0.03$", color=BLUE),
}
SMOOTH_WIN = 3  # physics samples (120 Hz) averaged for the plot: keeps the real ripple, drops single-step spikes


def load(take):
    d = json.load(open(os.path.join(HERE, f"data_{take}.json")))
    t = np.array([e["t"] for e in d])
    push = np.array([e["push"][1] for e in d])
    push = np.convolve(push, np.ones(SMOOTH_WIN) / SMOOTH_WIN, mode="same")
    frames = [(e["frame"], e["t"]) for e in d if e["frame"] is not None]
    return t, push, frames


DATA = {k: load(k) for k in TAKES}
N = min(len(DATA[k][2]) for k in TAKES)
STEADY = (6.0, 11.0)


def stats(take):
    t, push, _ = DATA[take]
    m = (t > STEADY[0]) & (t < STEADY[1])
    return push[m].mean(), push[m].std()


def render(k):
    i = min(k, N - 1)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    for col, take in enumerate(TAKES):
        cfg = TAKES[take]
        frame, t_now = DATA[take][2][i]
        img = Image.open(os.path.join(HERE, f"take_{take}", "frames", f"{frame:05d}.png")).convert("RGB")
        img = img.crop((160, 60, 1760, 960)).resize((960, 540))
        ax.imshow(np.asarray(img), extent=(col * 960, col * 960 + 960, 540, 0))
        x = col * 960 + 30
        ax.add_patch(FancyBboxPatch((x, 22), 470, 92, boxstyle="round,pad=0,rounding_size=12", fc=BG, ec=cfg["color"],
                                    lw=3, alpha=0.88))
        ax.text(x + 22, 62, cfg["label"], fontsize=27, color=cfg["color"], fontweight="bold")
        ax.text(x + 22, 100, cfg["mu"], fontsize=22, color=WHITE)
    ax.plot([960, 960], [0, 540], color=BG, lw=6)
    t_now = DATA["rough"][2][i][1]

    # bottom: live push force
    pa = fig.add_axes([90 / W, 1 - 1020 / H, 1060 / W, 420 / H])
    pa.set_facecolor(PANEL)
    for s in pa.spines.values():
        s.set_color(MUTED)
    pa.tick_params(colors=SOFT, labelsize=16)
    pa.grid(color="#2B3547")
    pa.set_xlim(3.5, 13.0)
    pa.set_ylim(-1, 30)
    pa.set_xlabel("time (s)", color=SOFT, fontsize=18)
    pa.set_ylabel("push force from the robot (N)", color=SOFT, fontsize=18)
    for take, cfg in TAKES.items():
        t, push, _ = DATA[take]
        m = t <= t_now
        pa.plot(t[m], push[m], color=cfg["color"], lw=2.5, label=cfg["label"])
    pa.legend(loc="upper left", facecolor=PANEL, edgecolor=MUTED, labelcolor=WHITE, fontsize=17)
    ax.text(90, 585, "Effort: how hard the robot has to push", fontsize=26, color=WHITE, fontweight="bold")

    # right: numbers + physics
    x0 = 1250
    ax.add_patch(FancyBboxPatch((x0 - 20, 560), 690, 480, boxstyle="round,pad=0,rounding_size=16", fc=PANEL, ec=PANEL))
    ax.text(x0 + 10, 615, "Kinetic friction", fontsize=24, color=YELLOW, fontweight="bold")
    ax.text(x0 + 10, 680, r"$F_{push} \approx F_{friction} = \mu_k\, N$", fontsize=34, color=WHITE)
    ax.text(x0 + 10, 725, "same 2 kg block (N ≈ 20-24 N), same motion", fontsize=18, color=SOFT)
    if t_now > STEADY[0]:
        rows = [(take, *stats(take)) for take in TAKES]
        ax.text(x0 + 10, 790, "while sliding", fontsize=18, color=MUTED)
        ax.text(x0 + 330, 790, "effort", fontsize=18, color=MUTED)
        ax.text(x0 + 480, 790, "bumpiness", fontsize=18, color=MUTED)
        for r, (take, mean, std) in enumerate(rows):
            y = 840 + 55 * r
            c = TAKES[take]["color"]
            ax.text(x0 + 10, y, TAKES[take]["label"], fontsize=22, color=c, fontweight="bold")
            ax.text(x0 + 330, y, f"{mean:4.1f} N", fontsize=24, color=WHITE, fontweight="bold")
            ax.text(x0 + 480, y, f"± {std:4.2f} N", fontsize=24, color=WHITE)
        ratio = stats("rough")[0] / max(stats("smooth")[0], 1e-6)
        ax.text(x0 + 10, 975, f"Rough needs ~{ratio:.0f}× the effort, and the force", fontsize=20, color=YELLOW)
        ax.text(x0 + 10, 1008, "chatters as the surfaces grip and let go.", fontsize=20, color=YELLOW)
    else:
        ax.text(x0 + 10, 820, "Watch the two curves once the", fontsize=20, color=SOFT)
        ax.text(x0 + 10, 852, "fingers touch the block.", fontsize=20, color=SOFT)
    ax.text(W - 40, 1065, "Topic 9 · Contact Mechanics & Friction", fontsize=15, color=MUTED, ha="right")
    fig.savefig(os.path.join(HERE, "_seq", f"{k:05d}.png"), facecolor=BG)
    plt.close(fig)


def encode(src, out):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", src, "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out], check=True)


def main():
    seq = os.path.join(HERE, "_seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    total = N + int(HOLD * FPS)
    with Pool(max(os.cpu_count() - 2, 1)) as pool:
        pool.map(render, range(total), chunksize=8)
    encode(os.path.join(seq, "%05d.png"), os.path.join(ROOT, "videos", "edited", "09_friction_push.mp4"))
    # raw: the two clean takes side by side
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i",
                    os.path.join(HERE, "take_rough", "frames", "%05d.png"), "-framerate", str(FPS), "-i",
                    os.path.join(HERE, "take_smooth", "frames", "%05d.png"), "-filter_complex",
                    "[0]scale=960:540[a];[1]scale=960:540[b];[a][b]hstack", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "18", "-movflags", "+faststart", os.path.join(ROOT, "videos", "raw", "09_friction_push.mp4")],
                   check=True)
    shutil.rmtree(seq)
    print("wrote videos/{raw,edited}/09_friction_push.mp4")


if __name__ == "__main__":
    main()
