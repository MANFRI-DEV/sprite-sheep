"""Ricava l'icona dell'applicazione dal PNG della pecora.

Produce due file:
  godot/icon.png   256x256, usato da Godot come icona del progetto
  godot/icona.ico  multi-risoluzione, incorporato nell'eseguibile Windows

Lo sprite sorgente ha lo sfondo bianco pieno e molta aria attorno al soggetto:
un'icona ritagliata cosi' diventa una pecora minuscola dentro un quadrato
bianco. Qui lo sfondo si toglie, si ritaglia sul soggetto e si riempie il
quadrato lasciando un margine.

Si rilancia quando cambia lo sprite:
    python build_icona.py
"""
import sys
from pathlib import Path

from PIL import Image

RADICE = Path(__file__).resolve().parent
SORGENTE = RADICE / "godot" / "sprites" / "sprite_sheep_trasparente.png"
PNG = RADICE / "godot" / "icon.png"
ICO = RADICE / "godot" / "icona.ico"

## Windows rimpicciolisce l'icona fino a 16 px nella barra delle applicazioni:
## sotto quella misura i dettagli spariscono, ma la sagoma resta riconoscibile.
MISURE = [256, 128, 64, 48, 32, 24, 16]
MARGINE = 0.06   # aria attorno al soggetto, in frazione del lato

if not SORGENTE.exists():
    sys.exit("manca %s: esegui prima lo scontorno dello sprite" % SORGENTE)

im = Image.open(SORGENTE).convert("RGBA")
taglio = im.getbbox()          # riquadro dei pixel non trasparenti
if taglio is None:
    sys.exit("lo sprite e' completamente trasparente")
sog = im.crop(taglio)
print("sorgente %dx%d -> soggetto %dx%d" % (im.width, im.height, sog.width, sog.height))

# Tela quadrata: il soggetto e' piu' largo che alto e non va deformato.
lato = int(max(sog.size) * (1 + 2 * MARGINE))
tela = Image.new("RGBA", (lato, lato), (0, 0, 0, 0))
tela.alpha_composite(sog, ((lato - sog.width) // 2, (lato - sog.height) // 2))

grande = tela.resize((256, 256), Image.LANCZOS)
grande.save(PNG)
print("scritto %s (256x256)" % PNG.name)

# Ogni misura viene ridotta a parte: lasciare fare a save() produce riduzioni
# piu' grossolane alle dimensioni piccole, dove servirebbe il contrario.
livelli = [tela.resize((n, n), Image.LANCZOS) for n in MISURE]
livelli[0].save(ICO, format="ICO",
                sizes=[(n, n) for n in MISURE],
                append_images=livelli[1:])
print("scritto %s (%s)" % (ICO.name, ", ".join("%dx%d" % (n, n) for n in MISURE)))
print("peso ico: %.1f KB" % (ICO.stat().st_size / 1024))
