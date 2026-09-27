**Windows 64-bit · 104.6 MB · no build step required**

Four things you asked for, one model that halves the wait, and the three
buttons this page has been missing.

### Cut out any background colour, not just white

The old cutout assumed a light background: `r,g,b > 225`. Point it at a green
screen and nothing happened at all. There is now a colour picker in the image
panel — presets, a hex field, an eyedropper that samples the image itself —
and a tolerance slider.

Two things in there are worth knowing about, because both were bugs first.

**"Green" is not green.** The preset says (0,177,64); a real green-screen
render came out at (64,173,84). That is 67 apart, so no pixel fell inside the
threshold and the whole frame stayed opaque. The requested tint now snaps onto
the one the image actually contains, which is why `auto`, `green`, `#00B140`
and `0,177,64` all give the same result.

**Enclosed areas.** The gap between the head and the ponytail is green, it is
background, and it stayed opaque — because the rule was "background is what
touches the border", which that gap does not. The rule is now "a region is
background if it contains a pixel of the full background colour", seed by
seed. On one sheet that recovered 524 regions and 27,211 pixels.

The same cutout runs on every generated frame, so the sheet and the GIF come
out transparent without a second pass.

### A wizard instead of a node graph

The prompt used to be a graph of section and beat nodes on a canvas. It was
compact and it was the wrong shape for the job: you had to know the whole
structure before you could fill in any of it.

**Wizard prompt creation** asks one section at a time — subject, style,
background, camera, beats, loop — validates each page before the next, and
shows the assembled prompt at the end. The output is identical to what the
graph produced; only the way in changed.

### A progress bar that says what it is doing

Generating takes minutes and the bar used to sit at 12% for most of them, then
jump to 100%. Sprite Sheep now listens to ComfyUI over its WebSocket and
reports the actual phase:

```
preparing the conditioning
loading the diffusion model
generating frames 3/8
decoding the video (the GPU is maxed out)
saving the output
```

Both event formats are handled — `progress_state`, which recent ComfyUI sends,
and the older `progress` — so an older install still gets a bar instead of
being treated as broken.

### MiniMax H3 Fast

FastVideo's distilled H3 runs the sampler in **8 steps instead of 20**. It is
a separate entry in the Models panel; the weights are 22.1 GB and it shares
the text encoder and both VAEs with the full model, so if you already have H3
only the checkpoint is downloaded.

Measured here on an RTX 3050 8 GB, same prompt, same seed, 73 frames at
448×448:

| | H3 | H3 Fast |
|---|---:|---:|
| steps | 20 | 8 |
| sampling | 388.7 s | 243.4 s |
| total, weights already loaded | 10:01 | 4:38 |

**Sampling is 1.60× faster, not 2.5×**, and the reason is worth stating: the
fast checkpoint ships as `int8_convrot`, which on Ampere costs about 1.57×
more per step than the full model's `fp8_scaled`. Two and a half times fewer
steps, each one half again as expensive. On a card with native FP8 the gap
should be wider; on a 30-series it is what you see above.

The MiniMax H3 Community Licence applies to the distilled weights too, EU
exclusion included. The app shows the full text before downloading.

### Four buttons

**Check for update**, **Discord**, **Instagram** and **Ko-fi**, in the header
and on the splash screen. A link that is not configured leaves its button
switched off with the reason in the tooltip, rather than sending you to a 404.

### Also in this release

- **The splash has a Start button.** It used to dismiss itself the moment the
  engine answered, so if you had walked away you came back to a screen you
  never saw appear. Start stays disabled until the engine responds, and turns
  into "Enter anyway" after 25 seconds — being stuck on the sheep is worse
  than seeing the error in the status bar.
- **Sprite Sheep asks ComfyUI instead of guessing.** Weight filenames were
  hard-coded down to the quantisation suffix, the sprite was copied into an
  `input/` inferred from the ComfyUI path, and the result was read back from
  an inferred `output/`. None of those hold: your H3 may be `int8_convrot`
  rather than `fp8_scaled`, and `--input-directory` or
  `extra_model_paths.yaml` move the folders. Weights are now resolved against
  `/object_info`, the sprite is sent with `POST /upload/image`, and the result
  is fetched from `/view`.
- **One version number.** It lived in four independent constants and they had
  already contradicted each other on screen — `/health` answering one number
  while the badge showed another. The Python side reads one constant, the
  splash reads the project setting, and the build refuses to run if the two
  disagree.
- **English throughout, white text, layout that fits.** The interface was a
  mix of Italian and English, and the header alone wanted 1421 px on a 1366 px
  screen. Both fixed.

### Requirements

NVIDIA GPU with at least 8 GB of VRAM · ComfyUI installed separately · one
model, downloaded from inside the app. Python is not required, the package
carries its own.

The MiniMax H3 Community License **excludes the EU, the UK, South Korea and
the United States**, and the clause covers the outputs. The program shows the
full text before downloading.
