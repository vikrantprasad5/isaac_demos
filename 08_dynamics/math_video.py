"""Video 8a: the mathematics of forward and inverse dynamics, as an animated explainer.

A two-joint arm is simulated in pure NumPy and drawn with matplotlib (mathtext for the equations):

  1. One joint: I θ̈ + m g l sin θ = τ  (Newton's second law for rotation)
  2. Many joints: M(q) q̈ + C(q, q̇) q̇ + g(q) = τ, term by term
  3. Two questions, one equation: forward dynamics (τ -> motion) vs inverse dynamics (motion -> τ)
  4. Forward dynamics live: motors off, the simulator integrates q̈ = M⁻¹(τ − C q̇ − g)
  5. Inverse dynamics live: torques for a circle, slow then twice as fast (inertia ×4, gravity unchanged)
  6. The loop: controller = inverse dynamics, robot / simulator = forward dynamics

Run with Isaac Sim's Python (it ships matplotlib):
    ./run.sh 08_dynamics/math_video.py            # -> videos/raw/08a_dynamics_math.mp4 (+ copy in videos/edited)
    ./run.sh 08_dynamics/math_video.py --preview  # a few stills into 08_dynamics/preview/
"""

import argparse
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
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FPS = 30
W, H = 1920, 1080

for f in ("Ubuntu-R.ttf", "Ubuntu-B.ttf"):
    p = "/usr/share/fonts/truetype/ubuntu/" + f
    if os.path.exists(p):
        font_manager.fontManager.addfont(p)
plt.rcParams.update({"font.family": ["Ubuntu", "DejaVu Sans"], "mathtext.fontset": "cm", "axes.unicode_minus": False})

# Palette (same as the slide theme and caption cards).
BG = "#0E1726"
PANEL = "#1B2333"
WHITE = "#FFFFFF"
SOFT = "#C9D1DD"
MUTED = "#8793A6"
YELLOW = "#FFC400"
BLUE = "#4F9FD1"
RED = "#E0393E"
GREEN = "#2EAD5B"
ORANGE = "#F28C28"

# ------------------------------------------------------------------ two-link arm physics
L1, L2 = 1.0, 1.0          # link lengths (m)
M1, M2 = 2.0, 2.0          # link masses (kg)
LC1, LC2 = 0.5, 0.5        # centre of mass along each link
I1, I2 = M1 * L1**2 / 12, M2 * L2**2 / 12
G = 9.81


def mass_matrix(q):
    c2 = np.cos(q[1])
    m11 = M1 * LC1**2 + I1 + M2 * (L1**2 + LC2**2 + 2 * L1 * LC2 * c2) + I2
    m12 = M2 * (LC2**2 + L1 * LC2 * c2) + I2
    m22 = M2 * LC2**2 + I2
    return np.array([[m11, m12], [m12, m22]])


def coriolis(q, qd):
    h = M2 * L1 * LC2 * np.sin(q[1])
    return np.array([-h * (2 * qd[0] * qd[1] + qd[1] ** 2), h * qd[0] ** 2])


def gravity(q):
    """Angles measured from the horizontal, counter-clockwise positive, gravity along -y."""
    g2 = M2 * LC2 * G * np.cos(q[0] + q[1])
    return np.array([(M1 * LC1 + M2 * L1) * G * np.cos(q[0]) + g2, g2])


def forward_dynamics(q, qd, tau):
    return np.linalg.solve(mass_matrix(q), tau - coriolis(q, qd) - gravity(q))


def rk4(q, qd, tau_fn, dt, t):
    def f(state, tt):
        qq, vv = state[:2], state[2:]
        return np.concatenate([vv, forward_dynamics(qq, vv, tau_fn(qq, vv, tt))])

    s = np.concatenate([q, qd])
    k1 = f(s, t)
    k2 = f(s + dt / 2 * k1, t + dt / 2)
    k3 = f(s + dt / 2 * k2, t + dt / 2)
    k4 = f(s + dt * k3, t + dt)
    s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    return s[:2], s[2:]


def joints_xy(q):
    p1 = np.array([L1 * np.cos(q[0]), L1 * np.sin(q[0])])
    p2 = p1 + np.array([L2 * np.cos(q[0] + q[1]), L2 * np.sin(q[0] + q[1])])
    return p1, p2


SUB = 20  # physics substeps per video frame


def simulate_fall(seconds):
    """Motors off: τ = 0, start horizontal and at rest."""
    q, qd = np.array([0.0, 0.0]), np.zeros(2)
    out = []
    dt = 1.0 / (FPS * SUB)
    for k in range(int(seconds * FPS) + 1):
        qdd = forward_dynamics(q, qd, np.zeros(2))
        out.append((q.copy(), qd.copy(), qdd.copy()))
        for j in range(SUB):
            q, qd = rk4(q, qd, lambda a, b, c: np.zeros(2), dt, 0)
    return out


