"""Video 2: pick-and-place with and without a wall in the way (collision avoidance).

Run once per take:
    ./run.sh 02_obstacle_planning/record.py --take open   # no wall
    ./run.sh 02_obstacle_planning/record.py --take wall   # wall between pick and place

A trail of small spheres marks the gripper's path so the detour is visible.
"""

import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--take", choices=("open", "wall"), required=True)
parser.add_argument("--max-seconds", type=float, default=40.0)
parser.add_argument("--wall-height", type=float, default=0.33)
args, _ = parser.parse_known_args()

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import omni.kit.app

omni.kit.app.get_app().get_extension_manager().set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)

import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.robot_motion.experimental.motion_generation as mg
import numpy as np
import warp as wp
from isaacsim.core.experimental.objects import Cube, Sphere
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.robot_motion.cumotion import RmpFlowController, load_cumotion_supported_robot
from isaacsim.robot_motion.examples.manipulation import (
    GripperCommand,
    JointGripperController,
    ManipulationScenario,
    PickPlaceController,
    PickPlacePhase,
)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common.recorder import Recorder

ROBOT_PATH = "/World/robot"
CUBE_PATH = "/World/Cube"
TARGET_PATH = "/World/PlaceTarget"
WALL_PATH = "/World/Wall"
PHYSICS_DT = 1.0 / 60.0
RECORD_EVERY = 2
TRAIL_EVERY = 4
HOLD_SECONDS = 2.5

PICK = (0.45, -0.22, 0.025)
PLACE = (0.45, 0.32, 0.025)
TRAIL_COLOR = {"open": [0.15, 0.45, 1.0], "wall": [1.0, 0.75, 0.0]}


def make_controller(scenario):
    gripper = scenario.robot_config.gripper
    cumotion_robot = load_cumotion_supported_robot("franka")
    tool_frame = scenario.robot_config.tool.controller_frame
    arm = RmpFlowController(
        cumotion_robot=cumotion_robot,
        cumotion_world_interface=scenario.world_interface,
        robot_joint_space=scenario.joint_space,
        robot_site_space=scenario.site_space,
        tool_frame=tool_frame,
    )
    grip_args = {
        "robot_joint_space": scenario.joint_space,
        "joint_names": gripper.joint_names,
        "open_positions": gripper.open_positions,
        "closed_positions": gripper.closed_positions,
        "position_tolerance": gripper.position_tolerance,
        "velocity_tolerance": gripper.velocity_tolerance,
        "minimum_close_fraction": gripper.minimum_close_fraction,
    }
    return PickPlaceController(
        arm_controller=arm,
        gripper_open_controller=JointGripperController(**grip_args, command=GripperCommand.OPEN),
        gripper_close_controller=JointGripperController(**grip_args, command=GripperCommand.CLOSE),
        robot_site_space=scenario.site_space,
        tool_frame=tool_frame,
        controller_to_grasp_position=scenario.robot_config.tool.controller_to_grasp_position,
        controller_to_grasp_orientation=scenario.robot_config.tool.controller_to_grasp_orientation,
        grasp_orientation=scenario.robot_config.grasp_orientation,
        approach_height=0.20,
    )


def make_goal():
    names = [PickPlaceController.PICK_SITE, PickPlaceController.PLACE_SITE]
    return mg.RobotState(
        sites=mg.SpatialState.from_name(
            spatial_space=names,
            positions=(names, wp.array([PICK, PLACE], dtype=wp.float32, device="cpu")),
        )
    )


def tool_position(estimated, tool_frame):
    sites = estimated.sites
    if sites is None or sites.positions is None:
        return None
    return sites.positions.numpy()[sites.position_names.index(tool_frame)]


def main():
    SimulationManager.setup_simulation(dt=PHYSICS_DT, device="cpu")
    scenario = ManipulationScenario("franka", robot_prim_path=ROBOT_PATH)
    scenario.setup_scene()

    Cube(CUBE_PATH, positions=[PICK], sizes=0.05, colors=[[0.85, 0.1, 0.1]])
    cube = RigidPrim(CUBE_PATH)
    GeomPrim(CUBE_PATH, apply_collision_apis=True)
    Cube(TARGET_PATH, positions=[(PLACE[0], PLACE[1], 0.001)], sizes=1.0, scales=[[0.09, 0.09, 0.002]],
         colors=[[0.1, 0.8, 0.2]])
    if args.take == "wall":
        h = args.wall_height
        Cube(WALL_PATH, positions=[(0.45, 0.05, h / 2)], sizes=1.0, scales=[[0.45, 0.03, h]],
             colors=[[0.55, 0.6, 0.7]])
        GeomPrim(WALL_PATH, apply_collision_apis=True)

    scenario.initialize_world_binding(exclude_prim_paths=(TARGET_PATH,))
    controller = make_controller(scenario)
    tool_frame = scenario.robot_config.tool.controller_frame
    goal = make_goal()

    recorder = Recorder(os.path.join(HERE, f"take_{args.take}"), position=(2.25, -1.55, 1.5),
                        look_at=(0.3, 0.05, 0.32))

    simulation_app.update()
    app_utils.play()
    for _ in range(30):
        simulation_app.update()

    t = 0.0
    if not controller.reset(scenario.read_robot_state(), goal, t=t):
        raise RuntimeError(controller.failure_reason or "reset failed")

    trail = []
    done_at = None
    step = 0
    last_phase = None
    while step * PHYSICS_DT < args.max_seconds:
        simulation_app.update()
        t += PHYSICS_DT
        scenario.sync_world()
        estimated = scenario.read_robot_state()
        if done_at is None and not controller.is_done and not controller.failed:
            previous = controller.phase
            desired = controller.forward(estimated, goal, t)
            if desired is None:
                raise RuntimeError(controller.failure_reason or "no command")
            scenario.apply_robot_state(desired)
            if previous is not controller.phase:
                if controller.phase is PickPlacePhase.DESCEND_PICK:
                    scenario.set_planning_obstacles_enabled((CUBE_PATH,), False)
                elif controller.phase is PickPlacePhase.RETREAT:
                    scenario.set_planning_obstacles_enabled((CUBE_PATH,), True)
        elif done_at is None:
            done_at = t
            print(f"[demo] controller finished at t={t:.1f}s failed={controller.failed} "
                  f"reason={controller.failure_reason}", flush=True)
        if controller.phase is not last_phase:
            print(f"[demo] t={t:5.1f}s phase={controller.phase}", flush=True)
            last_phase = controller.phase

        carrying = controller.phase in (PickPlacePhase.LIFT, PickPlacePhase.APPROACH_PLACE, PickPlacePhase.DESCEND_PLACE)
        if step % TRAIL_EVERY == 0 and carrying:
            p = tool_position(estimated, tool_frame)
            if p is not None and (not trail or np.linalg.norm(p - trail[-1]) > 0.012):
                Sphere(f"/World/Trail/p{len(trail):04d}", positions=[p.tolist()], radii=0.007,
                       colors=[TRAIL_COLOR[args.take]])
                trail.append(p)

        if step % RECORD_EVERY == 0:
            recorder.capture()
        step += 1
        if done_at is not None and t - done_at > HOLD_SECONDS:
            break

    cube_pos = cube.get_world_poses()[0].numpy()[0]
    print(f"[demo] cube final={np.round(cube_pos, 3)} place={PLACE} "
          f"err={np.linalg.norm(cube_pos[:2] - np.asarray(PLACE[:2])):.3f}", flush=True)
    recorder.close()
    print(f"[demo] done, {recorder.count} frames, {len(trail)} trail points", flush=True)


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
