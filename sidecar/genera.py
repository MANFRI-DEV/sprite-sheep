"""Esecuzione di un lavoro: sprite + una o piu' azioni -> sheet + GIF ciascuna.

La catena e' divisa in due tronconi, con confini netti:

  1. INFERENZA  (backend/*.py)  sprite + prompt -> lista di frame
  2. POST       (sheet.py)      frame -> selezione, griglia, GIF

Un lavoro puo' contenere piu' azioni dello stesso personaggio (idle, walk,
attacco...): stesso modello, sprite, formato e scontorno; prompt, durata,
frame e seme propri. L'inferenza le fa in un colpo solo (`genera_lotto`),
cosi' i pesi si caricano una volta; il post le tratta una per una, e ogni
azione ha la sua cartella, il suo log e il suo `meta.json`.

Chi mette in fila i lavori e ne tiene lo stato e' `coda.py`: qui non ci sono
thread ne' registri, solo il lavoro.
"""
import json
import random
import shutil
import time
import traceback
from pathlib import Path

import config
from testi import t
import edizione
import filigrana
import inquadra
import modelli
import parametri
import rapporto
import scontorno
import sheet
from backend import ottieni_backend

## Campi comuni a tutte le azioni di un lavoro, con il loro valore se mancano.
COMUNI = {
    "modello": None,
    "sprite": None,
    "formato": parametri.FORMATO_PREDEFINITO,
    "margine": inquadra.MARGINE_PREDEFINITO,
    "scontorna": True,
    "colore_sfondo": "auto",
    "lato_cella": 256,
}

## Stima del tempo che resta per il post di un'azione: scontorno, sheet, GIF.
## Misurato su 25 frame a 448: pochi secondi, qui arrotondati per eccesso.
POST_S = 8


def normalizza(richiesta: dict) -> dict:
    """Da una richiesta singola o a lotto alla forma unica
    `{comuni..., "azioni": [{nome, prompt, durata_s, n_frame, seed}]}`.

    Solleva ValueError con un messaggio per l'utente se manca qualcosa.
    """
    fuori = {k: richiesta.get(k, v) for k, v in COMUNI.items()}
    for chiave in ("modello", "sprite"):
        if not fuori[chiave]:
            raise ValueError(t("gen.campo_mancante", campo=chiave))
    if "azioni" in richiesta:
        grezze = list(richiesta.get("azioni") or [])
    else:
        grezze = [richiesta]
    if not grezze:
        raise ValueError(t("gen.azioni_vuote"))
    azioni = []
    for a in grezze:
        if not (a.get("prompt") or "").strip():
            raise ValueError(t("gen.campo_mancante", campo="prompt"))
        azioni.append({
            "nome": (a.get("nome") or "animazione").strip() or "animazione",
            "prompt": a["prompt"],
            "durata_s": float(a.get("durata_s", 2.0)),
            "n_frame": int(a.get("n_frame", 25)),
            "seed": int(a.get("seed", 0) or 0),
        })
    # Formato e margine si controllano subito: un errore qui deve arrivare al
    # clic su Genera, non dopo sei minuti di caricamento pesi.
    parametri.risoluzione(fuori["formato"])
    if fuori["margine"] not in inquadra.MARGINI:
        raise ValueError("margine sconosciuto: %r" % fuori["margine"])
    fuori["azioni"] = azioni
    return fuori


class Stima:
    """Quanto manca, dall'andamento della barra.

    Prima del primo passo di campionamento non si dice niente: il caricamento
    dei pesi va da pochi secondi (in cache) a sei minuti (da disco), e un
    numero inventato e' peggio di nessun numero. Dal primo passo in poi il
    ritmo e' regolare e basta una proporzione.
    """
    INIZIO = 0.15      # dove FASI mette l'inizio del campionamento

    def __init__(self, n_azioni: int) -> None:
        self.n = n_azioni
        self.t0 = None
        self.p0 = 0.0

    def secondi(self, p: float) -> int | None:
        adesso = time.time()
        if self.t0 is None:
            if p > self.INIZIO:
                self.t0, self.p0 = adesso, p
            return None
        if p - self.p0 < 0.02:
            return None
        ritmo = (adesso - self.t0) / (p - self.p0)
        return int(ritmo * (1.0 - p) + POST_S * self.n)


