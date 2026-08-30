"""Backend ponte: delega l'inferenza a una ComfyUI installata dall'utente.

Scelta di licenza: ComfyUI e' GPL-3.0. Sprite Sheep **non la ridistribuisce**
e non la incorpora: la trova sul sistema e ci parla via HTTP su localhost.
Non c'e' linking ne' distribuzione, quindi il copyleft non si estende a questo
software. Il prezzo e' che l'utente deve installarla: se ne occupa la procedura
guidata (`comfyui_setup.py`).

Il grafo viene costruito qui, con **soli nodi del core di ComfyUI**: nessun
custom node richiesto, cosi' la procedura guidata deve solo verificare che
ComfyUI ci sia e sia aggiornata.

Interfaccia rispettata: entra sprite + prompt, esce una lista di frame. Il
resto della catena non sa che dietro c'e' ComfyUI.
"""
import json
import math
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

from testi import t

from . import Backend

COMFY = "http://127.0.0.1:8188"
COLONNE_STRIP = 8      # griglia di servizio per riportare indietro i frame

# Nodi usati dal grafo: tutti core. Serve alla procedura guidata per il controllo.
CLASSI_RICHIESTE = [
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage",
    "MiniMaxH3ImageToVideo", "KSamplerSelect", "BasicGuider", "BasicScheduler",
    "RandomNoise", "SamplerCustomAdvanced", "VAEDecode", "ImageGrid", "SaveImage",
]


def _post(rotta: str, corpo: dict) -> dict:
    req = urllib.request.Request(
        COMFY + rotta, data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def _get(rotta: str, timeout: int = 60) -> dict:
    return json.load(urllib.request.urlopen(COMFY + rotta, timeout=timeout))


def comfy_disponibile() -> bool:
    try:
        _get("/system_stats")
        return True
    except Exception:
        return False


def _cartelle_comfy() -> tuple[Path, Path]:
    """input/ e output/ della ComfyUI in uso.

    `/system_stats` non espone il percorso dell'installazione, quindi si usa
    quello individuato dalla procedura guidata. Nessun percorso cablato: su
    un'altra macchina non esisterebbe.
    """
    import comfyui_setup
    base = comfyui_setup.trova_installazione()
    if not base:
        raise RuntimeError(t("gen.cartella_ignota"))
    base = Path(base)
    return base / "input", base / "output"


def costruisci_grafo(immagine: str, prompt: str, lunghezza: int,
                     larghezza: int, altezza: int, seed: int,
                     modelli: dict, passi: int = 20) -> dict:
    """Grafo in formato API, soli nodi core."""
    righe = math.ceil(lunghezza / COLONNE_STRIP)
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": modelli["diffusion"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": modelli["text_encoder"], "type": "minimax", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": modelli["vae"]}},
        # Il VAE audio non entra nel grafo: il nodo H3 di ComfyUI espone un solo
        # ingresso `vae`, quello video, usato sia qui sia in decodifica.
        "5": {"class_type": "LoadImage", "inputs": {"image": immagine}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0],
            "first_frame": ["5", 0], "prompt": prompt,
            "width": larghezza, "height": altezza, "length": lunghezza}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "8": {"class_type": "BasicGuider", "inputs": {
            "model": ["1", 0], "conditioning": ["6", 0]}},
        "9": {"class_type": "BasicScheduler", "inputs": {
            "model": ["1", 0], "scheduler": "simple", "steps": passi, "denoise": 1.0}},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": int(seed)}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["10", 0], "guider": ["8", 0], "sampler": ["7", 0],
            "sigmas": ["9", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {
            "samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "ImageGrid", "inputs": {
            "images": ["12", 0], "columns": COLONNE_STRIP,
            "cell_width": larghezza, "cell_height": altezza, "padding": 0}},
        "14": {"class_type": "SaveImage", "inputs": {
            "images": ["13", 0], "filename_prefix": "SpriteSheep/raw"}},
    }, righe


class BackendComfyUIH3(Backend):
    nome = "MiniMax H3 via ComfyUI"

    # nomi attesi nelle cartelle modelli di ComfyUI
    MODELLI = {
        "diffusion": "minimax_h3_fl2va_pruned_fp8_scaled.safetensors",
        "text_encoder": "qwen3vl_32b_minimax_h3_int4_convrot.safetensors",
        "vae": "minimax_h3_video_vae_fp16.safetensors",
    }

    def genera(self, sprite: str, prompt: str, lunghezza: int,
               larghezza: int, altezza: int, seed: int,
               avanzamento=None) -> list:
        if not comfy_disponibile():
            raise RuntimeError(t("gen.comfy_muta", url=COMFY))

        cartella_in, cartella_out = _cartelle_comfy()
        src = Path(sprite)
        dst = cartella_in / ("spritesheep_" + src.name)
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dst)

        grafo, righe = costruisci_grafo(
            dst.name, prompt, lunghezza, larghezza, altezza,
            int(seed) or int(time.time()), self.MODELLI)

        r = _post("/prompt", {"prompt": grafo})
        job = r.get("prompt_id")
        if not job:
            raise RuntimeError(t("gen.grafo_rifiutato", dettaglio=r))

        file_out = None
        # ---------------------------------------------------------------
        # Attesa a scadenza, non a numero di giri: ogni tentativo puo'
        # costare fino al proprio timeout, quindi contare le iterazioni non
        # dice quanto tempo e' passato davvero.
        #
        # Mentre decodifica il VAE, ComfyUI tiene la GPU al 100% e il suo
        # server HTTP smette di rispondere per decine di secondi. Prima qui
        # si catturava solo HTTPError: un timeout saliva e buttava via la
        # generazione, con dieci minuti di GPU gia' spesi. Un timeout non
        # e' un fallimento, e' "adesso e' occupata".
        # ---------------------------------------------------------------
        scadenza = time.time() + 2 * 3600
        muti = 0
        while time.time() < scadenza:
            time.sleep(2.0)
            try:
                st = _get("/history/%s" % job, timeout=30)
                muti = 0
            except urllib.error.HTTPError:
                continue
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                # Se pero' non risponde per un quarto d'ora di fila, e'
                # caduta davvero e continuare non serve a nessuno.
                muti += 1
                if muti >= 30:
                    raise RuntimeError(
                        t("gen.comfy_muta", url=COMFY)) from e
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
                    file_out = cartella_out / im.get("subfolder", "") / im["filename"]
            if file_out:
                break
        if not file_out or not Path(file_out).exists():
            raise RuntimeError(t("gen.nessuna_immagine"))

        if avanzamento:
            avanzamento(0.95)

        strip = Image.open(file_out).convert("RGBA")
        cw, ch = strip.width // COLONNE_STRIP, strip.height // righe
        frames = []
        for i in range(lunghezza):
            r_i, c_i = divmod(i, COLONNE_STRIP)
            frames.append(strip.crop((c_i * cw, r_i * ch, (c_i + 1) * cw, (r_i + 1) * ch)))
        if avanzamento:
            avanzamento(1.0)
        return frames
