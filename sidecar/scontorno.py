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

## Sfondo a tinta scelta (0.0.4)

Quanto sopra vale per uno **sfondo chiaro**. Chi lavora con un green screen,
o con un fondo magenta, ha un problema diverso: il fondo non e' il colore piu'
chiaro dell'immagine, e' *un* colore preciso in mezzo agli altri. Li' si passa
per `_alfa_tinta`, che lavora a **due soglie**:

    stretta   questo e' il colore pieno del fondo, senza dubbio
    larga     fin qui il fondo puo' arrivare, sfumando

Una regione entro la soglia larga e' sfondo **se contiene almeno un pixel
entro quella stretta**. Le isole vengono da qui, ed e' il punto in cui e'
facile sbagliare in due modi opposti:

  isola di sfondo    il verde chiuso fra la testa e la coda di cavallo, o fra
                     un braccio e il fianco: non tocca il bordo dell'immagine
                     ma e' sfondo a tutti gli effetti, e va tolto;
  isola di soggetto  un pixel d'oro che per caso somiglia al verde: e'
                     soggetto, e va tenuto anche se sta in mezzo al fondo.

Una prima versione decideva per **vicinanza al bordo** dell'immagine. Sbagliata
in pieno: su sedici fogli di prova lasciava opache 524 regioni per 27.211
pixel, tutte fra i capelli e il collo, sotto le ascelle e dentro gli intrecci
dei sandali. Quello che distingue il fondo da un pixel che gli somiglia non e'
*dove sta*, e' **di che colore e' fatto**: la presenza del seme lo dice gia'.

L'alfa non e' binaria. Sul contorno il pixel e' una miscela di soggetto e
fondo: si stima quanto e' fondo e quello diventa la trasparenza. Con l'alfa
binaria la sagoma e' seghettata e un lembo sottile di stoffa perde una fila di
pixel a ogni fotogramma, cioe' sfarfalla nell'animazione.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

# Preset offerti dall'interfaccia. Non sono vincolanti: l'utente puo' passare
# qualunque colore, e "auto" li rende quasi sempre inutili.
PRESET = {
    "verde": (0, 177, 64),      # chroma key standard
    "magenta": (255, 0, 255),
    "blu": (0, 71, 187),
    "bianco": (255, 255, 255),
    "nero": (0, 0, 0),
}


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


def _tinta_angoli(a: np.ndarray) -> np.ndarray:
    """Il colore del fondo, misurato sui quattro angoli.

    Misurato e non scelto: lo stesso green screen esce a 0,177,64 da un
    programma e a 62,171,82 da un altro, e una costante scritta a mano sbaglia
    di poco tutte le volte.
    """
    q = 6
    ang = np.concatenate([a[:q, :q].reshape(-1, 3), a[:q, -q:].reshape(-1, 3),
                          a[-q:, :q].reshape(-1, 3), a[-q:, -q:].reshape(-1, 3)])
    return np.median(ang, 0)


def risolvi_colore(spec, a: np.ndarray) -> np.ndarray:
    """Da quello che arriva dall'interfaccia a una terna RGB.

    Accetta: `"auto"`, un nome di `PRESET`, `"#RRGGBB"`, `"r,g,b"` o gia' una
    sequenza di tre numeri.
    """
    if spec is None or spec == "" or spec == "auto":
        return _tinta_angoli(a)
    if isinstance(spec, (list, tuple)) and len(spec) == 3:
        return np.array([float(x) for x in spec])
    s = str(spec).strip().lower()
    if s in PRESET:
        return np.array(PRESET[s], float)
    if s.startswith("#") and len(s) == 7:
        return np.array([int(s[i:i + 2], 16) for i in (1, 3, 5)], float)
    if "," in s:
        parti = [p.strip() for p in s.split(",")]
        if len(parti) == 3:
            return np.array([float(p) for p in parti])
    raise ValueError("colore non riconosciuto: %r" % spec)


