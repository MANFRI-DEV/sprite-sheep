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
import os as _os
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent
GODOT = r"C:\GODOT\Godot_v4.6.1-stable_win64_console.exe"
PROGETTO = RADICE / "godot"
DIST = RADICE / "dist"
DIST_LINUX = RADICE / "dist_linux"

## I template di esportazione di Godot, uno per piattaforma. Sono file da
## centinaia di MB che si scaricano a parte: se quello di Linux non c'e', la
## build Windows deve uscire lo stesso e il pacchetto Linux si salta dicendo
## perche'. Fermare tutto per un template mancante punirebbe chi voleva solo
## ricompilare per Windows.
TEMPLATE = Path(_os.environ.get("APPDATA", "")) / "Godot" / "export_templates" \
    / "4.6.1.stable"
def _versione() -> str:
    """La versione, presa dalle due fonti e **confrontata**.

    Il lato Python la tiene in `sidecar/config.py`, il lato Godot in
    `project.godot`: nessuno dei due puo' leggere l'altra, quindi l'unico modo
    di non spedire un pacchetto con due numeri diversi e' controllarlo qui e
    fermarsi. E' gia' successo: `/health` rispondeva una versione e il badge
    dell'edizione un'altra, nella stessa schermata.
    """
    testo = (RADICE / "sidecar" / "config.py").read_text(encoding="utf-8")
    py = re.search(r'^VERSION\s*=\s*"([^"]+)"', testo, re.M)
    testo = (RADICE / "godot" / "project.godot").read_text(encoding="utf-8")
    gd = re.search(r'^config/version\s*=\s*"([^"]+)"', testo, re.M)
    if py is None or gd is None:
        raise SystemExit("versione non trovata in config.py o project.godot")
    if py.group(1) != gd.group(1):
        raise SystemExit(
            "versioni diverse: sidecar/config.py dice %s, project.godot dice %s"
            % (py.group(1), gd.group(1)))
    return py.group(1)


VERSIONE = _versione()
ZIP = RADICE / ("SpriteSheep-%s-win64.zip" % VERSIONE)
TARGZ = RADICE / ("SpriteSheep-%s-linux64.tar.gz" % VERSIONE)
ESEGUIBILE = "SpriteSheep.exe"
ESEGUIBILE_LINUX = "SpriteSheep.x86_64"

## Avviatore per Linux.
##
## Su Windows il pacchetto si porta dietro il proprio Python; su Linux no, e
## non e' pigrizia: la distribuzione "embeddable" esiste solo per Windows, e
## un virtualenv copiato contiene i percorsi assoluti della macchina che l'ha
## creato — su un altro PC non parte. Qui si usa il Python di sistema, che su
## qualunque distribuzione c'e' gia', e lo script controlla **prima** che
## abbia i quattro moduli: altrimenti il programma si apre, il motore muore
## in silenzio e l'utente vede solo una barra ferma.
AVVIATORE = """#!/bin/sh
# Sprite Sheep - avvio su Linux
set -e
cd "$(dirname "$(readlink -f "$0")")"

PY="${SPRITESHEEP_PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Sprite Sheep: serve Python 3.10 o piu' recente ($PY non trovato)." >&2
    echo "Installalo dal gestore pacchetti della tua distribuzione." >&2
    exit 1
fi

if ! "$PY" - <<'PYEOF' >/dev/null 2>&1
import importlib.util as u, sys
sys.exit(0 if all(u.find_spec(m) for m in ("PIL", "numpy", "scipy", "huggingface_hub")) else 1)
PYEOF
then
    echo "Sprite Sheep: al Python di sistema mancano dei moduli." >&2
    echo "Installali con:" >&2
    echo "    $PY -m pip install --user pillow numpy scipy huggingface_hub" >&2
    exit 1
fi

exec ./SpriteSheep.x86_64 "$@"
"""

