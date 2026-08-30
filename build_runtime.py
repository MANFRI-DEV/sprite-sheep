"""Costruisce il runtime Python incorporato in dist/python/.

L'utente non deve installare Python ne' fare pip: il programma si porta dietro
il proprio interprete. Restano a suo carico ComfyUI e i pesi, che sono
installazioni sue e vivono altrove.

Perche' la distribuzione "embeddable" e non un virtualenv copiato: un venv
contiene percorsi assoluti della macchina che l'ha creato e su un altro PC non
parte. L'embeddable e' fatto apposta per essere spostato.

Si lancia a mano quando cambiano le dipendenze:
    python build_runtime.py
"""
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

# Con `import site` attivo l'interprete aggiunge anche la user site della
# macchina che costruisce: pip ci trova numpy e scipy gia' installati, dice
# "already satisfied" e non mette niente nel runtime. La build sembra riuscita
# e il pacchetto esce vuoto. Va spenta sia per pip che per le verifiche.
AMBIENTE = dict(os.environ, PYTHONNOUSERSITE="1")

RADICE = Path(__file__).resolve().parent
DEST = RADICE / "dist" / "python"
SCARICATI = RADICE.parent / "_rt"
ZIP_EMBED = SCARICATI / "python-3.12.10-embed-amd64.zip"
GET_PIP = SCARICATI / "get-pip.py"

# Niente torch: il calcolo sulla GPU lo fa ComfyUI col proprio ambiente.
# Qui serve solo quello che il sidecar importa davvero.
PACCHETTI = ["pillow", "numpy", "scipy", "huggingface_hub"]

# Roba che pip si porta dietro e che a noi non serve mai: tolta a build finita.
INUTILI = ["pip", "setuptools", "wheel", "pkg_resources", "_distutils_hack"]


def passo(testo: str) -> None:
    print("\n== %s" % testo)


def esegui(*args: str) -> None:
    r = subprocess.run(args, capture_output=True, text=True, env=AMBIENTE)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise SystemExit("comando fallito: %s" % " ".join(args))


def peso(cartella: Path) -> float:
    return sum(f.stat().st_size for f in cartella.rglob("*") if f.is_file()) / 1e6


passo("estrazione dell'interprete")
if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)
with zipfile.ZipFile(ZIP_EMBED) as z:
    z.extractall(DEST)
print("   %.1f MB" % peso(DEST))

# ---------------------------------------------------------------------------
# Nell'embeddable il file _pth sostituisce sys.path e tiene `import site`
# commentato: senza site, site-packages non viene guardato e pip installa in
# una cartella che nessuno legge. Va riabilitato prima di installare.
# ---------------------------------------------------------------------------
passo("abilitazione di site-packages")
pth = next(DEST.glob("python*._pth"))
righe = pth.read_text(encoding="utf-8").splitlines()
fuori = []
for r in righe:
    fuori.append("import site" if r.strip() in ("#import site", "# import site") else r)
if "import site" not in fuori:
    fuori.append("import site")
if "Lib\\site-packages" not in fuori:
    fuori.insert(len(fuori) - 1, "Lib\\site-packages")
pth.write_text("\n".join(fuori) + "\n", encoding="utf-8")
print("   %s -> %s" % (pth.name, ", ".join(x for x in fuori if x)))

py = DEST / "python.exe"

passo("installazione di pip")
esegui(str(py), str(GET_PIP), "--no-warn-script-location")

passo("installazione delle librerie del sidecar")
# --target e --ignore-installed: si vuole una copia dentro il runtime, non un
# rimando a quello che c'e' gia' sulla macchina di chi costruisce.
esegui(str(py), "-m", "pip", "install", "--no-warn-script-location",
       "--ignore-installed", "--target", str(DEST / "Lib" / "site-packages"),
       *PACCHETTI)

# ---------------------------------------------------------------------------
# pip, setuptools e le loro dipendenze pesano ~15 MB e a runtime non servono:
# il sidecar non installa niente. Chi deve aggiungere pacchetti rilancia questo
# script, che ricostruisce tutto da zero.
# ---------------------------------------------------------------------------
passo("rimozione degli strumenti di installazione")
sp = DEST / "Lib" / "site-packages"
tolti = 0.0
for nome in INUTILI:
    for p in list(sp.glob(nome)) + list(sp.glob(nome + "-*")) + list(sp.glob(nome + ".*")):
        tolti += peso(p) if p.is_dir() else p.stat().st_size / 1e6
        shutil.rmtree(p) if p.is_dir() else p.unlink()
for p in list(sp.glob("*.exe")) + list((DEST / "Scripts").glob("*") if (DEST / "Scripts").exists() else []):
    if p.is_file():
        tolti += p.stat().st_size / 1e6
        p.unlink()
print("   liberati %.1f MB" % tolti)

passo("pulizia di cache e test")
tolti = 0.0
for p in list(sp.rglob("__pycache__")) + list(sp.rglob("tests")) + list(sp.rglob("test")):
    if p.is_dir():
        tolti += peso(p)
        shutil.rmtree(p, ignore_errors=True)
print("   liberati %.1f MB" % tolti)

# ---------------------------------------------------------------------------
# Finita l'installazione, `import site` si rispegne: a runtime servirebbe solo
# a far pescare dalla user site della macchina che ospita il programma, cioe' a
# rendere il comportamento dipendente da com'e' messo quel PC. Il _pth continua
# a elencare Lib\site-packages, che e' quello che serve.
# ---------------------------------------------------------------------------
passo("isolamento dalla user site")
righe = [r for r in pth.read_text(encoding="utf-8").splitlines()
         if r.strip() != "import site"]
pth.write_text("\n".join(righe) + "\n", encoding="utf-8")
print("   %s -> %s" % (pth.name, ", ".join(x for x in righe if x.strip())))

passo("verifica")
prova = (
    "import sys; print('   python', sys.version.split()[0]);"
    "import PIL, numpy, scipy, huggingface_hub;"
    "from PIL import Image, ImageFilter; from scipy import ndimage;"
    "import numpy as np;"
    "a = np.zeros((32,32), dtype=np.uint8); a[8:24,8:24] = 255;"
    "_, n = ndimage.label(a > 0);"
    "im = Image.new('RGBA', (16,16), (255,0,0,128)).filter(ImageFilter.GaussianBlur(1));"
    "print('   PIL', PIL.__version__, '| numpy', numpy.__version__,"
    "'| scipy', scipy.__version__, '| hub', huggingface_hub.__version__);"
    "print('   prova: ndimage.label ->', n, '| PIL blur ->', im.size);"
    "print('   percorsi esterni al runtime:',"
    "[p for p in sys.path if 'dist' not in p.replace('/', chr(92))] or 'nessuno')"
)
# cwd fuori dal runtime e senza user site: se il risultato dipendesse dalla
# macchina, qui si vedrebbe.
r = subprocess.run([str(py), "-c", prova], capture_output=True, text=True,
                   env=AMBIENTE, cwd=str(RADICE.parent))
print(r.stdout.rstrip() or r.stderr.rstrip())
if r.returncode != 0:
    raise SystemExit("il runtime non importa le librerie del sidecar")

print("\nruntime pronto: %s" % DEST)
print("peso finale: %.1f MB" % peso(DEST))