# Inverse-dynamics demo: the hand traces a circle, slow then twice as fast.
CIRCLE_C = np.array([1.05, 0.15])
CIRCLE_R = 0.42
ID_SECONDS = 34.0
SLOW_W = 2 * np.pi / 2.6
FAST_AT = (17.0, 18.0)  # speed doubles smoothly in this window


def smooth(t, t0, t1):
    s = np.clip((t - t0) / (t1 - t0), 0.0, 1.0)
    return s * s * (3 - 2 * s)


def circle_speed(t):
    return SLOW_W * smooth(t, 1.0, 2.5) * (1 + smooth(t, *FAST_AT))


def ik(p):
    c2 = (p[0] ** 2 + p[1] ** 2 - L1**2 - L2**2) / (2 * L1 * L2)
    q2 = np.arccos(np.clip(c2, -1, 1))  # elbow-down branch
    q1 = np.arctan2(p[1], p[0]) - np.arctan2(L2 * np.sin(q2), L1 + L2 * np.cos(q2))
    return np.array([q1, q2])


def plan_circle():
    dt = 1.0 / (FPS * SUB)
    ts = np.arange(0, ID_SECONDS + 1.0, dt)
    phase = np.cumsum([circle_speed(t) for t in ts]) * dt
    pts = CIRCLE_C + CIRCLE_R * np.stack([np.cos(phase - np.pi / 2), np.sin(phase - np.pi / 2)], 1)
    q = np.array([ik(p) for p in pts])
    q = np.unwrap(q, axis=0)
    qd = np.gradient(q, dt, axis=0)
    qdd = np.gradient(qd, dt, axis=0)
    return ts, pts, q, qd, qdd


def simulate_circle():
    """Computed torque: τ = M(q)(q̈_d + Kp e + Kd ė) + C q̇ + g, fed back into forward dynamics."""
    ts, pts, qd_plan, qdot_plan, qdd_plan = plan_circle()
    dt = ts[1] - ts[0]
    kp, kd = 200.0, 28.0
    q, qd = qd_plan[0].copy(), qdot_plan[0].copy()
    out = []
    for i in range(int(ID_SECONDS * FPS) + 1):
        k = i * SUB
        a = qdd_plan[k] + kp * (qd_plan[k] - q) + kd * (qdot_plan[k] - qd)
        Mq = mass_matrix(q)
        terms = {"inertia": Mq @ a, "coriolis": coriolis(q, qd), "gravity": gravity(q)}
        out.append((q.copy(), qd.copy(), terms, pts[k]))
        for j in range(SUB):
            kk = k + j

            def tau_fn(qq, vv, _t, kk=kk):
                aa = qdd_plan[kk] + kp * (qd_plan[kk] - qq) + kd * (qdot_plan[kk] - vv)
                return mass_matrix(qq) @ aa + coriolis(qq, vv) + gravity(qq)

            q, qd = rk4(q, qd, tau_fn, dt, 0)
    return out, pts


def simulate_pendulum(seconds):
    """Single joint: I θ̈ + m g l sin θ = τ, θ from straight down. Released at 90°, light damping."""
    m, l = 1.0, 1.0
    I = m * l * l
    th, w = np.pi / 2, 0.0
    out = []
    dt = 1.0 / (FPS * SUB)
    for k in range(int(seconds * FPS) + 1):
        acc = (-m * G * l * np.sin(th) - 0.15 * w) / I
        out.append((th, w, acc))
        for _ in range(SUB):
            acc = (-m * G * l * np.sin(th) - 0.15 * w) / I
            w += acc * dt
            th += w * dt
    return out


# ------------------------------------------------------------------ timeline
SCENES = [  # (name, seconds)
    ("pendulum", 26.0),
    ("equation", 18.0),
    ("questions", 18.0),
    ("forward", 26.0),
    ("inverse", ID_SECONDS),
    ("loop", 18.0),
]
TOTAL = sum(s for _, s in SCENES)

_cache = {}


def data(name):
    if name not in _cache:
        if name == "pendulum":
            _cache[name] = simulate_pendulum(26.0)
        elif name == "forward":
            _cache[name] = simulate_fall(26.0)
        elif name == "inverse":
            _cache[name] = simulate_circle()
    return _cache[name]


