"""Procedura guidata per l'installazione di ComfyUI.

Sprite Sheep non ridistribuisce ComfyUI (e' GPL-3.0): la usa se l'utente ce
l'ha. Questo modulo dice, passo per passo, cosa manca e come rimediare.

I controlli sono in ordine di dipendenza: se ComfyUI non c'e' non ha senso
controllare i modelli, quindi i passi successivi restano "in attesa" invece
di comparire come errori.
"""
import json
import os
import subprocess
import urllib.request
from pathlib import Path

import config
from testi import t

IMPOSTAZIONI = config.CACHE_DIR / "comfyui.json"
LOG_COMFY = config.CACHE_DIR / "comfyui.log"
URL_DOWNLOAD = "https://github.com/comfyanonymous/ComfyUI/releases/latest"
URL_GUIDA = "https://docs.comfy.org/installation/desktop/windows"

# Nomi di cartella tipici, cercati su ogni unita' e nelle cartelle utente:
# nessun percorso completo cablato, cosi' la ricerca funziona ovunque.
NOMI_TIPICI = [
    "ComfyUI",
    "ComfyUI_windows_portable/ComfyUI",
    "AI/ComfyUI",
    "AI_Video/ComfyUI",
    "Documents/ComfyUI",
    "Desktop/ComfyUI",
]

MODELLI_ATTESI = {
    "diffusion_models": "minimax_h3_fl2va_pruned_fp8_scaled.safetensors",
    "text_encoders": "qwen3vl_32b_minimax_h3_int4_convrot.safetensors",
    "vae": "minimax_h3_video_vae_fp16.safetensors",
}


def _leggi() -> dict:
    if IMPOSTAZIONI.exists():
        try:
            return json.loads(IMPOSTAZIONI.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def imposta_percorso(percorso: str) -> dict:
    p = Path(percorso)
    if not (p / "main.py").is_file():
        return {"ok": False, "errore": t("comfy.err.no_main")}
    d = _leggi()
    d["percorso"] = str(p)
    IMPOSTAZIONI.write_text(json.dumps(d, indent=2), encoding="utf-8")
    return {"ok": True, "percorso": str(p)}


def _radici() -> list[Path]:
    """Punti da cui iniziare la ricerca, adatti al sistema in uso.

    Su Windows le unita' hanno una lettera; su Linux e macOS si parte dalla
    radice e dai punti di mount abituali. Nessun percorso cablato: se
    l'installazione sta altrove, l'utente la indica dalla procedura guidata.
    """
    radici: list[Path] = []
    if os.name == "nt":
        for lettera in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            p = Path("%s:\\" % lettera)
            if p.exists():
                radici.append(p)
    else:
        for d in ("/", "/opt", "/srv", "/mnt", "/media", "/media/" + os.environ.get("USER", "")):
            p = Path(d)
            if d and p.is_dir():
                radici.append(p)

    casa = Path(os.path.expanduser("~"))
    if casa.is_dir():
        radici.append(casa)
    return radici


def trova_installazione() -> str | None:
    """Percorso salvato, altrimenti ricerca sui nomi tipici. Mai cablato."""
    salvato = _leggi().get("percorso")
    if salvato and (Path(salvato) / "main.py").is_file():
        return salvato
    for radice in _radici():
        for nome in NOMI_TIPICI:
            c = radice / nome
            try:
                if (c / "main.py").is_file():
                    return str(c)
            except OSError:
                continue          # unita' rimovibile non pronta
    return None


def _in_ascolto() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=3)
        return True
    except Exception:
        return False


def _classi_mancanti() -> list[str] | None:
    """None se non si riesce a chiedere; altrimenti l'elenco delle mancanti."""
    from backend.comfyui_bridge import CLASSI_RICHIESTE
    try:
        info = json.load(urllib.request.urlopen(
            "http://127.0.0.1:8188/object_info", timeout=30))
    except Exception:
        return None
    return [c for c in CLASSI_RICHIESTE if c not in info]


def _modelli_mancanti(percorso: str | None) -> list[str]:
    if not percorso:
        return list(MODELLI_ATTESI.values())
    base = Path(percorso) / "models"
    return [n for cart, n in MODELLI_ATTESI.items() if not (base / cart / n).is_file()]


