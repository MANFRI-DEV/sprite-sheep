"""Esporta l'eseguibile e prepara il pacchetto distribuibile.

Sostituisce `build_premium.py`. Fino alla 0.9 esistevano due edizioni e due
progetti Godot, uno copia dell'altro: quello script duplicava `godot/` in
`godot_premium/`, cambiava tre righe e esportava. Dalla 0.0.1 pre-alpha
l'edizione e' una sola, quindi non si copia piu' niente — si esporta il
progetto e basta.

Cosa finisce nel pacchetto:

    SpriteSheep.exe          l'applicazione
    sidecar/                 il servizio Python che fa l'inferenza
    python/                  runtime incorporato, cosi' non si installa nulla
    README.txt               istruzioni
    requirements.txt         elenco librerie
    THIRD-PARTY-LICENCES.txt licenze delle dipendenze

I pesi dei modelli **non** ci sono: si scaricano dall'applicazione, dopo aver
accettato la licenza di ciascuno.

    python build.py
"""
import shutil
import subprocess
import zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent
GODOT = r"C:\GODOT\Godot_v4.6.1-stable_win64_console.exe"
PROGETTO = RADICE / "godot"
DIST = RADICE / "dist"
VERSIONE = "0.0.4-pre-alpha"
ZIP = RADICE / ("SpriteSheep-%s-win64.zip" % VERSIONE)
ESEGUIBILE = "SpriteSheep.exe"

## Roba che non va nel pacchetto: cache di importazione, stato dell'editor,
## bytecode Python.
SALTA_SIDECAR = shutil.ignore_patterns("__pycache__", "*.pyc", "*.log",
                                       "edizione.cfg")

## Cartelle che l'applicazione **crea dentro `dist/` mentre gira**, e che nel
## pacchetto non devono finire.
##
## `models/` sono i pesi scaricati dall'utente: 39 GB. Il primo zip fatto senza
## questa esclusione pesava 13 GB compressi, ed e' stato accorto guardarlo
## invece di fidarsi — `rglob("*")` prende tutto quello che trova, e cio' che
## trova dipende da quanto l'applicazione e' stata usata prima della build.
## Un pacchetto il cui contenuto cambia a seconda di cosa e' successo prima
## non e' riproducibile.
##
## I pesi si scaricano dall'applicazione dopo aver accettato la licenza di
## ciascuno: nel pacchetto non potrebbero starci ne' tecnicamente ne'
## giuridicamente.
NON_IMPACCHETTARE = {"models", "cache", "output", "__pycache__"}


def passo(t: str) -> None:
    print("\n== %s" % t)


def esegui(*args: str) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    fuori = (r.stdout or "") + (r.stderr or "")
    brutte = [l for l in fuori.splitlines()
              if "ERROR" in l or "SCRIPT ERROR" in l or "Parse Error" in l]
    if brutte:
        print("\n".join(brutte[:6]))
        raise SystemExit("comando fallito: %s" % " ".join(args[:3]))


def main() -> None:
    passo("controllo del progetto")
    testo = (PROGETTO / "project.godot").read_text(encoding="utf-8")
    if 'config/version="%s"' % VERSIONE not in testo:
        raise SystemExit("project.godot non dichiara la versione %s" % VERSIONE)
    if "Premium" in testo:
        raise SystemExit("project.godot contiene ancora un riferimento premium")
    print("   versione %s, nessun riferimento premium" % VERSIONE)

    passo("importazione delle risorse")
    esegui(GODOT, "--headless", "--path", str(PROGETTO), "--import")

    passo("export dell'eseguibile")
    DIST.mkdir(parents=True, exist_ok=True)
    esegui(GODOT, "--headless", "--path", str(PROGETTO),
           "--export-release", "Windows Desktop", str(DIST / ESEGUIBILE))
    print("   %.1f MB" % ((DIST / ESEGUIBILE).stat().st_size / 1e6))

    passo("sidecar e documentazione")
    dst = DIST / "sidecar"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(RADICE / "sidecar", dst, ignore=SALTA_SIDECAR)

    DOCUMENTI = [
        ("dist_README.txt", "README.txt"),
        ("dist_requirements.txt", "requirements.txt"),
    ]
    ## Gli unici `.txt` che il pacchetto deve contenere. Tutti gli altri in
    ## cima a `dist/` sono avanzi di versioni precedenti e vanno buttati:
    ## `requisiti.txt` della 0.9 e' sopravvissuto a due build, e' finito nel
    ## pacchetto senza che nessuno lo copiasse e annunciava la versione
    ## sbagliata.
    ##
    ## L'elenco serve proprio a non cancellare troppo: il primo tentativo
    ## buttava *tutti* i `.txt`, e portava via anche le licenze appena
    ## generate da `build_licenze.py` — che non le riscrive questa build, e
    ## che i termini delle dipendenze impongono di allegare.
    ATTESI = {c for _, c in DOCUMENTI} | {"THIRD-PARTY-LICENCES.txt"}
    for vecchio in DIST.glob("*.txt"):
        if vecchio.name not in ATTESI:
            vecchio.unlink()
            print("   buttato avanzo: %s" % vecchio.name)

    for nome, come in DOCUMENTI:
        shutil.copy2(RADICE / nome, DIST / come)

    # Le licenze le scrive `build_licenze.py` leggendo il runtime davvero
    # distribuito: se non c'e' ancora, si dice, invece di spedire un pacchetto
    # a cui manca un documento che le licenze stesse impongono di includere.
    licenze = DIST / "THIRD-PARTY-LICENCES.txt"
    if not licenze.exists():
        raise SystemExit(
            "manca %s: lancia prima `python build_licenze.py`.\n"
            "Spedire il pacchetto senza quel file violerebbe i termini delle "
            "librerie incluse." % licenze.name)
    print("   sidecar copiato, %s" % ", ".join(c for _, c in DOCUMENTI))

    # Verifica che nel pacchetto non sia rimasto niente della vecchia doppia
    # edizione: un `edizione.cfg` dimenticato riaccenderebbe la filigrana.
    passo("verifica")
    if (dst / "edizione.cfg").exists():
        raise SystemExit("edizione.cfg e' finito nel pacchetto")
    import sys
    sys.path.insert(0, str(dst))
    import edizione                                        # noqa: E402
    print("   versione: %s | filigrana: %s"
          % (edizione.VERSIONE, edizione.FILIGRANA))
    if edizione.FILIGRANA:
        raise SystemExit("la build applicherebbe ancora la filigrana")

    passo("pacchetto")
    if ZIP.exists():
        ZIP.unlink()
    n = 0
    byte = 0
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as f:
        for q in sorted(DIST.rglob("*")):
            if not q.is_file():
                continue
            rel = q.relative_to(DIST)
            if NON_IMPACCHETTARE & set(rel.parts):
                continue
            f.write(q, str(Path("SpriteSheep") / rel))
            n += 1
            byte += q.stat().st_size
    print("   file: %d | %.0f MB dentro, %.1f MB compresso"
          % (n, byte / 1e6, ZIP.stat().st_size / 1e6))
    # Una build sana sta sotto il mezzo giga: eseguibile, runtime Python e
    # sidecar. Oltre, e' finito dentro qualcosa che non doveva.
    if ZIP.stat().st_size > 500e6:
        raise SystemExit("il pacchetto e' troppo grande: controlla dist/")
    print("\npronto: %s" % ZIP)


if __name__ == "__main__":
    main()
