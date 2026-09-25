"""Catalogo dei modelli, licenze e download da HuggingFace.

Sprite Sheep **non distribuisce pesi**: li scarica l'utente. Di conseguenza
l'obbligo di licenza resta suo, ma il programma deve metterlo in condizione
di sapere cosa accetta: il download e' bloccato finche' la licenza non
risulta accettata, e l'accettazione viene registrata su disco.

Nomi di file e repo sono stati verificati contro l'API di HuggingFace,
non ricostruiti a memoria.
"""
import json
import os
import shutil
import threading
import time
from pathlib import Path

import config
from testi import t

ACCETTAZIONI = config.MODELS_DIR / ".licenze_accettate.json"

CATALOGO: dict[str, dict] = {
    "wan22_ti2v_5b": {
        "nome": "WAN 2.2 TI2V 5B",
        "descrizione_key": "mod.wan.descrizione",
        # Scaricabile e selezionabile, ma la generazione non chiude in modo
        # affidabile su 8 GB: l'interfaccia lo marca invece di consigliarlo.
        "stato_sviluppo": "in_lavorazione",
        "licenza": {
            "id": "apache-2.0",
            "nome": "Apache 2.0",
            "url": "https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B/raw/main/LICENSE.txt",
            "riassunto_key": "lic.apache.riassunto",
            "avvertenze_key": [],
        },
        "file": [
            {"repo": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
             "path": "split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors",
             "gb": 9.3, "ruolo": "diffusion"},
            {"repo": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
             "path": "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
             "gb": 6.3, "ruolo": "text_encoder"},
            {"repo": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
             "path": "split_files/vae/wan2.2_vae.safetensors",
             "gb": 1.3, "ruolo": "vae"},
        ],
    },
    "minimax_h3_fl2va": {
        "nome": "MiniMax H3 (image-to-video)",
        "descrizione_key": "mod.h3.descrizione",
        "licenza": {
            "id": "minimax-h3-community",
            "nome": "MiniMax H3 Community License",
            "url": "https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/LICENSE",
            "riassunto_key": "lic.h3.riassunto",
            "avvertenze_key": [
                "lic.h3.territorio",
                "lic.h3.ricavi",
                "lic.h3.no_training",
                "lic.non_parere_legale",
            ],
        },
        "file": [
            {"repo": "Comfy-Org/MiniMax-H3",
             "path": "diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors",
             "gb": 19.5, "ruolo": "diffusion"},
            {"repo": "Abiray/MiniMax-H3-GGUF",
             "path": "text_encoders/qwen3vl_32b_minimax_h3_int4_convrot.safetensors",
             "gb": 13.9, "ruolo": "text_encoder",
             "nota": "quantizzazione adatta ad Ampere (RTX 30xx)"},
            {"repo": "Comfy-Org/MiniMax-H3",
             "path": "vae/minimax_h3_video_vae_fp16.safetensors",
             "gb": 4.9, "ruolo": "vae"},
            {"repo": "Comfy-Org/MiniMax-H3",
             "path": "vae/minimax_h3_audio_vae_fp32.safetensors",
             "gb": 0.6, "ruolo": "vae_audio"},
        ],
    },
    # -----------------------------------------------------------------------
    # FastH3: lo stesso H3 distillato per girare in **otto passi** invece di
    # venti. Non e' un modello diverso, e' lo stesso addestrato a saltare la
    # maggior parte del percorso di denoising (DMD2 senza dati, piu' attenzione
    # sparsa VSA all'80%).
    #
    # Il text encoder e i due VAE sono **gli stessi** della voce qui sopra: chi
    # ha gia' H3 scarica solo i 22 GB del checkpoint. E' il motivo per cui la
    # voce e' separata invece di essere un'opzione dentro l'altra — l'utente
    # vede quanto gli manca davvero.
    #
    # La licenza e' la stessa di H3, comprese le esclusioni territoriali: il
    # peso e' derivato da quei pesi e se le porta dietro.
    "minimax_h3_fast": {
        "nome": "MiniMax H3 Fast (8 passi)",
        "descrizione_key": "mod.h3fast.descrizione",
        "licenza": {
            "id": "minimax-h3-community",
            "nome": "MiniMax H3 Community License",
            "url": "https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/LICENSE",
            "riassunto_key": "lic.h3.riassunto",
            "avvertenze_key": [
                "lic.h3.territorio",
                "lic.h3.ricavi",
                "lic.h3.no_training",
                "lic.non_parere_legale",
            ],
        },
        "file": [
            {"repo": "FastVideo/FastVideo-FastH3-Comfy",
             "path": "diffusion_models/fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors",
             "gb": 22.1, "ruolo": "diffusion",
             "nota": "int8 convrot: quantizzazione adatta ad Ampere (RTX 30xx)"},
            {"repo": "Abiray/MiniMax-H3-GGUF",
             "path": "text_encoders/qwen3vl_32b_minimax_h3_int4_convrot.safetensors",
             "gb": 13.9, "ruolo": "text_encoder",
             "nota": "in comune con MiniMax H3"},
            {"repo": "Comfy-Org/MiniMax-H3",
             "path": "vae/minimax_h3_video_vae_fp16.safetensors",
             "gb": 4.9, "ruolo": "vae", "nota": "in comune con MiniMax H3"},
            {"repo": "Comfy-Org/MiniMax-H3",
             "path": "vae/minimax_h3_audio_vae_fp32.safetensors",
             "gb": 0.6, "ruolo": "vae_audio", "nota": "in comune con MiniMax H3"},
        ],
    },
}

