"""Coda, lotti, cronologia e margine, senza GPU.

Un backend finto al posto di ComfyUI; coda, post, meta e cronologia sono
quelli veri.

    python sidecar/test_coda.py
"""
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import coda
import config
import genera
import inquadra
import modelli
import storico
from backend import Backend

VERDE = (64, 173, 84)
errori: list[str] = []


def verifica(cond, msg):
    if not cond:
        errori.append(msg)


class Finto(Backend):
    nome = "finto"
    PASSI = 8

    def __init__(self):
        super().__init__(Path("."))
        self.lotti = []          # una voce per chiamata: quante azioni
        self.sprite = None
        self.pausa = 0.0
        self.via = threading.Event()

    def genera_lotto(self, sprite, voci, larghezza, altezza,
                     avanzamento=None, fermo=None):
        self.lotti.append(len(voci))
        self.sprite = Image.open(sprite).copy()
        fine = time.time() + self.pausa
        while time.time() < fine and not self.via.is_set():
            time.sleep(0.02)
        out = []
        for v in voci:
            frames = []
            for i in range(v["lunghezza"]):
                im = Image.new("RGB", (larghezza, altezza), VERDE)
                ImageDraw.Draw(im).rectangle((20 + i, 40, 60 + i, 120), fill=(200, 40, 40))
                frames.append(im)
            out.append(frames)
        if avanzamento:
            avanzamento(1.0, "pronto")
        return out


