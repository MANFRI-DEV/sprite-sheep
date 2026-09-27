**Windows 64-bit · 104.7 MB  |  Linux 64-bit · 28.3 MB (experimental)**

A whole move set in one click, any aspect ratio, a history you can regenerate
from, and a log for every render. Plus a Linux build, early AMD support, and a
Cancel button that actually stops the GPU.

### Queue a whole move set

Prepare an action (name, prompt, duration, frames), press **Add to queue**,
prepare the next one. With actions queued the button becomes **Generate N
actions**, and they all run as one job: same sprite, same model, same aspect
ratio, one output folder per action.

Under the hood the actions go to ComfyUI as **one** prompt with a branch per
action, sharing the loaders, so the model weights are read from disk once
instead of once per action. Measured here on an RTX 3050 8 GB with H3 Fast:

| character | actions | total | per action |
|---|---|---:|---:|
| low-poly sheep, 1:1 | walk, run, eat, sleep, sunglasses | 23:44 | 4:20 – 4:52 |
| platformer heroine, 3:4 | idle, run, jump, crouch, hurt | 22:03 | 3:58 – 4:57 |
| plush sheep, 1:1 | walk, run, eat, sleep, sunglasses | 22:46 | 4:22 – 4:48 |

Honest caveat: if Windows still has the weights in its file cache, running the
actions one by one is almost as fast (two actions: 760 s batched vs 786 s
separately). The big saving is on a cold start, when every separate run would
read ~20 GB from disk again. The real win is that you queue five actions and
walk away.

Only one job uses the GPU at a time. A second job waits and tells you how
many are ahead of it; cancelling a queued job just removes it from the line.

### Any aspect ratio

**1:1, 3:4, 4:3, 9:16, 16:9, 21:9**, all kept around the same pixel budget
that fits in 8 GB (3:4 is 384×512, 16:9 is 576×320...).

The sprite is **never stretched**. The H3 node stretches the first frame to
fill the canvas, and WAN crops it: a square sprite on a 3:4 clip came out
tall and thin. Sprite Sheep now widens the canvas with the background colour
instead, without resampling your sprite. That colour is the one measured on
your image, not the preset: with the green preset (0,177,64) on a real green
(64,173,84) the added border fell just outside the cutout threshold and came
out as dark blue bands on every cell. Fixed before release, and there is a
test for it.

### Room to move

A new **Space** option shrinks the figure and leaves air above the head:
*As the sprite*, *Normal* (80% of the height) or *Wide* (68%, feet at the
bottom). Without it, a jump or an uppercut either leaves the frame or makes
the model zoom out mid-clip. Use the same setting for every action of a
character and they all share one scale — which is what a game needs.

### History, and regenerate with a new seed

**History** in the header lists every generation with a thumbnail. Open the
folder, open the log, or **Regenerate with another seed**: it re-runs the
exact same request, using the copy of the sprite saved in that folder, so it
still works if you have since moved or redrawn the original.

### A log for every render

Every output folder now has `<name>_log.html` next to the sheet and the GIF:
start and end time, inference time, model, steps, **seed**, clip length,
frames generated and frames in the sheet, grid, real GIF fps, resolution,
aspect ratio, cutout details (method, requested and measured tint,
tolerance), and the full prompt — with the source sprite, the GIF and the
sheet shown side by side. It opens in any browser. A `meta.json` sits next to
it with the full request.

The seed used to be picked inside the backend and lost; it is now chosen up
front and recorded, so any animation can be reproduced.

### Cancel, and a bar that tells the truth

- **Cancel** stops the job and ComfyUI with it — it only interrupts *our*
  prompt now, not whatever else you are running in ComfyUI. Measured: GPU back
  to idle 3 seconds after the click.
- **Time left** appears from the first sampling step (before that, loading
  times vary from seconds to minutes and any number would be a guess).
- When a job finishes and the window is not focused, the taskbar flashes.

### Background removal fixes

On light backgrounds the cutout emptied **every** interior pixel that matched
the background colour — so white eyes and light highlights were punched out
(the sample sheep lost 99% of them). Only large enclosed areas, like the gap
between an arm and the body, are removed now.

### Linux and AMD — experimental

- A **Linux x86_64** build (`.tar.gz`, launcher script, uses your system
  Python 3 with pillow, numpy, scipy, huggingface_hub). It is built and
  checked, but **it has not been run on real Linux hardware yet** — reports
  very welcome on Discord.
- **AMD** (ROCm) and **Intel/AMD on DirectML** are now detected and named
  correctly instead of being reported as "no CUDA GPU". The heavy lifting is
  ComfyUI's, so if your ComfyUI runs on your card, Sprite Sheep should too —
  but it has **not been validated on AMD hardware**.

### For scripts: a command line

```
python sidecar/cli.py genera --sprite hero.png --prompt-file punch.txt --formato 3:4
python sidecar/cli.py lotto set.json      # several actions, one job
python sidecar/cli.py storico             # history
python sidecar/cli.py rigenera <folder>   # same request, new seed
```

Same pipeline, same output folders and history as the app. Ctrl+C cancels in
ComfyUI too.

### Also in this release

- **The local engine is locked down.** It only answers the app that launched
  it: a per-launch token, and requests from web pages (Origin/Host checks)
  are refused.
- **A quiet Ko-fi line.** From your second successful generation, a small
  grey line under the result mentions Ko-fi — once per session, with a × and a
  *Don't show again* that sticks. No pop-ups.
- The Windows exe properties now show the right version (they said 0.9.0.0).
- History, queue and plural fixes found while recording the trailer.
- Tests for the queue, cutout, parameters, log and scenes, and a CI workflow.

### Requirements

NVIDIA GPU with 8 GB of VRAM (tested on an RTX 3050 8 GB) · 32 GB RAM
recommended · ComfyUI installed separately · one model, downloaded from inside
the app. Windows: nothing else, Python is included. Linux: system Python 3.

The **MiniMax H3 Community License excludes the EU, the UK, South Korea and the
United States, and the clause covers the outputs.** The program shows the
full text before downloading. WAN 2.2 (Apache 2.0) has no such restriction.

"Windows protected your PC" on first launch: the exe is not code-signed —
click *More info* → *Run anyway*.
