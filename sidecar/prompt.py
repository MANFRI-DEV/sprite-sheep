"""Composizione e validazione del prompt strutturato, un dialetto per modello.

Le regole non sono teoriche: nascono da fallimenti osservati generando
sprite sheet.

La piu' importante e' `_oggetti_negati`. Un modello di diffusione non sa
disegnare un'assenza: nominare un oggetto lo evoca, anche negandolo. Un
prompt che diceva "invisible ledge, never drawn" ha prodotto la sporgenza
come barra magenta (il complementare esatto del verde di sfondo). La cura e'
non nominare l'oggetto affatto, oppure dichiararlo e vincolarne il colore.

**Perche' due dialetti.** MiniMax H3 e' addestrato su descrizioni multimodali
con intestazioni esplicite (`integrated_multimodal_description:`, blocchi audio)
e legge marcatori temporali `[0s-1s]`. WAN 2.2 usa umt5-xxl, un encoder di solo
testo: quelle intestazioni sono token che non ha mai visto, e i marcatori
temporali non li interpreta. Passargli il prompt di H3 funziona a meta' — e' il
motivo per cui il primo pesce generato con WAN cresceva a vista d'occhio.
"""
import re

from testi import t

# --- dialetto MiniMax H3 ---------------------------------------------------
INTESTAZIONE = "integrated_multimodal_description:"
CODA_SUONO = "overall_soundscape:"
CODA_MUSICA = "non_diegetic_music:"

IDENTITA = ("The subject's design, proportions, colors and line weight remain "
            "absolutely identical in every single frame. Anatomy stays correct "
            "throughout: no extra or missing parts.")

## Senza, in un montante il modello gira il personaggio di spalle a meta'
## clip: visto nell'uppercut della poliziotta, corretto a mano nel prompt.
ORIENTAMENTO = ("The subject keeps facing the same side of the frame as in the "
                "first frame for the whole clip, with the same side of the body "
                "turned toward the viewer and the face visible in every frame.")

## Lampi, scie e bagliori bianchi li mangia lo scontorno, e bucano la figura.
## Detto in positivo: nominarli, anche per escluderli, li fa disegnare.
SOLO_FIGURA = ("The frame contains only the subject and the flat background; "
               "the motion is shown entirely through the subject's own body, "
               "with clean, solid edges.")

CHIUSURA_CICLO = ("The final frame returns to exactly the same pose, position "
                  "and framing as the very first frame, so the cycle loops "
                  "seamlessly.")

_RE_BEAT = re.compile(r"\[(\d+(?:\.\d+)?)s\s*[-–]\s*(\d+(?:\.\d+)?)s\]")

# "invisible X", "unseen X", "X is never drawn/shown", "no X appears/visible"
_RE_NEGAZIONI = [
    re.compile(r"\b(invisible|unseen)\s+([a-z]+)", re.I),
    re.compile(r"\bnever (?:drawn|shown|rendered|visible)\b", re.I),
    re.compile(r"\bno\s+([a-z]+)\s+(?:appears?|is visible|are visible)\b", re.I),
]


def dialetto(model_id: str | None) -> str:
    """Quale famiglia di prompt serve a questo modello."""
    if model_id and model_id.startswith("wan"):
        return "wan"
    return "h3"


def componi(campi: dict, modello: str | None = None) -> str:
    """Costruisce il prompt dai campi dell'interfaccia, nel dialetto giusto."""
    if dialetto(modello) == "wan":
        return _componi_wan(campi)
    return _componi_h3(campi)


def _pezzi(campi: dict) -> tuple:
    return ((campi.get("soggetto") or "").strip(),
            (campi.get("stile") or "").strip(),
            (campi.get("sfondo") or "").strip(),
            (campi.get("camera") or "").strip(),
            campi.get("beat") or [],          # [{"da":0.0,"a":1.7,"testo":"..."}]
            bool(campi.get("ciclico", True)))


def _componi_h3(campi: dict) -> str:
    soggetto, stile, sfondo, camera, beat, ciclico = _pezzi(campi)

    testa = f"{INTESTAZIONE} {soggetto}"
    if stile:
        testa += f" {stile}"
    parti = [testa, IDENTITA, ORIENTAMENTO, SOLO_FIGURA]

    if sfondo:
        parti.append(sfondo)
    if camera:
        parti.append(camera)

    for b in beat:
        azione = (b.get("testo") or "").strip()
        if azione:
            parti.append(
                f"[{_fmt(b.get('da', 0))}s-{_fmt(b.get('a', 0))}s] {azione}")

    if ciclico and beat:
        parti.append(CHIUSURA_CICLO)

    parti.append(f"{CODA_SUONO} Silent, no audio content.")
    parti.append(f"{CODA_MUSICA} None.")
    return "\n\n".join(parti)


def _componi_wan(campi: dict) -> str:
    """Un paragrafo unico, descrittivo, senza intestazioni ne' marcatori.

    umt5 legge prosa. I tempi diventano parole ("first ... then ... finally"):
    l'ordine si esprime nella frase, non fra parentesi quadre.
    """
    soggetto, stile, sfondo, camera, beat, ciclico = _pezzi(campi)

    frasi = []
    if soggetto:
        frasi.append(soggetto.rstrip(".") + ".")
    if stile:
        frasi.append(stile.rstrip(".") + ".")
    if sfondo:
        frasi.append(sfondo.rstrip(".") + ".")

    testi = [(b.get("testo") or "").strip().rstrip(".")
             for b in beat if (b.get("testo") or "").strip()]
    if testi:
        frasi.append(_azioni_in_prosa(testi))

    if camera:
        frasi.append(camera.rstrip(".") + ".")
    frasi.append(IDENTITA)
    frasi.append(ORIENTAMENTO)
    frasi.append(SOLO_FIGURA)
    if ciclico and testi:
        frasi.append(CHIUSURA_CICLO)
    return " ".join(frasi)


