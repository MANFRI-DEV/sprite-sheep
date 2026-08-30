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
    LEGGIMI.txt              istruzioni
    LICENZE-TERZE-PARTI.txt  licenze delle dipendenze

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
VERSIONE = "0.0.1-pre-alpha"
ZIP = RADICE / ("SpriteSheep-%s-win64.zip" % VERSIONE)
ESEGUIBILE = "SpriteSheep.exe"

## Roba che non va nel pacchetto: cache di importazione, stato dell'editor,
## bytecode Python, e i pesi dei modelli, che pesano decine di gigabyte.
SALTA_SIDECAR = shutil.ignore_patterns("__pycache__", "*.pyc", "*.log",
                                       "edizione.cfg")


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
    for nome, come in (("dist_README.txt", "LEGGIMI.txt"),):
        shutil.copy2(RADICE / nome, DIST / come)
    print("   sidecar copiato, LEGGIMI.txt aggiornato")

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
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as f:
        for q in sorted(DIST.rglob("*")):
            if q.is_file():
                f.write(q, str(Path("SpriteSheep") / q.relative_to(DIST)))
                n += 1
    print("   file: %d | compresso %.1f MB" % (n, ZIP.stat().st_size / 1e6))
    print("\npronto: %s" % ZIP)


if __name__ == "__main__":
    main()