def esegui(job_id: str, lavoro: dict, fermo, aggiorna) -> None:
    """Esegue un lavoro gia' normalizzato. `aggiorna(**campi)` scrive lo
    stato che l'interfaccia legge; a fine lavoro `attivo` e' sempre False."""
    from backend.comfyui_bridge import Annullato
    inizio = time.time()
    adattato = config.CACHE_DIR / f"sprite_{job_id}.png"
    try:
        model_id = lavoro["modello"]
        st = modelli.stato(model_id)
        if not st["installato"]:
            mancanti = [f["path"] for f in st["file"] if not f["presente"]]
            raise RuntimeError(t(
                "mod.non_installato", id=model_id, n=len(mancanti),
                primo=Path(mancanti[0]).name))

        azioni = lavoro["azioni"]
        piani = [parametri.piano(model_id, a["durata_s"], a["n_frame"],
                                 lavoro["formato"]) for a in azioni]
        # Il seme si sceglie qui e non nel backend: 0 vuol dire "a caso", e se
        # il caso lo tirava il backend il valore usato si perdeva — il log
        # non poteva riportarlo e l'animazione non si poteva rifare uguale.
        semi = [a["seed"] or random.randint(1, 2**31 - 1) for a in azioni]
        larghezza, altezza = piani[0]["larghezza"], piani[0]["altezza"]
        aggiorna(fase="inferenza", percentuale=0.0, piano=piani[0],
                 azioni=len(azioni))

        sprite = inquadra.adatta(Path(lavoro["sprite"]), larghezza, altezza,
                                 lavoro["colore_sfondo"], lavoro["margine"],
                                 adattato)

        # Annullato mentre si adattava lo sprite: inutile svegliare ComfyUI.
        if fermo.is_set():
            raise Annullato(t("gen.annullato"))
        backend = ottieni_backend(model_id, config.MODELS_DIR / model_id)
        stima = Stima(len(azioni))

        # Il backend racconta due cose: a che punto e' e cosa sta facendo.
        # Dopo un Annulla il WebSocket continua a raccontare i passi finche'
        # ComfyUI non si ferma davvero: senza la condizione, la scritta "sto
        # fermando" verrebbe coperta da "genero i fotogrammi 5/8" e
        # sembrerebbe che il clic non sia servito.
        def avanzamento(p, dettaglio=""):
            if fermo.is_set():
                return
            campi = {"percentuale": round(p * 0.9, 3), "eta_s": stima.secondi(p)}
            if dettaglio:
                campi["dettaglio"] = dettaglio
            aggiorna(**campi)

        inizio_inferenza = time.time()
        tutti = backend.genera_lotto(
            str(sprite),
            [{"prompt": a["prompt"], "lunghezza": p["lunghezza"], "seed": s}
             for a, p, s in zip(azioni, piani, semi)],
            larghezza, altezza, avanzamento=avanzamento, fermo=fermo)
        fine_inferenza = time.time()

        comune = {
            "inizio": inizio, "inizio_inferenza": inizio_inferenza,
            "fine_inferenza": fine_inferenza, "modello_id": model_id,
            "modello_nome": modelli.CATALOGO.get(model_id, {}).get("nome", model_id),
            "backend": getattr(backend, "nome", type(backend).__name__),
            "passi": getattr(backend, "PASSI", None),
            "larghezza": larghezza, "altezza": altezza,
            "filigrana": bool(edizione.FILIGRANA),
            "n_azioni": len(azioni),
        }
        risultati = []
        usati = set()
        for i, (a, piano, seme, frames) in enumerate(zip(azioni, piani, semi, tutti)):
            base = 0.9 + 0.1 * i / len(azioni)
            aggiorna(fase="composizione", percentuale=round(base, 3), dettaglio=(
                t("gen.azione_di", i=i + 1, n=len(azioni)) + a["nome"]
                if len(azioni) > 1 else ""))
            risultati.append(_componi(a, piano, seme, frames, lavoro, comune,
                                      inizio, usati))

        # Per un'azione sola i campi stanno anche in cima, dove l'interfaccia
        # li ha sempre letti; per un lotto in cima c'e' l'ultima azione, che
        # e' quella che il pannello Risultato mostra.
        ultimo = risultati[-1]
        aggiorna(fase="fatto", percentuale=1.0, attivo=False, dettaglio="",
                 eta_s=0, risultati=risultati, sheet=ultimo["sheet"],
                 gif=ultimo["gif"], cartella=ultimo["cartella"],
                 log=ultimo["log"], seed=ultimo["seed"],
                 scontornato=lavoro["scontorna"], edizione=edizione.stato())

    except Annullato:
        # Non e' un errore: l'utente ha chiesto di fermare. Niente traccia da
        # copiare, niente rosso in interfaccia — solo lo stato.
        aggiorna(fase="annullato", attivo=False, dettaglio="", eta_s=None)
    except Exception as e:
        # La traccia viaggia intera fino all'interfaccia: e' quella che serve
        # incollare quando qualcosa si rompe, e ricostruirla a mano dai log del
        # sidecar significa non averla proprio.
        aggiorna(fase="errore", attivo=False, eta_s=None,
                 errore=f"{type(e).__name__}: {e}",
                 traccia=traceback.format_exc(),
                 richiesta={
                     **{k: lavoro.get(k) for k in ("modello", "sprite", "formato", "margine")},
                     "azioni": ", ".join("%s (%.1f s, %d frame)" % (
                         a["nome"], a["durata_s"], a["n_frame"])
                         for a in lavoro.get("azioni", []))})
        traceback.print_exc()
    finally:
        # Lo sprite adattato serve solo a ComfyUI, che l'ha gia' ricevuto via
        # HTTP; nel log finisce l'originale.
        adattato.unlink(missing_ok=True)


