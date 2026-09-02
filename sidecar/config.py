"""Percorsi e costanti condivise del sidecar.

Tenuto separato dal server cosi' i moduli di generazione e download
possono importarlo senza tirarsi dietro l'HTTP.
"""
import os as _os
from pathlib import Path

# Radice del progetto = cartella che contiene sidecar/ e godot/
ROOT = Path(__file__).resolve().parent.parent


def _scrivibile(cartella: Path) -> bool:
    """La cartella accetta scritture? In Program Files no, e va saputo prima."""
    try:
        cartella.mkdir(parents=True, exist_ok=True)
        prova = cartella / ".prova_scrittura"
        prova.write_text("x", encoding="utf-8")
        prova.unlink()
        return True
    except OSError:
        return False


def _dati_utente() -> Path:
    """Cartella dati dell'utente, secondo le convenzioni del sistema."""
    if _os.name == "nt":
        base = _os.environ.get("LOCALAPPDATA") or _os.path.expanduser("~")
    else:
        base = _os.environ.get("XDG_DATA_HOME") or _os.path.join(
            _os.path.expanduser("~"), ".local", "share")
    return Path(base) / "SpriteSheep"


# Installazione portatile: i dati stanno accanto al programma. Se pero' la
# cartella non e' scrivibile (installazione in Program Files, chiavetta in sola
# lettura) si passa alla cartella dati dell'utente invece di fallire all'avvio.
# Un percorso esplicito in SPRITESHEEP_DATI ha la precedenza su tutto.
_forzata = _os.environ.get("SPRITESHEEP_DATI")
if _forzata:
    DATI = Path(_forzata)
elif _scrivibile(ROOT):
    DATI = ROOT
else:
    DATI = _dati_utente()

# I pesi NON stanno nel progetto: vivono qui e li scarica il wizard.
MODELS_DIR = DATI / "models"
OUTPUT_DIR = DATI / "output"
CACHE_DIR = DATI / "cache"
XET_CACHE_DIR = CACHE_DIR / "xet"

for _d in (MODELS_DIR, OUTPUT_DIR, CACHE_DIR, XET_CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Tutto HuggingFace sta accanto ai modelli, sullo stesso disco.
#
# Passare `cache_dir=` a hf_hub_download sposta solo il file finale: la cache a
# blocchi di Xet segue HF_XET_CACHE e finiva in C:\Users\...\.cache\huggingface,
# su un disco di sistema che qui e' pieno al 100%. Le variabili vanno impostate
# prima che huggingface_hub venga importato: i suoi percorsi si fissano una
# volta sola, al momento dell'import.
# ---------------------------------------------------------------------------
_os.environ.setdefault("HF_HOME", str(CACHE_DIR))
_os.environ.setdefault("HF_HUB_CACHE", str(CACHE_DIR))
_os.environ.setdefault("HF_XET_CACHE", str(XET_CACHE_DIR))

# Porta di default. Godot puo' sovrascriverla passando --port.
DEFAULT_PORT = 8765
HOST = "127.0.0.1"

APP_NAME = "Sprite Sheep"
VERSION = "0.0.2-pre-alpha"

# ---------------------------------------------------------------------------
# MODALITA' DI PROVA — spenta.
#
# Con il bypass acceso il controllo di accettazione delle licenze e' aggirato:
# i pesi si scaricano senza che l'utente abbia letto e accettato i termini.
# In una build distribuita e' inaccettabile: la licenza di MiniMax H3 ha
# esclusioni territoriali che riguardano anche gli output, e il programma esiste
# anche per farle vedere prima del download.
#
# Per riaccenderlo durante lo sviluppo, senza toccare il codice:
#     set SPRITESHEEP_BYPASS_LICENZE=1     (Windows)
#     export SPRITESHEEP_BYPASS_LICENZE=1  (Linux/macOS)
#
# Lo stato e' esposto da GET /health, cosi' non resta acceso per distrazione.
# ---------------------------------------------------------------------------
BYPASS_LICENZE = _os.environ.get("SPRITESHEEP_BYPASS_LICENZE") == "1"
