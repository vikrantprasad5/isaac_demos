"""Unitree H1 on rough terrain with wide domain randomization (for the training demo).

Same task as Isaac-Velocity-Rough-H1, but every robot gets its own world:
  - feet/body friction 0.2 (icy) .. 1.25 (rubber on concrete)
  - torso mass -5 .. +15 kg (carrying a load)
  - random shoves every 4-8 s up to 1.2 m/s
  - terrain curriculum: flat, slopes, rough ground, stairs up/down
Copied into IsaacLab's h1 config folder by 07_h1_training/install_task.sh.
"""

from isaaclab.utils import configclass

from .rough_env_cfg import H1RoughEnvCfg


@configclass
class H1RoughDREnvCfg(H1RoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        ev = self.events
        ev.physics_material.params["static_friction_range"] = (0.2, 1.25)
        ev.physics_material.params["dynamic_friction_range"] = (0.15, 1.0)
        ev.add_base_mass.params["mass_distribution_params"] = (-5.0, 15.0)
        ev.add_base_mass.params["operation"] = "add"
        ev.add_base_mass.params["distribution"] = "uniform"
        ev.push_robot.interval_range_s = (4.0, 8.0)
        ev.push_robot.params["velocity_range"] = {"x": (-1.2, 1.2), "y": (-1.2, 1.2)}