def _componi(azione: dict, piano: dict, seme: int, frames: list, lavoro: dict,
             comune: dict, inizio: float, usati: set) -> dict:
    """Dal video di un'azione a cartella con sheet, GIF, log e meta."""
    nome = azione["nome"]
    scelti = [frames[i] for i in piano["indici"] if i < len(frames)]

    # I modelli di diffusione video non producono un canale alfa: i frame
    # arrivano opachi, con lo sfondo chiesto dal prompt. Uno sprite sheet con
    # lo sfondo pieno non e' utilizzabile in un gioco, quindi la trasparenza
    # va ricavata qui, frame per frame, con lo stesso scontorno dello sprite.
    diagnosi = None
    if lavoro["scontorna"]:
        colore = lavoro["colore_sfondo"]
        if scelti:
            diagnosi = scontorno.diagnosi(scelti[0], colore=colore)
        scelti = [scontorno.scontorna_immagine(f, colore=colore) for f in scelti]

    # La filigrana va qui, sui frame gia' scelti e scontornati: cosi' finisce
    # sia nel foglio sia nella GIF, e non viene mangiata dallo scontorno.
    if edizione.FILIGRANA:
        scelti = filigrana.applica(scelti, edizione.FILIGRANA_TESTO)

    # Una cartella per azione, marcata con l'istante in cui il lavoro e'
    # partito. Senza, rigenerare con lo stesso nome sovrascriveva il lavoro
    # precedente. Due azioni con lo stesso nome nello stesso lotto prendono
    # un suffisso invece di sovrascriversi a vicenda.
    marca = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(inizio))
    cartella = f"{nome}_{marca}"
    k = 2
    while cartella in usati or (config.OUTPUT_DIR / cartella).exists():
        cartella = f"{nome}_{marca}_{k}"
        k += 1
    usati.add(cartella)
    dest = config.OUTPUT_DIR / cartella

    cella = parametri.cella(int(lavoro["lato_cella"]),
                            comune["larghezza"], comune["altezza"])
    r_sheet = sheet.componi_sheet(scelti, piano["colonne"], piano["righe"],
                                  cella, dest / f"{nome}_sheet.png")
    r_gif = sheet.componi_gif(scelti, piano["fps_riproduzione"], cella,
                              dest / f"{nome}.gif")

    log = _scrivi_rapporti(dest, nome, azione, lavoro, {
        **comune, "seed": seme, "piano": piano, "cella": cella,
        "scontorno": diagnosi, "margine": lavoro["margine"],
        "gif": Path(r_gif["percorso"]).name,
        "sheet": Path(r_sheet["percorso"]).name,
        "fps_gif": r_gif["fps_reale"],
    })
    return {"nome": nome, "sheet": r_sheet, "gif": r_gif,
            "cartella": str(dest), "log": log, "seed": seme}


def _scrivi_rapporti(dest: Path, nome: str, azione: dict, lavoro: dict,
                     dati: dict):
    """Copia lo sprite di partenza, scrive il log HTML e `meta.json`.

    La copia serve perche' il log punta a file relativi, e perche' la
    cronologia la usa per rigenerare: lo sprite originale puo' essere
    spostato o sovrascritto. `meta.json` e' la richiesta completa, cosi'
    "rigenera con un altro seme" rifa esattamente la stessa cosa.

    Un rapporto che non si scrive non deve far perdere l'animazione: sheet e
    GIF sono gia' su disco, quindi l'errore si stampa e si va avanti.
    """
    try:
        src = Path(lavoro["sprite"])
        copia = dest / f"{nome}_sprite_iniziale{src.suffix.lower() or '.png'}"
        shutil.copy2(src, copia)
        fine = time.time()
        log = rapporto.scrivi(dest, nome, {
            **dati, "fine": fine, "versione": config.VERSION,
            "prompt": azione["prompt"], "sprite": copia.name,
            "sprite_originale": str(src),
        })
        meta = {
            "versione": config.VERSION,
            "nome": nome,
            "inizio": dati["inizio"], "fine": fine,
            "modello": lavoro["modello"],
            "modello_nome": dati["modello_nome"],
            "formato": lavoro["formato"], "margine": lavoro["margine"],
            "scontorna": lavoro["scontorna"],
            "colore_sfondo": lavoro["colore_sfondo"],
            "lato_cella": lavoro["lato_cella"],
            "prompt": azione["prompt"],
            "durata_s": azione["durata_s"], "n_frame": azione["n_frame"],
            "seed": dati["seed"],
            "sprite": copia.name, "sprite_originale": str(src),
            "gif": dati["gif"], "sheet": dati["sheet"], "log": log.name,
        }
        (dest / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(log)
    except Exception:
        traceback.print_exc()
        return None
