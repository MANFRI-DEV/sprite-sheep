"""Riconoscimento della GPU: NVIDIA, AMD, Intel, Apple.

Qui non c'e' una Radeon su cui provare, e comprarne una per verificare una
stringa non sta in piedi. Quello che si puo' fare — e che serve davvero — e'
dare in pasto al parser le risposte che quelle macchine producono davvero,
prese dalla forma documentata di `/system_stats` e dalle firme di versione di
PyTorch.

Il caso che conta e' il secondo: **le build ROCm di PyTorch espongono l'API
CUDA**, apposta per non far riscrivere il codice a nessuno. Chi guarda solo
`torch.cuda.is_available()` conclude "NVIDIA" davanti a una Radeon che sta
lavorando, ed e' esattamente quello che l'interfaccia faceva prima: scriveva
"nessuna GPU CUDA" a chi stava generando.

    python sidecar/test_gpu.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import server                                              # noqa: E402

## nome della scheda -> produttore atteso
NOMI = [
    ("NVIDIA GeForce RTX 3050", "nvidia"),
    ("NVIDIA RTX A4000", "nvidia"),
    ("AMD Radeon RX 7900 XTX", "amd"),
    ("Radeon RX 6800", "amd"),
    ("AMD Instinct MI210", "amd"),
    ("gfx1100", "amd"),                  # ROCm a volte da' solo il nome gfx
    ("Intel(R) Arc(TM) A770 Graphics", "intel"),
    ("Apple M3 Max", "apple"),
    ("Scheda Sconosciuta 9000", None),
]

## Risposte di /system_stats come le manda ComfyUI, una per piattaforma.
SISTEMI = [
    ("NVIDIA su Windows", {
        "system": {"pytorch_version": "2.11.0+cu128"},
        "devices": [{"name": "cuda:0 NVIDIA GeForce RTX 3050 : cudaMallocAsync",
                     "type": "cuda", "vram_total": 8589934592,
                     "vram_free": 7516192768}],
    }, {"api": "cuda", "produttore": "nvidia",
        "gpu": "NVIDIA GeForce RTX 3050", "vram_mb": 8192}),

    ("AMD su Linux (ROCm)", {
        "system": {"pytorch_version": "2.6.0+rocm6.2"},
        "devices": [{"name": "cuda:0 AMD Radeon RX 7900 XTX : native",
                     "type": "cuda", "vram_total": 25757220864,
                     "vram_free": 24000000000}],
    }, {"api": "rocm", "produttore": "amd",
        "gpu": "AMD Radeon RX 7900 XTX", "vram_mb": 24564}),

    ("AMD su Windows (DirectML)", {
        "system": {"pytorch_version": "2.4.1+cpu"},
        "devices": [{"name": "privateuseone:0 AMD Radeon RX 7800 XT",
                     "type": "directml", "vram_total": 17179869184,
                     "vram_free": 16000000000}],
    }, {"api": "directml", "produttore": "amd", "vram_mb": 16384}),

    ("Apple Silicon", {
        "system": {"pytorch_version": "2.6.0"},
        "devices": [{"name": "mps", "type": "mps",
                     "vram_total": 38654705664, "vram_free": 30000000000}],
    }, {"api": "mps", "produttore": "apple"}),

    ("solo CPU", {
        "system": {"pytorch_version": "2.6.0+cpu"},
        "devices": [{"name": "cpu", "type": "cpu",
                     "vram_total": 0, "vram_free": 0}],
    }, {"cuda": False}),
]


def main() -> int:
    errori = 0

    print("== produttore dal nome")
    for nome, atteso in NOMI:
        avuto = server._produttore(nome)
        ok = avuto == atteso
        errori += not ok
        print("   %-34s %-7s %s" % (nome, avuto, "" if ok else
                                    "ERRORE: atteso %s" % atteso))

    print("\n== risposta di ComfyUI")
    originale = server.__dict__.get("_get")
    for etichetta, risposta, atteso in SISTEMI:
        # Si sostituisce la sola funzione di rete: tutto il resto del parser
        # gira per davvero, che e' il punto del test.
        import backend.comfyui_bridge as ponte
        vero = ponte._get
        ponte._get = lambda rotta, timeout=60, _r=risposta: _r
        try:
            avuto = server._gpu_da_comfyui()
        finally:
            ponte._get = vero

        sbagliati = {k: (avuto.get(k), v) for k, v in atteso.items()
                     if avuto.get(k) != v}
        errori += bool(sbagliati)
        print("   %-26s %s" % (etichetta, "ok" if not sbagliati else
                               "ERRORE " + repr(sbagliati)))
        if not sbagliati and avuto.get("cuda"):
            print("      -> %s, %s, %s MB"
                  % (avuto.get("gpu"), avuto.get("api"), avuto.get("vram_mb")))
    del originale

    print("\n%s" % ("tutto a posto" if not errori else "%d errori" % errori))
    return 1 if errori else 0


if __name__ == "__main__":
    raise SystemExit(main())