# ------------------------------------------------------------------ drawing helpers
class Frame:
    def __init__(self):
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        self.ax.set_facecolor(BG)
        self.renderer = self.fig.canvas.get_renderer()

    def text(self, x, y, s, size=30, color=WHITE, alpha=1.0, weight="normal", ha="left", va="baseline", **kw):
        if alpha <= 0:
            return None
        return self.ax.text(x, y, s, fontsize=size, color=color, alpha=min(alpha, 1.0), fontweight=weight,
                            ha=ha, va=va, **kw)

    def width(self, t):
        return 0 if t is None else t.get_window_extent(self.renderer).width

    def eq(self, x, y, parts, size=48, alpha=1.0, ha="left", gap=None):
        """Draw [(mathtext, color), ...] side by side. Returns [(x_center, width)] per part (pixels)."""
        texts, widths = [], []
        for s, c in parts:
            t = self.ax.text(0, y, s, fontsize=size, color=c, alpha=max(min(alpha, 1.0), 0.0), va="baseline")
            widths.append(t.get_window_extent(self.renderer).width)
            texts.append(t)
        gap = size * 0.18 if gap is None else gap
        x0 = x - (sum(widths) + gap * (len(widths) - 1)) / 2 if ha == "center" else x
        spans = []
        for t, w in zip(texts, widths):
            t.set_x(x0)
            spans.append((x0 + w / 2, w))
            x0 += w + gap
        return spans

    def box(self, x, y, w, h, color=PANEL, edge=None, alpha=1.0, lw=2.5, radius=18):
        if alpha <= 0:
            return
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                                         fc=color, ec=edge or color, lw=lw, alpha=min(alpha, 1.0)))

    def arrow(self, x1, y1, x2, y2, color=SOFT, alpha=1.0, lw=4, ms=34, style="-|>", rad=0.0):
        if alpha <= 0:
            return
        self.ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=ms, color=color,
                                          lw=lw, alpha=min(alpha, 1.0), connectionstyle=f"arc3,rad={rad}"))

    def header(self, title, sub=None, alpha=1.0):
        self.ax.add_patch(FancyBboxPatch((80, 60), 10, 80, boxstyle="round,pad=0,rounding_size=4", fc=YELLOW, ec=YELLOW))
        self.text(115, 112, title, size=40, weight="bold")
        if sub:
            self.text(117, 160, sub, size=24, color=SOFT, alpha=alpha)
        self.text(W - 80, 100, "Topic · Robot Dynamics", size=20, color=YELLOW, ha="right", weight="bold")

    def save(self, path):
        self.fig.savefig(path, facecolor=BG)
        plt.close(self.fig)


def fade(t, t0, dur=0.6):
    return float(np.clip((t - t0) / dur, 0.0, 1.0))


def plot_axes(fr, rect, xlim, ylim, ylabel, alpha=1.0):
    ax = fr.fig.add_axes([rect[0] / W, 1 - (rect[1] + rect[3]) / H, rect[2] / W, rect[3] / H])
    ax.set_facecolor(PANEL)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    for s in ax.spines.values():
        s.set_color(MUTED)
    ax.tick_params(colors=SOFT, labelsize=15)
    ax.set_ylabel(ylabel, color=SOFT, fontsize=19)
    ax.grid(color="#2B3547", lw=1)
    ax.axhline(0, color=MUTED, lw=1)
    ax.patch.set_alpha(alpha)
    return ax


def draw_arm(fr, base, q, scale, color=WHITE, alpha=1.0, ghost=False, labels=False, torques=None):
    p1, p2 = joints_xy(q)
    pts = [base, (base[0] + p1[0] * scale, base[1] - p1[1] * scale), (base[0] + p2[0] * scale, base[1] - p2[1] * scale)]
    if ghost:
        fr.ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=10, alpha=0.25 * alpha, solid_capstyle="round")
        return pts
    # base mount
    fr.ax.add_patch(FancyBboxPatch((base[0] - 55, base[1] + 18), 110, 40, boxstyle="round,pad=0,rounding_size=8",
                                   fc="#3A4558", ec="#3A4558", alpha=alpha))
    fr.ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], color=BLUE, lw=26, solid_capstyle="round", alpha=alpha)
    fr.ax.plot([pts[1][0], pts[2][0]], [pts[1][1], pts[2][1]], color="#7FB8DE", lw=22, solid_capstyle="round", alpha=alpha)
    for p, r in ((pts[0], 22), (pts[1], 19)):
        fr.ax.add_patch(Circle(p, r, fc=YELLOW, ec=BG, lw=3, alpha=alpha, zorder=5))
    fr.ax.add_patch(Circle(pts[2], 13, fc=WHITE, ec=BG, lw=3, alpha=alpha, zorder=5))
    if labels:
        fr.text(pts[0][0] - 40, pts[0][1] - 35, r"$q_1$", size=30, color=YELLOW, ha="right", alpha=alpha)
        fr.text(pts[1][0] + 30, pts[1][1] - 30, r"$q_2$", size=30, color=YELLOW, alpha=alpha)
    if torques is not None:
        for p, tau, r in ((pts[0], torques[0], 50), (pts[1], torques[1], 42)):
            torque_arc(fr, p, tau, r, alpha)
    return pts