def aggancia_tinta(a: np.ndarray, tinta: np.ndarray,
                   raggio: float = 110.0) -> np.ndarray:
    """Sposta la tinta chiesta su quella che l'immagine ha davvero.

    Il preset "verde" vale (0,177,64), ma un green screen reale esce a
    (64,173,84): 67 di distanza, abbastanza da non trovare un solo pixel entro
    la soglia stretta e far fallire tutto. Senza questo passaggio i preset
    sarebbero decorativi e l'unica opzione utile resterebbe "auto".

    L'utente dice **quale colore** e' il fondo; qual e' esattamente quel colore
    lo misura il programma, sui pixel che gli somigliano piu' di `raggio`.
    """
    d = np.sqrt(((a.astype(np.float32) - tinta) ** 2).sum(2))
    vicini = d < raggio
    if vicini.sum() < 64:
        return tinta
    return np.median(a[vicini], axis=0).astype(np.float32)


def _alfa_tinta(a: np.ndarray, tinta: np.ndarray, larga: float) -> np.ndarray:
    """Alfa in 0..1 per uno sfondo a tinta unita. 0 fondo, 1 soggetto.

    Vedi l'intestazione del modulo per il perche' delle due soglie e per
    l'errore sulle isole che questa versione corregge.
    """
    stretta = max(4.0, larga * 0.4)
    d = np.sqrt(((a.astype(np.float32) - tinta) ** 2).sum(2))

    seme = d < stretta
    if not seme.any():
        # Nessun pixel e' davvero di quel colore: lo sfondo chiesto non c'e'.
        # Meglio restituire tutto opaco che bucare l'immagine a caso.
        return np.ones(a.shape[:2], np.float32)

    et, n = ndimage.label(d < larga)
    # Una regione e' fondo se contiene del colore pieno. Il bordo dell'immagine
    # non c'entra: e' l'errore che lasciava opaco il verde fra testa e coda.
    vere = np.zeros(n + 1, bool)
    vere[1:] = ndimage.sum_labels(seme, et, np.arange(1, n + 1)) > 0
    fondo = vere[et]

    # Dentro il fondo l'alfa sfuma fra le due soglie: il contorno resta morbido.
    sfuma = np.clip((d - stretta) / max(1e-6, larga - stretta), 0.0, 1.0)
    return np.where(fondo, sfuma, 1.0).astype(np.float32)


def _togli_spill(a: np.ndarray, tinta: np.ndarray) -> np.ndarray:
    """Lo sputo di colore che il fondo riflette sul contorno del soggetto.

    Si corregge solo sul canale dominante della tinta di fondo, riportandolo
    alla media degli altri due. Su un verde il blu e il rosso non si toccano,
    quindi un vestito blu e un bordo dorato restano quelli che erano.
    """
    canale = int(np.argmax(tinta))
    altri = [i for i in (0, 1, 2) if i != canale]
    c = a[:, :, canale]
    m = (a[:, :, altri[0]].astype(np.int16) + a[:, :, altri[1]]) // 2
    domina = c > np.maximum(a[:, :, altri[0]], a[:, :, altri[1]])
    fuori = a.copy()
    fuori[:, :, canale] = np.where(domina, m, c)
    return fuori


def _scontorna_tinta(im: Image.Image, a: np.ndarray, tinta: np.ndarray,
                     larga: float, togli_spill: bool) -> Image.Image:
    tinta = aggancia_tinta(a, tinta)
    alfa = _alfa_tinta(a, tinta, larga)
    rgb = _togli_spill(a, tinta) if togli_spill else a
    fuori = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8),
                       (alfa * 255).astype(np.uint8)])
    return Image.fromarray(fuori, "RGBA")


def _via_tinta(colore, tinta: np.ndarray) -> bool:
    """True se lo scontorno passa per la via a tinta, False se resta sulla
    via storica per fondi chiari. Una funzione sola perche' la usano sia lo
    scontorno sia `diagnosi`: il log deve dire la via che e' stata presa
    davvero, non una ricostruzione che puo' divergere."""
    esplicito = not (colore is None or colore == "" or colore == "auto")
    return esplicito or tinta.min() <= 225


def _esadecimale(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(round(float(c))) for c in rgb)


def diagnosi(im: Image.Image, colore: object = "auto",
             tolleranza_tinta: int = 66, togli_spill: bool = True) -> dict:
    """Cosa farebbe lo scontorno su questa immagine, senza farlo.

    Serve al log di generazione: quando un'animazione esce con il fondo
    rimasto o con il soggetto bucato, la prima cosa da sapere e' quale colore
    e' stato tolto e per quale via.
    """
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    tinta = risolvi_colore(colore, a)
    via_tinta = _via_tinta(colore, tinta)
    misurata = aggancia_tinta(a, tinta) if via_tinta else tinta
    return {
        "colore": "auto" if colore in (None, "") else str(colore),
        "via": "tinta" if via_tinta else "chiaro",
        "tinta_richiesta": _esadecimale(tinta),
        "tinta_misurata": _esadecimale(misurata),
        "tolleranza_tinta": int(tolleranza_tinta),
        "togli_spill": bool(togli_spill) and via_tinta,
    }


