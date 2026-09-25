"""La fila dei lavori: uno alla volta sulla GPU, gli altri in attesa.

Prima ogni `/genera` apriva un thread suo. Il lucchetto proteggeva il
dizionario degli stati, non la GPU: due clic ravvicinati mandavano due
prompt a ComfyUI, che li metteva in coda per conto suo, e l'interfaccia
mostrava due barre ferme senza dire quale stesse aspettando l'altra. E
`/interrupt` fermava qualunque cosa girasse, anche il lavoro sbagliato.

Qui c'e' un solo lavoratore. Un lavoro aspetta finche' quello prima non
finisce, e intanto il suo stato dice quanti ne ha davanti; annullarlo mentre
aspetta lo toglie dalla fila senza toccare ComfyUI.

Gli stati dei lavori finiti restano un'ora (`DURATA_S`), poi si buttano: un
sidecar acceso per giorni teneva in memoria ogni lavoro mai fatto.
"""
import threading
import time
from pathlib import Path

import edizione
import genera
from testi import t

DURATA_S = 3600

_lock = threading.Condition()
_lavori: dict[str, dict] = {}
## Un interruttore per lavoro. Il backend lo guarda ogni due secondi; alzarlo
## e' tutto quello che serve per fermare una generazione. Sta fuori da
## `_lavori` perche' quello si copia per rispondere a `/genera?job=`, e un
## `threading.Event` non si serializza in JSON.
_fermi: dict[str, threading.Event] = {}
_attesa: list[str] = []
_richieste: dict[str, dict] = {}
_in_corso: str | None = None
_lavoratore: threading.Thread | None = None
_contatore = 0


def _aggiorna(job_id: str, **campi) -> None:
    with _lock:
        if job_id in _lavori:
            _lavori[job_id].update(campi)


def _posizione(job_id: str) -> int:
    """Quanti lavori ha davanti. Si chiama con il lucchetto preso."""
    return _attesa.index(job_id) + (1 if _in_corso else 0)


def stato(job_id: str) -> dict:
    with _lock:
        s = _lavori.get(job_id)
        if s is None:
            return {"esiste": False}
        s = dict(s)
        if job_id in _attesa:
            n = _posizione(job_id)
            s["posizione"] = n
            # A zero il lavoratore lo sta per prendere: "0 lavori prima"
            # suonerebbe come un'attesa che non c'e'.
            s["dettaglio"] = t("gen.in_coda", n=n) if n > 0 else ""
        return s


def elenco() -> list[dict]:
    """I lavori non ancora finiti, nell'ordine in cui verranno eseguiti."""
    with _lock:
        ids = ([_in_corso] if _in_corso else []) + list(_attesa)
        return [{"job": j, "fase": _lavori[j].get("fase"),
                 "azioni": _lavori[j].get("nomi", []),
                 "percentuale": _lavori[j].get("percentuale", 0.0)}
                for j in ids if j in _lavori]


def _pulisci(adesso: float) -> None:
    """Toglie gli stati finiti da piu' di `DURATA_S`. Lucchetto preso."""
    vecchi = [j for j, s in _lavori.items()
              if s.get("finito") and adesso - s["finito"] > DURATA_S]
    for j in vecchi:
        _lavori.pop(j, None)
        _fermi.pop(j, None)


def avvia(richiesta: dict) -> dict:
    global _contatore, _lavoratore
    try:
        lavoro = genera.normalizza(richiesta)
    except (ValueError, TypeError) as e:
        return {"ok": False, "errore": str(e)}
    if not Path(lavoro["sprite"]).is_file():
        return {"ok": False, "errore": t("gen.sprite_assente")}

    # Il tetto si consuma prima di mettere in fila: chiedere dopo vorrebbe
    # dire aver gia' occupato la GPU per una generazione non ammessa.
    permesso = edizione.consuma()
    if not permesso.get("ok"):
        return {"ok": False, "errore": permesso["errore"],
                "edizione": edizione.stato()}

    adesso = time.time()
    with _lock:
        _pulisci(adesso)
        _contatore += 1
        # Il contatore evita due id uguali per due clic nello stesso
        # millesimo, che con la coda diventano possibili.
        job_id = "job_%d_%d" % (int(adesso * 1000), _contatore)
        _fermi[job_id] = threading.Event()
        _lavori[job_id] = {"attivo": True, "fase": "in_coda", "percentuale": 0.0,
                           "errore": None, "creato": adesso,
                           "nomi": [a["nome"] for a in lavoro["azioni"]]}
        _richieste[job_id] = lavoro
        _attesa.append(job_id)
        posizione = _posizione(job_id)
        if _lavoratore is None or not _lavoratore.is_alive():
            _lavoratore = threading.Thread(target=_lavora, daemon=True,
                                           name="lavoratore-gpu")
            _lavoratore.start()
        _lock.notify()
    return {"ok": True, "job": job_id, "posizione": posizione,
            "edizione": edizione.stato()}


def _lavora() -> None:
    global _in_corso
    while True:
        with _lock:
            while not _attesa:
                _lock.wait()
            job_id = _attesa.pop(0)
            lavoro = _richieste.pop(job_id)
            fermo = _fermi[job_id]
            _in_corso = job_id
            _lavori[job_id].update(fase="avvio", dettaglio="")
        try:
            genera.esegui(job_id, lavoro, fermo,
                          lambda **c: _aggiorna(job_id, **c))
        finally:
            with _lock:
                _in_corso = None
                if job_id in _lavori:
                    _lavori[job_id]["attivo"] = False
                    _lavori[job_id]["finito"] = time.time()


def annulla(job_id: str) -> dict:
    """Chiede di fermare un lavoro. Risponde subito.

    In attesa: esce dalla fila, e basta. In corso: si alza l'interruttore, lo
    stop vero arriva entro un paio di secondi, quando il backend lo guarda, e
    ComfyUI si ferma al primo confine fra un passo e l'altro. Lo stato passa
    a `annullamento` e non direttamente ad `annullato`: fra il clic e lo stop
    possono passare decine di secondi, e l'interfaccia deve poter dire "sto
    fermando" invece di sembrare bloccata."""
    with _lock:
        if job_id in _attesa:
            _attesa.remove(job_id)
            _richieste.pop(job_id, None)
            _lavori[job_id].update(fase="annullato", attivo=False, dettaglio="",
                                   finito=time.time())
            return {"ok": True, "job": job_id}
        fermo = _fermi.get(job_id)
        attivo = _lavori.get(job_id, {}).get("attivo", False)
    if fermo is None or not attivo:
        return {"ok": False, "errore": t("gen.niente_da_annullare")}
    fermo.set()
    _aggiorna(job_id, fase="annullamento", dettaglio=t("gen.in_annullamento"))
    return {"ok": True, "job": job_id}