def torque_arc(fr, p, tau, r, alpha, max_tau=45.0):
    """Curved arrow around a joint: direction = sign, sweep = size."""
    mag = min(abs(tau) / max_tau, 1.0)
    if mag < 0.02:
        return
    sweep = 40 + 230 * mag
    a0 = 90 - sweep / 2
    angs = np.radians(np.linspace(a0, a0 + sweep, 40))
    if tau < 0:
        angs = angs[::-1]
    xs, ys = p[0] + r * np.cos(angs), p[1] - r * np.sin(angs)
    fr.ax.plot(xs[:-3], ys[:-3], color=RED, lw=5, alpha=alpha, solid_capstyle="round", zorder=6)
    fr.arrow(xs[-4], ys[-4], xs[-1], ys[-1], color=RED, alpha=alpha, lw=5, ms=26)


def vec(v, fmt="{:+.1f}"):
    return r"$\left[\begin{array}{c}" + "\\\\".join(fmt.format(x) for x in v) + r"\end{array}\right]$"


def col(a, b, fmt="{:+.1f}"):
    return "(" + fmt.format(a) + ",  " + fmt.format(b) + ")"


# ------------------------------------------------------------------ scenes
def scene_pendulum(fr, t):
    fr.header("Start with one joint", "Dynamics = how forces and torques create motion (kinematics only described the geometry)")
    sim = data("pendulum")
    th, w, acc = sim[min(int(t * FPS), len(sim) - 1)]
    pivot = np.array([480, 360])
    length = 330
    bob = pivot + length * np.array([np.sin(th), np.cos(th)])
    fr.ax.add_patch(FancyBboxPatch((pivot[0] - 120, pivot[1] - 30), 240, 22, boxstyle="round,pad=0,rounding_size=6",
                                   fc="#3A4558", ec="#3A4558"))
    fr.ax.plot([pivot[0], pivot[0]], [pivot[1], pivot[1] + length + 60], color=MUTED, lw=2, ls=(0, (6, 6)))
    fr.ax.plot([pivot[0], bob[0]], [pivot[1], bob[1]], color=BLUE, lw=14, solid_capstyle="round")
    fr.ax.add_patch(Circle(pivot, 16, fc=YELLOW, ec=BG, lw=3, zorder=5))
    fr.ax.add_patch(Circle(bob, 38, fc="#7FB8DE", ec=BG, lw=3, zorder=5))
    fr.text(bob[0], bob[1] + 10, "m", size=26, color=BG, ha="center", weight="bold", zorder=6)
    # gravity arrow
    fr.arrow(bob[0], bob[1] + 45, bob[0], bob[1] + 140, color=GREEN, lw=5, ms=30)
    fr.text(bob[0] + 18, bob[1] + 125, r"$mg$", size=28, color=GREEN)
    # angle arc
    a = np.linspace(0, th, 30)
    fr.ax.plot(pivot[0] + 110 * np.sin(a), pivot[1] + 110 * np.cos(a), color=YELLOW, lw=3)
    fr.text(pivot[0] + 55 * np.sin(th / 2) + 10, pivot[1] + 150 * np.cos(th / 2) - 5, r"$\theta$", size=30, color=YELLOW)
    fr.text(480, 900, "Motor off (τ = 0): gravity alone swings it", size=24, color=SOFT, ha="center", alpha=fade(t, 1.0))

    x = 980
    fr.text(x, 330, "Newton's second law, for rotation", size=30, color=SOFT, alpha=fade(t, 1.5))
    spans = fr.eq(x, 440, [(r"$I\,\ddot{\theta}$", BLUE), (r"$\;\;+\;\;$", WHITE), (r"$m\,g\,l\,\sin\theta$", GREEN),
                           (r"$\;\;=\;\;$", WHITE), (r"$\tau$", RED)], size=64, alpha=fade(t, 2.0))
    labels = [("inertia × angular\nacceleration", BLUE, 0), ("gravity torque", GREEN, 2), ("motor torque", RED, 4)]
    for i, (lab, c, k) in enumerate(labels):
        al = fade(t, 3.5 + 1.2 * i)
        cx, wd = spans[k]
        fr.ax.plot([cx - wd / 2 + 6, cx + wd / 2 - 6], [470, 470], color=c, lw=4, alpha=al)
        fr.text(cx, 510, lab, size=22, color=c, ha="center", va="top", alpha=al, linespacing=1.2)
    fr.text(x, 690, r"Like $F = m\,a$:   (stuff that resists)  =  (torque you apply)", size=26, color=SOFT, alpha=fade(t, 8.0))
    al = fade(t, 9.5)
    fr.box(x - 20, 740, 830, 150, alpha=al)
    fr.text(x + 10, 790, r"right now:   $\theta$ = " + f"{np.degrees(th):+6.1f}°", size=26, color=WHITE, alpha=al)
    fr.text(x + 10, 840, r"$\ddot{\theta} = (\tau - m g l \sin\theta)\,/\,I$ = " + f"{acc:+6.2f} rad/s²", size=26,
            color=WHITE, alpha=al)


