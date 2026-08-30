"""Controlla il grafo del bridge contro la ComfyUI installata.

Serve perche' i nodi di ComfyUI cambiano firma fra una versione e l'altra: e'
gia' successo con `audio_vae`, sparito dal nodo H3 e rimasto nel nostro grafo.
Un errore cosi' si vede solo a generazione avviata, dopo il caricamento dei
modelli. Qui invece si vede subito.

Uso, con ComfyUI in esecuzione:
    python test_grafo.py
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Il Python incorporato usa un file `._pth` che fissa sys.path per intero: la
# cartella dello script, che l'avvio normale metterebbe in testa, non c'e'.
# Stessa riga di `server.py`, stesso motivo.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend import comfyui_bridge as b
from backend import comfyui_wan as w

COMFY = "http://127.0.0.1:8188"


def controlla(grafo: dict, info: dict) -> list[str]:
    problemi = []
    for nid, n in grafo.items():
        ct = n["class_type"]
        if ct not in info:
            problemi.append("nodo %s: classe %s assente da ComfyUI" % (nid, ct))
            continue
        spec = info[ct]["input"]
        req = spec.get("required", {})
        opt = spec.get("optional", {})
        noti = set(req) | set(opt)

        for k in n["inputs"]:
            if k not in noti:
                problemi.append("nodo %s (%s): ingresso '%s' non esiste; attesi %s"
                                % (nid, ct, k, sorted(noti)))
        for k in req:
            if k not in n["inputs"]:
                problemi.append("nodo %s (%s): manca l'ingresso obbligatorio '%s'"
                                % (nid, ct, k))
        # valori scelti da un elenco: nomi di modello, sampler, scheduler
        for k, v in n["inputs"].items():
            s = req.get(k) or opt.get(k)
            if isinstance(s, list) and isinstance(s[0], list) and not isinstance(v, list):
                if v not in s[0]:
                    problemi.append("nodo %s (%s): '%s'=%r non e' fra le scelte"
                                    % (nid, ct, k, v))
    return problemi


def main() -> int:
    try:
        info = json.load(urllib.request.urlopen(COMFY + "/object_info", timeout=60))
    except (urllib.error.URLError, OSError) as e:
        print("ComfyUI non risponde su %s: %s" % (COMFY, e))
        return 2

    # il nome del file d'ingresso esiste solo a runtime, dentro ComfyUI/input
    campione = info["LoadImage"]["input"]["required"]["image"][0][0]

    grafi = {
        "MiniMax H3": (b.costruisci_grafo(
            "sprite.png", "prompt di prova", 56, 256, 256, 1234,
            b.BackendComfyUIH3.MODELLI)[0], "5"),
        "WAN 2.2": (w.costruisci_grafo(
            "sprite.png", "prompt di prova", 49, 256, 256, 1234,
            w.BackendComfyUIWan22.MODELLI)[0], "4"),
    }

    esito = 0
    for nome, (grafo, nodo_immagine) in grafi.items():
        grafo[nodo_immagine]["inputs"]["image"] = campione
        problemi = controlla(grafo, info)
        if problemi:
            esito = 1
            print("%s: NON valido" % nome)
            for p in problemi:
                print("   -", p)
        else:
            print("%s: grafo valido" % nome)
    return esito


if __name__ == "__main__":
    sys.exit(main())