# Stato dei download in corso, letto da GET /modelli
_progressi: dict[str, dict] = {}
_lock = threading.Lock()


def _accettate() -> dict:
    if ACCETTAZIONI.exists():
        try:
            return json.loads(ACCETTAZIONI.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def accetta_licenza(model_id: str) -> dict:
    if model_id not in CATALOGO:
        raise KeyError(model_id)
    dati = _accettate()
    dati[model_id] = {
        "licenza": CATALOGO[model_id]["licenza"]["id"],
        "url": CATALOGO[model_id]["licenza"]["url"],
        "quando": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    ACCETTAZIONI.parent.mkdir(parents=True, exist_ok=True)
    ACCETTAZIONI.write_text(json.dumps(dati, indent=2, ensure_ascii=False), encoding="utf-8")
    return dati[model_id]


def licenza_accettata(model_id: str) -> bool:
    # MODALITA' DI PROVA: vedi config.BYPASS_LICENZE
    if getattr(config, "BYPASS_LICENZE", False):
        return True
    return model_id in _accettate()


def _percorso_locale(model_id: str, f: dict) -> Path:
    return config.MODELS_DIR / model_id / Path(f["path"]).name


def riusa_da_altri_modelli(model_id: str) -> list[str]:
    """Collega i pesi che un altro modello gia' installato ha in comune.

    FastH3 divide con MiniMax H3 il text encoder e i due VAE: venti giga su
    ventidue erano gia' sul disco, ma in un'altra cartella, e senza questo
    passaggio il programma li avrebbe chiesti di nuovo. Chi installa la
    variante veloce avrebbe scaricato quaranta giga invece di ventidue, per
    ritrovarsi due copie identiche dello stesso file.

    Si collega con hardlink: stesso volume, zero spazio in piu'. Su volumi
    diversi `_porta_nel_progetto` ricade sulla copia, che e' il caso raro.
    """
    if model_id not in CATALOGO:
        return []
    fatti = []
    for f in CATALOGO[model_id]["file"]:
        dst = _percorso_locale(model_id, f)
        if dst.exists():
            continue
        nome = dst.name
        for altra in sorted(config.MODELS_DIR.glob("*/" + nome)):
            if altra.parent.name == model_id or not altra.is_file():
                continue
            try:
                _porta_nel_progetto(altra, dst)
                fatti.append(nome)
            except OSError:
                pass                  # si ricadra' sul download normale
            break
    return fatti


def cerca_in_cartella(model_id: str, cartella: str) -> dict:
    """Collega i pesi gia' presenti sul disco dell'utente, senza scaricarli.

    Chi ha gia' i modelli (tipicamente dentro una ComfyUI) non deve riscaricare
    decine di GB. Si cerca per nome di file, ricorsivamente, e si collega con
    hardlink: sullo stesso volume non costa spazio, e su volumi diversi si
    ricade sulla copia a blocchi.

    Non si sposta e non si cancella niente dalla cartella indicata: i file
    dell'utente restano dove sono.
    """
    if model_id not in CATALOGO:
        return {"ok": False, "errore": t("mod.err.sconosciuto")}
    radice = Path(cartella)
    if not radice.is_dir():
        return {"ok": False, "errore": t("mod.err.cartella", cartella=cartella)}

    attesi = {Path(f["path"]).name: f for f in CATALOGO[model_id]["file"]}
    trovati: dict[str, Path] = {}
    for p in radice.rglob("*.safetensors"):
        if p.name in attesi and p.name not in trovati:
            trovati[p.name] = p

    collegati, errori = [], []
    for nome, sorgente in trovati.items():
        destinazione = _percorso_locale(model_id, attesi[nome])
        if destinazione.exists() and destinazione.stat().st_size == sorgente.stat().st_size:
            collegati.append(nome)
            continue
        try:
            _porta_nel_progetto(sorgente, destinazione)
            collegati.append(nome)
        except OSError as e:
            errori.append("%s: %s" % (nome, e))

    if collegati:
        pubblica_in_comfyui(model_id)

    mancanti = [n for n in attesi if n not in trovati]
    return {
        "ok": not errori and not mancanti,
        "collegati": collegati,
        "mancanti": mancanti,
        "errori": errori,
        "errore": None if not mancanti else t(
            "mod.err.mancanti", n=len(mancanti), tot=len(attesi),
            elenco=", ".join(mancanti)),
        "stato": stato(model_id),
    }


def stato(model_id: str) -> dict:
    m = CATALOGO[model_id]
    file_stato = []
    presenti = 0
    with _lock:
        prog_ora = dict(_progressi.get(model_id, {}))
    esiti = prog_ora.get("esiti") or {}
    in_corso = prog_ora.get("file_corrente") if prog_ora.get("attivo") else None

    for f in m["file"]:
        p = _percorso_locale(model_id, f)
        nome = Path(f["path"]).name
        ok = p.exists() and p.stat().st_size > 1024 * 1024
        presenti += int(ok)

        # Uno stato per file: e' quello che permette all'utente di vedere
        # *quale* pezzo manca invece di un solo "installato: no" sul modello.
        if ok:
            stato_f = "presente"
        elif nome == in_corso:
            stato_f = "in_corso"
        elif esiti.get(nome):
            stato_f = "errore"
        else:
            stato_f = "mancante"

        file_stato.append({
            "path": f["path"], "nome": nome, "ruolo": f["ruolo"],
            "gb": f["gb"], "repo": f["repo"], "nota": f.get("nota", ""),
            "presente": ok, "locale": str(p),
            "stato": stato_f, "errore": esiti.get(nome),
            "byte": p.stat().st_size if ok else 0,
        })
    with _lock:
        prog = dict(_progressi.get(model_id, {}))
    gb_totali = round(sum(f["gb"] for f in m["file"]), 1)
    return {
        "id": model_id,
        "nome": m["nome"],
        "descrizione": t(m["descrizione_key"]),
        "stato_sviluppo": m.get("stato_sviluppo", ""),
        "licenza": _licenza_tradotta(m["licenza"]),
        "licenza_accettata": licenza_accettata(model_id),
        "gb_totali": gb_totali,
        "file": file_stato,
        "installato": presenti == len(m["file"]),
        "parziale": 0 < presenti < len(m["file"]),
        "download": _con_percentuale(prog, m, gb_totali),
    }


def _licenza_tradotta(lic: dict) -> dict:
    """La licenza esce nella lingua scelta: e' il testo su cui l'utente clicca
    "accetto", e in una lingua che non legge non e' un'accettazione."""
    fuori = {k: v for k, v in lic.items()
             if k not in ("riassunto_key", "avvertenze_key")}
    fuori["riassunto"] = t(lic["riassunto_key"])
    fuori["avvertenze"] = [t(k) for k in lic.get("avvertenze_key", [])]
    return fuori


def _con_percentuale(prog: dict, m: dict, gb_totali: float) -> dict:
    """Aggiunge al progresso la percentuale sull'intero scaricamento.

    Il thread sa solo a che punto sta il file corrente. Chi guarda vuole sapere
    quanto manca in tutto: con quattro file da 19,5 a 0,6 GB, "2 di 4" non dice
    niente: il secondo file puo' valere meta' dell'attesa o un ventesimo.
    """
    if not prog:
        return prog
    fuori = dict(prog)
    indice = int(prog.get("indice", 0))
    if indice <= 0 or gb_totali <= 0:
        fuori["percentuale"] = 0.0
        return fuori

    # I file gia' chiusi contano per intero, quello in corso per la frazione
    # osservata sul suo .incomplete.
    fatti = sum(f["gb"] for f in m["file"][:indice - 1])
    corrente = m["file"][indice - 1]["gb"] if indice <= len(m["file"]) else 0.0
    fatti += corrente * float(prog.get("frazione_file", 0.0))

    fuori["gb_totali"] = gb_totali
    fuori["gb_scaricati"] = round(fatti, 2)
    fuori["percentuale"] = round(min(100.0, 100.0 * fatti / gb_totali), 1)
    if not prog.get("attivo") and not prog.get("errore"):
        fuori["percentuale"] = 100.0
    return fuori


def elenco() -> list[dict]:
    return [stato(k) for k in CATALOGO]


## Dove ComfyUI cerca ciascun ruolo, dentro la propria cartella `models/`.
## I nomi dei ruoli sono quelli del catalogo.
CARTELLE_COMFY = {
    "diffusion": "diffusion_models",
    "text_encoder": "text_encoders",
    "vae": "vae",
    "vae_audio": "vae",
}


def pubblica_in_comfyui(model_id: str) -> dict:
    """Rende i pesi visibili a ComfyUI, che li carica **per nome** dalle
    proprie cartelle.

    Senza questo passo un utente che scarica dall'applicazione si ritrova i
    file in `SpriteSheep/models/`, `installato: True` nell'interfaccia, e una
    generazione che fallisce perche' ComfyUI in `models/diffusion_models/` non
    trova nulla. Funzionava solo a chi aveva gia' i pesi dentro ComfyUI e li
    aveva collegati con "Seleziona cartella...", cioe' il verso opposto.

    Si usano hardlink: sullo stesso volume non costano un byte, e i 38,9 GB di
    H3 restano contati una volta sola. Su volumi diversi si ricade sulla copia.

    **Gli errori si restituiscono, non si ingoiano.** Prima un collegamento
    fallito spariva in un `except OSError: pass`, e l'utente restava davanti a
    "n file non ancora visibili a ComfyUI" per sempre, senza sapere che il
    tentativo c'era stato ne' perche' fosse andato male.
    """
    import comfyui_setup
    base = comfyui_setup.trova_installazione()
    if not base:
        return {"fatti": [], "errori": []}   # ComfyUI non ancora configurata

    fatti, errori = [], []
    for f in CATALOGO[model_id]["file"]:
        sorgente = _percorso_locale(model_id, f)
        if not sorgente.exists():
            continue
        cartella = CARTELLE_COMFY.get(f["ruolo"])
        if not cartella:
            continue
        dst = Path(base) / "models" / cartella / sorgente.name
        if dst.exists() and dst.stat().st_size == sorgente.stat().st_size:
            continue
        try:
            _porta_nel_progetto(sorgente, dst)
            fatti.append(sorgente.name)
        except OSError as e:
            # Non deve far fallire il download: si annota e si prosegue.
            errori.append("%s: %s" % (sorgente.name, e))
    return {"fatti": fatti, "errori": errori}


def _porta_nel_progetto(scaricato: Path, locale: Path) -> None:
    """Porta il file dalla cache di HuggingFace al layout piatto del progetto.

    Prima si tenta un hardlink: stesso volume, costo zero, nessun byte copiato.
    Se fallisce (volumi diversi, filesystem senza hardlink) si copia a blocchi.

    Mai `write_bytes(read_bytes())`: su un file da 9,3 GB significa chiederne
    altrettanti di RAM in un colpo solo, e la macchina ne ha 5 liberi.
    """
    locale.parent.mkdir(parents=True, exist_ok=True)
    if locale.exists():
        locale.unlink()
    try:
        os.link(scaricato, locale)
        return
    except OSError:
        pass
    shutil.copyfile(scaricato, locale)


def _osservatore(model_id: str, f: dict) -> threading.Event:
    """Sorveglia i file .incomplete della cache e riporta i GB scaricati.

    `hf_hub_download` non offre callback di avanzamento utilizzabile da qui, e
    senza questo l'interfaccia mostra "1/3" fermo per tredici minuti: l'utente
    non ha modo di distinguere un download lento da uno bloccato.
    """
    fine = threading.Event()

    def guarda() -> None:
        attesi = float(f["gb"]) * 1e9
        while not fine.wait(1.5):
            fatti = sum(p.stat().st_size
                        for p in config.CACHE_DIR.rglob("*.incomplete")
                        if p.exists())
            with _lock:
                p = _progressi.get(model_id)
                if not p or not p.get("attivo"):
                    return
                p["gb_fatti"] = round(fatti / 1e9, 2)
                p["frazione_file"] = round(min(1.0, fatti / attesi), 3) if attesi else 0.0

    threading.Thread(target=guarda, daemon=True).start()
    return fine


def _scarica_thread(model_id: str) -> None:
    """Qualunque cosa vada storta finisce in _progressi[...]["errore"].

    Un'eccezione che sfugge qui non la vede nessuno: il thread muore, il dict
    resta {"attivo": True}, e l'interfaccia mostra un download in corso che non
    scarica niente. E' successo davvero, con huggingface_hub non installato.
    """
    totale = len(CATALOGO[model_id]["file"])
    try:
        _scarica(model_id)
    except Exception as e:
        with _lock:
            p = _progressi.get(model_id, {})
            _progressi[model_id] = {
                "attivo": False, "errore": _spiega(e),
                "file_corrente": p.get("file_corrente"),
                "indice": p.get("indice", 0), "totale": totale,
            }


def _spiega(e: Exception) -> str:
    """Messaggio che dice anche cosa fare, non solo cosa e' rotto."""
    if isinstance(e, ModuleNotFoundError):
        return (f"manca il modulo Python '{e.name}'. "
                f"Installalo con:  pip install -r requirements.txt")
    return f"{type(e).__name__}: {e}"


def _scarica(model_id: str) -> None:
    from huggingface_hub import hf_hub_download
    m = CATALOGO[model_id]
    dest = config.MODELS_DIR / model_id
    dest.mkdir(parents=True, exist_ok=True)
    totale = len(m["file"])

    # Esito per file, cosi' l'interfaccia puo' dire quale manca e perche'.
    esiti: dict[str, str | None] = {}

    for i, f in enumerate(m["file"]):
        nome = Path(f["path"]).name
        locale = _percorso_locale(model_id, f)
        with _lock:
            _progressi[model_id] = {
                "attivo": True, "file_corrente": nome,
                "indice": i + 1, "totale": totale, "errore": None,
                "gb_file": f["gb"], "gb_fatti": 0.0, "frazione_file": 0.0,
                "esiti": dict(esiti),
            }
        if locale.exists() and locale.stat().st_size > 1024 * 1024:
            esiti[nome] = None
            continue
        try:
            osserva = _osservatore(model_id, f)
            scaricato = hf_hub_download(
                repo_id=f["repo"], filename=f["path"],
                cache_dir=str(config.CACHE_DIR))
            osserva.set()
            _porta_nel_progetto(Path(scaricato), locale)
            esiti[nome] = None
        except Exception as e:
            # Si prosegue con gli altri file. Prima qui c'era un `return`: un
            # solo file fallito — un repo momentaneamente irraggiungibile, una
            # connessione caduta a meta' — lasciava il modello con un pezzo
            # solo e nessun tentativo sui restanti. E' il difetto per cui i
            # tester vedevano scaricare uno solo dei quattro file di H3.
            esiti[nome] = _spiega(e)

    # Anche parziale: quello che c'e' va comunque reso visibile a ComfyUI,
    # cosi' un download ripreso non lascia meta' pesi invisibili.
    pubblica_in_comfyui(model_id)

    falliti = [n for n, err in esiti.items() if err]
    with _lock:
        _progressi[model_id] = {
            "attivo": False,
            "errore": (t("mod.err.parziale", n=len(falliti), tot=totale)
                       if falliti else None),
            "indice": totale, "totale": totale,
            "esiti": esiti,
        }


def avvia_download(model_id: str) -> dict:
    """Rifiuta se la licenza non e' stata accettata. Il controllo sta qui,
    non solo nell'interfaccia: e' il punto che conta davvero."""
    if model_id not in CATALOGO:
        return {"ok": False, "errore": t("mod.err.sconosciuto")}
    if not licenza_accettata(model_id):
        return {"ok": False, "errore": "licenza non accettata: download rifiutato"}
    # Prima di scaricare si guarda cosa c'e' gia': fra due varianti dello
    # stesso modello i pesi in comune sono la maggior parte.
    riusa_da_altri_modelli(model_id)
    with _lock:
        if _progressi.get(model_id, {}).get("attivo"):
            return {"ok": False, "errore": "download gia' in corso"}
        _progressi[model_id] = {"attivo": True, "indice": 0,
                                "totale": len(CATALOGO[model_id]["file"]), "errore": None}
    threading.Thread(target=_scarica_thread, args=(model_id,), daemon=True).start()
    return {"ok": True, "avviato": model_id}
