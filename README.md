# isaac_demos

Recorded Isaac Sim 6.2.0 demo videos for "Talk 03: Manipulation and Contact".

`videos/raw/` = clean renders, `videos/edited/` = same clips with captions.

| # | Video | Topic |
|---|---|---|
| 1 | Follow target: [edited](videos/edited/01_follow_target.mp4) · [raw](videos/raw/01_follow_target.mp4) | Robot kinematics: inverse kinematics, reachability |
| 2 | Obstacle planning: [edited](videos/edited/02_obstacle_planning.mp4) · raw [open](videos/raw/02_obstacle_open.mp4), [wall](videos/raw/02_obstacle_wall.mp4) | Collision checking and motion planning |
| 3 | Friction slip: [edited](videos/edited/03_friction_slip.mp4) · raw [grip](videos/raw/03_friction_grip.mp4), [slip](videos/raw/03_friction_slip.mp4) | Contact mechanics and friction |
| 4 | Learned policy: [edited](videos/edited/04_learned_policy.mp4) · raw [real-time](videos/raw/04_drawer_policy_realtime.mp4), [slow-mo](videos/raw/04_drawer_policy_slowmo.mp4) | Learning manipulation policies (pre-trained RL drawer-opening policy) |

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
