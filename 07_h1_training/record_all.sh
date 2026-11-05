#!/bin/bash
# Record every clip for video 7 from the training checkpoints.
#   07_h1_training/record_all.sh <run_dir>
set -u
RUN=${1:-$(ls -d ~/IsaacLab/logs/rsl_rl/h1_rough/*/ | tail -1)}
OUT=~/isaac_demos/07_h1_training/clips
mkdir -p "$OUT"
rec() {  # name checkpoint args...
  local name=$1 ckpt=$2; shift 2
  [ -f "$OUT/$name.mp4" ] && { echo "skip $name"; return; }
  ~/IsaacLab/nocondarun.sh -p ~/isaac_demos/07_h1_training/record_policy.py \
    --checkpoint "$RUN/model_$ckpt.pt" --out "$OUT/$name" "$@" > "$OUT/$name.log" 2>&1
  echo "$name: $(grep -E '\[demo\] done' "$OUT/$name.log" || echo FAILED)"
}
# Training progress: same 60 robots on the training ground, at different stages.
for c in 0 50 150 400 1000 1999; do
  rec "grid_$(printf %04d $c)" $c --scenario grid --seconds 7
done
# Tests of the final policy (one condition at a time, then all together).
rec ice    1999 --scenario ice    --num_envs 4 --track 0 --follow --eye=4.5,-5,0.9 --lookat=-0.8,1.0,-0.3 --focal 28 --seconds 8
rec heavy  1999 --scenario heavy  --num_envs 4 --track 0 --follow --eye=4.5,-5,0.9 --lookat=-0.8,1.0,-0.3 --focal 28 --seconds 8
rec push   1999 --scenario push   --num_envs 4 --track 0 --follow --eye=4.5,-5,0.9 --lookat=-0.8,1.0,-0.3 --focal 28 --seconds 8
rec combo  1999 --scenario combo  --num_envs 4 --track 0 --follow --eye=4.5,-5,0.9 --lookat=-0.8,1.0,-0.3 --focal 28 --seconds 8
rec stairs 1999 --scenario stairs --num_envs 3 --track 0 --speed 0.6 --eye=2.0,-7.0,2.4 --lookat=2.0,0,0.8 --focal 18 --seconds 11
echo ALL DONE
