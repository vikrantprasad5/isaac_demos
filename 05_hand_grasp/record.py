"""Video 5: a Shadow Hand (human-like, 5 fingers) grips a rod, the stand drops away,
then the squeeze slowly fades until friction can no longer hold the rod's weight.

    ./run.sh 05_hand_grasp/record.py

Finger motions are scripted joint targets (not a learned policy). Squeeze strength is the
finger motors' maximum torque. While the fingers close, the rod is given a large mass so the
fingers cannot knock it over; it gets its real mass (0.25 kg) before the stand drops.
Frames are captured at 120 per second (every 4th = real time at 30 fps).
"""

import argparse
import math
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--r", type=float, default=None)
parser.add_argument("--seconds", type=float, default=14.5)
parser.add_argument("--squeeze", type=float, default=None, help="Override finger max torque (N*m).")
parser.add_argument("--can", default=None, help="x,y,z override")
parser.add_argument("--thumb", type=float, default=1.0, help="Scale thumb closing targets.")
parser.add_argument("--relax", default="7,13", help="t0,t1: squeeze fades 100x weaker between t0 and t1 (s).")
parser.add_argument("--mu", type=float, default=0.7)
parser.add_argument("--cam", default="main")
parser.add_argument("--out", default=None)
args, _ = parser.parse_known_args()
if args.out:
    args.out = os.path.abspath(args.out)

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import numpy as np
import omni.timeline
import omni.usd
from isaacsim.core.experimental.materials import RigidBodyMaterial
from isaacsim.core.experimental.objects import Cube, Cylinder
from isaacsim.core.experimental.prims import Articulation, GeomPrim, RigidPrim
from isaacsim.core.experimental.utils.stage import add_reference_to_stage, define_prim, set_stage_units, set_stage_up_axis
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.storage.native import get_assets_root_path
from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common.recorder import Recorder

PHYSICS_DT = 1.0 / 120.0
RECORD_EVERY = 1  # every 120 Hz step: every 4th frame = real time at 30 fps, all frames = 4x slow motion
SQUEEZE = 0.8  # finger motor max torque (N*m) at full grip
HAND = "/World/hand"
CAN = "/World/Can"
STAND = "/World/Stand"
CAN_R, CAN_H, CAN_MASS = 0.012, 0.25, 0.25
HEAVY_MASS = 50.0
CAN_POS = np.array([0.024, -0.367, 0.0])
STAND_H = 0.25
STAND_TOP = CAN_POS[2] - CAN_H / 2
FLOOR_Z = -0.6

# Timeline (seconds)
T_CLOSE0, T_CLOSE1 = 1.5, 3.5  # fingers close
T_RELEASE = 4.3  # can switches from pinned to free (gravity acts)
T_DROP0, T_DROP1 = 4.5, 5.5  # stand drops away
DROP = 0.12

# Joint targets (radians) for the closed hand; everything else stays at 0.
CLOSED = {
    "FFJ2": 1.55, "MFJ2": 1.55, "RFJ2": 1.55, "LFJ2": 1.55,
    "FFJ1": 1.55, "MFJ1": 1.55, "RFJ1": 1.55, "LFJ1": 1.55,
    "FFJ0": 1.4, "MFJ0": 1.4, "RFJ0": 1.4, "LFJ0": 1.4,
    "THJ4": 1.05, "THJ3": 1.2, "THJ1": 0.5, "THJ0": -0.3,
}

CAMERAS = {
    "main": dict(position=(0.72, -0.74, 0.08), look_at=(0.02, -0.33, -0.07)),
    "top": dict(position=(0.04, -0.37, 0.45), look_at=(0.04, -0.37, 0.0)),
    "front": dict(position=(0.05, -0.95, 0.05), look_at=(0.03, -0.36, -0.02)),
}


def smooth(t, t0, t1):
    s = min(max((t - t0) / (t1 - t0), 0.0), 1.0)
    return s * s * (3 - 2 * s)


if args.r:
    CAN_R = args.r
if args.can:
    CAN_POS = np.array([float(v) for v in args.can.split(",")])
    STAND_TOP = CAN_POS[2] - CAN_H / 2


