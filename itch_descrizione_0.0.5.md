# Sprite Sheep — one drawing in, a game-ready sprite sheet out

**Sprite Sheep animates a single starting drawing and exports a consistent
sprite sheet and a GIF, ready for your game — generated entirely on your own
PC.** No account, no uploads, no cloud.

It drives a local ComfyUI with video models — **MiniMax H3**, **H3 Fast** and
**WAN 2.2** — and takes care of everything around the model: the prompt, the
clip length the model accepts, picking the frames, removing the background,
and packing the sheet.

## What's new in 0.0.5

- **Queue a whole move set** — idle, run, jump, attack… prepared one by one,
  generated in one click.
- **Any aspect ratio** — 1:1, 3:4, 4:3, 9:16, 16:9, 21:9. Your sprite is never
  stretched.
- **Room to move** — shrink the figure so jumps and high hits stay in frame,
  with the same scale across every action.
- **History** — every render with its thumbnail; regenerate any of them with a
  new seed.
- **A log for every render** — model, seed, timings, frames, cutout details,
  full prompt, in a page you can open in any browser.
- **Cancel** that really stops the GPU, a time-left estimate, and better
  background removal.
- **Linux build and AMD detection** (both experimental), and a command line
  for scripts.

## How it works

1. **One drawing** — your character on a flat background (any colour: white,
   green screen…). Square or not.
2. **A prompt** — a step-by-step wizard writes it in the format each model
   expects, and checks it before you spend GPU time.
3. **Generate** — pick duration, frames, aspect ratio. Queue several actions
   if you like.
4. **Get** — a transparent sprite sheet (e.g. 5×5, 25 frames), a looping GIF,
   and an HTML log.

**Real timings** on an RTX 3050 8 GB with H3 Fast: about **4½ minutes per
action**, five actions in 22–24 minutes.

## Requirements

- **NVIDIA GPU with 8 GB of VRAM** (tested on RTX 3050 8 GB). AMD (ROCm /
  DirectML) is detected but not yet validated.
- **32 GB RAM** recommended (less may work with more VRAM).
- **ComfyUI**, installed separately — the app finds it and guides you.
- **One video model**, downloaded from inside the app after you accept its
  licence (~20 GB for H3).
- Windows 64-bit (Python included) or Linux x86_64 (experimental, uses your
  system Python 3).

## Licences — please read

Sprite Sheep itself is free. **What you may do with the animations depends on
the model you use:**

- **MiniMax H3 / H3 Fast** — MiniMax H3 Community License. It **excludes the
  EU, the UK, South Korea and the United States, and the exclusion covers the
  outputs.** Read it before using the results commercially.
- **WAN 2.2** — Apache 2.0, no territorial restriction.

The app shows the full licence text before downloading any model. Credit to
Sprite Sheep is appreciated.

## Support

Sprite Sheep is free and made by one person. Bug reports and feedback on
**Discord** are the most useful help; if you want to support the development
of local, no-cloud tools, there is **Ko-fi**.

*Pre-alpha: it works, it has rough edges, and formats may change.*