def scene_equation(fr, t):
    fr.header("Many joints: the equation of motion", "One row per joint. Every robot simulator and torque controller is built on it.")
    spans = fr.eq(W / 2, 400, [(r"$M(q)\,\ddot{q}$", BLUE), (r"$\quad+\quad$", WHITE), (r"$C(q,\dot{q})\,\dot{q}$", ORANGE),
                               (r"$\quad+\quad$", WHITE), (r"$g(q)$", GREEN), (r"$\quad=\quad$", WHITE), (r"$\tau$", RED)],
                  size=72, ha="center", alpha=fade(t, 0.5))
    labels = [
        (0, BLUE, "Inertia", "mass matrix ×\njoint accelerations;\nM changes with pose", 2.0),
        (2, ORANGE, "Coriolis & centrifugal", "appear when several\njoints move at once\n(grow with speed²)", 4.0),
        (4, GREEN, "Gravity", "torque needed just\nto hold the arm up\n(depends on pose only)", 6.0),
        (6, RED, "Motor torques", "what the\nactuators apply", 8.0),
    ]
    for k, c, name, desc, t0 in labels:
        al = fade(t, t0)
        cx, wd = spans[k]
        fr.ax.plot([cx - wd / 2 + 8, cx + wd / 2 - 8], [445, 445], color=c, lw=5, alpha=al)
        fr.arrow(cx, 455, cx, 545, color=c, alpha=al, lw=3, ms=22)
        fr.text(cx, 590, name, size=28, color=c, ha="center", weight="bold", alpha=al)
        fr.text(cx, 615, desc, size=21, color=SOFT, ha="center", va="top", alpha=al, linespacing=1.25)
    al = fade(t, 10.5)
    fr.box(330, 820, 1260, 150, alpha=al)
    fr.eq(380, 880, [(r"$q = (q_1, q_2, \ldots, q_n)$", YELLOW)], size=32, alpha=al)
    fr.text(820, 880, "joint angles,   q̇ = velocities,   q̈ = accelerations", size=26, color=SOFT, alpha=al)
    fr.text(380, 935, "Two joints → 2 equations.   Franka arm → 7.   Humanoid → 30+.", size=26, color=WHITE, alpha=fade(t, 12.5))


def flow_row(fr, y, t0, t, items, color, title, question, users):
    al = fade(t, t0)
    tt = fr.text(120, y - 95, title, size=34, color=color, weight="bold", alpha=al)
    fr.text(120 + fr.width(tt) + 30, y - 95, question, size=26, color=SOFT, alpha=al)
    x = 120
    widths = [330, 540, 330]
    for i, ((latex, c), sub) in enumerate(items):
        ai = fade(t, t0 + 0.8 + 0.9 * i)
        fr.box(x, y - 50, widths[i], 140, color=PANEL, edge=c, alpha=ai)
        fr.eq(x + widths[i] / 2, y + 15, [(latex, c)], size=36 if i != 1 else 40, ha="center", alpha=ai)
        fr.text(x + widths[i] / 2, y + 62, sub, size=20, color=SOFT, ha="center", alpha=ai)
        if i < 2:
            fr.arrow(x + widths[i] + 10, y + 20, x + widths[i] + 90, y + 20, color=c, alpha=fade(t, t0 + 1.4 + 0.9 * i))
            x += widths[i] + 100
    fr.text(1560, y - 15, "Used by", size=22, color=MUTED, alpha=fade(t, t0 + 3.5))
    fr.text(1560, y + 5, users, size=22, color=WHITE, va="top", alpha=fade(t, t0 + 3.5), linespacing=1.3)


