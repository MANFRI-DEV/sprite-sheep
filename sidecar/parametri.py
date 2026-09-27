"""Conversione fra parametri utente e parametri del modello.

L'utente ragiona in secondi e numero di frame dello sprite sheet. I modelli
invece accettano solo certe lunghezze: H3 vuole 17k+5, i Wan 4n+1. Qui sta
la traduzione, con i valori arrotondati al primo valido utile.

La quota utile (`FRAZIONE_UTILE`) e' l'altra lezione sul campo: campionando
fino in fondo alla clip il ritorno alla posa iniziale cade negli ultimi frame,
che spesso il modello usa per assestarsi. Si campiona la parte iniziale.
"""
import math

DURATA_MIN = 2.0
DURATA_MAX = 10.0
FRAME_MIN = 4
FRAME_MAX = 64

# Si campiona solo l'inizio della clip: la coda serve al modello per chiudere
FRAZIONE_UTILE = 0.85

# Regole per modello: passo e offset della lunghezza valida, piu' gli fps
REGOLE = {
    "minimax_h3_fl2va": {"fps": 24, "passo": 17, "offset": 5, "max": 362},
    # FastH3 e' lo stesso modello distillato: stesse lunghezze valide, stessi
    # fps. Cambia solo quanti passi di campionamento servono, che e' una cosa
    # del backend e non della geometria della clip.
    "minimax_h3_fast":  {"fps": 24, "passo": 17, "offset": 5, "max": 362},
    "wan22_ti2v_5b":    {"fps": 24, "passo": 4,  "offset": 1, "max": 241},
}


## Formati della clip generata, larghezza x altezza in pixel.
##
## Sono i sei rapporti per cui H3 dichiara supporto. L'area resta vicina a
## 448x448 (~200 mila pixel), che e' il budget provato sugli 8 GB della RTX
## 3050: un 16:9 alla risoluzione nativa di H3 (1344x768) ne costerebbe cinque
## volte tanto. Lati multipli di 32, come vogliono sia H3 sia WAN 2.2.
##
## I rapporti sono approssimati dove il 32 non lo consente (9:16 esce 0,556
## invece di 0,5625): non importa, perche' lo sprite viene adattato alla tela
## esatta e non al rapporto nominale, quindi niente viene stirato.
FORMATI = {
    "1:1":  (448, 448),
    "3:4":  (384, 512),
    "4:3":  (512, 384),
    "9:16": (320, 576),
    "16:9": (576, 320),
    "21:9": (672, 288),
}
FORMATO_PREDEFINITO = "1:1"


def risoluzione(formato: str) -> tuple[int, int]:
    """Larghezza e altezza della clip. Un formato sconosciuto e' un errore:
    ripiegare in silenzio sul quadrato darebbe un'animazione diversa da
    quella chiesta senza dire perche'."""
    if formato not in FORMATI:
        raise ValueError("formato sconosciuto: %r (validi: %s)"
                         % (formato, ", ".join(FORMATI)))
    return FORMATI[formato]


def cella(lato: int, larghezza: int, altezza: int) -> tuple[int, int]:
    """Dimensioni di una cella dello sheet: il lato lungo vale `lato`, l'altro
    segue le proporzioni della clip."""
    if larghezza >= altezza:
        return lato, max(1, round(lato * altezza / larghezza))
    return max(1, round(lato * larghezza / altezza)), lato


def lunghezza_valida(model_id: str, durata_s: float) -> dict:
    """Primo valore accettato dal modello che copre la durata richiesta."""
    r = REGOLE.get(model_id)
    if r is None:
        raise KeyError("modello sconosciuto: %s" % model_id)

    durata_s = max(DURATA_MIN, min(DURATA_MAX, float(durata_s)))
    voluti = durata_s * r["fps"]

    # primo k con passo*k + offset >= voluti
    k = max(0, math.ceil((voluti - r["offset"]) / r["passo"]))
    lung = r["passo"] * k + r["offset"]
    troncata = False
    if lung > r["max"]:
        lung = r["passo"] * ((r["max"] - r["offset"]) // r["passo"]) + r["offset"]
        troncata = True

    return {
        "modello": model_id,
        "durata_richiesta_s": round(durata_s, 2),
        "fps": r["fps"],
        "lunghezza": lung,
        "durata_effettiva_s": round(lung / r["fps"], 2),
        "troncata": troncata,
        "max_modello": r["max"],
    }


def griglia_per(n_frame: int) -> tuple[int, int]:
    """Colonne e righe piu' vicine al quadrato che contengono n_frame."""
    cols = math.ceil(math.sqrt(n_frame))
    rows = math.ceil(n_frame / cols)
    return cols, rows


def indici_frame(lunghezza: int, n_frame: int) -> list[int]:
    """Indici equispaziati sulla porzione utile della clip.

    Restituisce esattamente n_frame indici crescenti e distinti (finche'
    la lunghezza lo consente).
    """
    n_frame = max(1, int(n_frame))
    ultimo = max(0, int(lunghezza * FRAZIONE_UTILE) - 1)
    if n_frame == 1:
        return [0]
    grezzi = [round(i * ultimo / (n_frame - 1)) for i in range(n_frame)]

    # de-duplica mantenendo la crescita, se la clip e' piu' corta dei frame chiesti
    visti: list[int] = []
    for v in grezzi:
        if visti and v <= visti[-1]:
            v = visti[-1] + 1
        visti.append(min(v, lunghezza - 1))
    return visti


def piano(model_id: str, durata_s: float, n_frame: int,
          formato: str = FORMATO_PREDEFINITO) -> dict:
    """Riassunto completo per l'interfaccia e per la generazione."""
    n_frame = max(FRAME_MIN, min(FRAME_MAX, int(n_frame)))
    larghezza, altezza = risoluzione(formato)
    L = lunghezza_valida(model_id, durata_s)
    cols, rows = griglia_per(n_frame)
    idx = indici_frame(L["lunghezza"], n_frame)
    return {
        **L,
        "n_frame": n_frame,
        "colonne": cols,
        "righe": rows,
        "celle_vuote": cols * rows - n_frame,
        "formato": formato,
        "larghezza": larghezza,
        "altezza": altezza,
        "indici": idx,
        # fps di riproduzione dello sprite sheet: n_frame distribuiti sulla durata
        "fps_riproduzione": round(n_frame / L["durata_effettiva_s"], 2),
        # istante dell'ultimo frame che finisce davvero nel foglio: oltre questo
        # punto la clip esiste ma viene scartata, quindi i beat del prompt non
        # devono spingersi piu' in la'.
        "fine_utile_s": round(idx[-1] / L["fps"], 2) if idx else 0.0,
    }