## Roba che non va nel pacchetto: cache di importazione, stato dell'editor,
## bytecode Python.
## I `test_*.py` restano fuori: servono a chi sviluppa, e uno di loro
## (`test_annulla.py`) contiene un percorso assoluto di questa macchina che
## nel pacchetto di qualcun altro non vorrebbe dire niente.
SALTA_SIDECAR = shutil.ignore_patterns("__pycache__", "*.pyc", "*.log",
                                       "edizione.cfg", "test_*.py")

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


DOCUMENTI = [
    ("dist_README.txt", "README.txt"),
    ("dist_requirements.txt", "requirements.txt"),
]


def prepara(dest: Path, readme: str) -> None:
    """Sidecar e documenti dentro `dest`, uguali per tutte le piattaforme.

    `readme` e' il file sorgente del LEGGIMI: Windows e Linux hanno istruzioni
    diverse — uno si porta dietro Python, l'altro usa quello di sistema — e
    spedire a un utente Linux le istruzioni di Windows e' peggio che non
    spedirne affatto.
    """
    dst = dest / "sidecar"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(RADICE / "sidecar", dst, ignore=SALTA_SIDECAR)

    ## Gli unici `.txt` che il pacchetto deve contenere. Tutti gli altri in
    ## cima alla cartella sono avanzi di versioni precedenti e vanno buttati:
    ## `requisiti.txt` della 0.9 e' sopravvissuto a due build, e' finito nel
    ## pacchetto senza che nessuno lo copiasse e annunciava la versione
    ## sbagliata.
    ##
    ## L'elenco serve proprio a non cancellare troppo: il primo tentativo
    ## buttava *tutti* i `.txt`, e portava via anche le licenze generate da
    ## `build_licenze.py` — che questa build non riscrive, e che i termini
    ## delle dipendenze impongono di allegare.
    attesi = {c for _, c in DOCUMENTI} | {"THIRD-PARTY-LICENCES.txt"}
    for vecchio in dest.glob("*.txt"):
        if vecchio.name not in attesi:
            vecchio.unlink()
            print("   buttato avanzo: %s" % vecchio.name)

    # La versione nei documenti si riscrive qui, non si copia: la portano
    # scritta in prima riga ed erano gia' rimasti indietro mentre tutto il
    # resto del pacchetto annunciava la versione nuova. Nessun controllo
    # poteva accorgersene, perche' erano gli unici due posti in cui il numero
    # non veniva mai riletto da nessuno — se non dall'utente.
    for nome, come in [(readme, "README.txt"), DOCUMENTI[1]]:
        testo = (RADICE / nome).read_text(encoding="utf-8")
        nuovo = re.sub(r"\d+\.\d+\.\d+-pre-alpha", VERSIONE, testo)
        (dest / come).write_text(nuovo, encoding="utf-8")
        if nuovo != testo:
            print("   %s: versione aggiornata a %s" % (come, VERSIONE))
        elif VERSIONE not in nuovo:
            print("   ATTENZIONE: %s non nomina nessuna versione" % come)

    # Le licenze le scrive `build_licenze.py` leggendo il runtime davvero
    # distribuito: se non c'e' ancora, si dice, invece di spedire un pacchetto
    # a cui manca un documento che le licenze stesse impongono di includere.
    licenze = dest / "THIRD-PARTY-LICENCES.txt"
    if not licenze.exists():
        sorgente = DIST / "THIRD-PARTY-LICENCES.txt"
        if sorgente.exists():
            shutil.copy2(sorgente, licenze)
        else:
            raise SystemExit(
                "manca %s: lancia prima `python build_licenze.py`.\n"
                "Spedire il pacchetto senza quel file violerebbe i termini "
                "delle librerie incluse." % licenze.name)

    # Un `edizione.cfg` dimenticato riaccenderebbe la filigrana.
    if (dst / "edizione.cfg").exists():
        raise SystemExit("edizione.cfg e' finito nel pacchetto")


def _da_impacchettare(dest: Path):
    for q in sorted(dest.rglob("*")):
        if q.is_file() and not (NON_IMPACCHETTARE & set(q.relative_to(dest).parts)):
            yield q, q.relative_to(dest)