def scontorna_immagine(
    im: Image.Image,
    tolleranza: int = 225,
    area_min: int = 200,
    rimuovi_ombra: bool = True,
    saturazione_min: int = 45,
    soglia_scuro: int = 140,
    buchi_trasparenti: bool = True,
    tolleranza_buco: int = 10,
    colore: object = "auto",
    tolleranza_tinta: int = 66,
    togli_spill: bool = True,
) -> Image.Image:
    """Come `scontorna`, ma su un'immagine gia' in memoria.

    Serve ai frame generati: sono decine per animazione e passare da file
    temporanei significherebbe scrivere e rileggere centinaia di MB per niente.

    colore             "auto" (misurato dagli angoli), un nome di PRESET,
                       "#RRGGBB" o "r,g,b". Su "auto" con fondo quasi bianco
                       si usa la via storica, che sa togliere anche le ombre
    tolleranza_tinta   raggio della soglia larga, solo per la via a tinta
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

    # Due vie, e la scelta e' esplicita invece che indovinata a meta' strada.
    #
    # La via storica e' tarata su sfondo chiaro e sa fare una cosa che l'altra
    # non fa: separare l'ombra morbida sotto il soggetto, che tocca il
    # soggetto ed e' grigia. La via a tinta sa fare quello che serve a un
    # green screen. Su "auto" si guarda il colore misurato: se e' quasi bianco
    # si resta sulla via collaudata, altrimenti si passa all'altra.
    tinta = risolvi_colore(colore, a)
    if _via_tinta(colore, tinta):
        return _scontorna_tinta(im, a, tinta, float(tolleranza_tinta),
                                togli_spill)

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
    colore: object = "auto",
    tolleranza_tinta: int = 66,
) -> dict:
    """Scrive `dst` (PNG RGBA) e restituisce statistiche."""
    src, dst = Path(src), Path(dst)
    im = Image.open(src)
    rgba = scontorna_immagine(im, tolleranza, area_min, rimuovi_ombra,
                              saturazione_min, soglia_scuro,
                              colore=colore, tolleranza_tinta=tolleranza_tinta)
    dst.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(dst)

    a = np.asarray(im.convert("RGB")).astype(np.int16)
    tinta = aggancia_tinta(a, risolvi_colore(colore, a))
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
        # Quale colore e' stato tolto davvero: su "auto" e' l'unico modo che
        # ha l'utente di sapere cosa ha misurato il programma, e quando il
        # risultato non torna e' la prima cosa da guardare.
        "colore_sfondo": "#%02X%02X%02X" % tuple(int(c) for c in tinta),
        # Quanti pixel hanno alfa intermedia: e' il contorno sfumato. Se e'
        # zero la soglia e' troppo stretta, se e' enorme e' troppo larga.
        "bordo_sfumato_pct": round(100 * float(((al > 8) & (al < 247)).mean()), 2),
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

    # Il colore che il programma proporrebbe, e quanto e' d'accordo con se'
    # stesso: se i quattro angoli non concordano, lo sfondo non e' a tinta
    # unita e l'utente deve saperlo prima di premere, non dopo.
    tinta = _tinta_angoli(rgb)
    scarto = max(float(np.abs(np.array(c, float) - tinta).max()) for c in angoli)

    return {
        "larghezza": im.width,
        "altezza": im.height,
        "quadrata": im.width == im.height,
        "formato": im.format,
        "ha_canale_alfa": ha_alfa,
        "colore_sfondo": "#%02X%02X%02X" % tuple(int(c) for c in tinta),
        "sfondo_tinta_unita": bool(scarto <= 12),
        "scarto_angoli": round(scarto, 1),
        "trasparenti_pct": trasparenti,
        # se gli angoli sono quasi bianchi lo sfondo e' probabilmente pieno
        "sfondo_uniforme_chiaro": bool(all(c.min() > 225 for c in angoli)),
    }
