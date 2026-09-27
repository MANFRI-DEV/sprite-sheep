"""Cronologia delle generazioni, letta dalle cartelle di output.

Nessun database: ogni cartella ha il suo `meta.json` (scritto da
`genera._scrivi_rapporti`), e la cronologia e' l'elenco di quei file. Se
l'utente cancella una cartella a mano, sparisce anche dalla cronologia; se la
sposta in `output/` da un'altra macchina, compare. Le cartelle di prima della
0.0.5, senza `meta.json`, compaiono lo stesso ma non si possono rigenerare.
"""
import json
import time
from pathlib import Path

import config

MASSIMO = 200


def _dentro_output(cartella: str) -> Path | None:
    """La cartella, se sta davvero dentro `output/`. Il percorso arriva
    dall'interfaccia: senza questo controllo `/rigenera` leggerebbe un
    `meta.json` e uno sprite da qualunque punto del disco."""
    try:
        radice = config.OUTPUT_DIR.resolve()
        c = Path(cartella).resolve()
        c.relative_to(radice)
    except (ValueError, OSError):
        return None
    return c if c.is_dir() and c != radice else None


def _meta(cartella: Path) -> dict | None:
    f = cartella / "meta.json"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def elenco() -> list[dict]:
    """Le generazioni, dalla piu' recente. Solo quello che serve a mostrarle:
    il prompt intero sta nel log."""
    voci = []
    if not config.OUTPUT_DIR.is_dir():
        return voci
    for c in config.OUTPUT_DIR.iterdir():
        if not c.is_dir():
            continue
        m = _meta(c)
        if m is None:
            gif = next(iter(sorted(c.glob("*.gif"))), None)
            if gif is None:
                continue
            voce = {"cartella": str(c), "nome": c.name,
                    "quando": c.stat().st_mtime, "gif": str(gif),
                    "rigenerabile": False}
            # Il foglio serve alla miniatura: senza, le generazioni di prima
            # della 0.0.5 comparivano come righe nude in mezzo alle altre.
            foglio = next(iter(sorted(c.glob("*sheet*.png"))), None)
            if foglio is not None:
                voce["sheet"] = str(foglio)
            voci.append(voce)
            continue
        voce = {
            "cartella": str(c), "nome": m.get("nome", c.name),
            "quando": m.get("fine") or c.stat().st_mtime,
            "modello": m.get("modello_nome") or m.get("modello"),
            "formato": m.get("formato"), "seed": m.get("seed"),
            "durata_s": m.get("durata_s"), "n_frame": m.get("n_frame"),
            "prompt": (m.get("prompt") or "")[:160],
            "rigenerabile": (c / m.get("sprite", "")).is_file(),
        }
        for chiave in ("gif", "sheet", "log"):
            if m.get(chiave) and (c / m[chiave]).is_file():
                voce[chiave] = str(c / m[chiave])
        voci.append(voce)
    voci.sort(key=lambda v: v["quando"], reverse=True)
    for v in voci:
        v["data"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(v["quando"]))
    return voci[:MASSIMO]


def richiesta_da(cartella: str, seed: int = 0) -> dict:
    """La richiesta che rifa la generazione di `cartella`, con un altro seme
    (0 = a caso). Solleva ValueError se non si puo'."""
    c = _dentro_output(cartella)
    if c is None:
        raise ValueError("cartella non valida: %s" % cartella)
    m = _meta(c)
    if m is None:
        raise ValueError("generazione senza meta.json: non rigenerabile")
    sprite = c / m.get("sprite", "")
    if not sprite.is_file():
        raise ValueError("sprite iniziale mancante in %s" % c.name)
    return {
        "modello": m["modello"], "sprite": str(sprite),
        "formato": m.get("formato", "1:1"),
        "margine": m.get("margine", "nessuno"),
        "scontorna": m.get("scontorna", True),
        "colore_sfondo": m.get("colore_sfondo", "auto"),
        "lato_cella": m.get("lato_cella", 256),
        "nome": m.get("nome", "animazione"), "prompt": m["prompt"],
        "durata_s": m.get("durata_s", 2.0), "n_frame": m.get("n_frame", 25),
        "seed": int(seed),
    }
