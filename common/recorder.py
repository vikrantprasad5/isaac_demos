"""Offscreen frame recorder for Isaac Sim demo videos.

Renders a fixed camera into its own render product, so recording works headless
and with the screen locked. Frames go to PNG; encode() turns them into an MP4.
"""

import os
import shutil
import subprocess

import carb
import omni.replicator.core as rep
from omni.replicator.core.functional import write_image


class Recorder:
    def __init__(self, out_dir, position, look_at, resolution=(1920, 1080), focal_length=24.0):
        self.frames_dir = os.path.join(out_dir, "frames")
        shutil.rmtree(self.frames_dir, ignore_errors=True)
        os.makedirs(self.frames_dir)
        rep.orchestrator.set_capture_on_play(False)
        carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)
        self.camera = rep.functional.create.camera(
            position=position, look_at=look_at, focal_length=focal_length, parent="/World", name="DemoCamera"
        )
        self.render_product = rep.create.render_product(self.camera, resolution=resolution, name="DemoRP")
        self.rgb = rep.AnnotatorRegistry.get_annotator("rgb")
        self.rgb.attach(self.render_product)
        self.count = 0

    def capture(self):
        rep.orchestrator.step(rt_subframes=1, delta_time=0.0, pause_timeline=False)
        data = self.rgb.get_data()
        if data is None or getattr(data, "size", 0) == 0:
            return
        write_image(path=os.path.join(self.frames_dir, f"{self.count:05d}.png"), data=data[..., :3])
        self.count += 1

    def close(self):
        rep.orchestrator.wait_until_complete()
        self.rgb.detach()
        self.render_product.destroy()


def encode(frames_dir, mp4_path, fps=30):
    os.makedirs(os.path.dirname(mp4_path), exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps),
            "-i", os.path.join(frames_dir, "%05d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart",
            mp4_path,
        ],
        check=True,
    )
