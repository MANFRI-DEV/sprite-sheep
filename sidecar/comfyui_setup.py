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
## La guida dipende dal sistema: mandare un utente Linux alla pagina Windows
## e' un rimando che non aiuta nessuno, e su AMD le due installazioni non si
## somigliano nemmeno (ROCm contro DirectML).
URL_GUIDA = ("https://docs.comfy.org/installation/desktop/windows"
             if os.name == "nt"
             else "https://docs.comfy.org/installation/manual_install")

# Nomi di cartella tipici, cercati su ogni unita' e nelle cartelle utente:
# nessun percorso completo cablato, cosi' la ricerca funziona ovunque.
#
# Le ultime voci sono le convenzioni Linux: `~/ComfyUI` clonato a mano,
# `~/.local/share` e `/opt` per le installazioni di sistema. Costano niente da
# provare su Windows, dove semplicemente non esistono.
NOMI_TIPICI = [
    "ComfyUI",
    "ComfyUI_windows_portable/ComfyUI",
    "AI/ComfyUI",
    "AI_Video/ComfyUI",
    "Documents/ComfyUI",
    "Desktop/ComfyUI",
    "git/ComfyUI",
    "src/ComfyUI",
    ".local/share/ComfyUI",
    "opt/ComfyUI",
]

## La lista dei file attesi **non sta piu' qui**: si ricava dal catalogo in
## `modelli.py`, che e' l'unico posto in cui i nomi dei pesi sono scritti.
##
## Era il terzo elenco parallelo degli stessi file, ed era divergiato senza che
## nulla desse errore: conteneva tre dei quattro file di MiniMax H3 e nessuno
## di WAN. Un utente con WAN scaricato si vedeva dire che ne mancavano tre.