def scene_questions(fr, t):
    fr.header("One equation, two questions", "Same as kinematics had forward and inverse, dynamics does too")
    flow_row(fr, 380, 0.8, t,
             [((r"$\tau$", RED), "torques we apply"),
              ((r"$\ddot{q} = M^{-1}\,(\tau - C\dot{q} - g)$", WHITE), "solve for acceleration"),
              ((r"$\ddot{q} \;\rightarrow\; \dot{q},\, q$", BLUE), "integrate: the motion")],
             BLUE, "Forward dynamics", "Given these torques, how will the robot move?",
             "physics simulators\n(Isaac Sim, PhysX),\nprediction")
    flow_row(fr, 760, 6.5, t,
             [((r"$q,\ \dot{q},\ \ddot{q}$", BLUE), "the motion we want"),
              ((r"$\tau = M\ddot{q} + C\dot{q} + g$", WHITE), "plug in, just multiply"),
              ((r"$\tau$", RED), "torques needed")],
             RED, "Inverse dynamics", "To move like this, what torques do I need?",
             "controllers,\ngravity compensation,\nsizing motors")
    fr.text(W / 2, 1010, "Forward: solve + integrate, step after step.   Inverse: one direct evaluation, fast enough for 1 kHz control.",
            size=23, color=YELLOW, ha="center", alpha=fade(t, 12.5))


def scene_forward(fr, t):
    fr.header("Forward dynamics in action", "Motors off: τ = 0. Each step the simulator solves for q̈ and integrates.")
    sim = data("forward")
    i = min(int(t * FPS), len(sim) - 1)
    q, qd, qdd = sim[i]
    base = (520, 560)
    scale = 210
    trail = [joints_xy(s[0])[1] for s in sim[max(0, i - 45): i + 1]]
    if len(trail) > 1:
        xs = [base[0] + p[0] * scale for p in trail]
        ys = [base[1] - p[1] * scale for p in trail]
        for k in range(len(xs) - 1):
            fr.ax.plot(xs[k:k + 2], ys[k:k + 2], color=YELLOW, lw=3, alpha=0.6 * (k + 1) / len(xs))
    draw_arm(fr, base, q, scale, labels=True)
    fr.text(520, 1010, "No friction: it never settles, and the motion is chaotic",
            size=21, color=SOFT, ha="center")
    # equations with live numbers
    x0 = 1030
    al = fade(t, 0.5)
    fr.box(x0 - 30, 215, 880, 330, alpha=al)
    fr.text(x0, 265, "Every 1/600 s:", size=24, color=MUTED, alpha=al)
    fr.eq(x0, 335, [(r"$\tau = $", RED), (r"$\;(0,\ 0)$", WHITE), (r"$\quad$ given", SOFT)], size=34, alpha=al)
    fr.eq(x0, 410, [(r"$\ddot{q} = M^{-1}(\tau - C\dot{q} - g)$", WHITE)], size=34, alpha=fade(t, 1.5))
    fr.text(x0 + 450, 410, "= " + col(*qdd), size=25, color=BLUE, alpha=fade(t, 1.5), family="DejaVu Sans Mono")
    fr.eq(x0, 485, [(r"$\dot{q} \leftarrow \dot{q} + \ddot{q}\,\Delta t, \quad q \leftarrow q + \dot{q}\,\Delta t$", WHITE)],
          size=32, alpha=fade(t, 2.5))
    # plot q over time
    al = fade(t, 3.0)
    if al > 0:
        ax = plot_axes(fr, (1050, 600, 820, 340), (0, 26), (-3.5, 3.5), "angle (rad)", al)
        ax.set_yticks([-np.pi, 0, np.pi], ["−π", "0", "π"])
        ts = np.arange(i + 1) / FPS
        qs = (np.array([s[0] for s in sim[: i + 1]]) + np.pi) % (2 * np.pi) - np.pi  # wrap to (-π, π]
        jumps = np.abs(np.diff(qs, axis=0)) > np.pi
        qs = qs.copy()
        qs[1:][jumps] = np.nan
        ax.plot(ts, qs[:, 0], color=YELLOW, lw=3, label=r"$q_1$")
        ax.plot(ts, qs[:, 1], color="#7FB8DE", lw=3, label=r"$q_2$")
        ax.set_xlabel("time (s)", color=SOFT, fontsize=18)
        ax.legend(loc="upper right", facecolor=PANEL, edgecolor=MUTED, labelcolor=WHITE, fontsize=18)


