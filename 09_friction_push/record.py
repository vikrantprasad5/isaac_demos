"""Video 9: Franka pushes the same box across a rough mat and a smooth (icy) mat.

Same box, same push motion, only the surface friction changes. We log the contact forces on the box every
physics step: the force from the robot's fingers (the effort) and the friction force from the mat.

    ./run.sh 09_friction_push/record.py --take rough
    ./run.sh 09_friction_push/record.py --take smooth
    ./run.sh 09_friction_push/record.py --take rough --seconds 6   # quick test
"""

import argparse
import json
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--take", choices=("rough", "smooth"), required=True)
parser.add_argument("--seconds", type=float, default=None)
args, _ = parser.parse_known_args()

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import omni.kit.app

omni.kit.app.get_app().get_extension_manager().set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)

import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.robot_motion.experimental.motion_generation as mg
import numpy as np
import omni.usd
import warp as wp
from isaacsim.core.experimental.materials import RigidBodyMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from isaacsim.core.experimental.utils import transform as transform_utils
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.robot_motion.cumotion import RmpFlowController, load_cumotion_supported_robot
from isaacsim.robot_motion.examples.manipulation import ManipulationScenario
from pxr import PhysxSchema

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common.recorder import Recorder

PHYSICS_DT = 1.0 / 120.0
RECORD_EVERY = 4  # 30 fps
BOX_PATH = "/World/Box"
MAT_PATH = "/World/Mat"
BOX_SIZE = (0.12, 0.12, 0.05)  # low, heavy block: the hand body passes over it, the fingers push
BOX_MASS = 2.0
MAT_TOP = 0.01
X = 0.55
PUSH_Z = MAT_TOP + 0.022  # fingertips low on the block so it slides instead of tipping
BOX_Y0 = -0.27
SURFACE = {
    # static, dynamic friction; mat colour
    "rough": (1.0, 0.6, (0.16, 0.16, 0.17)),   # rubber / sandpaper
    "smooth": (0.04, 0.03, (0.70, 0.86, 0.97)),  # ice / polished, oily
}

# (time, grasp-point position): eased between keyframes. The push leg is constant speed.
KEYFRAMES = [
    (0.0, (0.45, -0.30, 0.40)),
    (2.0, (X, -0.43, 0.25)),
    (3.5, (X, -0.43, PUSH_Z)),
    (4.0, (X, -0.43, PUSH_Z)),
    (12.0, (X, 0.17, PUSH_Z)),   # 0.6 m in 8 s: slow enough to narrate while it pushes
    (13.5, (X, 0.17, PUSH_Z)),
    (15.0, (X, 0.10, 0.30)),
    (16.5, (X, 0.10, 0.30)),
]
LINEAR = {3}  # index of segments that move at constant speed (4.0 -> 12.0 s)


def grasp_target(t):
    for k, ((t0, p0), (t1, p1)) in enumerate(zip(KEYFRAMES, KEYFRAMES[1:])):
        if t <= t1:
            s = (t - t0) / (t1 - t0)
            if k in LINEAR:
                # constant speed with short 0.3 s ramps at both ends
                r = 0.3 / (t1 - t0)
                if s < r:
                    s = s * s / (2 * r)
                elif s > 1 - r:
                    s = 1 - (1 - s) ** 2 / (2 * r) - r / 2
                else:
                    s = s - r / 2
                s /= 1 - r
            else:
                s = s * s * (3 - 2 * s)
            return (1 - s) * np.asarray(p0) + s * np.asarray(p1)
    return np.asarray(KEYFRAMES[-1][1])


def target_state(scenario, grasp_position):
    grasp_orientation = scenario.robot_config.grasp_orientation
    tool = scenario.robot_config.tool
    pos = wp.array(np.asarray(grasp_position, dtype=np.float32), dtype=wp.float32, device="cpu")
    inv = transform_utils.quaternion_conjugate(tool.controller_to_grasp_orientation, dtype=wp.float32, device="cpu")
    offset = transform_utils.rotate_vectors_by_quaternion(
        -np.asarray(tool.controller_to_grasp_position), inv, dtype=wp.float32, device="cpu")
    cpos = transform_utils.transform_local_to_world(offset, pos, grasp_orientation, dtype=wp.float32, device="cpu")
    cori = transform_utils.quaternion_multiplication(grasp_orientation, inv, dtype=wp.float32, device="cpu")
    return mg.RobotState(
        sites=mg.SpatialState.from_name(
            spatial_space=scenario.site_space,
            positions=([tool.controller_frame], cpos.reshape((1, 3))),
            orientations=([tool.controller_frame], cori.reshape((1, 4))),
        )
    )


