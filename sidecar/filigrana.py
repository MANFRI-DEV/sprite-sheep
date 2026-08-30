"""Filigrana dell'edizione free: una lettera per frame, in basso a destra.

Su un singolo frame si vede una lettera sola; chi guarda l'animazione intera
legge "CREATED-WITH-SPRITESHEEP!" scorrere lettera dopo lettera, e chi estrae i
frame dal foglio se li porta dietro tutti.

Scelte:
  - lettera nel quadrante in basso a destra, alta meta' del lato: occupa
    esattamente quel quarto di immagine, in altezza e in larghezza;
  - colore casuale a ogni frame, cosi' non basta filtrare una tinta sola;
  - opacita' 60%: si vede bene, e a quella dimensione non copre lo sprite;
  - si lavora su copie, i frame originali non vengono toccati. L'edizione senza
    filigrana non richiede altro che saltare questa chiamata.

Il compromesso e' dichiarato: in un angolo si ritaglia via piu' facilmente di
quanto facesse la lettera al centro. A meta' del lato pero' e' abbastanza
grande da rendere il ritaglio una perdita visibile, e il soggetto al centro
resta leggibile.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Font di sistema, in ordine di preferenza, per Windows e per Linux/macOS.
# Se non c'e' nulla si usa il font incorporato in Pillow: brutto ma sempre
# presente, e una filigrana brutta e' meglio di una filigrana assente.
_CANDIDATI = [
    # Windows
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\consolab.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]

QUOTA_LATO = 0.50     # altezza della lettera rispetto al lato del frame
ALFA = 153            # 60% di 255

## Centro del quadrante in basso a destra. Con la lettera alta meta' del lato,
## 0.75 la fa combaciare col quadrante: da meta' immagine al bordo, sia in
## altezza sia in larghezza.
CENTRO_X = 0.75
CENTRO_Y = 0.75


def _percorso_font() -> str | None:
    for p in _CANDIDATI:
        if Path(p).exists():
            return p
    return None


def _font_per(lettera: str, lato: int) -> ImageFont.ImageFont:
    """Font della dimensione che porta la lettera a `QUOTA_LATO` del lato.

    La dimensione in punti non coincide con l'altezza resa: si parte da una
    stima e si corregge misurando il glifo vero, altrimenti lettere strette
    come "I" e larghe come "W" verrebbero di altezze diverse.
    """
    percorso = _percorso_font()
    voluta = lato * QUOTA_LATO
    if percorso is None:
        return ImageFont.load_default()

    dim = max(8, int(voluta))
    for _ in range(6):
        f = ImageFont.truetype(percorso, dim)
        box = f.getbbox(lettera)
        alta = box[3] - box[1]
        if alta <= 0:
            return f
        if abs(alta - voluta) <= max(1.0, voluta * 0.02):
            return f
        dim = max(8, int(dim * voluta / alta))
    return ImageFont.truetype(percorso, dim)


def _colore(rng: random.Random) -> tuple:
    """Tinta satura a caso: sempre leggibile, mai grigia."""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(rng.random(), 0.85, 1.0)
    return int(r * 255), int(g * 255), int(b * 255), ALFA


def applica(frames: list[Image.Image], testo: str,
            seme: int | None = None) -> list[Image.Image]:
    """Una lettera per frame, in sequenza ciclica. Restituisce nuove immagini."""
    if not frames or not testo:
        return frames

    rng = random.Random(seme)
    lato = min(frames[0].size)

    fuori = []
    for i, f in enumerate(frames):
        im = f.convert("RGBA").copy()
        lettera = testo[i % len(testo)]
        font = _font_per(lettera, lato)

        velo = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(velo)
        box = d.textbbox((0, 0), lettera, font=font)
        lc, la = box[2] - box[0], box[3] - box[1]
        # Il glifo si centra sul punto voluto sottraendo il proprio riquadro:
        # `textbbox` non parte da zero, e ignorarlo sposta ogni lettera di una
        # quantita' diversa.
        x = int(im.width * CENTRO_X - lc / 2) - box[0]
        y = int(im.height * CENTRO_Y - la / 2) - box[1]
        # Nessuna lettera deve uscire dal frame, nemmeno la piu' larga.
        x = max(0, min(x, im.width - lc - box[0]))
        y = max(0, min(y, im.height - la - box[1]))
        d.text((x, y), lettera, font=font, fill=_colore(rng))

        fuori.append(Image.alpha_composite(im, velo))
    return fuori
