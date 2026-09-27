"""Scontorno su immagini sintetiche con la risposta nota. Niente GPU.

Ogni caso riproduce un fallimento visto sul campo: il green screen che non
e' il verde del preset, il verde chiuso fra testa e coda, l'ombra grigia su
fondo bianco, il soggetto crema su fondo bianco.

    python sidecar/test_scontorno.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import scontorno as S

errori: list[str] = []
VERDE_VERO = (64, 173, 84)


def verifica(cond, msg):
    if not cond:
        errori.append(msg)


def alfa(im) -> np.ndarray:
    return np.asarray(im.getchannel("A"))


def main() -> int:
    # --- risolvi_colore -------------------------------------------------------
    a = np.zeros((20, 20, 3), np.int16)
    verifica(tuple(S.risolvi_colore("#102030", a)) == (16, 32, 48), "esadecimale")
    verifica(tuple(S.risolvi_colore("1, 2, 3", a)) == (1, 2, 3), "terna")
    verifica(tuple(S.risolvi_colore([4, 5, 6], a)) == (4, 5, 6), "lista")
    verifica(tuple(S.risolvi_colore("verde", a)) == tuple(S.PRESET["verde"]), "preset")
    for sbagliato in ("#12", "rosso-fuoco", "1,2"):
        try:
            S.risolvi_colore(sbagliato, a)
            errori.append("colore %r accettato" % sbagliato)
        except ValueError:
            pass

    # --- green screen vero con il preset "verde" ------------------------------
    # Il preset e' lontano dal verde reale: aggancia_tinta deve trovarlo.
    im = Image.new("RGB", (200, 200), VERDE_VERO)
    d = ImageDraw.Draw(im)
    d.rectangle((60, 40, 139, 179), fill=(200, 40, 40))      # corpo
    d.rectangle((90, 90, 109, 109), fill=VERDE_VERO)          # buco chiuso nel corpo
    r = S.scontorna_immagine(im, colore="verde")
    al = alfa(r)
    verifica(al[5, 5] == 0 and al[195, 195] == 0, "fondo verde non tolto")
    verifica(al[60, 100] == 255 and al[170, 70] == 255, "corpo bucato")
    verifica(al[100, 100] == 0, "verde chiuso nel corpo rimasto opaco")
    dg = S.diagnosi(im, "verde")
    verifica(dg["via"] == "tinta" and dg["tinta_misurata"] == "#40ad54",
             "diagnosi: %s" % dg)

    # --- spill: il bordo verdastro torna neutro, il blu non si tocca ----------
    sp = Image.new("RGB", (100, 100), VERDE_VERO)
    ImageDraw.Draw(sp).rectangle((30, 30, 69, 69), fill=(120, 160, 120))   # grigio verdastro
    ImageDraw.Draw(sp).rectangle((40, 40, 59, 59), fill=(30, 40, 200))     # blu
    rs = np.asarray(S.scontorna_immagine(sp, colore="verde"))
    g = rs[35, 35]
    verifica(g[1] <= max(g[0], g[2]) + 1 and rs[35, 35, 3] == 255, "spill non tolto: %s" % g)
    verifica(tuple(rs[50, 50, :3]) == (30, 40, 200), "blu alterato dallo spill")
    senza = np.asarray(S.scontorna_immagine(sp, colore="verde", togli_spill=False))
    verifica(tuple(senza[35, 35, :3]) == (120, 160, 120), "togli_spill=False ignorato")

    # --- fondo bianco: via storica, ombra grigia via, soggetto crema salvo ----
    bi = Image.new("RGB", (200, 200), (255, 255, 255))
    d = ImageDraw.Draw(bi)
    d.ellipse((50, 160, 150, 185), fill=(215, 215, 215))       # ombra morbida grigia
    d.rectangle((70, 40, 129, 165), fill=(240, 228, 200))      # lana crema
    d.rectangle((70, 40, 129, 165), outline=(40, 30, 20), width=3)
    rb = S.scontorna_immagine(bi)
    ab = alfa(rb)
    verifica(S.diagnosi(bi)["via"] == "chiaro", "fondo bianco non sulla via storica")
    verifica(ab[5, 5] == 0, "bianco non tolto")
    verifica(ab[100, 100] > 200, "soggetto crema bucato")
    verifica(ab[178, 60] < 50, "ombra grigia rimasta")

    # --- fondo bianco: occhio bianco racchiuso resta, buco grande si svuota --
    # Il bianco degli occhi e' bianco quanto il fondo: prima veniva svuotato
    # pixel per pixel, e la pecora di esempio aveva gli occhi neri.
    oc = Image.new("RGB", (300, 300), (255, 255, 255))
    d = ImageDraw.Draw(oc)
    d.rectangle((40, 40, 259, 259), fill=(200, 60, 60), outline=(0, 0, 0), width=4)
    d.ellipse((70, 70, 90, 90), fill=(255, 255, 255), outline=(0, 0, 0), width=2)   # occhio
    d.rectangle((140, 120, 230, 230), fill=(255, 255, 255), outline=(0, 0, 0), width=4)  # buco
    ao = alfa(S.scontorna_immagine(oc))
    verifica(ao[80, 80] == 255, "occhio bianco svuotato")
    verifica(ao[175, 185] == 0, "buco grande rimasto opaco")
    pecora = Path(__file__).parent.parent / "godot" / "sprites" / "sprite_sheep.png"
    if pecora.is_file():
        im_p = Image.open(pecora).convert("RGB")
        ap = alfa(S.scontorna_immagine(im_p))
        a_p = np.asarray(im_p).astype(np.int16)
        bianchi = (a_p > 245).all(2)
        interni = bianchi & ~S._componenti_al_bordo(bianchi)
        salvi = float((ap[interni] > 128).mean())
        verifica(salvi > 0.95, "pecora di esempio: bianchi interni salvi solo al %.0f%%"
                 % (100 * salvi))

    # --- nessun pixel del colore chiesto: tutto opaco, non bucato a caso ------
    blu = Image.new("RGB", (60, 60), (20, 20, 220))
    verifica(alfa(S.scontorna_immagine(blu, colore="verde")).min() == 255,
             "sfondo assente: immagine bucata")

    # --- analizza: angoli discordi = fondo non a tinta unita -------------------
    tmp = Path(__file__).parent / "_prova_analizza.png"
    mista = Image.new("RGB", (40, 40), (255, 255, 255))
    ImageDraw.Draw(mista).rectangle((0, 0, 9, 9), fill=(0, 0, 0))
    mista.save(tmp)
    try:
        info = S.analizza(tmp)
        verifica(not info["sfondo_tinta_unita"], "angoli discordi non segnalati")
        verifica(info["quadrata"] and not info["ha_canale_alfa"], "analizza: %s" % info)
    finally:
        tmp.unlink(missing_ok=True)

    for e in errori:
        print("ERRORE:", e)
    print("tutto a posto" if not errori else f"{len(errori)} errori")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
