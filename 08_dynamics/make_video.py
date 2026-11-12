"""Build video 8b from the Isaac Sim frames + data.json: live equation and torque plot beside the Franka.

    ./run.sh 08_dynamics/record.py       # frames + data.json
    ./run.sh 08_dynamics/make_video.py   # -> videos/raw/08b_dynamics_franka.mp4 and videos/edited/ (with overlay)
"""

import json
import os
import shutil
import subprocess
import sys
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
FRAMES = os.path.join(HERE, "frames")
FPS = 30
W, H = 1920, 1080
for f in ("Ubuntu-R.ttf", "Ubuntu-B.ttf"):
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/ubuntu/" + f)
plt.rcParams.update({"font.family": ["Ubuntu", "DejaVu Sans"], "mathtext.fontset": "cm"})

PANEL = "#0E1726"
WHITE, SOFT, MUTED = "#FFFFFF", "#C9D1DD", "#8793A6"
YELLOW, BLUE, RED, GREEN, ORANGE = "#FFC400", "#4F9FD1", "#E0393E", "#2EAD5B", "#F28C28"

TAKES = {
    "fall": dict(
        kicker="Forward dynamics", color=BLUE, title="Motors off:  τ = 0",
        eq=r"$\ddot{q} = M(q)^{-1}\,(\tau - C\dot{q} - g(q))$",
        lines=["We only give torques. PhysX solves for q̈", "and integrates: gravity wins, the arm falls."],
        plot="angle"),
    "hover": dict(
        kicker="Inverse dynamics", color=RED, title="Motors give exactly  τ = g(q)",
        eq=r"$\tau = M\ddot{q} + C\dot{q} + g(q)$",
        lines=["Holding still: q̈ = q̇ = 0, only g(q) is left.", "No position control: the torque cancels", "gravity exactly, and the arm floats."],
        plot="torque"),
    "track": dict(
        kicker="Inverse dynamics", color=RED, title="Torques for a desired motion",
        eq=r"$\tau = M(q)\,(\ddot{q}_d + K_p e + K_d \dot{e}) + C\dot{q} + g(q)$",
        lines=["Waves on 4 joints, torques computed each step.", "Shoulder: mostly gravity.", "Base (vertical axis): no gravity, only inertia."],
        plot="torque"),
}
J = 1  # panda_joint2 (shoulder pitch): carries most of the gravity load


def load():
    data = json.load(open(os.path.join(HERE, "data.json")))
    starts = {}
    for e in data:
        starts.setdefault(e["take"], e)
    return data, starts


DATA, STARTS = load()


