"""Video 8b: forward vs inverse dynamics on a real Franka model in Isaac Sim.

The arm's position drives are switched off; we command raw joint torques τ each physics step.

  take "fall"  : τ = 0. Forward dynamics only: the simulator solves q̈ = M⁻¹(τ − C q̇ − g) and the arm collapses.
  take "hover" : τ = g(q). Inverse dynamics for "stay still": exactly the torque gravity needs, so the arm floats.
  take "track" : τ = M(q)(q̈_d + Kp e + Kd ė) + C q̇ + g(q). Inverse dynamics for a moving target (computed torque).

    ./run.sh 08_dynamics/record.py            # all three takes into 08_dynamics/frames + data.json
    ./run.sh 08_dynamics/record.py --seconds 2  # quick test (2 s per take)
"""

import argparse
import json
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=float, default=None, help="Shorten every take (quick tests).")
args, _ = parser.parse_known_args()

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import omni.kit.app

omni.kit.app.get_app().get_extension_manager().set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)

import isaacsim.core.experimental.utils.app as app_utils
import numpy as np
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.robot_motion.examples.manipulation import ManipulationScenario

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common.recorder import Recorder

PHYSICS_DT = 1.0 / 120.0
RECORD_EVERY = 4  # 120 Hz physics -> 30 fps video
ARM = list(range(7))

# Arm reaching forward, roughly horizontal: gravity has a long lever arm here.
START = np.array([0.0, 0.25, 0.0, -1.35, 0.0, 1.6, 0.785])
TAKES = [("fall", 8.0), ("hover", 12.0), ("track", 24.0)]

# Tracking target: slow waves on the shoulder, elbow and base joints.
AMP = np.array([0.9, 0.35, 0.0, 0.55, 0.0, 0.3, 0.0])
FREQ = np.array([0.25, 0.4, 0.0, 0.4, 0.0, 0.5, 0.0])  # Hz
KP, KD = 900.0, 60.0


def desired(t):
    w = 2 * np.pi * FREQ
    ramp = min(t / 1.0, 1.0)  # fade the motion in over 1 s
    ramp = ramp * ramp * (3 - 2 * ramp)
    q = START + ramp * AMP * np.sin(w * t)
    qd = ramp * AMP * w * np.cos(w * t)
    qdd = -ramp * AMP * w * w * np.sin(w * t)
    return q, qd, qdd


def main():
    SimulationManager.setup_simulation(dt=PHYSICS_DT, device="cpu")
    scenario = ManipulationScenario("franka")
    art = scenario.setup_scene()

    recorder = Recorder(HERE, position=(0.55, -2.1, 0.75), look_at=(0.4, 0.0, 0.42), focal_length=24.0)

    simulation_app.update()
    app_utils.play()
    for _ in range(20):
        simulation_app.update()

    n_dof = art.num_dofs
    # Arm joints: no PD drive, pure torque control. Fingers keep their position drive.
    art.set_dof_gains(stiffnesses=np.zeros((1, 7)), dampings=np.zeros((1, 7)), dof_indices=ARM)

    data = []
    for take, seconds in TAKES:
        seconds = min(seconds, args.seconds or seconds)
        q0 = np.concatenate([START, [0.04, 0.04]])
        art.set_dof_positions(q0.reshape(1, -1))
        art.set_dof_velocities(np.zeros((1, n_dof)))
        art.set_dof_position_targets(q0.reshape(1, -1))
        art.set_dof_efforts(np.zeros((1, 7)), dof_indices=ARM)
        for _ in range(2):
            simulation_app.update()
            art.set_dof_positions(q0.reshape(1, -1))
            art.set_dof_velocities(np.zeros((1, n_dof)))

        steps = int(seconds / PHYSICS_DT)
        print(f"[demo] take {take}: {steps} steps", flush=True)
        for step in range(steps):
            t = step * PHYSICS_DT
            q = art.get_dof_positions().numpy()[0, :7]
            qd = art.get_dof_velocities().numpy()[0, :7]
            g = art.get_dof_gravity_compensation_forces().numpy()[0, :7]
            c = art.get_dof_coriolis_and_centrifugal_compensation_forces().numpy()[0, :7]
            M = art.get_mass_matrices().numpy()[0][:7, :7]
            q_des = qd_des = None
            inertia = np.zeros(7)
            if take == "fall":
                tau = np.zeros(7)
            elif take == "hover":
                tau = g.copy()
            else:
                q_des, qd_des, qdd_des = desired(t)
                a = qdd_des + KP * (q_des - q) + KD * (qd_des - qd)
                inertia = M @ a
                tau = inertia + c + g
            art.set_dof_efforts(tau.reshape(1, -1), dof_indices=ARM)
            simulation_app.update()
            if step % RECORD_EVERY == 0:
                recorder.capture()
                data.append({
                    "take": take, "t": round(t, 4), "frame": recorder.count - 1,
                    "q": q.round(4).tolist(), "qd": qd.round(4).tolist(),
                    "tau": tau.round(3).tolist(), "g": g.round(3).tolist(),
                    "c": c.round(3).tolist(), "inertia": inertia.round(3).tolist(),
                    "q_des": None if q_des is None else q_des.round(4).tolist(),
                })
        print(f"[demo] take {take} done, q={np.round(q, 2)}", flush=True)

    recorder.close()
    with open(os.path.join(HERE, "data.json"), "w") as f:
        json.dump(data, f)
    print(f"[demo] done, {recorder.count} frames", flush=True)


if __name__ == "__main__":
    code = 0
    try:
        main()
    except BaseException:
        import traceback

        traceback.print_exc()
        code = 1
    finally:
        simulation_app.close(exit_code=code)
    sys.exit(code)