def scene_inverse(fr, t):
    fr.header("Inverse dynamics in action", "Wanted: hand traces the circle. Compute the torques for that motion, then apply them.")
    sim, pts = data("inverse")
    i = min(int(t * FPS), len(sim) - 1)
    q, qd, terms, target = sim[i]
    tau = terms["inertia"] + terms["coriolis"] + terms["gravity"]
    base = (430, 640)
    scale = 230
    cx, cy = base[0] + CIRCLE_C[0] * scale, base[1] - CIRCLE_C[1] * scale
    fr.ax.add_patch(Circle((cx, cy), CIRCLE_R * scale, fill=False, ec=YELLOW, lw=3, ls=(0, (8, 6)), alpha=0.8))
    fr.ax.add_patch(Circle((base[0] + target[0] * scale, base[1] - target[1] * scale), 11, fc=YELLOW, ec=BG, zorder=7))
    draw_arm(fr, base, q, scale, torques=tau)
    fast = t > FAST_AT[0]
    speed_txt = "2× faster" if fast else "slow"
    fr.box(150, 900, 560, 90, color=RED if fast else PANEL, alpha=0.9)
    fr.text(430, 957, "Circle speed: " + speed_txt, size=30, color=WHITE, ha="center", weight="bold")

    # equation with the live numbers per term
    x0 = 900
    al = fade(t, 0.5)
    fr.box(x0 - 30, 205, 1000, 225, alpha=al)
    spans = fr.eq(x0, 275, [(r"$\tau$", RED), (r"$\;=\;$", WHITE), (r"$M\ddot{q}$", BLUE), (r"$\;+\;$", WHITE),
                            (r"$C\dot{q}$", ORANGE), (r"$\;+\;$", WHITE), (r"$g(q)$", GREEN)], size=44, alpha=al)
    mono = dict(family="DejaVu Sans Mono", size=22, ha="center", alpha=al)
    for k, v, c in ((0, tau, RED), (2, terms["inertia"], BLUE), (4, terms["coriolis"], ORANGE), (6, terms["gravity"], GREEN)):
        fr.text(spans[k][0], 335, f"{v[0]:+6.1f}", color=c, **mono)
        fr.text(spans[k][0], 370, f"{v[1]:+6.1f}", color=c, **mono)
    fr.text(spans[-1][0] + 120, 335, "joint 1  (N·m)", size=19, color=MUTED, alpha=al)
    fr.text(spans[-1][0] + 120, 370, "joint 2", size=19, color=MUTED, alpha=al)
    fr.text(x0, 410, r"Red arrows on the joints = $\tau$ applied by the motors", size=20, color=SOFT, alpha=al)

    # bars: size of each term at joint 1 (shoulder)
    al = fade(t, 1.5)
    if al > 0:
        ax = plot_axes(fr, (920, 470, 440, 440), (-0.6, 2.6), (-60, 60), "joint-1 torque (N·m)", al)
        vals = [terms["inertia"][0], terms["coriolis"][0], terms["gravity"][0]]
        ax.bar([0, 1, 2], vals, color=[BLUE, ORANGE, GREEN], width=0.6)
        ax.set_xticks([0, 1, 2], ["inertia\nM q̈", "Coriolis\nC q̇", "gravity\ng(q)"])
        ax.tick_params(axis="x", labelsize=17)
        # rolling torque history
        ax2 = plot_axes(fr, (1470, 470, 400, 440), (max(0, t - 8), max(8, t)), (-60, 60), "", al)
        ts = np.arange(max(0, i - 8 * FPS), i + 1)
        tau_hist = np.array([sum(sim[k][2].values()) for k in ts])
        g_hist = np.array([sim[k][2]["gravity"] for k in ts])
        ax2.plot(ts / FPS, tau_hist[:, 0], color=RED, lw=3, label=r"$\tau_1$ total")
        ax2.plot(ts / FPS, g_hist[:, 0], color=GREEN, lw=2.5, ls="--", label=r"$g_1$ part")
        ax2.set_xlabel("time (s)", color=SOFT, fontsize=18)
        ax2.legend(loc="lower left", facecolor=PANEL, edgecolor=MUTED, labelcolor=WHITE, fontsize=16)
    if t > FAST_AT[1] + 0.5:
        al = fade(t, FAST_AT[1] + 0.5)
        fr.box(110, 215, 680, 130, color=PANEL, edge=YELLOW, alpha=al)
        fr.text(450, 268, "2× speed → inertia term ≈ 4×  (q̈ ∝ speed²)", size=25, color=YELLOW, ha="center", alpha=al)
        fr.text(450, 315, "Gravity term: unchanged (pose only)", size=25, color=GREEN, ha="center", alpha=al)


