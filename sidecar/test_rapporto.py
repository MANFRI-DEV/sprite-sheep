"""Il log HTML di generazione, senza GPU.

Un backend finto disegna un cerchio che si muove su fondo verde; il resto
della catena (scontorno, sheet, GIF, log) e' quello vero.

    python sidecar/test_rapporto.py
"""
import re
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import config
import genera
import modelli
from backend import Backend

VERDE = (64, 173, 84)


class Finto(Backend):
    nome = "backend finto"
    PASSI = 8

    def __init__(self):
        super().__init__(Path("."))
        self.seed = None
        self.sprite = None

    def genera(self, sprite, prompt, lunghezza, larghezza, altezza, seed,
               avanzamento=None, fermo=None):
        self.seed = seed
        self.sprite = Image.open(sprite).copy()
        out = []
        for i in range(lunghezza):
            im = Image.new("RGB", (larghezza, altezza), VERDE)
            x = 60 + i * 3
            ImageDraw.Draw(im).ellipse((x, 150, x + 120, 270), fill=(200, 40, 40))
            out.append(im)
        return out


_stati: dict[str, dict] = {}


def esegui(job: str, richiesta: dict) -> None:
    """Come fa `coda`, ma nello stesso thread: normalizza ed esegue."""
    _stati[job] = {}
    try:
        lavoro = genera.normalizza(richiesta)
    except ValueError as e:
        _stati[job] = {"fase": "errore", "errore": str(e)}
        return
    genera.esegui(job, lavoro, threading.Event(),
                  lambda **c: _stati[job].update(c))


def stato(job: str) -> dict:
    return _stati.get(job, {})


def main() -> int:
    errori = []
    tmp = Path(tempfile.mkdtemp(prefix="ss_log_"))
    config.OUTPUT_DIR = tmp
    sprite = tmp / "Eroe.PNG"
    Image.new("RGB", (448, 448), VERDE).save(sprite)

    finto = Finto()
    genera.ottieni_backend = lambda *_: finto
    modelli.stato = lambda _id: {"installato": True, "file": []}

    prompt = 'Uppercut <script>alert("x")</script> & [0s-1s] "salto"'
    esegui("job_t", {
        "modello": "minimax_h3_fast", "sprite": str(sprite), "prompt": prompt,
        "nome": "eroe", "durata_s": 2.0, "n_frame": 16, "lato_cella": 128,
        "colore_sfondo": "verde",
    })

    st = stato("job_t")
    if st.get("fase") != "fatto":
        print(st.get("traccia") or st)
        return 1
    log = Path(st["log"] or "")
    if not log.is_file():
        return print("log mancante:", st) or 1
    h = log.read_text(encoding="utf-8")

    def verifica(cond, msg):
        if not cond:
            errori.append(msg)

    verifica(finto.seed and finto.seed == st["seed"], "seed del backend != seed riportato")
    verifica(f"<code>{finto.seed}</code>" in h, "seed assente dal log")
    verifica("<script>" not in h, "prompt non escapato")
    verifica("&lt;script&gt;" in h, "prompt assente")
    verifica("MiniMax H3 Fast" in h, "nome modello assente")
    verifica(">8<" in h, "passi assenti")
    verifica("56 @ 24 fps" in h, "frame generati assenti")
    verifica("chroma key" in h or "tinta unita" in h, "via di scontorno sbagliata")
    verifica("#40ad54" in h, "tinta misurata assente (atteso #40ad54)")
    for f in re.findall(r'src="([^"]+)"', h):
        verifica((log.parent / f).is_file(), "immagine non trovata: " + f)
    verifica((log.parent / "eroe_sprite_iniziale.png").is_file(), "sprite non copiato")
    verifica(h.count("<tr>") >= 20, "righe mancanti")

    # Senza scontorno la sezione deve dirlo e non inventare tinte.
    esegui("job_t2", {
        "modello": "wan22_ti2v_5b", "sprite": str(sprite), "prompt": "idle",
        "nome": "eroe2", "durata_s": 2.0, "n_frame": 9, "scontorna": False,
        "seed": 1234,
    })
    st2 = stato("job_t2")
    h2 = Path(st2.get("log") or tmp / "x").read_text(encoding="utf-8") \
        if st2.get("log") else ""
    verifica(st2.get("seed") == 1234 and finto.seed == 1234, "seed esplicito non rispettato")
    verifica("<code>1234</code>" in h2, "seed esplicito assente dal log")
    verifica("#40ad54" not in h2, "tinta riportata senza scontorno")

    # Formato 3:4 con sprite quadrato: la tela si allarga in altezza, lo
    # sprite resta com'era, i bordi sono del colore del fondo.
    quadro = tmp / "quadro.png"
    q = Image.new("RGB", (200, 200), VERDE)
    ImageDraw.Draw(q).rectangle((50, 50, 149, 149), fill=(200, 40, 40))
    q.save(quadro)
    esegui("job_t3", {
        "modello": "minimax_h3_fast", "sprite": str(quadro), "prompt": "idle",
        "nome": "alto", "durata_s": 2.0, "n_frame": 9, "lato_cella": 256,
        # "verde" e non "auto": il preset (0,177,64) e' lontano dal verde vero
        # dello sprite, ed e' il caso che alla prova su GPU dava bande blu.
        "formato": "3:4", "colore_sfondo": "verde",
    })
    st3 = stato("job_t3")
    verifica(st3.get("fase") == "fatto", "3:4 fallito: %s" % st3.get("errore"))
    if st3.get("fase") == "fatto":
        a = finto.sprite
        verifica(a.size == (200, 267), "tela adattata %s, attesa 200x267" % (a.size,))
        verifica(a.getpixel((100, 5)) == VERDE, "bordo sopra non del colore di fondo")
        verifica(a.crop((0, 33, 200, 233)).tobytes() == q.tobytes(),
                 "sprite alterato nell'adattamento")
        verifica(st3["sheet"]["cella_larghezza"] == 192
                 and st3["sheet"]["cella_altezza"] == 256, "cella 3:4 sbagliata")
        g = st3["gif"]
        verifica((g["larghezza"], g["altezza"]) == (192, 256), "GIF 3:4 sbagliata")
        h3 = Path(st3["log"]).read_text(encoding="utf-8")
        verifica("384 × 512 px" in h3 and "192 × 256 px" in h3, "formato assente dal log")
        verifica(not (config.CACHE_DIR / "sprite_job_t3.png").exists(),
                 "sprite adattato non rimosso")

    # Sprite gia' nel rapporto giusto: passa intatto, nessun file temporaneo.
    esegui("job_t4", {
        "modello": "minimax_h3_fast", "sprite": str(quadro), "prompt": "idle",
        "nome": "quadro", "n_frame": 9, "formato": "1:1",
    })
    verifica(finto.sprite.size == (200, 200), "1:1 con sprite quadrato modificato")

    # Formato sconosciuto: errore chiaro, non un ripiego sul quadrato.
    esegui("job_t5", {
        "modello": "minimax_h3_fast", "sprite": str(quadro), "prompt": "idle",
        "formato": "2:1"})
    verifica("formato sconosciuto" in str(stato("job_t5").get("errore")),
             "formato sconosciuto accettato")

    print("log:", log)
    for e in errori:
        print("ERRORE:", e)
    print("tutto a posto" if not errori else f"{len(errori)} errori")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
