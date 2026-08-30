"""Rimozione dello sfondo da uno sprite sorgente.

Algoritmo validato sul campo (pecora, cane, lupo, pesce). Due punti chiave,
entrambi nati da fallimenti concreti:

1. Non si sogliano i pixel chiari e basta: si tolgono solo quelli **collegati
   al bordo**. Un soggetto bianco (la lana della pecora, il petto del cane)
   verrebbe altrimenti bucato dall'interno.

2. Le ombre morbide sotto il soggetto lo toccano, quindi "tieni la componente
   piu' grande" se le porta dietro. Si separano per **saturazione**: il
   soggetto e' colorato, l'ombra e' grigia neutra. Occhi e zone chiare interne
   si recuperano con `binary_fill_holes`, perche' sono racchiusi dalla sagoma
   mentre l'ombra sta fuori.

3. `binary_fill_holes` pero' riempie anche i buchi che sono sfondo davvero: il
   triangolo fra un braccio sul fianco e il corpo, lo spazio fra le gambe
   divaricate. Restavano bianchi dentro uno sprite altrimenti trasparente.
   Si distinguono per colore: un buco che ha **lo stesso identico colore dello
   sfondo esterno** e' sfondo rimasto intrappolato, mentre gli occhi e la lana
   crema di un soggetto chiaro hanno comunque una tinta loro. Il confronto e'
   stretto di proposito: sbagliare da questo lato lascia una macchia bianca,
   sbagliare dall'altro buca il soggetto.

rembg/u2net e' stato provato e scartato: su disegni con contorni netti lascia
un alone sfocato largo decine di pixel.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


def _componenti_al_bordo(maschera: np.ndarray) -> np.ndarray:
    """Etichetta la maschera e tiene solo i blob che toccano il bordo."""
    lab, _ = ndimage.label(maschera)
    bordo = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    bordo.discard(0)
    return np.isin(lab, list(bordo))


def _scarta_isolotti(maschera: np.ndarray, area_min: int) -> np.ndarray:
    lab, n = ndimage.label(maschera)
    if not n:
        return maschera
    aree = ndimage.sum(maschera, lab, range(1, n + 1))
    piccoli = [i + 1 for i, s in enumerate(aree) if s < area_min]
    if piccoli:
        maschera = maschera & ~np.isin(lab, piccoli)
    return maschera


def _buchi_di_sfondo(a: np.ndarray, fg: np.ndarray, sfondo: np.ndarray,
                     tolleranza: int) -> np.ndarray:
    """Pixel interni alla sagoma che sono sfondo rimasto intrappolato.

    Il colore dello sfondo non si assume bianco: si misura da quello vero,
    perche' un frame generato puo' averlo su 252 o 254 e una soglia fissa
    sbaglierebbe in un verso o nell'altro.
    """
    if not sfondo.any():
        return np.zeros_like(fg)
    tinta = np.median(a[sfondo], axis=0)
    # Distanza dal colore di sfondo, sul canale che si scosta di piu':
    # una media nasconderebbe uno scarto forte su un canale solo.
    scarto = np.abs(a - tinta).max(axis=2)
    return fg & (scarto <= tolleranza)


def scontorna_immagine(
    im: Image.Image,
    tolleranza: int = 225,
    area_min: int = 200,
    rimuovi_ombra: bool = True,
    saturazione_min: int = 45,
    soglia_scuro: int = 140,
    buchi_trasparenti: bool = True,
    tolleranza_buco: int = 10,
) -> Image.Image:
    """Come `scontorna`, ma su un'immagine gia' in memoria.

    Serve ai frame generati: sono decine per animazione e passare da file
    temporanei significherebbe scrivere e rileggere centinaia di MB per niente.

    tolleranza         sopra questo valore su tutti i canali = candidato sfondo
    rimuovi_ombra      separa per saturazione, togliendo le ombre morbide grigie
    buchi_trasparenti  svuota i buchi racchiusi dalla sagoma che hanno il colore
                       dello sfondo (braccio sul fianco, gambe divaricate)
    tolleranza_buco    quanto un buco puo' scostarsi dal colore dello sfondo e
                       contare ancora come sfondo. Stretto: la lana crema di un
                       soggetto chiaro sta a ~15 da un bianco puro e va salvata
    """
    im = im.convert("RGB")
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    sat = a.max(2) - a.min(2)
    val = a.max(2)

    chiaro = (r > tolleranza) & (g > tolleranza) & (b > tolleranza)
    sfondo = _componenti_al_bordo(chiaro)

    if rimuovi_ombra:
        # nucleo = colore saturo oppure contorno scuro; l'ombra grigia chiara
        # non rientra in nessuno dei due
        core = (~sfondo) & ((sat >= saturazione_min) | (val < soglia_scuro))
        core = _scarta_isolotti(core, area_min)
        lab, n = ndimage.label(core)
        if n > 1:
            aree = ndimage.sum(core, lab, range(1, n + 1))
            core = lab == int(np.argmax(aree)) + 1
        fg = ndimage.binary_fill_holes(core)
    else:
        fg = _scarta_isolotti(~sfondo, area_min)

    if buchi_trasparenti:
        fg = fg & ~_buchi_di_sfondo(a, fg, sfondo, tolleranza_buco)

    alpha = Image.fromarray(np.where(fg, 255, 0).astype(np.uint8)) \
                 .filter(ImageFilter.GaussianBlur(0.6))
    rgba = im.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def scontorna(
    src: str | Path,
    dst: str | Path,
    tolleranza: int = 225,
    area_min: int = 200,
    rimuovi_ombra: bool = True,
    saturazione_min: int = 45,
    soglia_scuro: int = 140,
) -> dict:
    """Scrive `dst` (PNG RGBA) e restituisce statistiche."""
    src, dst = Path(src), Path(dst)
    im = Image.open(src)
    rgba = scontorna_immagine(im, tolleranza, area_min, rimuovi_ombra,
                              saturazione_min, soglia_scuro)
    dst.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(dst)

    al = np.asarray(rgba.getchannel("A"))
    return {
        "sorgente": str(src),
        "destinazione": str(dst),
        "larghezza": rgba.width,
        "altezza": rgba.height,
        "quadrata": rgba.width == rgba.height,
        "opachi_pct": round(100 * float((al > 8).mean()), 2),
        "trasparenti_pct": round(100 * float((al < 8).mean()), 2),
        "ombra_rimossa": rimuovi_ombra,
    }


def analizza(src: str | Path) -> dict:
    """Ispezione senza modificare nulla: serve all'UI per avvisare l'utente."""
    im = Image.open(src)
    ha_alfa = im.mode in ("RGBA", "LA") or "transparency" in im.info
    trasparenti = 0.0
    if ha_alfa:
        al = np.asarray(im.convert("RGBA"))[:, :, 3]
        trasparenti = round(100 * float((al < 8).mean()), 2)
    rgb = np.asarray(im.convert("RGB")).astype(np.int16)
    angoli = [rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]]
    return {
        "larghezza": im.width,
        "altezza": im.height,
        "quadrata": im.width == im.height,
        "formato": im.format,
        "ha_canale_alfa": ha_alfa,
        "trasparenti_pct": trasparenti,
        # se gli angoli sono quasi bianchi lo sfondo e' probabilmente pieno
        "sfondo_uniforme_chiaro": bool(all(c.min() > 225 for c in angoli)),
    }