def render(k):
    e = DATA[k]
    take = e["take"]
    cfg = TAKES[take]
    img = np.asarray(Image.open(os.path.join(FRAMES, f"{e['frame']:05d}.png")).convert("RGB"))
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img, extent=(0, W, H, 0))
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    x0, y0, pw, ph = 1330, 60, 560, 960
    ax.add_patch(FancyBboxPatch((x0, y0), pw, ph, boxstyle="round,pad=0,rounding_size=18", fc=PANEL, ec=PANEL, alpha=0.9))
    ax.add_patch(FancyBboxPatch((x0, y0), 10, ph, boxstyle="round,pad=0,rounding_size=5", fc=cfg["color"], ec=cfg["color"]))
    tx = x0 + 45
    ax.text(tx, y0 + 60, cfg["kicker"], fontsize=24, color=cfg["color"], fontweight="bold")
    ax.text(tx, y0 + 115, cfg["title"], fontsize=27, color=WHITE, fontweight="bold")
    ax.text(tx, y0 + 195, cfg["eq"], fontsize=24 if take != "track" else 19, color=WHITE)
    for i, line in enumerate(cfg["lines"]):
        ax.text(tx, y0 + 250 + 34 * i, line, fontsize=17, color=SOFT)

    rows = [d for d in DATA[: k + 1] if d["take"] == take]
    t = np.array([d["t"] for d in rows])
    pa = fig.add_axes([(tx + 70) / W, 1 - 930 / H, 400 / W, 420 / H])
    pa.set_facecolor("#1B2333")
    for s in pa.spines.values():
        s.set_color(MUTED)
    pa.tick_params(colors=SOFT, labelsize=14)
    pa.grid(color="#2B3547")
    dur = max(d["t"] for d in DATA if d["take"] == take) + 0.1
    pa.set_xlim(0, dur)
    pa.set_xlabel("time (s)", color=SOFT, fontsize=16)
    if cfg["plot"] == "angle":
        q = np.array([d["q"][J] for d in rows])
        pa.plot(t, q, color=YELLOW, lw=3, label="shoulder angle $q_2$")
        pa.set_ylim(0, 2.0)
        pa.set_ylabel("angle (rad)", color=SOFT, fontsize=16)
        g = np.array([d["g"][J] for d in rows])
        pa.legend(loc="upper left", facecolor="#1B2333", edgecolor=MUTED, labelcolor=WHITE, fontsize=15)
        ax.text(tx, 440, f"Gravity torque nobody cancels: {abs(g[-1]):4.1f} N·m", fontsize=19, color=GREEN)
    else:
        tau = np.array([d["tau"][J] for d in rows])
        g = np.array([d["g"][J] for d in rows])
        pa.plot(t, tau, color=RED, lw=3, label=r"motor torque $\tau_2$")
        pa.plot(t, g, color=GREEN, lw=2.5, ls="--", label=r"gravity part $g_2(q)$")
        pa.set_ylim(-70, 10)
        pa.set_ylabel("shoulder torque (N·m)", color=SOFT, fontsize=16)
        pa.legend(loc="lower right", facecolor="#1B2333", edgecolor=MUTED, labelcolor=WHITE, fontsize=15)
        if take == "track":
            err = np.degrees(np.abs(np.array(rows[-1]["q"]) - np.array(rows[-1]["q_des"])).max())
            ax.text(tx, 440, f"tracking error {err:3.1f}°", fontsize=19, color=WHITE)
            pa.set_position([(tx + 70) / W, 1 - 700 / H, 400 / W, 200 / H])
            pa.set_xlabel("")
            pa.set_ylim(-50, -15)
            pa.set_ylabel("shoulder (N·m)", color=SOFT, fontsize=15)
            pa.legend(loc="lower right", facecolor="#1B2333", edgecolor=MUTED, labelcolor=WHITE, fontsize=12)
            pb = fig.add_axes([(tx + 70) / W, 1 - 975 / H, 400 / W, 200 / H])
            pb.set_facecolor("#1B2333")
            for sp in pb.spines.values():
                sp.set_color(MUTED)
            pb.tick_params(colors=SOFT, labelsize=14)
            pb.grid(color="#2B3547")
            pb.set_xlim(0, dur)
            pb.set_ylim(-4.5, 4.5)
            pb.plot(t, [d["tau"][0] for d in rows], color=RED, lw=3, label=r"motor torque $\tau_1$")
            pb.plot(t, [d["inertia"][0] for d in rows], color=BLUE, lw=2.5, ls="--", label=r"inertia part $(M\ddot{q})_1$")
            pb.plot(t, [d["g"][0] for d in rows], color=GREEN, lw=2, ls=":", label=r"gravity part $= 0$")
            pb.set_ylabel("base (N·m)", color=SOFT, fontsize=15)
            pb.set_xlabel("time (s)", color=SOFT, fontsize=16)
            pb.set_title("base: τ₁ (red) = inertia part (blue), gravity part = 0", color=SOFT, fontsize=13, loc="left")
        else:
            ax.text(tx, 440, f"shoulder: τ₂ = {tau[-1]:+5.1f} N·m  =  g₂(q)", fontsize=19, color=WHITE)
    ax.text(80, 110, "Topic · Robot Dynamics", fontsize=20, color=YELLOW, fontweight="bold")
    out = os.path.join(HERE, "_seq", f"{k:05d}.png")
    fig.savefig(out)
    plt.close(fig)


def encode(src, out):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", src, "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out], check=True)


def main():
    seq = os.path.join(HERE, "_seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    with Pool(max(os.cpu_count() - 2, 1)) as pool:
        pool.map(render, range(len(DATA)), chunksize=8)
    encode(os.path.join(FRAMES, "%05d.png"), os.path.join(ROOT, "videos", "raw", "08b_dynamics_franka.mp4"))
    encode(os.path.join(seq, "%05d.png"), os.path.join(ROOT, "videos", "edited", "08b_dynamics_franka.mp4"))
    shutil.rmtree(seq)
    print("wrote videos/{raw,edited}/08b_dynamics_franka.mp4")


if __name__ == "__main__":
    main()
