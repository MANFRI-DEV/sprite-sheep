"""Orchestrazione della generazione: sprite + prompt -> sheet + GIF.

La catena e' divisa in due tronconi, con confini netti:

  1. INFERENZA  (backend/*.py)  sprite + prompt -> lista di frame
  2. POST       (sheet.py)      frame -> selezione, griglia, GIF

Il troncone 2 e' completo e collaudato. Il troncone 1 dipende dai pesi:
finche' il modello non e' scaricato, `esegui` fallisce con un messaggio che
dice cosa manca invece di rompersi a meta'.
"""
import threading
import time
import traceback
from pathlib import Path

import config
from testi import t
import edizione
import filigrana
import modelli
import parametri
import scontorno
import sheet
from backend import ottieni_backend

_lavori: dict[str, dict] = {}
_lock = threading.Lock()


def _aggiorna(job_id: str, **campi) -> None:
    with _lock:
        _lavori.setdefault(job_id, {}).update(campi)


def stato(job_id: str) -> dict:
    with _lock:
        return dict(_lavori.get(job_id, {"esiste": False}))


def _esegui(job_id: str, richiesta: dict) -> None:
    try:
        model_id = richiesta["modello"]
        nome = richiesta.get("nome") or "animazione"
        n_frame = int(richiesta.get("n_frame", 25))
        durata = float(richiesta.get("durata_s", 2.0))
        lato = int(richiesta.get("lato_cella", 256))

        st = modelli.stato(model_id)
        if not st["installato"]:
            mancanti = [f["path"] for f in st["file"] if not f["presente"]]
            raise RuntimeError(t(
                "mod.non_installato", id=model_id, n=len(mancanti),
                primo=Path(mancanti[0]).name))

        piano = parametri.piano(model_id, durata, n_frame)
        _aggiorna(job_id, fase="inferenza", percentuale=0.0, piano=piano)

        backend = ottieni_backend(model_id, config.MODELS_DIR / model_id)
        frames = backend.genera(
            sprite=richiesta["sprite"],
            prompt=richiesta["prompt"],
            lunghezza=piano["lunghezza"],
            larghezza=int(richiesta.get("larghezza", 448)),
            altezza=int(richiesta.get("altezza", 448)),
            seed=int(richiesta.get("seed", 0)),
            avanzamento=lambda p: _aggiorna(job_id, percentuale=round(p * 0.9, 3)),
        )

        _aggiorna(job_id, fase="composizione", percentuale=0.92)
        scelti = [frames[i] for i in piano["indici"] if i < len(frames)]

        # I modelli di diffusione video non producono un canale alfa: i frame
        # arrivano opachi, con lo sfondo bianco chiesto dal prompt. Uno sprite
        # sheet con lo sfondo pieno non e' utilizzabile in un gioco, quindi la
        # trasparenza va ricavata qui, frame per frame, con lo stesso scontorno
        # che si applica allo sprite sorgente.
        scontorna = bool(richiesta.get("scontorna", True))
        if scontorna:
            _aggiorna(job_id, fase="scontorno", percentuale=0.93)
            scelti = [scontorno.scontorna_immagine(f) for f in scelti]

        # La filigrana va qui, sui frame gia' scelti e scontornati: cosi'
        # finisce sia nel foglio sia nella GIF, e non viene mangiata dallo
        # scontorno. L'edizione senza filigrana e' questo `if`.
        if edizione.FILIGRANA:
            _aggiorna(job_id, fase="filigrana", percentuale=0.94)
            scelti = filigrana.applica(scelti, edizione.FILIGRANA_TESTO)

        # Una cartella per generazione, marcata con l'istante in cui e' partita.
        # Senza, rigenerare con lo stesso nome sovrascriveva il lavoro
        # precedente: dieci minuti di GPU persi in silenzio, e nessun modo di
        # confrontare due tentativi dello stesso soggetto.
        dest = config.OUTPUT_DIR / f"{nome}_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
        r_sheet = sheet.componi_sheet(
            scelti, piano["colonne"], piano["righe"], lato,
            dest / f"{nome}_sheet.png")

        _aggiorna(job_id, fase="gif", percentuale=0.97)
        r_gif = sheet.componi_gif(
            scelti, piano["fps_riproduzione"], lato, dest / f"{nome}.gif")

        # `scontornato` viaggia fino all'interfaccia: quando il risultato non e'
        # quello atteso, la prima domanda e' se l'opzione fosse davvero attiva,
        # e senza questo dato la risposta si puo' solo indovinare.
        _aggiorna(job_id, fase="fatto", percentuale=1.0, attivo=False,
                  sheet=r_sheet, gif=r_gif, cartella=str(dest),
                  scontornato=scontorna, edizione=edizione.stato())

    except Exception as e:
        # La traccia viaggia intera fino all'interfaccia: e' quella che serve
        # incollare quando qualcosa si rompe, e ricostruirla a mano dai log del
        # sidecar significa non averla proprio.
        _aggiorna(job_id, fase="errore", attivo=False,
                  errore=f"{type(e).__name__}: {e}",
                  traccia=traceback.format_exc(),
                  richiesta={k: richiesta.get(k) for k in
                             ("modello", "sprite", "nome", "durata_s", "n_frame")})
        traceback.print_exc()


def avvia(richiesta: dict) -> dict:
    for chiave in ("modello", "sprite", "prompt"):
        if not richiesta.get(chiave):
            return {"ok": False, "errore": t("gen.campo_mancante", campo=chiave)}
    if not Path(richiesta["sprite"]).is_file():
        return {"ok": False, "errore": t("gen.sprite_assente")}

    # Il tetto si consuma prima di avviare il thread: chiedere dopo vorrebbe
    # dire aver gia' occupato la GPU per una generazione non ammessa.
    permesso = edizione.consuma()
    if not permesso.get("ok"):
        return {"ok": False, "errore": permesso["errore"],
                "edizione": edizione.stato()}

    job_id = "job_%d" % int(time.time() * 1000)
    _aggiorna(job_id, attivo=True, fase="avvio", percentuale=0.0, errore=None)
    threading.Thread(target=_esegui, args=(job_id, richiesta), daemon=True).start()
    return {"ok": True, "job": job_id, "edizione": edizione.stato()}