def impacchetta_zip(dest: Path, archivio: Path) -> None:
    archivio.unlink(missing_ok=True)
    n = byte = 0
    with zipfile.ZipFile(archivio, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6) as f:
        for q, rel in _da_impacchettare(dest):
            f.write(q, str(Path("SpriteSheep") / rel))
            n += 1
            byte += q.stat().st_size
    _riassunto(archivio, n, byte)


def impacchetta_tar(dest: Path, archivio: Path) -> None:
    """Tar.gz invece di zip, e non e' una preferenza estetica.

    Lo zip non conserva il bit di esecuzione: scompattato su Linux,
    `SpriteSheep.x86_64` arriva senza permesso di esecuzione e l'utente deve
    dare un `chmod +x` che nessuno documenta mai. Il tar lo porta dentro.
    """
    archivio.unlink(missing_ok=True)
    n = byte = 0
    with tarfile.open(archivio, "w:gz") as f:
        for q, rel in _da_impacchettare(dest):
            info = f.gettarinfo(str(q), str(Path("SpriteSheep") / rel))
            info.mode = 0o755 if rel.suffix in (".sh", ".x86_64") else 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            with q.open("rb") as fp:
                f.addfile(info, fp)
            n += 1
            byte += q.stat().st_size
    _riassunto(archivio, n, byte)


def _riassunto(archivio: Path, n: int, byte: int) -> None:
    print("   file: %d | %.0f MB dentro, %.1f MB compresso"
          % (n, byte / 1e6, archivio.stat().st_size / 1e6))
    # Una build sana sta sotto il mezzo giga: eseguibile, runtime e sidecar.
    # Oltre, e' finito dentro qualcosa che non doveva.
    if archivio.stat().st_size > 500e6:
        raise SystemExit("il pacchetto e' troppo grande: controlla la cartella")


def costruisci_linux() -> None:
    """Il pacchetto Linux, se i template di Godot ci sono."""
    template = TEMPLATE / "linux_release.x86_64"
    if not template.is_file():
        print("   SALTATO: manca %s" % template)
        print("   scarica i template di esportazione 4.6.1 e riprova")
        return

    DIST_LINUX.mkdir(parents=True, exist_ok=True)
    binario = DIST_LINUX / ESEGUIBILE_LINUX
    esegui(GODOT, "--headless", "--path", str(PROGETTO),
           "--export-release", "Linux", str(binario))
    if not binario.is_file():
        raise SystemExit("l'export Linux non ha prodotto %s" % binario.name)
    print("   %.1f MB" % (binario.stat().st_size / 1e6))

    prepara(DIST_LINUX, "dist_README_linux.txt")
    avvio = DIST_LINUX / "SpriteSheep.sh"
    # Fine riga LF: uno script con i CRLF di Windows non parte su Linux, e
    # l'errore che da' — "bad interpreter: /bin/sh^M" — non dice a nessuno
    # cosa sia successo.
    avvio.write_bytes(AVVIATORE.replace("\r\n", "\n").encode("utf-8"))
    print("   avviatore: %s" % avvio.name)

    impacchetta_tar(DIST_LINUX, TARGZ)
    print("   pronto: %s" % TARGZ.name)


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
    prepara(DIST, "dist_README.txt")
    print("   sidecar copiato, README.txt, requirements.txt")

    passo("verifica")
    import sys
    sys.path.insert(0, str(DIST / "sidecar"))
    import edizione                                        # noqa: E402
    print("   versione: %s | filigrana: %s"
          % (edizione.VERSIONE, edizione.FILIGRANA))
    if edizione.FILIGRANA:
        raise SystemExit("la build applicherebbe ancora la filigrana")

    passo("pacchetto Windows")
    impacchetta_zip(DIST, ZIP)
    print("   pronto: %s" % ZIP.name)

    passo("pacchetto Linux")
    costruisci_linux()

    print("\npronto: %s" % ZIP)
    if TARGZ.exists():
        print("pronto: %s" % TARGZ)


if __name__ == "__main__":
    main()
