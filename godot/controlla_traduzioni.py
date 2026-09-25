"""Quali testi dell'interfaccia non hanno una traduzione.

Una stringa senza riga in `traduzioni.csv` non da' errore: Godot mostra
l'originale. Con l'interfaccia in inglese questo vuol dire italiano in mezzo
all'inglese, ed e' invisibile finche' qualcuno non apre il programma nella
lingua sbagliata e legge tutto.

    python godot/controlla_traduzioni.py

Esce con 1 se manca qualcosa, cosi' si puo' mettere in una verifica automatica.
"""
import csv
import re
import sys
from pathlib import Path

QUI = Path(__file__).resolve().parent

# Testo vero e proprio: `tr("...")` negli script, e le proprieta' dei controlli
# nelle scene, che Godot traduce da solo.
RE_TR = re.compile(r'tr\(\s*"([^"]*)"')
RE_SCENA = re.compile(
    r'^(?:text|placeholder_text|tooltip_text|title|ok_button_text)\s*=\s*"([^"]*)"',
    re.M)

# Da ignorare: marchi, valori di esempio che il codice sovrascrive subito, e
# simboli. Tradurre "12 fps" non servirebbe a niente: quel testo nella scena
# esiste solo perche' l'etichetta non nasca vuota nell'editor.
IGNORA = {"", "Sprite Sheep", "SPRITE SHEEP", "Discord", "Ko-fi", "Magenta",
          "FREE", "+", "−", "0%", "12 fps", "2.0 s", "idle"}


def chiavi_note() -> set[str]:
    fuori = set()
    with open(QUI / "traduzioni.csv", encoding="utf-8") as f:
        for riga in csv.reader(f):
            if riga:
                fuori.add(riga[0])
    return fuori


# Due letterali attaccati da un `+` sono una stringa sola: GDScript li unisce
# in compilazione, quindi `tr()` riceve il testo intero e nel csv sta intero.
# Senza questo passaggio il controllo vedeva solo il primo pezzo e segnalava
# come mancante una riga che c'era.
RE_GIUNTA = re.compile(r'"\s*\+\s*"')


def usate() -> dict[str, set[str]]:
    fuori: dict[str, set[str]] = {}
    for p in sorted(QUI.glob("**/*.gd")):
        for m in RE_TR.finditer(RE_GIUNTA.sub("", p.read_text(encoding="utf-8"))):
            fuori.setdefault(m.group(1), set()).add(p.name)
    for p in sorted(QUI.glob("**/*.tscn")):
        for m in RE_SCENA.finditer(p.read_text(encoding="utf-8")):
            fuori.setdefault(m.group(1), set()).add(p.name)
    return fuori


def main() -> int:
    note = chiavi_note()
    tutte = usate()
    mancanti = {k: v for k, v in tutte.items()
                if k not in note and k.strip() and k not in IGNORA}

    print("%d stringhe in interfaccia, %d righe in csv, %d senza traduzione"
          % (len(tutte), len(note), len(mancanti)))
    for k in sorted(mancanti):
        print('  "%s"   [%s]' % (k, ", ".join(sorted(mancanti[k]))))

    # Righe del csv che questo controllo non vede usate.
    #
    # **Non sono per forza da cancellare.** Una stringa passata da una
    # costante — `tr(v[1])`, `tr(SEZIONI[i][1])` — qui non compare, perche' il
    # controllo legge il testo letterale dentro `tr(...)` e li' c'e' un nome di
    # variabile. Le voci delle tendine e i titoli del wizard finiscono tutti in
    # questo elenco pur essendo usatissimi. Serve a notare le vere dimenticanze,
    # non a fare pulizia automatica.
    orfane = sorted(k for k in note
                    if k not in tutte and k not in ("keys",) and k.strip())
    if orfane:
        print("\n%d righe del csv non viste (molte sono passate da costanti):"
              % len(orfane))
    return 1 if mancanti else 0


if __name__ == "__main__":
    sys.exit(main())
