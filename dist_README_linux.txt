SPRITE SHEEP 0.0.5-pre-alpha  -  Linux x86_64
===========================================

From one sprite and a prompt, generates an animated sprite sheet and a GIF.

This build contains NO dependencies and NO model weights: you install those
once, following the three steps below. The program checks by itself what is
missing and says so in the Settings window.

This is a PRE-ALPHA. It works, but it has rough edges, and formats may change
without notice.


WHAT IS IN THE PACKAGE
----------------------
  SpriteSheep.x86_64   the application
  SpriteSheep.sh       launcher: checks your Python, then starts the app
  sidecar/             the Python engine (source code, readable)
  README.txt           this file
  requirements.txt     the four libraries the engine needs
  THIRD-PARTY-LICENCES.txt

Keep the sidecar/ folder next to the executable: the application looks for it
there.

Start it with ./SpriteSheep.sh — the launcher checks that your Python has the
libraries before starting, so a missing module shows up as one clear line
instead of an engine that dies in silence.


WHAT YOU NEED TO INSTALL
------------------------

1) COMFYUI
   https://github.com/comfyanonymous/ComfyUI/releases/latest
   Install it wherever you like. Sprite Sheep looks for it in the usual
   places on its own; if it cannot find it, you point it there from Settings.

   A recent version is required. The nodes used — MiniMaxH3ImageToVideo,
   Wan22ImageToVideoLatent, ModelSamplingSD3 — are part of the ComfyUI core,
   so you do not need to install any custom node.

   Python 3.10 or newer, from your distribution, with four libraries:

       python3 -m pip install --user pillow numpy scipy huggingface_hub

   Unlike the Windows build, this one does NOT carry its own interpreter.
   There is no official embeddable Python for Linux, and a copied virtualenv
   holds the absolute paths of the machine that made it, so it would not
   start on yours. Every distribution already ships Python; the launcher
   checks it and tells you exactly what is missing.

2) ONE MODEL, your choice
   From the Models panel you have two ways:

   - "Download": fetches the weights from HuggingFace. It shows you the
     licence first and asks you to accept it.
   - "Select folder...": if you already have the weights — inside ComfyUI's
     models/ folder, for instance — it links them without copying and without
     downloading anything again.

   MiniMax H3        38.9 GB   The one that works. High quality and steady,
                               but heavy and slow: about ten minutes for two
                               seconds of animation on an RTX 3050.
                               MIND THE LICENCE. The MiniMax H3 Community
                               License excludes the European Union, the United
                               Kingdom, South Korea and the United States, and
                               the clause covers the outputs you produce as
                               well. Read it before accepting; the program
                               shows it to you in full.

   WAN 2.2 TI2V 5B   16.9 GB   Apache 2.0, no territorial restrictions, and
                               far lighter. IN PROGRESS, not reliable yet:
                               the VAE decode thrashes under 8 GB of VRAM and
                               does not finish. You can select it and it will
                               download, but expect generation to stall.
                               The Models panel marks it as such.


HARDWARE
--------
  A GPU with at least 8 GB of VRAM. Any card ComfyUI can drive will do:

    NVIDIA   CUDA drivers. This is the path the program was developed and
             measured on.
    AMD      DirectML on Windows, ROCm on Linux. Sprite Sheep detects the
             card and reports which API is in use. The generation itself is
             ComfyUI's job, and on AMD it is slower and less tested than on
             NVIDIA: treat it as usable, not as validated.
    Intel    Arc with oneAPI, same caveat as AMD.

  The computation never happens inside Sprite Sheep: it asks ComfyUI which
  device it is using and shows it to you.

  Without a GPU the application starts and tells you so, but generating is
  impractical.
  Disk space: 39 GB for H3, 17 GB for WAN.


LANGUAGES
---------
Italian and English, from the selector at the top right. On first run it
follows your system language ($LANG).


THIRD-PARTY LICENCES
--------------------
ComfyUI is third-party free software under GPL-3.0. Sprite Sheep neither
redistributes nor embeds it: you install it yourself, and the two programs
talk to each other over HTTP on localhost.

The model weights are not included and remain subject to the licences of their
respective authors, which the program shows you before downloading.

The licences of the libraries bundled with this package are listed in
THIRD-PARTY-LICENCES.txt.
