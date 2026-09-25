"""Il pulsante Annulla ferma davvero la GPU?

Non basta che il sidecar dica "annullato": se ComfyUI continua a campionare
per altri quattro minuti, l'utente ha la GPU occupata e l'impressione che il
clic non sia servito. Qui si avvia una generazione vera, la si lascia
arrivare al campionamento, si annulla e si misura:

- quanto ci mette il sidecar a passare ad `annullato`;
- se la coda di ComfyUI si svuota;
- se la GPU scende sotto il 30% di utilizzo, cioe' se ha smesso davvero.

Richiede ComfyUI acceso e i pesi di FastH3. Dura qualche minuto, quasi
tutto di caricamento pesi.

    python sidecar/test_annulla.py
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))

import config                                              # noqa: E402
import genera                                              # noqa: E402
import modelli                                             # noqa: E402

SPRITE = Path(r"E:\AI_Video\tmp\polizia\frame0.png")


def coda() -> int:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8188/queue",
                                         timeout=10))
    return len(d.get("queue_running", [])) + len(d.get("queue_pending", []))


def gpu() -> int:
    r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu",
                        "--format=csv,noheader,nounits"],
                       capture_output=True, text=True)
    try:
        return int(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1


def main() -> int:
    # Il catalogo guarda in MODELS_DIR: si punta alla cartella dei sorgenti,
    # dove i pesi di FastH3 ci sono gia'.
    if not modelli.stato("minimax_h3_fast")["installato"]:
        print("FastH3 non installato in %s" % config.MODELS_DIR)
        return 1

    r = genera.avvia({
        "modello": "minimax_h3_fast", "sprite": str(SPRITE),
        "prompt": "integrated_multimodal_description: a test.\n\n"
                  "overall_soundscape: Silent.\n\nnon_diegetic_music: None.",
        "nome": "test_annulla", "durata_s": 56 / 24, "n_frame": 25,
        "larghezza": 448, "altezza": 448, "seed": 1,
    })
    if not r.get("ok"):
        print("avvio rifiutato:", r)
        return 1
    job = r["job"]
    print("lavoro %s avviato" % job)

    # Si aspetta il campionamento: annullare durante il caricamento dei pesi
    # prova meno, perche' li' ComfyUI non guarda l'interruttore.
    t0 = time.time()
    while time.time() - t0 < 900:
        s = genera.stato(job)
        if "1/" in (s.get("dettaglio") or "") or "2/" in (s.get("dettaglio") or ""):
            break
        if not s.get("attivo", True):
            print("finito prima di poter annullare:", s.get("fase"), s.get("errore"))
            return 1
        time.sleep(2)
    print("campionamento iniziato dopo %.0f s, GPU al %d%%"
          % (time.time() - t0, gpu()))

    t_clic = time.time()
    print("annullo:", genera.annulla(job))

    while genera.stato(job).get("attivo"):
        time.sleep(0.5)
    t_sidecar = time.time() - t_clic
    fase = genera.stato(job).get("fase")
    print("sidecar: fase %s dopo %.1f s" % (fase, t_sidecar))

    # La GPU: si guarda per un minuto al massimo quando scende.
    t_gpu = None
    for _ in range(60):
        if coda() == 0 and 0 <= gpu() < 30:
            t_gpu = time.time() - t_clic
            break
        time.sleep(1)
    print("ComfyUI: coda %d, GPU %d%%, ferma dopo %s"
          % (coda(), gpu(), "%.0f s" % t_gpu if t_gpu else "PIU' DI UN MINUTO"))

    ok = fase == "annullato" and t_gpu is not None
    print("\n%s" % ("tutto a posto" if ok else "ERRORE"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
