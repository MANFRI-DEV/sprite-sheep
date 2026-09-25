"""Backend ponte per WAN 2.2 TI2V 5B, via la ComfyUI dell'utente.

Stessa scelta di licenza del ponte H3 (vedi `comfyui_bridge.py`): ComfyUI non
viene ridistribuita, ci si parla via HTTP su localhost.

Differenze rispetto a H3, tutte dovute al modello:
  - lunghezze valide 4n+1 invece di 17k+5;
  - il condizionamento e' testuale classico, positivo e negativo separati, con
    `CLIPTextEncode`; H3 invece impacchetta tutto nel suo nodo;
  - l'immagine di partenza entra in `Wan22ImageToVideoLatent`, che produce solo
    un LATENT: il condizionamento non la vede;
  - si campiona con `KSampler`, non con la catena guider/sigmas.

Il grafo usa soli nodi del core, come per H3.
"""
import io
import math
import time
import urllib.error
from pathlib import Path

from PIL import Image

from testi import t

from . import Backend
from .comfyui_bridge import (COLONNE_STRIP, COMFY, Annullato, _get, _post,
                             annulla_prompt, carica_immagine,
                             comfy_disponibile, scarica_uscita)

CLASSI_RICHIESTE = [
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "CLIPTextEncode",
    "ModelSamplingSD3", "Wan22ImageToVideoLatent", "KSampler", "VAEDecode",
    "ImageGrid", "SaveImage",
]

# Riscalatura dei sigma per i modelli a flow matching. Il workflow ufficiale di
# ComfyUI per Wan 2.2 TI2V 5B la mette a 8: senza, la prima prova ha prodotto un
# pesce che cresceva di frame in frame e artefatti gialli negli angoli.
SHIFT = 8.0

# Cosa non deve comparire. Per gli sprite conta piu' del prompt positivo: e'
# quello che tiene fuori sfondi, bordi e mani in piu'.
NEGATIVO = (
    "blurry, low quality, jpeg artifacts, watermark, text, letters, signature, "
    "extra limbs, deformed anatomy, changing design, flickering, "
    "camera motion, zoom, pan, cut, scene change, multiple characters, "
    # Lo scontorno toglie il bianco: lampi e scie diventano buchi nella figura.
    "white flash, glow, sparkles, speed lines, motion trails, "
    "turning around, back view"
)


def costruisci_grafo(immagine: str, prompt: str, lunghezza: int,
                     larghezza: int, altezza: int, seed: int,
                     modelli: dict, passi: int = 20,
                     cfg: float = 5.0) -> tuple[dict, int]:
    righe = math.ceil(lunghezza / COLONNE_STRIP)
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": modelli["diffusion"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": modelli["text_encoder"], "type": "wan", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": modelli["vae"]}},
        "4": {"class_type": "LoadImage", "inputs": {"image": immagine}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["2", 0], "text": prompt}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["2", 0], "text": NEGATIVO}},
        "7": {"class_type": "Wan22ImageToVideoLatent", "inputs": {
            "vae": ["3", 0], "start_image": ["4", 0], "batch_size": 1,
            "width": larghezza, "height": altezza, "length": lunghezza}},
        "12": {"class_type": "ModelSamplingSD3", "inputs": {
            "model": ["1", 0], "shift": SHIFT}},
        "8": {"class_type": "KSampler", "inputs": {
            "model": ["12", 0], "positive": ["5", 0], "negative": ["6", 0],
            "latent_image": ["7", 0], "seed": int(seed), "steps": passi,
            "cfg": cfg, "sampler_name": "uni_pc", "scheduler": "simple",
            "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {
            "samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "ImageGrid", "inputs": {
            "images": ["9", 0], "columns": COLONNE_STRIP,
            "cell_width": larghezza, "cell_height": altezza, "padding": 0}},
        "11": {"class_type": "SaveImage", "inputs": {
            "images": ["10", 0], "filename_prefix": "SpriteSheep/wan"}},
    }, righe


class BackendComfyUIWan22(Backend):
    nome = "WAN 2.2 TI2V 5B via ComfyUI"
    PASSI = 20

    MODELLI = {
        "diffusion": "wan2.2_ti2v_5B_fp16.safetensors",
        "text_encoder": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "vae": "wan2.2_vae.safetensors",
    }

    def genera(self, sprite: str, prompt: str, lunghezza: int,
               larghezza: int, altezza: int, seed: int,
               avanzamento=None, fermo=None) -> list:
        if (lunghezza - 1) % 4:
            raise ValueError(t("gen.lunghezza_wan", n=lunghezza))
        if not comfy_disponibile():
            raise RuntimeError(t("gen.comfy_muta", url=COMFY))

        # Lo sprite si manda a ComfyUI via HTTP, come per H3, invece di
        # copiarlo in una cartella `input/` dedotta dal percorso. Qui era
        # rimasta la vecchia strada, e la funzione che deduceva le cartelle
        # e' stata tolta dal ponte nella 0.0.4: da allora questo modulo non
        # si importava nemmeno, e scegliere WAN dava un ImportError.
        nome_in = carica_immagine(Path(sprite))

        grafo, righe = costruisci_grafo(
            nome_in, prompt, lunghezza, larghezza, altezza,
            int(seed) or int(time.time()), self.MODELLI, passi=self.PASSI)

        r = _post("/prompt", {"prompt": grafo})
        job = r.get("prompt_id")
        if not job:
            raise RuntimeError(t("gen.grafo_rifiutato", dettaglio=r))

        file_out = None
        for _ in range(4000):                        # tetto ~2 ore
            time.sleep(2.0)
            if fermo is not None and fermo.is_set():
                annulla_prompt(job)
                raise Annullato(t("gen.annullato"))
            try:
                st = _get("/history/%s" % job)
            except urllib.error.HTTPError:
                continue
            if job not in st:
                if avanzamento:
                    avanzamento(0.5)
                continue
            voce = st[job]
            if voce.get("status", {}).get("status_str") == "error":
                raise RuntimeError(t("gen.comfy_fallita", dettaglio=voce.get("status")))
            for uscita in voce.get("outputs", {}).values():
                for im in uscita.get("images", []):
                    file_out = im
            if file_out:
                break
        if not file_out:
            raise RuntimeError(t("gen.nessuna_immagine"))

        if avanzamento:
            avanzamento(0.95)

        strip = Image.open(io.BytesIO(scarica_uscita(file_out))).convert("RGBA")
        cw, ch = strip.width // COLONNE_STRIP, strip.height // righe
        frames = []
        for i in range(lunghezza):
            r_i, c_i = divmod(i, COLONNE_STRIP)
            frames.append(strip.crop((c_i * cw, r_i * ch, (c_i + 1) * cw, (r_i + 1) * ch)))
        if avanzamento:
            avanzamento(1.0)
        return frames
