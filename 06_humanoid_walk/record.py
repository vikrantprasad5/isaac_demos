"""Video 6: Unitree H2 humanoid walking with a learned policy (trained with RL in Isaac Lab).

Based on Isaac Sim's h2_standalone.py policy example; the scripted velocity commands are ours.
The policy only runs here (no training). Recorded offscreen.

    ./run.sh 06_humanoid_walk/record.py
"""

import argparse
import math
import os
import sys
from functools import partial

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=float, default=None, help="Stop early (quick tests).")
parser.add_argument("--cam", default="main")
args, _ = parser.parse_known_args()

from isaacsim import SimulationApp

simulation_app = SimulationApp(
    {"headless": True, "extra_args": ["--/exts/isaacsim.core.simulation_manager/default_engine=physx"]}
)

import carb
import newton
import numpy as np
import omni.timeline
from isaacsim.core.experimental.utils.stage import define_prim, get_current_stage
from isaacsim.core.rendering_manager import RenderingManager
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.core.simulation_manager.impl.isaac_events import IsaacEvents
from isaacsim.robot.policy.examples import PolicyArtifact, PolicyEnvConfig, PolicySpec, RobotPolicyRunner
from isaacsim.robot.policy.examples.binding import derive_binding
from isaacsim.storage.native import get_assets_root_path
from pxr import UsdLux

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common.recorder import Recorder

H2_POLICY_SHA256 = "0a47182bbe203eddc2b7a9185f822c14d3799723f8b8392c7a2895d25d449c83"
AUTONOMOUS_ACTION_PATH = "agile.rl_env.mdp.actions.random_actions.RandomPositionAction"

# (duration s, [vx, vy, yaw rate]) — within the trained ranges (|v| <= 0.5 m/s, |yaw| <= 1 rad/s).
COMMANDS = [
    (1.5, (0.0, 0.0, 0.0)),  # stand
    (5.0, (0.5, 0.0, 0.0)),  # walk forward
    (math.pi, (0.0, 0.0, 1.0)),  # turn around (half a turn)
    (5.0, (0.5, 0.0, 0.0)),  # walk back
    (3.0, (0.0, 0.4, 0.0)),  # side-step left
    (2.0, (0.0, 0.0, 0.0)),  # stop
]
TOTAL = sum(d for d, _ in COMMANDS)

CAMERAS = {
    "main": dict(position=(1.25, -4.7, 1.3), look_at=(1.25, 0.3, 0.85)),
}

state = {"first": True, "failed": False, "t": 0.0}
robot = None


def command_at(t):
    for duration, cmd in COMMANDS:
        if t < duration:
            return np.asarray(cmd, dtype=np.float32)
        t -= duration
    return np.zeros(3, dtype=np.float32)


def h2_binding(artifact, env_config):
    """Same as h2_standalone.py: drop the zero-width autonomous upper-body action."""
    del env_config
    descriptor = dict(artifact.load_descriptor())
    descriptor["actions"] = [r for r in descriptor.get("actions", ()) if r.get("full_path") != AUTONOMOUS_ACTION_PATH]
    return derive_binding(descriptor)


def on_physics_step(step_size, context):
    if state["failed"] or robot is None:
        return
    try:
        if state["first"]:
            robot.restart_from_default_state(command_at(0.0))
            state["first"] = False
        else:
            state["t"] += step_size
            robot.step(step_size, command_at(state["t"]))
    except Exception as error:  # noqa: BLE001
        state["failed"] = True
        carb.log_error(f"policy failed: {error}")


def main():
    global robot
    root = get_assets_root_path()
    ground = define_prim("/World/Ground", "Xform")
    ground.GetReferences().AddReference(root + "/Isaac/Environments/Simple_Warehouse/warehouse.usd")
    define_prim("/World/PhysicsScene", "PhysicsScene")
    UsdLux.DistantLight.Define(get_current_stage(), "/World/DistantLight").CreateIntensityAttr(1500.0)

    policy_dir = f"{root}/Isaac/Samples/Policies/h2"
    artifact = PolicyArtifact.from_files(
        f"{policy_dir}/policy.pt", f"{policy_dir}/env.yaml", f"{policy_dir}/IO_descriptors.yaml",
        model_sha256=H2_POLICY_SHA256,
    )
    env_config = PolicyEnvConfig.from_file(artifact.env_config_path)
    SimulationManager.set_physics_sim_device("cuda")
    newton.use_coord_layout_targets = True
    spec = PolicySpec(
        name="unitree_h2_velocity_history",
        engines={"physx": artifact},
        usd_path=root + "/Isaac/Robots/Unitree/H2/H2.usda",
        binding=partial(h2_binding, artifact),
    )
    robot = RobotPolicyRunner(spec, prim_path="/World/H2", training_engine="physx")
    robot.spawn()
    SimulationManager.set_physics_dt(robot.physics_dt)
    render_dt = robot.physics_dt * env_config.timing.render_interval
    RenderingManager.set_dt(render_dt)
    callback_id = SimulationManager.register_callback(on_physics_step, IsaacEvents.POST_PHYSICS_STEP)

    recorder = Recorder(HERE if args.cam == "main" else os.path.join(HERE, f"cam_{args.cam}"), **CAMERAS[args.cam])
    print(f"[demo] render_dt={render_dt:.4f} ({1 / render_dt:.0f} fps)", flush=True)

    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    simulation_app.update()
    duration = args.seconds or TOTAL
    for i in range(int(duration / render_dt)):
        simulation_app.update()
        recorder.capture()
        if i % 25 == 0:
            p, _ = robot.articulation.get_world_poses()
            p = p.numpy()[0]
            print(f"[demo] t={state['t']:5.2f}s cmd={command_at(state['t'])} pos=({p[0]:+.2f},{p[1]:+.2f},{p[2]:.2f})"
                  f" failed={state['failed']}", flush=True)
    recorder.close()
    print(f"[demo] done, {recorder.count} frames", flush=True)
    timeline.stop()
    SimulationManager.deregister_callback(callback_id)
    robot.close()


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