def material(path, mu_s, mu_d):
    mat = RigidBodyMaterial(path, static_frictions=mu_s, dynamic_frictions=mu_d)
    prim = omni.usd.get_context().get_stage().GetPrimAtPath(path)
    PhysxSchema.PhysxMaterialAPI.Apply(prim).CreateFrictionCombineModeAttr().Set("min")
    return mat


def main():
    mu_s, mu_d, color = SURFACE[args.take]
    SimulationManager.setup_simulation(dt=PHYSICS_DT, device="cpu")
    scenario = ManipulationScenario("franka")
    scenario.setup_scene()

    # Mat: static slab the box slides on.
    Cube(MAT_PATH, positions=[(X, -0.05, MAT_TOP / 2)], sizes=1.0, scales=[[0.42, 0.95, MAT_TOP]], colors=[color])
    GeomPrim(MAT_PATH, apply_collision_apis=True)
    GeomPrim(MAT_PATH).apply_physics_materials(material("/World/Materials/Mat", mu_s, mu_d))

    Cube(BOX_PATH, positions=[(X, BOX_Y0, MAT_TOP + BOX_SIZE[2] / 2)], sizes=1.0, scales=[list(BOX_SIZE)],
         colors=[[0.95, 0.55, 0.1]])
    GeomPrim(BOX_PATH, apply_collision_apis=True)
    RigidPrim(BOX_PATH, masses=[BOX_MASS]).set_enabled_contact_tracking([True])
    GeomPrim(BOX_PATH).apply_physics_materials(material("/World/Materials/Box", mu_s, mu_d))
    box = RigidPrim(BOX_PATH, contact_filter_paths=[MAT_PATH], max_contact_count=64)

    scenario.initialize_world_binding(exclude_prim_paths=(BOX_PATH, MAT_PATH))
    controller = RmpFlowController(
        cumotion_robot=load_cumotion_supported_robot("franka"),
        cumotion_world_interface=scenario.world_interface,
        robot_joint_space=scenario.joint_space,
        robot_site_space=scenario.site_space,
        tool_frame=scenario.robot_config.tool.controller_frame,
    )
    art = scenario.articulation

    recorder = Recorder(os.path.join(HERE, f"take_{args.take}"), position=(1.75, -0.05, 0.62),
                        look_at=(0.5, -0.05, 0.08), focal_length=24.0)

    simulation_app.update()
    app_utils.play()
    for _ in range(30):
        simulation_app.update()

    # close the gripper (position targets on the two finger joints)
    n_dof = art.num_dofs
    fingers = [n_dof - 2, n_dof - 1]
    art.set_dof_position_targets(np.zeros((1, 2)), dof_indices=fingers)

    duration = args.seconds or KEYFRAMES[-1][0]
    t = 0.0
    controller.reset(scenario.read_robot_state(), target_state(scenario, grasp_target(0.0)), t=t)
    log = []
    for step in range(int(duration / PHYSICS_DT)):
        simulation_app.update()
        t += PHYSICS_DT
        scenario.sync_world()
        desired = controller.forward(scenario.read_robot_state(), target_state(scenario, grasp_target(t)), t)
        if desired is not None:
            scenario.apply_robot_state(desired)
        art.set_dof_position_targets(np.zeros((1, 2)), dof_indices=fingers)

        net = box.get_net_contact_forces(dt=PHYSICS_DT).numpy()[0]
        mat = box.get_contact_force_matrix(dt=PHYSICS_DT).numpy()[0, 0]
        pos, _ = box.get_world_poses()
        vel = box.get_velocities()[0].numpy()[0]
        push = net - mat  # everything that is not the mat: the robot's fingers
        effort = art.get_dof_projected_joint_forces().numpy()[0, :7]
        log.append({
            "t": round(t, 4), "push": push.round(3).tolist(), "mat": mat.round(3).tolist(),
            "pos": pos.numpy()[0].round(4).tolist(), "vel": vel.round(4).tolist(), "effort": effort.round(3).tolist(),
            "frame": recorder.count if step % RECORD_EVERY == 0 else None,
        })
        if step % RECORD_EVERY == 0:
            recorder.capture()
        if step % 240 == 0:
            print(f"[demo] t={t:5.2f} box y={pos.numpy()[0][1]:+.3f} push={np.round(push, 1)} mat={np.round(mat, 1)} "
                  f"tau1={effort[0]:+.1f}", flush=True)

    recorder.close()
    with open(os.path.join(HERE, f"data_{args.take}.json"), "w") as f:
        json.dump(log, f)
    print(f"[demo] done, {recorder.count} frames, box final {np.round(pos.numpy()[0], 3)}", flush=True)


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
