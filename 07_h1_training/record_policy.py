"""Replay one H1 training checkpoint in a chosen test scenario and save frames (50 fps).

    ~/IsaacLab/nocondarun.sh -p ~/isaac_demos/07_h1_training/record_policy.py \
        --checkpoint ~/IsaacLab/logs/rsl_rl/h1_rough/<run>/model_500.pt --scenario grid --out frames/grid_0500

Scenarios (all use the same trained policy, only the world changes):
  grid    many robots spread over the training terrain (stairs, slopes, rough ground, boxes)
  ice     flat floor, friction 0.2 (the slipperiest the robot ever saw in training)
  heavy   flat floor, +15 kg strapped to the torso
  push    flat floor, shoved sideways every 2-3 s
  stairs  up and over a stair pyramid (hard level)
  combo   ice + 15 kg + shoves, all at once
"""

import argparse
import os
import sys

import warp as wp

wp.config.enable_backward = False

parser = argparse.ArgumentParser()
parser.add_argument("--checkpoint", required=True)
parser.add_argument("--scenario", default="grid")
parser.add_argument("--num_envs", type=int, default=None)
parser.add_argument("--seconds", type=float, default=10.0)
parser.add_argument("--speed", type=float, default=0.8, help="Forward command (m/s).")
parser.add_argument("--out", required=True)
parser.add_argument("--eye", default=None, help="x,y,z camera position")
parser.add_argument("--lookat", default=None, help="x,y,z camera target")
parser.add_argument("--focal", type=float, default=24.0)
parser.add_argument("--seed", type=int, default=1)
parser.add_argument("--track", type=int, default=None, help="Camera eye/lookat are relative to this robot's start.")
parser.add_argument("--follow", action="store_true", help="Also follow the tracked robot as it moves.")

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

add_launcher_args(parser)
args = parser.parse_args()
sys.argv = sys.argv[:1]  # Hydra (inside resolve_task_config) parses sys.argv again
args.enable_cameras = True
args.out = os.path.abspath(os.path.expanduser(args.out))
args.checkpoint = os.path.abspath(os.path.expanduser(args.checkpoint))

import gymnasium as gym  # noqa: E402
import warp as wp  # noqa: E402,F811
import torch  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, create_rsl_rl_runner, handle_deprecated_rsl_rl_cfg, check_rsl_rl_version  # noqa: E402
from isaaclab_tasks.utils import resolve_task_config  # noqa: E402

TASK = "Demo-Velocity-Rough-H1-DR"
HERE = os.path.dirname(os.path.abspath(__file__))

# Default cameras per scenario: (eye, lookat). Robots start near the world origin area.
CAMS = {
    "grid": ((-9.0, -9.0, 7.5), (3.0, 3.0, 0.0)),
    "flat": ((4.5, -5.0, 1.8), (-0.8, 1.0, 0.7)),  # relative to the tracked robot (use --track)
}


def vec(s):
    return tuple(float(v) for v in s.split(","))


def configure(env_cfg):
    s = args.scenario
    ev = env_cfg.events
    cmd = env_cfg.commands.base_velocity
    cmd.debug_vis = False
    cmd.heading_command = False
    cmd.rel_standing_envs = 0.0
    cmd.rel_heading_envs = 0.0
    cmd.resampling_time_range = (1000.0, 1000.0)
    cmd.ranges.lin_vel_x = (args.speed, args.speed)
    cmd.ranges.lin_vel_y = (0.0, 0.0)
    cmd.ranges.ang_vel_z = (0.0, 0.0)
    env_cfg.episode_length_s = 1000.0
    # Spawn upright, facing +x, standing still: clean starts for the camera.
    ev.reset_base.params["pose_range"] = {"x": (0.0, 0.0), "y": (0.0, 0.0), "yaw": (0.0, 0.0)}
    ev.reset_base.params["velocity_range"] = {}
    # The tests set one condition at a time; everything else at its "normal" value.
    ev.physics_material.params["static_friction_range"] = (1.0, 1.0)
    ev.physics_material.params["dynamic_friction_range"] = (0.8, 0.8)
    ev.add_base_mass.params["mass_distribution_params"] = (0.0, 0.0)
    ev.push_robot = None
    ev.base_external_force_torque = None
    terrain = env_cfg.scene.terrain
    if s == "grid":
        env_cfg.scene.num_envs = args.num_envs or 60
        terrain.terrain_generator.num_rows = 5
        terrain.terrain_generator.num_cols = 6
        terrain.terrain_generator.curriculum = True  # rows = difficulty levels
        terrain.max_init_terrain_level = None
        cmd.ranges.ang_vel_z = (-0.3, 0.3)
        # No auto-reset after a fall: fallen robots stay down, so early training stages read clearly.
        env_cfg.terminations.base_contact = None
    elif s == "stairs":
        env_cfg.scene.num_envs = args.num_envs or 5
        gen = terrain.terrain_generator
        # Stair pyramid: the robot starts at the foot, climbs over the top and walks down the far side.
        gen.sub_terrains = {"stairs": gen.sub_terrains["pyramid_stairs"]}
        gen.sub_terrains["stairs"].proportion = 1.0
        gen.num_rows, gen.num_cols = 1, 3
        gen.difficulty_range = (0.9, 0.9)
        gen.curriculum = False
        terrain.max_init_terrain_level = None
        ev.reset_base.params["pose_range"]["x"] = (-3.7, -3.7)
    else:
        env_cfg.scene.num_envs = args.num_envs or 5
        terrain.terrain_type = "plane"
        terrain.terrain_generator = None
        env_cfg.scene.height_scanner.mesh_prim_paths = ["/World/ground"]
        env_cfg.scene.env_spacing = 2.5
        env_cfg.curriculum.terrain_levels = None
        if s in ("ice", "combo"):
            ev.physics_material.params["static_friction_range"] = (0.2, 0.2)
            ev.physics_material.params["dynamic_friction_range"] = (0.15, 0.15)
        if s in ("heavy", "combo"):
            ev.add_base_mass.params["mass_distribution_params"] = (15.0, 15.0)
        if s in ("push", "combo"):
            from isaaclab.managers import EventTermCfg, SceneEntityCfg
            from isaaclab_tasks.core.velocity import mdp

            ev.push_robot = EventTermCfg(
                func=mdp.push_by_setting_velocity,
                mode="interval",
                interval_range_s=(2.0, 3.0),
                params={"velocity_range": {"x": (-0.6, 0.6), "y": (-1.2, 1.2)}, "asset_cfg": SceneEntityCfg("robot")},
            )
    env_cfg.seed = args.seed


