# isaac_demos

Recorded Isaac Sim 6.2.0 demo videos for "Talk 03: Manipulation and Contact".

| # | Video | Topic |
|---|---|---|
| 1 | [Follow target](videos/01_follow_target.mp4) | Robot kinematics: inverse kinematics, reachability |

## Re-recording

Each demo has a `record.py` that renders offscreen (works headless / screen locked) and writes PNG frames:

```bash
./run.sh 01_follow_target/record.py            # full take
./run.sh 01_follow_target/record.py --seconds 4  # quick test
ffmpeg -framerate 30 -i 01_follow_target/frames/%05d.png -c:v libx264 -pix_fmt yuv420p -crf 20 videos/01_follow_target.mp4
```

`run.sh` strips conda from the environment before calling `~/isaacsim/python.sh`.
