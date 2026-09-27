"""Regole di lunghezza, griglia, indici e formati. Niente GPU, niente rete.

    python sidecar/test_parametri.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parametri as P

errori: list[str] = []


def verifica(cond, msg):
    if not cond:
        errori.append(msg)


def main() -> int:
    # Lunghezze valide: 17k+5 per H3, 4n+1 per WAN, sempre >= durata chiesta.
    for mid in P.REGOLE:
        r = P.REGOLE[mid]
        for d in (2.0, 2.33, 3.0, 5.0, 7.5, 10.0):
            L = P.lunghezza_valida(mid, d)
            n = L["lunghezza"]
            verifica((n - r["offset"]) % r["passo"] == 0, "%s %.2f s: %d fuori griglia" % (mid, d, n))
            verifica(n <= r["max"], "%s: %d oltre il massimo" % (mid, n))
            if not L["troncata"]:
                verifica(n >= d * r["fps"] - 1e-6, "%s %.2f s: %d frame non coprono" % (mid, d, n))
                verifica(n - r["passo"] < d * r["fps"], "%s %.2f s: %d non e' il primo valido" % (mid, d, n))
    verifica(P.lunghezza_valida("minimax_h3_fast", 2.33)["lunghezza"] == 56, "H3 2,33 s != 56")
    verifica(P.lunghezza_valida("wan22_ti2v_5b", 2.0)["lunghezza"] == 49, "WAN 2 s != 49")
    # Durate fuori campo si portano dentro, non esplodono.
    verifica(P.lunghezza_valida("minimax_h3_fast", 0.1)["durata_richiesta_s"] == P.DURATA_MIN, "min")
    verifica(P.lunghezza_valida("minimax_h3_fast", 99)["durata_richiesta_s"] == P.DURATA_MAX, "max")
    try:
        P.lunghezza_valida("inesistente", 2)
        errori.append("modello sconosciuto accettato")
    except KeyError:
        pass

    # Griglia: contiene i frame, e' quasi quadrata.
    for n in range(P.FRAME_MIN, P.FRAME_MAX + 1):
        c, r = P.griglia_per(n)
        verifica(c * r >= n and c * (r - 1) < n, "griglia %d: %dx%d" % (n, c, r))
        verifica(abs(c - r) <= 1, "griglia %d non quasi quadrata: %dx%d" % (n, c, r))

    # Indici: crescenti, distinti, dentro la parte utile della clip.
    for L in (22, 56, 73, 124):
        for n in (4, 9, 16, 25, 36, 64):
            idx = P.indici_frame(L, n)
            verifica(len(idx) == n, "indici %d/%d: %d" % (L, n, len(idx)))
            verifica(all(b > a for a, b in zip(idx, idx[1:])) or L < n,
                     "indici %d/%d non crescenti" % (L, n))
            verifica(idx[-1] <= L - 1, "indici %d/%d oltre la clip" % (L, n))
            if L >= n / P.FRAZIONE_UTILE:
                verifica(idx[-1] <= int(L * P.FRAZIONE_UTILE), "indici %d/%d oltre la parte utile" % (L, n))

    # Formati: lati multipli di 32, area entro il budget provato su 8 GB,
    # rapporto vicino a quello dichiarato.
    budget = 448 * 448 * 1.08
    for nome, (w, h) in P.FORMATI.items():
        a, b = (int(x) for x in nome.split(":"))
        verifica(w % 32 == 0 and h % 32 == 0, "%s: %dx%d non multipli di 32" % (nome, w, h))
        verifica(w * h <= budget, "%s: area %d oltre il budget" % (nome, w * h))
        verifica(abs(w / h - a / b) / (a / b) < 0.03, "%s: rapporto %.3f" % (nome, w / h))
        cw, ch = P.cella(256, w, h)
        verifica(max(cw, ch) == 256 and abs(cw / ch - w / h) < 0.02, "cella %s: %dx%d" % (nome, cw, ch))
    try:
        P.risoluzione("2:1")
        errori.append("formato sconosciuto accettato")
    except ValueError:
        pass

    # Piano: coerente con i pezzi.
    p = P.piano("minimax_h3_fast", 2.33, 25, "9:16")
    verifica((p["larghezza"], p["altezza"]) == P.FORMATI["9:16"], "piano: risoluzione")
    verifica(p["colonne"] * p["righe"] - p["n_frame"] == p["celle_vuote"], "piano: celle vuote")
    verifica(abs(p["fps_riproduzione"] - 25 / p["durata_effettiva_s"]) < 0.01, "piano: fps")

    for e in errori:
        print("ERRORE:", e)
    print("tutto a posto" if not errori else f"{len(errori)} errori")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
