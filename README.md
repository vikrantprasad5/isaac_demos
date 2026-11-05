# isaac_demos

Recorded Isaac Sim 6.2.0 demo videos for "Talk 03: Manipulation and Contact".

`videos/raw/` = clean renders, `videos/edited/` = same clips with captions.

| # | Video | Topic |
|---|---|---|
| 1 | Follow target: [edited](videos/edited/01_follow_target.mp4) · [raw](videos/raw/01_follow_target.mp4) | Robot kinematics: inverse kinematics, reachability |
| 2 | Obstacle planning: [edited](videos/edited/02_obstacle_planning.mp4) · raw [open](videos/raw/02_obstacle_open.mp4), [wall](videos/raw/02_obstacle_wall.mp4) | Collision checking and motion planning |
| 3 | Friction slip: [edited](videos/edited/03_friction_slip.mp4) · raw [grip](videos/raw/03_friction_grip.mp4), [slip](videos/raw/03_friction_slip.mp4) | Contact mechanics and friction |
| 4 | Learned policy: [edited](videos/edited/04_learned_policy.mp4) · raw [real-time](videos/raw/04_drawer_policy_realtime.mp4), [slow-mo](videos/raw/04_drawer_policy_slowmo.mp4) | Learning manipulation policies (pre-trained RL drawer-opening policy) |
| 5 | Hand grip and slip: [edited](videos/edited/05_hand_grasp.mp4) · [raw](videos/raw/05_hand_grasp.mp4) | Contact and friction with a five-finger Shadow Hand (scripted fingers; squeeze fades until the rod slips) |
| 6 | Humanoid walking: [edited](videos/edited/06_humanoid_walk.mp4) · [raw](videos/raw/06_humanoid_walk.mp4) | Learned policies: pre-trained Unitree H2 walking policy (trained with domain randomization) |
| 7 | Training a humanoid: [edited](videos/edited/07_h1_training.mp4) · [raw](videos/raw/07_h1_training.mp4) | Learned policies: our own Unitree H1 training run in Isaac Lab with domain randomization (montage from round 0 to 2000, then tests: slippery floor, +15 kg, shoves, all at once, stairs) |

## Re-recording

Each demo has a `record.py` that renders offscreen (works headless / screen locked) and writes PNG frames:

```bash
./run.sh 01_follow_target/record.py            # full take
./run.sh 01_follow_target/record.py --seconds 4  # quick test
ffmpeg -framerate 30 -i 01_follow_target/frames/%05d.png -c:v libx264 -pix_fmt yuv420p -crf 20 videos/raw/01_follow_target.mp4
```

Add captions (needs Pillow):

```bash
python3 common/annotate.py 01_follow_target/captions.json videos/raw/01_follow_target.mp4 videos/edited/01_follow_target.mp4
```

Video 5 records at 120 fps and is assembled (real time + 4x slow-motion replay + squeeze meter + captions) by `python3 05_hand_grasp/make_video.py`. Video 6 is encoded at 50 fps.

### Video 7: training in Isaac Lab

Isaac Lab 3.0 (`~/IsaacLab`, linked to `~/isaacsim`). `07_h1_training/install_task.sh` registers the task
`Demo-Velocity-Rough-H1-DR` (H1 on rough terrain with wide randomization: friction 0.2-1.25, torso mass -5..+15 kg,
shoves every 4-8 s up to 1.2 m/s). Training (4096 robots, 2000 rounds, ~33 min on an RTX 5070):

```bash
~/IsaacLab/nocondarun.sh -p scripts/reinforcement_learning/train.py --rl_library rsl_rl \
    --task Demo-Velocity-Rough-H1-DR --num_envs 4096 --max_iterations 2000 --seed 7
07_h1_training/record_all.sh <run_dir>   # replays checkpoints into 07_h1_training/clips/
python3 07_h1_training/make_video.py     # montage + panels + captions
```

The final policy and its training config are in `07_h1_training/policy/`.

`run.sh` strips conda from the environment before calling `~/isaacsim/python.sh`.

## Slides

One PowerPoint deck per topic, each with the captioned video embedded, screenshots and speaker notes (the talking points live in the notes):

| Topic | Deck |
|---|---|
| 3 Kinematics | [slides/Topic03_Kinematics.pptx](slides/Topic03_Kinematics.pptx) |
| 7 Collision & planning | [slides/Topic07_Collision_Planning.pptx](slides/Topic07_Collision_Planning.pptx) |
| 9 Contact & friction | [slides/Topic09_Contact_Friction.pptx](slides/Topic09_Contact_Friction.pptx) |
| 14 Learned policies | [slides/Topic14_Learned_Policies.pptx](slides/Topic14_Learned_Policies.pptx) |

Rebuild with `node slides/build_decks.js` (needs pptxgenjs, react-icons, react, react-dom, sharp on NODE_PATH and APPLY_THEME pointing at the pptx skill's apply_theme.js).

Photo credits (Wikimedia Commons, also credited on each slide):
- BMW Leipzig MEDIA 050719 Download Karosseriebau max.jpg: BMW Werk Leipzig, CC BY-SA 2.0 de (https://commons.wikimedia.org/wiki/File:BMW_Leipzig_MEDIA_050719_Download_Karosseriebau_max.jpg)
- WBAMC first in DoD to use robot for surgery 160426-A-EK666-506.jpg: Marcy Sanchez, Public domain (https://commons.wikimedia.org/wiki/File:WBAMC_first_in_DoD_to_use_robot_for_surgery_160426-A-EK666-506.jpg)
- Hedge maze - Nokkakivi.jpg: Juustila, CC BY-SA 4.0 (https://commons.wikimedia.org/wiki/File:Hedge_maze_-_Nokkakivi.jpg)
- Amazon warehouse robot 2020.JPG: Geni, CC BY-SA 4.0 (https://commons.wikimedia.org/wiki/File:Amazon_warehouse_robot_2020.JPG)
- Human-Robot-Collaboration-Sawing-2016-Luka-Peternel.jpg: Luka Peternel, CC BY-SA 4.0 (https://commons.wikimedia.org/wiki/File:Human-Robot-Collaboration-Sawing-2016-Luka-Peternel.jpg)
- Shadow Hand Bulb large.jpg: Richard Greenhill and Hugo Elias (myself) of the Shadow Robo, CC BY-SA 3.0 (https://commons.wikimedia.org/wiki/File:Shadow_Hand_Bulb_large.jpg)
- Humanoid robot at Science Square Tsukuba.jpg: Syced, CC0 (https://commons.wikimedia.org/wiki/File:Humanoid_robot_at_Science_Square_Tsukuba.jpg)
- Chinese Crested hairless agility.jpg: Ron Armstrong from Helena, MT, USA, CC BY 2.0 (https://commons.wikimedia.org/wiki/File:Chinese_Crested_hairless_agility.jpg)
