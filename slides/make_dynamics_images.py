"""Stills, video covers and equation images for the dynamics deck and the friction-push slides.

    ./run.sh slides/make_dynamics_images.py   (needs 08_dynamics/frames and 09_friction_push/take_*/frames)
"""
import os
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IMG = os.path.join(ROOT, "slides", "img")
plt.rcParams.update({"mathtext.fontset": "cm"})


def eq(name, tex, color="#1B2333", size=40):
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, tex, fontsize=size, color=color)
    fig.savefig(os.path.join(IMG, name), dpi=200, transparent=True, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def still(src, name, crop=None):
    im = Image.open(src).convert("RGB")
    if crop:
        im = im.crop(crop)
    im.save(os.path.join(IMG, name), quality=90)


def frame_of(video, t, name):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", "-q:v", "3",
                    os.path.join(IMG, name)], check=True)


eq("eq_motion.png", r"$M(q)\,\ddot{q} + C(q,\dot{q})\,\dot{q} + g(q) = \tau$", size=44)
eq("eq_forward.png", r"$\ddot{q} = M(q)^{-1}\,(\tau - C\dot{q} - g)$")
eq("eq_inverse.png", r"$\tau = M(q)\,\ddot{q} + C\dot{q} + g(q)$")
eq("eq_forward_w.png", r"$\ddot{q} = M(q)^{-1}\,(\tau - C\dot{q} - g)$", color="#FFFFFF")
eq("eq_inverse_w.png", r"$\tau = M(q)\,\ddot{q} + C\dot{q} + g(q)$", color="#FFFFFF")
eq("eq_pendulum.png", r"$I\,\ddot{\theta} + m\,g\,l\,\sin\theta = \tau$")

F = os.path.join(ROOT, "08_dynamics", "frames")
still(os.path.join(F, "00200.png"), "dyn_fall.jpg", (200, 80, 1700, 1000))      # fallen
still(os.path.join(F, "00400.png"), "dyn_hover.jpg", (200, 80, 1700, 1000))     # floating
still(os.path.join(F, "01000.png"), "dyn_track.jpg", (200, 80, 1700, 1000))     # tracking
still(os.path.join(F, "00000.png"), "dyn_start.jpg", (200, 80, 1700, 1000))
V = os.path.join(ROOT, "videos", "edited")
N = os.path.join(ROOT, "videos", "narrated")  # covers match the narrated videos the decks embed
frame_of(os.path.join(N, "08a_dynamics_math.mp4"), 52, "cover_08a_dynamics_math.jpg")
frame_of(os.path.join(N, "08b_dynamics_franka.mp4"), 45, "cover_08b_dynamics_franka.jpg")
frame_of(os.path.join(V, "08a_dynamics_math.mp4"), 72, "dyn_math_inverse.jpg")
frame_of(os.path.join(N, "09_friction_push.mp4"), 30, "cover_09_friction_push.jpg")
P = os.path.join(ROOT, "09_friction_push")
still(os.path.join(P, "take_rough", "frames", "00190.png"), "t9_push_rough.jpg", (160, 60, 1760, 960))
still(os.path.join(P, "take_smooth", "frames", "00190.png"), "t9_push_smooth.jpg", (160, 60, 1760, 960))
print("ok")
