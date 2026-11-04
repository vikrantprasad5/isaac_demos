"""Video 1: Franka follows a moving target cube (inverse kinematics, reachability).

The red target sweeps through reachable poses, then moves out of reach so the
arm stretches and stalls, then comes back. Recorded offscreen at 30 fps.
"""

import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=float, default=None, help="Stop early (for quick test renders).")
args, _ = parser.parse_known_args()

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import omni.kit.app

omni.kit.app.get_app().get_extension_manager().set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)

import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.robot_motion.experimental.motion_generation as mg
import numpy as np
import warp as wp
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim
from isaacsim.core.experimental.utils import transform as transform_utils
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.robot_motion.cumotion import RmpFlowController, load_cumotion_supported_robot
from isaacsim.robot_motion.examples.manipulation import ManipulationScenario

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common.recorder import Recorder

TARGET_PATH = "/World/TargetCube"
PHYSICS_DT = 1.0 / 60.0
RECORD_EVERY = 2  # 60 Hz physics -> 30 fps video

# (time in seconds, target position) — eased between keyframes.
KEYFRAMES = [
    (0.0, [0.50, 0.00, 0.35]),
    (3.0, [0.50, 0.00, 0.35]),
    (7.0, [0.45, 0.35, 0.25]),
    (11.0, [0.35, -0.35, 0.55]),
    (15.0, [0.60, -0.20, 0.15]),
    (19.0, [0.50, 0.25, 0.50]),
    (23.0, [0.50, 0.00, 0.35]),
    (25.0, [0.50, 0.00, 0.35]),
    (30.0, [1.15, 0.00, 0.45]),  # out of reach: arm stretches and stalls
    (35.0, [1.15, 0.00, 0.45]),
    (39.0, [0.50, 0.00, 0.35]),
    (42.0, [0.50, 0.00, 0.35]),
]


def target_position(t):
    for (t0, p0), (t1, p1) in zip(KEYFRAMES, KEYFRAMES[1:]):
        if t <= t1:
            s = (t - t0) / (t1 - t0)
            s = s * s * (3 - 2 * s)
            return (1 - s) * np.asarray(p0) + s * np.asarray(p1)
    return np.asarray(KEYFRAMES[-1][1])


def target_state(scenario, target):
    positions, _ = target.get_world_poses()
    grasp_position = positions.numpy()[0]
    grasp_orientation = scenario.robot_config.grasp_orientation
    tool = scenario.robot_config.tool
    grasp_to_controller_orientation = transform_utils.quaternion_conjugate(
        tool.controller_to_grasp_orientation, dtype=wp.float32, device=positions.device
    )
    grasp_to_controller_position = transform_utils.rotate_vectors_by_quaternion(
        -np.asarray(tool.controller_to_grasp_position),
        grasp_to_controller_orientation,
        dtype=wp.float32,
        device=positions.device,
    )
    controller_position = transform_utils.transform_local_to_world(
        grasp_to_controller_position, grasp_position, grasp_orientation, dtype=wp.float32, device=positions.device
    )
    controller_orientation = transform_utils.quaternion_multiplication(
        grasp_orientation, grasp_to_controller_orientation, dtype=wp.float32, device=positions.device
    )
    return mg.RobotState(
        sites=mg.SpatialState.from_name(
            spatial_space=scenario.site_space,
            positions=([tool.controller_frame], controller_position.reshape((1, 3))),
            orientations=([tool.controller_frame], controller_orientation.reshape((1, 4))),
        )
    )


def main():
    SimulationManager.setup_simulation(dt=PHYSICS_DT, device="cuda")

    scenario = ManipulationScenario("franka")
    scenario.setup_scene()
    Cube(TARGET_PATH, positions=KEYFRAMES[0][1], sizes=0.05, colors=[1.0, 0.0, 0.0])
    target = GeomPrim(TARGET_PATH)

    scenario.initialize_world_binding(exclude_prim_paths=[TARGET_PATH])
    cumotion_robot = load_cumotion_supported_robot("franka")
    controller = RmpFlowController(
        cumotion_robot=cumotion_robot,
        cumotion_world_interface=scenario.world_interface,
        robot_joint_space=scenario.joint_space,
        robot_site_space=scenario.site_space,
        tool_frame=scenario.robot_config.tool.controller_frame,
    )

    recorder = Recorder(HERE, position=(2.3, 2.0, 1.35), look_at=(0.55, 0.0, 0.45))

    simulation_app.update()
    app_utils.play()
    for _ in range(30):  # let renderer and materials settle
        simulation_app.update()

    duration = args.seconds or KEYFRAMES[-1][0]
    total_steps = int(duration / PHYSICS_DT)
    t = 0.0
    estimated = scenario.read_robot_state()
    controller.reset(estimated, target_state(scenario, target), t=t)

    for step in range(total_steps):
        target.set_world_poses(positions=[target_position(t).tolist()])
        simulation_app.update()
        t += PHYSICS_DT
        estimated = scenario.read_robot_state()
        scenario.sync_world()
        desired = controller.forward(estimated, target_state(scenario, target), t)
        if desired is not None:
            scenario.apply_robot_state(desired)
        if step % RECORD_EVERY == 0:
            recorder.capture()
        if step % 300 == 0:
            print(f"[demo] t={t:5.1f}s frames={recorder.count}", flush=True)

    recorder.close()
    print(f"[demo] done, {recorder.count} frames in {recorder.frames_dir}", flush=True)


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