def main():
    import subprocess

    env_cfg, agent_cfg = resolve_task_config(TASK, "rsl_rl_cfg_entry_point", play_mode=True)
    configure(env_cfg)
    key = "grid" if args.scenario == "grid" else "flat"
    eye, lookat = CAMS[key]
    eye = torch.tensor(vec(args.eye) if args.eye else eye)
    lookat = torch.tensor(vec(args.lookat) if args.lookat else lookat)
    W, H = 1920, 1080
    from isaaclab_visualizers.kit import KitVisualizerCfg

    # A headless Kit visualizer makes Isaac Lab start Kit (RTX renderer); we film with our own camera.
    env_cfg.sim.visualizer_cfgs = [KitVisualizerCfg(headless=True, window_width=W, window_height=H, focal_length=args.focal)]
    steps = int(args.seconds / (env_cfg.sim.dt * env_cfg.decimation))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    mp4 = args.out if args.out.endswith(".mp4") else args.out + ".mp4"
    with launch_simulation(env_cfg, args):
        agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, check_rsl_rl_version())
        agent_cfg.device = env_cfg.sim.device
        env = gym.make(TASK, cfg=env_cfg)
        env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
        runner = create_rsl_rl_runner(env, agent_cfg)
        runner.load(args.checkpoint)
        policy = runner.get_inference_policy(device=env.unwrapped.device)
        scene = env.unwrapped.scene
        robot = scene["robot"]
        # Film through the headless Kit visualizer: we set its camera every step and grab its frame.
        vis = env.unwrapped.sim._visualizers[0]

        def root_pos():
            rp = robot.data.root_pos_w
            return (rp if isinstance(rp, torch.Tensor) else wp.to_torch(rp)).cpu()

        def aim(center):
            e, t = (eye + center, lookat + center) if center is not None else (eye, lookat)
            vis.cfg.eye, vis.cfg.lookat = tuple(e.tolist()), tuple(t.tolist())
            vis._viewer_origin = torch.zeros(3)
            vis._apply_viewer_origin_to_camera()

        center = None
        if args.track is not None:
            center = root_pos()[args.track].clone()
            center[2] = 0.0
        aim(center)
        ff = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "50",
             "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", mp4],
            stdin=subprocess.PIPE,
        )
        obs = env.get_observations()
        print(f"[demo] scenario={args.scenario} envs={env.num_envs} steps={steps}", flush=True)
        falls, frames, warmup = 0, 0, 40
        for i in range(steps + warmup):
            with torch.inference_mode():
                act = policy(obs)
                obs, _, dones, _ = env.step(act)
                policy.reset(dones)
                if i >= warmup:
                    falls += int(dones.sum().item())
            if args.track is not None and args.follow:
                p = root_pos()[args.track]
                target = torch.tensor([p[0], p[1], 0.0])
                center = 0.9 * center + 0.1 * target  # smooth follow
            aim(center)
            rgb = vis.render_rgb_array()
            if i < warmup:
                continue  # renderer warm-up (first frames are dark)
            if rgb is None or getattr(rgb, "size", 0) == 0 or rgb.max() == 0:
                if i % 50 == 0:
                    print(f"[demo] step {i}: no image yet", flush=True)
                continue
            ff.stdin.write(rgb[:, :, :3].tobytes())
            frames += 1
            if i % 50 == 0:
                print(f"[demo] t={(i - warmup) * env.unwrapped.step_dt:5.1f}s resets_so_far={falls}", flush=True)
        ff.stdin.close()
        ff.wait()
        print(f"[demo] final_root={root_pos().tolist()[:4]}", flush=True)
        print(f"[demo] done frames={frames} resets={falls} -> {mp4}", flush=True)
        env.close()


if __name__ == "__main__":
    main()