def scene_loop(fr, t):
    fr.header("Putting it together", "Every torque-controlled robot runs this loop, hundreds to thousands of times a second")
    al = [fade(t, 0.5 + 0.8 * k) for k in range(6)]
    fr.box(110, 330, 360, 150, edge=YELLOW, alpha=al[0])
    fr.text(290, 395, "Desired motion", size=28, ha="center", weight="bold", alpha=al[0])
    fr.eq(290, 450, [(r"$q_d,\ \dot{q}_d,\ \ddot{q}_d$", YELLOW)], size=30, ha="center", alpha=al[0])
    fr.arrow(480, 405, 590, 405, alpha=al[1])
    fr.box(600, 300, 470, 210, edge=RED, alpha=al[1])
    fr.text(835, 360, "Controller", size=30, ha="center", weight="bold", color=RED, alpha=al[1])
    fr.text(835, 400, "inverse dynamics", size=22, ha="center", color=SOFT, alpha=al[1])
    fr.eq(835, 465, [(r"$\tau = M\ddot{q}_d + C\dot{q} + g$", WHITE)], size=28, ha="center", alpha=al[1])
    fr.arrow(1080, 405, 1260, 405, color=RED, alpha=al[2])
    fr.eq(1170, 385, [(r"$\tau$", RED)], size=34, ha="center", alpha=al[2])
    fr.box(1270, 300, 540, 210, edge=BLUE, alpha=al[3])
    fr.text(1540, 360, "Robot / simulator", size=30, ha="center", weight="bold", color=BLUE, alpha=al[3])
    fr.text(1540, 400, "forward dynamics (physics)", size=22, ha="center", color=SOFT, alpha=al[3])
    fr.eq(1540, 465, [(r"$\ddot{q} = M^{-1}(\tau - C\dot{q} - g)$", WHITE)], size=28, ha="center", alpha=al[3])
    fr.arrow(1540, 520, 840, 520, color=BLUE, alpha=al[4], rad=-0.35, lw=4)
    fr.text(1190, 690, "sensors measure  q, q̇  →  correct errors", size=24, color=SOFT, ha="center", alpha=al[4])
    items = [
        ("Gravity compensation", "τ = g(q) only: the arm feels weightless, so people can hand-guide a cobot", GREEN, 5.5),
        ("Faster moves cost more", "inertia term grows with acceleration → bigger motors, more heat", BLUE, 7.5),
        ("Next", "the same equations on a 7-joint Franka arm in Isaac Sim", YELLOW, 9.5),
    ]
    for k, (a, b, c, t0) in enumerate(items):
        y = 790 + 80 * k
        alk = fade(t, t0)
        fr.ax.add_patch(Circle((140, y - 10), 10, fc=c, ec=c, alpha=alk))
        ta = fr.text(170, y, a + ":", size=27, color=c, weight="bold", alpha=alk)
        fr.text(170 + fr.width(ta) + 16, y, b, size=27, color=WHITE, alpha=alk)


DRAW = {"pendulum": scene_pendulum, "equation": scene_equation, "questions": scene_questions,
        "forward": scene_forward, "inverse": scene_inverse, "loop": scene_loop}


def scene_at(frame):
    t = frame / FPS
    for name, dur in SCENES:
        if t < dur:
            return name, t, dur
        t -= dur
    name, dur = SCENES[-1]
    return name, dur, dur


def render(args):
    frame, path = args
    name, t, dur = scene_at(frame)
    fr = Frame()
    DRAW[name](fr, t)
    # fade to/from black at scene cuts
    edge = min(t, dur - t)
    if edge < 0.35:
        fr.ax.add_patch(plt.Rectangle((0, 0), W, H, fc=BG, ec=BG, alpha=1 - edge / 0.35, zorder=50))
    fr.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--jobs", type=int, default=max(os.cpu_count() - 2, 1))
    args = parser.parse_args()
    for name in ("pendulum", "forward", "inverse"):
        data(name)  # warm the cache before forking workers
    if args.preview:
        out = os.path.join(HERE, "preview")
        os.makedirs(out, exist_ok=True)
        starts = np.cumsum([0] + [d for _, d in SCENES])
        picks = [(s + d - 1.0) for s, (_, d) in zip(starts, SCENES)] + [starts[4] + 20.0]
        jobs = [(int(p * FPS), os.path.join(out, f"{k:02d}.png")) for k, p in enumerate(picks)]
        with Pool(args.jobs) as pool:
            pool.map(render, jobs)
        print("preview in", out)
        return
    frames = os.path.join(HERE, "math_frames")
    shutil.rmtree(frames, ignore_errors=True)
    os.makedirs(frames)
    n = int(TOTAL * FPS)
    with Pool(args.jobs) as pool:
        for k, _ in enumerate(pool.imap_unordered(render, [(f, os.path.join(frames, f"{f:05d}.png")) for f in range(n)], chunksize=8)):
            if k % 300 == 0:
                print(f"[math] {k}/{n}", flush=True)
    raw = os.path.join(ROOT, "videos", "raw", "08a_dynamics_math.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(frames, "%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", raw], check=True)
    shutil.copy(raw, os.path.join(ROOT, "videos", "edited", "08a_dynamics_math.mp4"))
    shutil.rmtree(frames)
    print("wrote", raw)


if __name__ == "__main__":
    main()
