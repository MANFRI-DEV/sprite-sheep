# 🐑 Welcome to Sprite Sheep

**Sprite Sheep** turns a still sprite into an **animated sprite sheet** and a **GIF**, using video diffusion models that run on your own PC. No cloud, no subscription: everything stays on your machine.

## How it works
You give the program **one sprite** and **a prompt built from fields** — subject, style, background, camera, and the steps of the animation. It composes that into the dialect the chosen model expects, generates the clip, pulls the frames out, keys the background to transparent and lays them out into a sheet you can use straight away.

## What you need
> **An NVIDIA GPU with at least 8 GB of VRAM** · **ComfyUI** installed · **one model** of your choice
> Python is **not** required: the program carries its own.

## The models
🟢 **MiniMax H3** — 38.9 GB · about **9–10 minutes** for 2 seconds on an RTX 3050. This is the one we recommend today.
🟡 **WAN 2.2** — 16.9 GB · **in progress**: the decode stalls under 8 GB of VRAM. Selectable, but not reliable yet.

⚠️ **Read the licence before downloading.** The *MiniMax H3 Community License* excludes the **European Union, the United Kingdom, South Korea and the United States**, and the clause covers the outputs you produce as well. The program shows it to you in full and blocks the download until you accept it. WAN 2.2 is Apache 2.0, with no territorial restrictions.

## Status: pre-alpha 0.0.2
A single edition, no watermark and no generation limits. This is very young
software and we say so openly: it works, but it has rough edges. If you find a bug, post in **#reports** and attach what the *Copy diagnostics* button gives you: it contains GPU, version and paths, and that is what makes a report answerable.

## Where to start
1️⃣ Read 📌 **#install** — three steps, half an hour at most counting downloads
2️⃣ Show what you make in 🎨 **#creations**
3️⃣ Prompts that work, and recipes, in 💡 **#useful-prompts**
4️⃣ Questions in ❓ **#support**

Happy animating. 🐑