## Gli avverbi di sequenza sostituiscono i marcatori [0s-1s], che umt5 ignora.
_ORDINE = ["First", "Then", "Next", "After that", "Then", "Next",
           "After that", "Finally"]


def _azioni_in_prosa(testi: list[str]) -> str:
    if len(testi) == 1:
        return testi[0].capitalize() + "."
    frasi = []
    for i, azione in enumerate(testi):
        parola = "Finally" if i == len(testi) - 1 else _ORDINE[min(i, len(_ORDINE) - 1)]
        frasi.append(f"{parola} {azione}.")
    return " ".join(frasi)


def _fmt(v) -> str:
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:.1f}"


def _oggetti_negati(testo: str) -> list[str]:
    trovati = []
    for rx in _RE_NEGAZIONI:
        for m in rx.finditer(testo):
            trovati.append(m.group(0).strip())
    return sorted(set(trovati))


## Le tre parti che il prompt dovrebbe avere ma la cui assenza non impedisce di
## generare: quale campo le contiene, e con quale parola si riconoscono in un
## testo scritto a mano.
_PARTI = [
    ("soggetto", "identical in every", "prompt.no_identita"),
    ("camera", "camera", "prompt.no_camera"),
    ("sfondo", "background", "prompt.no_sfondo"),
]


def _mancanti(testo: str, campi: dict | None) -> list[str]:
    """Quali delle tre parti non ci sono, guardando i campi se li abbiamo.

    Per l'identita' il campo da controllare e' `soggetto`, non un campo suo:
    il blocco IDENTITA lo aggiunge `_componi_h3` da solo ogni volta che c'e'
    un soggetto, quindi non e' una cosa che l'utente possa dimenticare — puo'
    solo non aver scritto il soggetto.
    """
    if campi is None:
        basso = testo.lower()
        return [chiave for _, parola, chiave in _PARTI if parola not in basso]
    return [chiave for campo, _, chiave in _PARTI
            if not (campi.get(campo) or "").strip()]


def valida(testo: str, durata_s: float = 2.0, modello: str | None = None,
           campi: dict | None = None) -> dict:
    """Restituisce esito, problemi bloccanti e avvisi.

    semaforo: "verde" generabile, "giallo" generabile ma migliorabile,
              "rosso" da correggere prima di generare.

    `campi` sono i campi da cui il testo e' stato composto, quando esistono.
    Averli cambia la qualita' di tre controlli — identita', camera e sfondo —
    che senza si riducono a cercare una parola inglese nel testo:

        if "background" not in testo.lower(): ...

    Bastava descrivere lo sfondo con altre parole ("solid white, no scenery"),
    o scriverlo in italiano, e il programma diceva che mancava una cosa che
    c'era. Un avviso che ha torto e' peggio di nessun avviso: insegna a
    ignorare anche quelli giusti.

    Quando i campi ci sono si guarda **il campo**, che e' l'informazione vera.
    La ricerca nel testo resta per il caso in cui i campi non esistano
    davvero: il prompt scritto o incollato a mano.
    """
    testo = testo or ""
    dial = dialetto(modello)
    problemi: list[str] = []
    avvisi: list[str] = []

    if len(testo.strip()) < 80:
        problemi.append(t("prompt.corto"))

    beat = [(float(a), float(b)) for a, b in _RE_BEAT.findall(testo)]

    if dial == "h3":
        if INTESTAZIONE not in testo:
            avvisi.append(t("prompt.manca_blocco", blocco=INTESTAZIONE))
        if CODA_SUONO not in testo:
            avvisi.append(t("prompt.manca_blocco", blocco=CODA_SUONO))
        if not beat:
            problemi.append(t("prompt.no_beat"))
    else:
        # WAN non legge i marcatori: se ci sono, sono token sprecati.
        if INTESTAZIONE in testo or CODA_SUONO in testo:
            avvisi.append(t("prompt.wan_intestazioni"))
        if beat:
            avvisi.append(t("prompt.wan_marcatori"))

    if beat:
        fine = max(b for _, b in beat)
        if fine > durata_s + 0.01:
            problemi.append(t("prompt.beat_oltre",
                              fine=round(fine, 1), durata=round(durata_s, 1)))
        # margine di sicurezza: la griglia campiona solo i primi ~85% dei frame
        elif fine > durata_s * 0.9:
            avvisi.append(t("prompt.beat_vicino", fine=round(fine, 1),
                            durata=round(durata_s, 1),
                            limite=round(durata_s * 0.85, 1)))
        for da, a in beat:
            if a <= da:
                problemi.append(t("prompt.beat_invalido", da=da, a=a))

    negati = _oggetti_negati(testo)
    if negati:
        problemi.append(t("prompt.negati", elenco=", ".join(negati[:3])))

    for chiave in _mancanti(testo, campi):
        avvisi.append(t(chiave))

    if problemi:
        semaforo = "rosso"
    elif avvisi:
        semaforo = "giallo"
    else:
        semaforo = "verde"

    return {
        "semaforo": semaforo,
        "generabile": not problemi,
        "problemi": problemi,
        "avvisi": avvisi,
        "caratteri": len(testo),
        "n_beat": len(beat),
        "fine_beat_s": max([b for _, b in beat], default=0.0),
        "dialetto": dial,
    }
