SPRITE SHEEP 0.0.2-pre-alpha
============================

From one sprite and a prompt, generates an animated sprite sheet and a GIF.

This build contains NO dependencies and NO model weights: you install those
once, following the three steps below. The program checks by itself what is
missing and says so in the Settings window.

This is a PRE-ALPHA. It works, but it has rough edges, and formats may change
without notice.


WHAT IS IN THE PACKAGE
----------------------
  SpriteSheep.exe    the application
  sidecar/           the Python engine (source code, readable)
  python/            embedded Python runtime, so you install nothing
  README.txt         this file
  requirements.txt   library list, for running the sidecar with your own Python
  THIRD-PARTY-LICENCES.txt

Keep the sidecar/ folder next to the executable: the application looks for it
there.


WHAT YOU NEED TO INSTALL
------------------------

1) COMFYUI
   https://github.com/comfyanonymous/ComfyUI/releases/latest
   Install it wherever you like. Sprite Sheep looks for it in the usual
   places on its own; if it cannot find it, you point it there from Settings.

   A recent version is required. The nodes used — MiniMaxH3ImageToVideo,
   Wan22ImageToVideoLatent, ModelSamplingSD3 — are part of the ComfyUI core,
   so you do not need to install any custom node.

   Python is NOT required separately: this build carries its own in python\.

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
  An NVIDIA GPU with at least 8 GB of VRAM and CUDA drivers.
  Without a GPU the application starts and tells you so, but generating is
  impractical.
  Disk space: 39 GB for H3, 17 GB for WAN.


LANGUAGES
---------
Italian and English, from the selector at the top right. On first run it
follows the Windows language.


THIRD-PARTY LICENCES
--------------------
ComfyUI is third-party free software under GPL-3.0. Sprite Sheep neither
redistributes nor embeds it: you install it yourself, and the two programs
talk to each other over HTTP on localhost.

The model weights are not included and remain subject to the licences of their
respective authors, which the program shows you before downloading.

The licences of the libraries bundled with this package are listed in
THIRD-PARTY-LICENCES.txt.