def _leggi() -> dict:
    if IMPOSTAZIONI.exists():
        try:
            return json.loads(IMPOSTAZIONI.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


## Che genere di installazione e' una cartella.
##
## Esistono due ComfyUI, e per un po' ne abbiamo riconosciuta una sola:
##
## - **sorgente**: la versione portable o clonata da git. Ha `main.py` in cima,
##   e la si puo' anche avviare.
## - **dati**: quella installata da **ComfyUI Desktop**. La cartella che
##   l'utente sceglie contiene `models/`, `input/`, `output/`, `user/` e un
##   marcatore `.comfyui-desktop-*`, ma **non** `main.py`: il codice sta dentro
##   l'applicazione Electron, altrove.
##
## Pretendere `main.py` rifiutava le installazioni Desktop con un messaggio che
## chiedeva un file inesistente — "there is no such thing?", parole di un utente
## alla prima release. Eppure di quel percorso ci serve `models/`, che c'e'
## eccome: e' li' che si pubblicano i pesi perche' ComfyUI li veda.
SORGENTE = "sorgente"
DATI = "dati"

## Cartelle che ComfyUI crea nella propria directory dati. `models/` e'
## indispensabile; delle altre ne basta una, perche' una cartella `models/`
## qualsiasi non fa di per se' un'installazione.
COMPAGNE = ("input", "output", "user", "custom_nodes")


def genere(p: Path) -> str | None:
    """`SORGENTE`, `DATI`, oppure None se non e' un'installazione ComfyUI."""
    try:
        if (p / "main.py").is_file():
            return SORGENTE
        if (p / "models").is_dir() and any((p / c).is_dir() for c in COMPAGNE):
            return DATI
    except OSError:
        pass                      # unita' rimovibile non pronta
    return None


def imposta_percorso(percorso: str) -> dict:
    p = Path(percorso)
    if genere(p) is None:
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
    if salvato and genere(Path(salvato)) is not None:
        return salvato
    for radice in _radici():
        for nome in NOMI_TIPICI:
            c = radice / nome
            if genere(c) is not None:
                return str(c)
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


def _attesi(model_id: str | None) -> list[tuple[str, str]]:
    """(cartella, nome file) che ComfyUI deve vedere per il modello scelto.

    Si ricavano dal catalogo invece di stare in una lista qui.
    `MODELLI_ATTESI` era una copia scritta a mano dei file di MiniMax H3 — tre
    dei suoi quattro, per giunta — e ignorava del tutto WAN: chi aveva scaricato
    WAN si vedeva dire che ne mancavano tre, perche' si cercavano i file di un
    modello che non aveva scelto.
    """
    import modelli
    scheda = modelli.CATALOGO.get(model_id or "")
    if not scheda:
        return []
    fuori = []
    for f in scheda["file"]:
        cartella = modelli.CARTELLE_COMFY.get(f["ruolo"])
        if cartella:
            fuori.append((cartella, Path(f["path"]).name))
    return fuori


def _scaricati() -> list[str]:
    """I modelli che l'utente ha davvero scaricato, per intero."""
    import modelli
    fuori = []
    for mid in modelli.CATALOGO:
        try:
            if modelli.stato(mid).get("installato"):
                fuori.append(mid)
        except Exception:
            continue
    return fuori


def _ripubblica(percorso: str | None) -> list[str]:
    """Ricollega nella cartella di ComfyUI i pesi gia' scaricati.

    Il collegamento avveniva in due soli momenti: alla fine di un download e
    quando si indicava una cartella con "Seleziona cartella...". Chi scaricava
    i pesi **prima** di configurare ComfyUI non passava per nessuno dei due:
    al momento del download `trova_installazione()` dava None e la pubblicazione
    usciva subito senza fare nulla.

    Poi l'utente indicava la cartella e premeva Ricontrolla — che si limitava a
    guardare — e restava per sempre davanti a "n file non ancora visibili a
    ComfyUI", mentre l'istruzione sotto prometteva l'esatto contrario:
    "premi Ricontrolla: vengono collegati alla cartella di ComfyUI".

    Ora il controllo prova prima a collegare. E' anche la causa dell'HTTP 400
    in generazione: senza il file nella cartella di ComfyUI il suo nome non e'
    fra i valori ammessi dal nodo, e il grafo viene rifiutato in validazione.
    """
    if not percorso:
        return []
    import modelli
    errori = []
    for mid in _scaricati():
        try:
            errori += modelli.pubblica_in_comfyui(mid).get("errori", [])
        except Exception as e:
            errori.append("%s: %s" % (mid, e))
    return errori


def _modelli_mancanti(percorso: str | None) -> list[str] | None:
    """I file che ComfyUI non vede. `None` = non si puo' ancora sapere.

    Due difetti stavano insieme qui, e producevano lo stesso sintomo: il
    pannello Modelli dava tutto scaricato e questo passo diceva "3 files
    missing". L'utente aveva ragione, e la risposta e' che erano due domande
    diverse — "li ho?" e "ComfyUI li vede?".

    1. **Senza il percorso di ComfyUI si dichiaravano mancanti tutti i file.**
       Ma senza percorso non si puo' guardare da nessuna parte: la risposta
       giusta e' "non lo so ancora", non "mancano".
    2. **La lista dei file attesi era scritta a mano**, e conteneva tre dei
       quattro file di MiniMax H3 e nessuno di WAN. Chi usava WAN si sentiva
       dire che ne mancavano tre, perche' si cercava un modello che non aveva
       scelto.

    Si guardano ora i modelli **che l'utente ha scaricato**: e' quella la
    domanda che questo passo deve rispondere.
    """
    if not percorso:
        return None
    base = Path(percorso) / "models"
    mancanti = []
    for mid in _scaricati():
        for cartella, nome in _attesi(mid):
            if not (base / cartella / nome).is_file():
                mancanti.append(nome)
    return mancanti


def stato() -> dict:
    """Elenco dei passi, ognuno con esito e istruzione."""
    percorso = trova_installazione()
    acceso = _in_ascolto()
    classi = _classi_mancanti() if acceso else None
    # Prima si collega, poi si guarda: e' quello che l'istruzione promette.
    errori_link = _ripubblica(percorso)
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
            # Su un'installazione Desktop il pulsante non puo' funzionare: il
            # codice di ComfyUI non sta nella cartella scelta. Dirgli di
            # premerlo lo manderebbe contro un errore.
            "istruzione": None if acceso else (
                t("comfy.avviata.prima") if not percorso else
                (t("comfy.err.desktop_avvia") if genere(Path(percorso)) == DATI
                 else t("comfy.avviata.premi"))),
            "avviabile": bool(percorso) and genere(Path(percorso)) == SORGENTE,
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
        # Tre stati, non due. `None` vuol dire "non lo so ancora", ed e' un
        # caso diverso da "mancano": senza il percorso di ComfyUI non si puo'
        # guardare nelle sue cartelle, e dichiararli mancanti sarebbe
        # un'affermazione che non abbiamo modo di verificare.
        {
            "id": "modelli",
            "titolo": t("comfy.modelli.titolo"),
            "esito": ("attesa" if mancanti_modelli is None
                      else ("ok" if not mancanti_modelli else "azione")),
            "dettaglio": (t("comfy.modelli.non_verificabile")
                          if mancanti_modelli is None
                          else (t("comfy.modelli.presenti") if not mancanti_modelli
                                else t("comfy.modelli.mancano",
                                       n=len(mancanti_modelli)))),
            # Se il collegamento e' stato tentato ed e' fallito, il motivo va
            # detto qui: e' l'unico posto in cui l'utente lo puo' leggere, e
            # senza di esso "non ancora visibili" sembra un controllo rotto.
            "istruzione": (t("comfy.modelli.prima_comfy")
                           if mancanti_modelli is None
                           else (None if not mancanti_modelli
                                 else (t("comfy.modelli.link_fallito",
                                         dettaglio=errori_link[0])
                                       if errori_link
                                       else t("comfy.modelli.istruzione")))),
            "link": None,
        },
    ]
    return {
        "percorso": percorso,
        # Che genere di installazione e', e se il pulsante "Avvia" ha senso.
        # Su ComfyUI Desktop non ce l'ha: il codice non sta nella cartella
        # scelta, e l'interfaccia deve spegnere il pulsante invece di offrire
        # un'azione che fallirebbe.
        "genere": genere(Path(percorso)) if percorso else None,
        "avviabile": bool(percorso) and genere(Path(percorso)) == SORGENTE,
        "in_esecuzione": acceso,
        "pronto": all(p["esito"] == "ok" for p in passi),
        "passi": passi,
        "nota_licenza": t("comfy.nota_licenza"),
    }


## Dove sta l'interprete di una ComfyUI, su Windows come su Linux.
_INTERPRETI = [
    ("venv", "Scripts", "python.exe"),      # venv Windows
    ("venv", "bin", "python"),              # venv Linux/macOS
    ("venv", "bin", "python3"),             # distribuzioni senza alias python
    (".venv", "Scripts", "python.exe"),
    (".venv", "bin", "python"),
    (".venv", "bin", "python3"),
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
    # Un'installazione Desktop si avvia dalla sua applicazione, non da qui: il
    # codice non sta in questa cartella. Si dice, invece di provare a lanciare
    # un `main.py` che non c'e' e riportare un errore di file mancante.
    if genere(base) == DATI:
        return {"ok": False, "errore": t("comfy.err.desktop_avvia")}

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