def aspetta(job, fasi=("fatto", "errore", "annullato"), tetto=20.0):
    fine = time.time() + tetto
    while time.time() < fine:
        s = coda.stato(job)
        if s.get("fase") in fasi:
            return s
        time.sleep(0.05)
    return coda.stato(job)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ss_coda_"))
    config.OUTPUT_DIR = tmp / "output"
    config.OUTPUT_DIR.mkdir()
    config.CACHE_DIR = tmp / "cache"
    config.CACHE_DIR.mkdir()
    sprite = tmp / "eroe.png"
    im = Image.new("RGB", (200, 200), VERDE)
    ImageDraw.Draw(im).rectangle((70, 20, 129, 179), fill=(200, 40, 40))
    im.save(sprite)

    finto = Finto()
    genera.ottieni_backend = lambda *_: finto
    modelli.stato = lambda _id: {"installato": True, "file": []}
    base = {"modello": "minimax_h3_fast", "sprite": str(sprite),
            "colore_sfondo": "verde"}

    # --- fila: il secondo aspetta, il terzo si annulla mentre aspetta ------
    finto.pausa = 5.0
    a = coda.avvia({**base, "nome": "primo", "prompt": "uno", "n_frame": 4})
    b = coda.avvia({**base, "nome": "secondo", "prompt": "due", "n_frame": 4})
    c = coda.avvia({**base, "nome": "terzo", "prompt": "tre", "n_frame": 4})
    verifica(a["ok"] and b["ok"] and c["ok"], "avvio rifiutato: %s" % [a, b, c])
    time.sleep(0.3)
    sb = coda.stato(b["job"])
    verifica(sb.get("fase") == "in_coda" and sb.get("posizione") == 1,
             "secondo non in coda dietro al primo: %s" % sb)
    verifica(coda.stato(c["job"]).get("posizione") == 2, "terzo non in posizione 2")
    verifica(len(coda.elenco()) == 3, "elenco coda: %s" % coda.elenco())
    r = coda.annulla(c["job"])
    verifica(r["ok"] and coda.stato(c["job"])["fase"] == "annullato",
             "annullo in coda non riuscito")
    verifica(coda.stato(b["job"]).get("posizione") == 1, "posizione non aggiornata")
    finto.pausa = 0.0
    finto.via.set()
    sa, sb = aspetta(a["job"]), aspetta(b["job"])
    verifica(sa.get("fase") == "fatto" and sb.get("fase") == "fatto",
             "fila non completata: %s / %s" % (sa.get("errore"), sb.get("errore")))
    verifica(finto.lotti == [1, 1], "il terzo e' stato eseguito: %s" % finto.lotti)
    verifica(sa["finito"] <= sb["finito"], "ordine non rispettato")

    # --- lotto: tre azioni, un solo giro di backend -------------------------
    finto.lotti.clear()
    finto.via.clear()
    l = coda.avvia({**base, "formato": "3:4", "azioni": [
        {"nome": "idle", "prompt": "respira", "durata_s": 2, "n_frame": 9},
        {"nome": "colpo", "prompt": "colpisce", "durata_s": 3, "n_frame": 16, "seed": 42},
        {"nome": "idle", "prompt": "respira ancora", "n_frame": 4}]})
    sl = aspetta(l["job"])
    verifica(sl.get("fase") == "fatto", "lotto fallito: %s" % sl.get("traccia"))
    verifica(finto.lotti == [3], "backend chiamato %s volte" % finto.lotti)
    ris = sl.get("risultati") or []
    verifica(len(ris) == 3, "risultati lotto: %d" % len(ris))
    cartelle = [Path(x["cartella"]).name for x in ris]
    verifica(len(set(cartelle)) == 3 and cartelle[2].endswith("_2"),
             "nomi doppi non distinti: %s" % cartelle)
    verifica(ris[1]["seed"] == 42, "seme esplicito del lotto perso")
    for x in ris:
        m = json.loads((Path(x["cartella"]) / "meta.json").read_text(encoding="utf-8"))
        verifica(m["seed"] == x["seed"] and m["formato"] == "3:4",
                 "meta.json incoerente in %s" % x["cartella"])
    verifica(sl["cartella"] == ris[-1]["cartella"], "in cima non c'e' l'ultima azione")

    # --- cronologia e rigenera ---------------------------------------------
    voci = storico.elenco()
    verifica(len(voci) == 5, "cronologia: %d voci" % len(voci))
    verifica(all(v["rigenerabile"] for v in voci), "voce non rigenerabile")
    rq = storico.richiesta_da(ris[1]["cartella"], seed=7)
    verifica(rq["seed"] == 7 and rq["prompt"] == "colpisce" and rq["formato"] == "3:4",
             "richiesta ricostruita male: %s" % rq)
    # Stessa cartella sul disco, non stessa stringa: `richiesta_da` normalizza
    # con resolve(), che su Windows espande i nomi brevi. Sul server della CI
    # la cartella temporanea e' C:\Users\RUNNER~1\... e il confronto fra
    # stringhe falliva su una cartella giusta.
    verifica(os.path.samefile(Path(rq["sprite"]).parent, ris[1]["cartella"]),
             "rigenera non usa la copia dello sprite")
    for fuori in (str(tmp), str(sprite.parent.parent), "C:\\Windows", ""):
        try:
            storico.richiesta_da(fuori)
            errori.append("cartella fuori da output accettata: %r" % fuori)
        except ValueError:
            pass
    rg = coda.avvia(rq)
    verifica(aspetta(rg["job"]).get("seed") == 7, "rigenerazione fallita")

    # --- TTL ----------------------------------------------------------------
    coda.DURATA_S = 0
    time.sleep(0.05)
    coda.avvia({**base, "nome": "x", "prompt": "p", "n_frame": 4})
    verifica(coda.stato(a["job"]) == {"esiste": False}, "stato vecchio non buttato")
    coda.DURATA_S = 3600

    # --- errori di richiesta ------------------------------------------------
    for sbagliata, attesa in (({**base, "azioni": []}, "azioni"),
                              ({**base, "prompt": "p", "formato": "5:4"}, "formato"),
                              ({**base, "prompt": "p", "margine": "enorme"}, "margine"),
                              ({**base, "prompt": ""}, "prompt")):
        r = coda.avvia(sbagliata)
        verifica(not r["ok"], "richiesta sbagliata accettata: %s" % attesa)

    # --- margine: figura al 68%, piedi in basso, niente stiramento ----------
    dst = tmp / "adattato.png"
    out = inquadra.adatta(sprite, 384, 512, "verde", "ampio", dst)
    a2 = Image.open(out)
    verifica(a2.size == (384, 512), "margine: tela %s" % (a2.size,))
    rosso = a2.point(lambda v: 255 if v > 150 else 0).split()[0]
    x0, y0, x1, y1 = rosso.getbbox()
    verifica(abs((y1 - y0) - 0.68 * 512) <= 3, "figura alta %d, attesa ~348" % (y1 - y0))
    verifica(abs(y1 - 512 * 0.96) <= 3, "piedi a %d, attesi ~491" % y1)
    verifica(abs((x1 - x0) / (y1 - y0) - 60 / 160) < 0.03, "figura deformata")
    verifica(inquadra.adatta(sprite, 448, 448, "verde", "nessuno", dst) == sprite,
             "senza margine uno sprite quadrato su 1:1 deve passare intatto")

    # --- stima -----------------------------------------------------------------
    st = genera.Stima(1)
    verifica(st.secondi(0.05) is None, "stima prima del campionamento")
    st.secondi(0.2)
    st.t0 -= 10                      # dieci secondi per il 20% che segue
    eta = st.secondi(0.4)
    verifica(eta is not None and 25 <= eta <= 45, "stima fuori misura: %s" % eta)

    # --- barra del lotto: ComfyUI esegue i rami in ordine suo --------------
    # Ordine vero visto con la pecora: 1, 2, 5, 4, 3. La barra deve salire
    # regolare, non saltare al 74% dopo due azioni.
    from backend.comfyui_bridge import _Racconto, mappa_lotto, nodo
    visti = []
    rc = _Racconto(lambda p, d="": visti.append(p), mappa_lotto(5))
    for ramo in (0, 1, 4, 3, 2):
        rc.evento({"type": "executing", "data": {"node": nodo(6, ramo)}})
        rc.evento({"type": "progress", "data": {"node": nodo(11, ramo), "value": 8, "max": 8}})
    verifica(all(b >= a for a, b in zip(visti, visti[1:])), "barra del lotto che rincula")
    verifica(visti[3] < 0.5, "barra del lotto troppo avanti dopo due azioni: %.2f" % visti[3])

    for e in errori:
        print("ERRORE:", e)
    print("tutto a posto" if not errori else f"{len(errori)} errori")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