def build_scene():
    set_stage_up_axis("Z")
    set_stage_units(meters_per_unit=1.0)
    root = get_assets_root_path()
    ground = define_prim("/World/Ground", "Xform")
    ground.GetReferences().AddReference(root + "/Isaac/Environments/Grid/default_environment.usd")
    UsdGeom.XformCommonAPI(ground).SetTranslate((0, 0, FLOOR_Z))

    add_reference_to_stage(root + "/Isaac/Robots/ShadowRobot/ShadowHand/shadow_hand_instanceable.usd", HAND)
    stage = omni.usd.get_context().get_stage()
    UsdGeom.XformCommonAPI(stage.GetPrimAtPath(HAND)).SetRotate((0, 90, 0))  # palm faces +X, thumb up
    squeeze = args.squeeze if args.squeeze is not None else SQUEEZE
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.RevoluteJoint) and str(prim.GetPath()).startswith(HAND):
            wrist = "WRJ" in prim.GetName()
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
            drive.CreateTypeAttr("force")
            # USD angular drive gains are per degree.
            drive.CreateStiffnessAttr((50.0 if wrist else 5.0) * math.pi / 180)
            drive.CreateDampingAttr((2.0 if wrist else 0.1) * math.pi / 180)
            drive.CreateMaxForceAttr(20.0 if wrist else squeeze)
            drive.CreateTargetPositionAttr(0.0)

    Cylinder(CAN, radii=CAN_R, heights=CAN_H, axes="Z", positions=[CAN_POS.tolist()], colors=[[0.85, 0.12, 0.1]])
    GeomPrim(CAN, apply_collision_apis=True)
    # Heavy while the fingers close (so they cannot knock it over); real mass from T_RELEASE.
    can = RigidPrim(CAN, masses=[HEAVY_MASS])
    material = RigidBodyMaterial("/World/Materials/Can", static_frictions=args.mu, dynamic_frictions=args.mu)
    PhysxSchema.PhysxMaterialAPI.Apply(stage.GetPrimAtPath("/World/Materials/Can")).CreateFrictionCombineModeAttr().Set("min")
    GeomPrim(CAN).apply_physics_materials(material)

    stand_pos = [CAN_POS[0], CAN_POS[1], STAND_TOP - STAND_H / 2]
    Cube(STAND, sizes=1.0, scales=[[0.09, 0.09, STAND_H]], positions=[stand_pos], colors=[[0.55, 0.6, 0.7]])
    GeomPrim(STAND, apply_collision_apis=True)
    stand_prim = stage.GetPrimAtPath(STAND)
    UsdPhysics.RigidBodyAPI.Apply(stand_prim).CreateKinematicEnabledAttr(True)
    # Kinematic target set through USD so both physics and the renderer see the move.
    return can, stand_prim.GetAttribute("xformOp:translate"), np.array(stand_pos), squeeze


def main():
    SimulationManager.setup_simulation(dt=PHYSICS_DT, device="cpu")
    can, stand, stand_pos, squeeze = build_scene()
    hand = Articulation(HAND)
    out_dir = args.out or (HERE if args.cam == "main" else os.path.join(HERE, f"cam_{args.cam}"))
    recorder = Recorder(out_dir, near_clip=0.02, focal_length=24.0, **CAMERAS[args.cam])

    omni.timeline.get_timeline_interface().play()
    simulation_app.update()
    names = [n.replace("robot0_", "") for n in hand.dof_names]
    closed = np.array([CLOSED.get(n, 0.0) * (args.thumb if n.startswith("TH") else 1.0) for n in names])
    print(f"[demo] squeeze={squeeze} mu={args.mu}", flush=True)

    n_steps = int(args.seconds / PHYSICS_DT)
    released = False
    finger = np.array([not n.startswith("WR") for n in names])
    relax = [float(v) for v in args.relax.split(",")] if args.relax else None
    current = squeeze
    for step in range(n_steps):
        t = step * PHYSICS_DT
        if not released and t >= T_RELEASE:
            can.set_masses([CAN_MASS])
            print(f"[demo] released, mass={can.get_masses().numpy()}", flush=True)
            released = True
        if relax:
            current = squeeze * 0.01 ** smooth(t, *relax) if t >= relax[0] else squeeze
            hand.set_dof_max_efforts([np.where(finger, current, 20.0).tolist()])
        hand.set_dof_position_targets([(closed * smooth(t, T_CLOSE0, T_CLOSE1)).tolist()])
        z = stand_pos[2] - DROP * smooth(t, T_DROP0, T_DROP1)
        if T_DROP0 <= t <= T_DROP1 + 0.05:
            stand.Set(Gf.Vec3d(stand_pos[0], stand_pos[1], z))
        simulation_app.update()
        if step % RECORD_EVERY == 0:
            recorder.capture()
        if step % 30 == 0 or (relax and abs(t - 12.3) < 1.0 and step % 6 == 0):
            p = can.get_world_poses()[0].numpy()[0]
            print(f"[demo] t={t:5.2f}s squeeze={current:.4f} can z={p[2]:+.3f} x={p[0]:+.3f} y={p[1]:+.3f}", flush=True)

    p = can.get_world_poses()[0].numpy()[0]
    print(f"[demo] final can z={p[2]:+.3f} (start {CAN_POS[2]:+.3f}) held={p[2] > CAN_POS[2] - 0.05}", flush=True)
    recorder.close()
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
