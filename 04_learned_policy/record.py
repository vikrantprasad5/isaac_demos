"""Video 4: a trained policy (neural network) makes the Franka open a cabinet drawer.

Based on Isaac Sim's franka_standalone.py policy example. The policy was trained with
reinforcement learning in Isaac Lab; here it only runs (no training). Recorded offscreen.
"""

import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=float, default=4.0, help="Record length.")
args, _ = parser.parse_known_args()

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import carb
import numpy as np
import omni.timeline
from isaacsim.core.experimental.prims import Articulation
from isaacsim.core.experimental.utils.stage import add_reference_to_stage, define_prim, set_stage_units, set_stage_up_axis
from isaacsim.core.rendering_manager import RenderingManager
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.core.simulation_manager.impl.isaac_events import IsaacEvents
from isaacsim.robot.policy.examples import (
    PolicyEnvConfig,
    RobotPolicyRunner,
    get_franka_spec,
    make_franka_task_state_provider,
)
from isaacsim.storage.native import get_assets_root_path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from common.recorder import Recorder

state = {"first": True, "failed": False}


def on_physics_step(step_size, context):
    if state["failed"]:
        return
    try:
        if state["first"]:
            franka.initialize()
            franka.articulation.set_stabilization_thresholds([0.0])
            franka.articulation.set_sleep_thresholds([0.0])
            state["first"] = False
        else:
            franka.step(step_size)
    except Exception as error:  # noqa: BLE001
        state["failed"] = True
        carb.log_error(f"policy failed: {error}")


set_stage_up_axis("Z")
set_stage_units(meters_per_unit=1.0)
assets_root_path = get_assets_root_path()
ground = define_prim("/World/Ground", "Xform")
ground.GetReferences().AddReference(assets_root_path + "/Isaac/Environments/Grid/default_environment.usd")
define_prim("/World/PhysicsScene", "PhysicsScene")
SimulationManager.set_physics_sim_device("cuda")

spec = get_franka_spec()
env_config = PolicyEnvConfig.from_file(spec.engines["physx"].env_config_path)
cabinet_path = "/World/cabinet"
add_reference_to_stage(env_config.scene_entity_usd_path("cabinet"), cabinet_path)
cabinet = Articulation(paths=cabinet_path, reset_xform_op_properties=True)
cabinet_position, cabinet_orientation = env_config.scene_entity_root_pose("cabinet")
cabinet.set_world_poses([cabinet_position], [cabinet_orientation])
print(f"[demo] cabinet at {cabinet_position}", flush=True)

franka = RobotPolicyRunner(
    spec, prim_path="/World/franka", task_state_provider=make_franka_task_state_provider(cabinet, env_config)
)
franka.spawn()
franka.apply_scene_properties({"cabinet": cabinet})

timing = env_config.timing
render_dt = timing.render_interval * timing.physics_dt
RenderingManager.set_dt(render_dt)
SimulationManager.set_physics_dt(franka.physics_dt)
callback_id = SimulationManager.register_callback(on_physics_step, IsaacEvents.PRE_PHYSICS_STEP)

recorder = Recorder(HERE, position=(0.2, -2.35, 1.3), look_at=(0.38, 0.0, 0.45))
record_every = 1  # every render step (60 fps) so the fast pull can be slowed down
duration = args.seconds
print(f"[demo] render_dt={render_dt:.4f} record_every={record_every} duration={duration}s", flush=True)

timeline = omni.timeline.get_timeline_interface()
timeline.play()
simulation_app.update()

drawer_index = None
max_opening = 0.0
n_updates = int(duration / render_dt)
for i in range(n_updates):
    simulation_app.update()
    if drawer_index is None:
        drawer_index = cabinet.get_dof_indices("drawer_top_joint")
    opening = float(np.asarray(cabinet.get_dof_positions(dof_indices=drawer_index).numpy()).reshape(-1)[0])
    max_opening = max(max_opening, opening)
    if i % record_every == 0:
        recorder.capture()
    if i % 60 == 0:
        print(f"[demo] t={i * render_dt:5.1f}s drawer={opening:.3f} m", flush=True)

print(f"[demo] max drawer opening {max_opening:.3f} m, failed={state['failed']}", flush=True)
recorder.close()
print(f"[demo] done, {recorder.count} frames", flush=True)
timeline.stop()
SimulationManager.deregister_callback(callback_id)
franka.close()
simulation_app.close()
