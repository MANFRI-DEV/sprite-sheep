"""Lo sprite di partenza portato alla tela della clip.

Due problemi diversi, risolti nello stesso punto perche' toccano la stessa
immagine:

**Il formato.** Il nodo di H3 stira il primo frame sulla tela ("plain
stretch"): uno sprite quadrato su una clip 3:4 uscirebbe allungato, e il
modello animerebbe un personaggio deformato. WAN invece ritaglia al centro e
taglierebbe testa e piedi. Si aggiunge fondo ai lati, del colore del fondo.

**Lo spazio per muoversi.** Uno sprite che riempie il quadro non ha dove
andare: in un montante o in un salto il modello, per tenere il pugno dentro
l'inquadratura, allarga la ripresa invece di alzare il braccio, e il
personaggio cambia scala a meta' clip. A mano lo si risolveva riducendo la
figura al 68% dell'altezza con i piedi in basso (`tmp/polizia_frame0.py`);
`margine` fa la stessa cosa.
"""
from pathlib import Path

import numpy as np
from PIL import Image

import scontorno

## Frazione dell'altezza della tela occupata dalla figura. `None` = lo sprite
## resta com'e' e si aggiunge solo il fondo che manca al formato.
MARGINI = {
    "nessuno": None,
    "normale": 0.80,
    # Salti, montanti, braccia alzate: e' la misura provata a mano.
    "ampio": 0.68,
}
MARGINE_PREDEFINITO = "nessuno"

## Spazio sotto i piedi, in frazione dell'altezza: poco, perche' il suolo non
## si muove, ma non zero, se no l'ombra e i tacchi toccano il bordo.
PIEDI = 0.04
## Larghezza massima della figura: in un formato stretto (9:16) l'altezza non
## e' il limite, e un braccio teso uscirebbe dai lati.
LARGHEZZA_MAX = 0.92


def tinta_fondo(rgb: Image.Image, colore) -> tuple:
    """La tinta **misurata** del fondo dello sprite, non quella del preset.

    Il "verde" vale (0,177,64), un green screen vero esce (64,173,84), e un
    bordo del colore del preset cade appena fuori dalla soglia dello
    scontorno: restava opaco e la rimozione dello spill lo tingeva di blu
    scuro. Bande sopra e sotto ogni cella, viste alla prima prova vera in 3:4.
    """
    a = np.asarray(rgb).astype(np.int16)
    t = scontorno.aggancia_tinta(a, scontorno.risolvi_colore(colore, a))
    return tuple(int(round(float(c))) for c in t)


def adatta(src: Path, larghezza: int, altezza: int, colore, margine: str,
           dst: Path) -> Path:
    """Restituisce `src` se va gia' bene cosi', altrimenti scrive `dst`."""
    if margine not in MARGINI:
        raise ValueError("margine sconosciuto: %r (validi: %s)"
                         % (margine, ", ".join(MARGINI)))
    im = Image.open(src)
    quota = MARGINI[margine]
    if quota is not None:
        tela = _con_margine(im, larghezza, altezza, colore, quota)
        if tela is not None:
            tela.save(dst)
            return dst
    return _solo_formato(im, src, larghezza, altezza, colore, dst)


def _solo_formato(im: Image.Image, src: Path, larghezza: int, altezza: int,
                  colore, dst: Path) -> Path:
    """Allarga la tela senza ricampionare: scala il nodo, come prima. Uno
    sprite gia' nel rapporto giusto passa intatto, quindi il caso quadrato su
    1:1 non cambia di un bit."""
    w, h = im.size
    if w * altezza == h * larghezza:
        return src
    # Stessa conversione di LoadImage in ComfyUI: l'alfa si scarta e restano
    # i colori sotto. Cosi' il bordo aggiunto e lo sprite si comportano come
    # si comportava lo sprite da solo.
    rgb = im.convert("RGB")
    tw = max(w, -(-h * larghezza // altezza))
    th = max(h, -(-w * altezza // larghezza))
    tela = Image.new("RGB", (tw, th), tinta_fondo(rgb, colore))
    tela.paste(rgb, ((tw - w) // 2, (th - h) // 2))
    tela.save(dst)
    return dst


def _con_margine(im: Image.Image, larghezza: int, altezza: int, colore,
                 quota: float) -> Image.Image | None:
    """Figura alta `quota` della tela, piedi in basso, centrata in larghezza.

    La figura si trova con lo stesso scontorno dei frame generati. Se non si
    trova niente (sprite vuoto, fondo non a tinta unita) si torna `None` e si
    ripiega sull'adattamento semplice: meglio uno sprite senza margine che
    uno ridotto a caso.
    """
    rgb = im.convert("RGB")
    alfa = scontorno.scontorna_immagine(rgb, colore=colore).getchannel("A")
    riquadro = alfa.point(lambda v: 255 if v > 128 else 0).getbbox()
    if riquadro is None:
        return None
    x0, y0, x1, y1 = riquadro
    bw, bh = x1 - x0, y1 - y0
    scala = min(quota * altezza / bh, LARGHEZZA_MAX * larghezza / bw)

    nw, nh = max(1, round(rgb.width * scala)), max(1, round(rgb.height * scala))
    # Ingrandire pixel art con un filtro morbido la sfoca: sopra 1 si usa
    # NEAREST, sotto LANCZOS, come per le celle dello sheet.
    filtro = Image.NEAREST if scala > 1 else Image.LANCZOS
    ridotta = rgb.resize((nw, nh), filtro)

    tela = Image.new("RGB", (larghezza, altezza), tinta_fondo(rgb, colore))
    ox = round(larghezza / 2 - (x0 + x1) / 2 * scala)
    oy = round(altezza * (1 - PIEDI) - y1 * scala)
    tela.paste(ridotta, (ox, oy))
    return tela