def stato() -> dict:
    """Elenco dei passi, ognuno con esito e istruzione."""
    percorso = trova_installazione()
    acceso = _in_ascolto()
    classi = _classi_mancanti() if acceso else None
    mancanti_modelli = _modelli_mancanti(percorso)

    passi = [
        {
            "id": "installata",
            "titolo": t("comfy.installata.titolo"),
            "esito": "ok" if percorso else "azione",
            "dettaglio": percorso or t("comfy.installata.assente"),
            "istruzione": None if percorso else t("comfy.installata.istruzione"),
            "link": None if percorso else URL_DOWNLOAD,
        },
        {
            "id": "avviata",
            "titolo": t("comfy.avviata.titolo"),
            "esito": "ok" if acceso else ("azione" if percorso else "attesa"),
            "dettaglio": t("comfy.avviata.si") if acceso else t("comfy.avviata.no"),
            "istruzione": None if acceso else
                (t("comfy.avviata.premi") if percorso else t("comfy.avviata.prima")),
            "link": None,
        },
        {
            "id": "nodi",
            "titolo": t("comfy.nodi.titolo"),
            "esito": ("attesa" if classi is None else ("ok" if not classi else "azione")),
            "dettaglio": (t("comfy.nodi.irraggiungibile") if classi is None else
                          (t("comfy.nodi.ok") if not classi
                           else t("comfy.nodi.mancano", elenco=", ".join(classi)))),
            "istruzione": None if not classi else t("comfy.nodi.istruzione"),
            "link": None if not classi else URL_GUIDA,
        },
        {
            "id": "modelli",
            "titolo": t("comfy.modelli.titolo"),
            "esito": "ok" if not mancanti_modelli else ("azione" if percorso else "attesa"),
            "dettaglio": (t("comfy.modelli.presenti") if not mancanti_modelli
                          else t("comfy.modelli.mancano", n=len(mancanti_modelli))),
            "istruzione": None if not mancanti_modelli else t("comfy.modelli.istruzione"),
            "link": None,
        },
    ]
    return {
        "percorso": percorso,
        "in_esecuzione": acceso,
        "pronto": all(p["esito"] == "ok" for p in passi),
        "passi": passi,
        "nota_licenza": t("comfy.nota_licenza"),
    }


## Dove sta l'interprete di una ComfyUI, su Windows come su Linux.
_INTERPRETI = [
    ("venv", "Scripts", "python.exe"),      # venv Windows
    ("venv", "bin", "python"),              # venv Linux/macOS
    (".venv", "Scripts", "python.exe"),
    (".venv", "bin", "python"),
]
_INTERPRETI_VICINI = [
    ("python_embeded", "python.exe"),       # pacchetto portatile Windows
    ("python_embedded", "python.exe"),
]


def _interprete(base: Path) -> Path | None:
    for parti in _INTERPRETI:
        p = base.joinpath(*parti)
        if p.is_file():
            return p
    for parti in _INTERPRETI_VICINI:
        p = base.parent.joinpath(*parti)
        if p.is_file():
            return p
    # ultima spiaggia: l'interprete con cui gira il sidecar
    import sys
    return Path(sys.executable) if Path(sys.executable).is_file() else None


def avvia() -> dict:
    """Lancia ComfyUI in un processo separato."""
    if _in_ascolto():
        return {"ok": True, "gia_attiva": True}
    percorso = trova_installazione()
    if not percorso:
        return {"ok": False, "errore": t("comfy.err.non_trovata")}

    base = Path(percorso)
    py = _interprete(base)
    if py is None:
        return {"ok": False,
                "errore": t("comfy.err.no_python", base=base)}

    # Niente finestra di console: l'utente non deve vedere un prompt Python
    # comparire dal nulla. L'output non si butta pero' via, finisce in un log:
    # se ComfyUI non parte, quello e' l'unico posto dove si legge il perche'.
    senza_finestra = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        log = open(LOG_COMFY, "w", encoding="utf-8", errors="replace")
    except OSError:
        log = subprocess.DEVNULL

    try:
        subprocess.Popen(
            [str(py), "main.py", "--preview-method", "none"],
            cwd=str(base),
            creationflags=senza_finestra,
            stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            close_fds=True)
    except Exception as e:
        return {"ok": False, "errore": "%s: %s" % (type(e).__name__, e)}
    return {"ok": True, "avviata": True, "percorso": str(base),
            "log": str(LOG_COMFY),
            "nota": t("comfy.nota_avvio")}


def coda_log(righe: int = 20) -> str:
    """Ultime righe del log di ComfyUI, per capire un avvio che non arriva."""
    try:
        with open(LOG_COMFY, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-righe:])
    except OSError:
        return ""
