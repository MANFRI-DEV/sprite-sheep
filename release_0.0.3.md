**Windows 64-bit · 104.6 MB · no build step required**

Two reports on itch.io looked like two different problems. One was stuck on
*"2 files not visible to ComfyUI yet"* after downloading the weights and
pointing Sprite Sheep at the ComfyUI folder. The other got `HTTP Error 400:
Bad Request` and reasonably asked where it was even connecting, since
everything runs locally.

It was one bug, seen from two ends.

### The weights were never linked into ComfyUI

ComfyUI loads models **by name** from its own `models/` directory, so a file
sitting in `SpriteSheep/models/` is invisible to it. The linking step ran in
exactly two places: at the end of a download, and from **Select folder…**.
Anyone who downloaded the weights *before* setting the ComfyUI path hit
neither — at download time there was no path to link into, so the step
returned immediately.

Pressing **Re-check** did not help, because Re-check only looked. The
instruction printed under it promised the opposite: *"press Re-check: they get
linked into ComfyUI's folder"*. It now does what it says.

### The 400 was the same bug

The connection was local and it worked; ComfyUI answered by **rejecting the
graph**. Its loader nodes only accept filenames they can see in `models/`, so
with nothing linked, validation failed and returned 400 with the reason in the
response body.

That body was being discarded: `json.load(urlopen(...))` raises on a 400
before anything reads the response. The same failure now reads:

```
ComfyUI rejected the graph: Prompt outputs failed validation —
UNETLoader: unet_name: 'minimax_h3_fl2va_pruned_fp8_scaled.safetensors' not in [] —
VAELoader: vae_name: 'minimax_h3_video_vae_fp16.safetensors' not in []
```

The empty `[]` is the whole diagnosis: ComfyUI can see no models in that folder.

### Also fixed

- **Failed links were silent.** `OSError` was caught and ignored, so a genuine
  failure (no disk space, read-only folder, no hard-link support) left you at
  "not visible to ComfyUI yet" with no reason. The error is now shown.
- **`<null>` under every file** in the Models panel. The engine sends
  `errore: null` for a healthy file, and GDScript's `get()` fallback does not
  apply when the key exists and holds null, so `str(null)` produced the literal
  `"<null>"`.

### Upgrading

Nothing gets re-downloaded. Install 0.0.3, open **Settings**, press
**Re-check** once: the weights are linked in place and the Models step turns
green. If you were hitting the 400, the same press fixes it.

### Requirements

NVIDIA GPU with at least 8 GB of VRAM · ComfyUI installed separately · one
model, downloaded from inside the app. Python is not required, the package
carries its own.

The MiniMax H3 Community License **excludes the EU, the UK, South Korea and
the United States**, and the clause covers the outputs. The program shows the
full text before downloading.
