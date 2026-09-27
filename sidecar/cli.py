"""Sprite Sheep da riga di comando, senza interfaccia.

Usa la stessa catena del programma (coda, backend, post, log): quello che
esce e' identico a una generazione fatta dall'interfaccia, e finisce nella
stessa cartella di output e nella stessa cronologia. Serve ComfyUI accesa,
come per l'interfaccia.

Un'azione:
    python sidecar/cli.py genera --sprite eroe.png --modello minimax_h3_fast \\
        --prompt-file uppercut.txt --nome uppercut --durata 2.33 --formato 3:4

Piu' azioni dello stesso personaggio, pesi caricati una volta sola:
    python sidecar/cli.py lotto set_eroe.json

    set_eroe.json:
    {"modello": "minimax_h3_fast", "sprite": "eroe.png", "formato": "3:4",
     "colore_sfondo": "verde", "margine": "ampio",
     "azioni": [
        {"nome": "idle", "prompt_file": "idle.txt", "durata_s": 2},
        {"nome": "walk", "campi": {"soggetto": "...", "beat": [...]}},
        {"nome": "jump", "prompt": "...", "seed": 42}]}

    Il prompt di un'azione puo' essere testo (`prompt`), un file
    (`prompt_file`, relativo al JSON) o i campi del wizard (`campi`), che si
    compongono nel dialetto del modello come fa l'interfaccia.

Cronologia:
    python sidecar/cli.py storico
    python sidecar/cli.py rigenera <cartella> [--seed N]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import coda
import inquadra
import parametri
import prompt as prompt_mod
import storico


def _prompt_di(azione: dict, modello: str, base: Path) -> str:
    if azione.get("prompt"):
        return azione["prompt"]
    if azione.get("prompt_file"):
        return (base / azione["prompt_file"]).read_text(encoding="utf-8")
    if azione.get("campi"):
        return prompt_mod.componi(azione["campi"], modello)
    raise SystemExit("azione %r senza prompt, prompt_file o campi"
                     % azione.get("nome"))


def _segui(job: str) -> int:
    """Stampa l'avanzamento finche' il lavoro non finisce. Codice d'uscita:
    0 fatto, 1 errore, 2 annullato."""
    ultimo = ""
    try:
        while True:
            s = coda.stato(job)
            eta = s.get("eta_s")
            riga = "%5.1f%%  %-12s %s%s" % (
                100 * (s.get("percentuale") or 0), s.get("fase", ""),
                s.get("dettaglio", ""),
                "  (~%d:%02d)" % divmod(int(eta), 60) if eta else "")
            if riga != ultimo:
                print(riga, flush=True)
                ultimo = riga
            if s.get("fase") == "fatto":
                for r in s.get("risultati", []):
                    print("\n%s  seme %s\n  %s\n  log: %s" % (
                        r["nome"], r["seed"], r["cartella"], r["log"]))
                return 0
            if s.get("fase") == "errore":
                print("\n" + (s.get("traccia") or s.get("errore", "")), file=sys.stderr)
                return 1
            if s.get("fase") == "annullato":
                return 2
            time.sleep(2)
    except KeyboardInterrupt:
        # Ctrl+C ferma anche ComfyUI: lasciarla a macinare un lavoro che
        # nessuno ritirera' e' il difetto che il pulsante Annulla ha tolto.
        print("\nannullo...", file=sys.stderr)
        coda.annulla(job)
        while coda.stato(job).get("fase") not in ("annullato", "errore", "fatto"):
            time.sleep(1)
        return 2


def _avvia(richiesta: dict) -> int:
    r = coda.avvia(richiesta)
    if not r.get("ok"):
        print("rifiutato: %s" % r.get("errore"), file=sys.stderr)
        return 1
    return _segui(r["job"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="spritesheep", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando", required=True)

    g = sub.add_parser("genera", help="un'azione")
    g.add_argument("--sprite", required=True)
    g.add_argument("--modello", default="minimax_h3_fast",
                   choices=sorted(parametri.REGOLE))
    g.add_argument("--prompt")
    g.add_argument("--prompt-file")
    g.add_argument("--nome", default="animazione")
    g.add_argument("--durata", type=float, default=2.0)
    g.add_argument("--frame", type=int, default=25)
    g.add_argument("--formato", default=parametri.FORMATO_PREDEFINITO,
                   choices=list(parametri.FORMATI))
    g.add_argument("--margine", default=inquadra.MARGINE_PREDEFINITO,
                   choices=list(inquadra.MARGINI))
    g.add_argument("--colore", default="auto",
                   help="auto, verde, bianco, #RRGGBB o r,g,b")
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--cella", type=int, default=256, help="lato lungo della cella")
    g.add_argument("--no-scontorno", action="store_true")

    lo = sub.add_parser("lotto", help="piu' azioni da un file JSON")
    lo.add_argument("file")

    sub.add_parser("storico", help="elenca le generazioni")

    rg = sub.add_parser("rigenera", help="rifa una generazione con un altro seme")
    rg.add_argument("cartella")
    rg.add_argument("--seed", type=int, default=0)

    a = ap.parse_args(argv)

    if a.comando == "genera":
        testo = a.prompt or (Path(a.prompt_file).read_text(encoding="utf-8")
                             if a.prompt_file else None)
        if not testo:
            ap.error("serve --prompt o --prompt-file")
        return _avvia({
            "modello": a.modello, "sprite": str(Path(a.sprite).resolve()),
            "prompt": testo, "nome": a.nome, "durata_s": a.durata,
            "n_frame": a.frame, "formato": a.formato, "margine": a.margine,
            "colore_sfondo": a.colore, "seed": a.seed, "lato_cella": a.cella,
            "scontorna": not a.no_scontorno})

    if a.comando == "lotto":
        f = Path(a.file)
        dati = json.loads(f.read_text(encoding="utf-8"))
        modello = dati.get("modello", "minimax_h3_fast")
        dati["modello"] = modello
        dati["sprite"] = str((f.parent / dati["sprite"]).resolve())
        dati["azioni"] = [dict(az, prompt=_prompt_di(az, modello, f.parent))
                          for az in dati.get("azioni", [])]
        return _avvia(dati)

    if a.comando == "storico":
        for v in storico.elenco():
            print("%s  %-24s %-6s seme %-11s %s" % (
                v["data"], v["nome"][:24], v.get("formato") or "-",
                v.get("seed") or "-", v["cartella"]))
        return 0

    if a.comando == "rigenera":
        try:
            return _avvia(storico.richiesta_da(a.cartella, a.seed))
        except ValueError as e:
            print(e, file=sys.stderr)
            return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
