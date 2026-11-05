#!/bin/bash
# Register Demo-Velocity-Rough-H1-DR inside the local IsaacLab checkout.
set -e
H1=~/IsaacLab/source/isaaclab_tasks/isaaclab_tasks/core/velocity/config/h1
cp "$(dirname "$0")/h1_dr_env_cfg.py" "$H1/h1_dr_env_cfg.py"
grep -q Demo-Velocity-Rough-H1-DR "$H1/__init__.py" || cat >> "$H1/__init__.py" <<'PY'

gym.register(
    id="Demo-Velocity-Rough-H1-DR",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": f"{__name__}.h1_dr_env_cfg:H1RoughDREnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:H1RoughPPORunnerCfg",
        "default_agent": "rsl_rl",
    },
)
PY
echo registered
