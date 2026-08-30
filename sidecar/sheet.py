"""Composizione dello sprite sheet e della GIF a partire dai frame.

Due dettagli che sembrano minori ma non lo sono:

- Il ridimensionamento delle celle usa NEAREST se la cella e' piu' piccola di
  un multiplo esatto, altrimenti LANCZOS. Su pixel art il filtro morbido
  distrugge la griglia dei pixel.
- Il delay della GIF si esprime in centesimi di secondo interi. Un fps che non
  cade su un intero (24 -> 4,1666 cs) viene arrotondato e l'animazione deriva a
  ogni ripetizione. Qui si sceglie il delay intero piu' vicino e si ricalcola
  l'fps reale, cosi' quello che si dichiara e' quello che si vede.
"""
from pathlib import Path

from PIL import Image


def _ridimensiona(im: Image.Image, lato: int) -> Image.Image:
    if im.size == (lato, lato):
        return im
    # ingrandimento a fattore intero = pixel art: NEAREST tiene i bordi netti
    intero = lato % im.width == 0 and lato % im.height == 0 and lato > im.width
    return im.resize((lato, lato), Image.NEAREST if intero else Image.LANCZOS)


def componi_sheet(frames: list[Image.Image], colonne: int, righe: int,
                  lato_cella: int, dst: str | Path,
                  sfondo: tuple | None = None) -> dict:
    """Scrive lo sprite sheet. `sfondo=None` mantiene la trasparenza."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tela = Image.new("RGBA", (colonne * lato_cella, righe * lato_cella),
                     sfondo if sfondo else (0, 0, 0, 0))
    for i, f in enumerate(frames):
        if i >= colonne * righe:
            break
        r, c = divmod(i, colonne)
        tela.alpha_composite(_ridimensiona(f.convert("RGBA"), lato_cella),
                             (c * lato_cella, r * lato_cella))
    if sfondo:
        tela.convert("RGB").save(dst)
    else:
        tela.save(dst)
    return {"percorso": str(dst), "larghezza": tela.width, "altezza": tela.height,
            "colonne": colonne, "righe": righe, "celle": len(frames)}


def _tavolozza_comune(frames: list[Image.Image]) -> Image.Image:
    """Una sola palette per tutta l'animazione, ricavata da tutti i frame.

    Quantizzare ogni frame per conto suo darebbe palette diverse, e con esse
    indici diversi: l'indice dichiarato trasparente in testa al file varrebbe
    per il primo frame e indicherebbe un colore qualsiasi negli altri.
    """
    n = len(frames)
    strisca = Image.new("RGB", (frames[0].width, frames[0].height * n))
    for i, f in enumerate(frames):
        strisca.paste(f.convert("RGB"), (0, i * frames[0].height))
    # 255 colori: il 256esimo resta libero per la trasparenza.
    return strisca.quantize(colors=_INDICE_TRASPARENTE, method=Image.MEDIANCUT)


def _gif_trasparente(rgba: Image.Image, tavolozza: Image.Image) -> Image.Image:
    """Un frame RGBA in modalita' P, con i pixel trasparenti su un indice suo."""
    p = rgba.convert("RGB").quantize(palette=tavolozza, dither=Image.Dither.NONE)
    # Soglia netta: la GIF non ha mezze misure, e sotto meta' alfa il pixel
    # appartiene piu' allo sfondo che al soggetto.
    maschera = rgba.getchannel("A").point(lambda v: 255 if v < 128 else 0)
    p.paste(_INDICE_TRASPARENTE, maschera)
    return p


def _delay_centesimi(fps: float) -> tuple[int, float]:
    """Delay intero in centesimi e fps realmente ottenuto."""
    cs = max(2, round(100.0 / max(fps, 0.01)))   # sotto 2cs i browser rallentano
    return cs, round(100.0 / cs, 3)


## Indice della palette riservato alla trasparenza. La GIF ha 256 colori: se ne
## cede uno e si quantizza il resto su 255, cosi' nessun colore del soggetto
## puo' finire sull'indice trasparente e bucare lo sprite.
_INDICE_TRASPARENTE = 255


def componi_gif(frames: list[Image.Image], fps: float, lato: int,
                dst: str | Path, sfondo: tuple | None = None) -> dict:
    """GIF in loop infinito.

    La GIF non ha un canale alfa come il PNG: ha un solo indice di palette
    dichiarato trasparente, tutto o niente per pixel. Con `sfondo=None` si usa
    quello; passando un colore si appiattisce su di esso, che serve quando la
    GIF va incollata dove la trasparenza non e' gradita.
    """
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cs, fps_reale = _delay_centesimi(fps)

    if sfondo is not None:
        piatti = []
        for f in frames:
            base = Image.new("RGBA", f.size, tuple(sfondo) + (255,))
            base.alpha_composite(f.convert("RGBA"))
            piatti.append(_ridimensiona(base, lato).convert("RGB"))
        piatti[0].save(dst, save_all=True, append_images=piatti[1:],
                       duration=cs * 10, loop=0, optimize=True, disposal=2)
    else:
        scalati = [_ridimensiona(f.convert("RGBA"), lato) for f in frames]
        tavolozza = _tavolozza_comune(scalati)
        piatti = [_gif_trasparente(f, tavolozza) for f in scalati]
        # `optimize=True` rimappa la palette per risparmiare byte e sposta
        # l'indice trasparente, che qui e' l'unica cosa che non deve muoversi.
        piatti[0].save(dst, save_all=True, append_images=piatti[1:],
                       duration=cs * 10, loop=0,
                       transparency=_INDICE_TRASPARENTE, disposal=2)
    return {
        "percorso": str(dst), "frame": len(piatti), "lato": lato,
        "delay_ms": cs * 10, "fps_richiesto": round(fps, 2),
        "fps_reale": fps_reale,
        "durata_s": round(len(piatti) * cs / 100.0, 3),
    }


def taglia_da_sheet(src: str | Path, colonne: int, righe: int,
                    n_frame: int) -> list[Image.Image]:
    """Estrae i frame da uno sprite sheet gia' pronto. Serve per rigenerare
    la GIF senza rifare l'inferenza."""
    im = Image.open(src).convert("RGBA")
    cw, ch = im.width // colonne, im.height // righe
    out = []
    for i in range(min(n_frame, colonne * righe)):
        r, c = divmod(i, colonne)
        out.append(im.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)))
    return out
