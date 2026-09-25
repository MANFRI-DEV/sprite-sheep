"""Log HTML di una generazione, scritto accanto a sheet e GIF.

Perche' HTML e non JSON: lo apre chiunque con un doppio clic, mostra la GIF
e lo sprite di partenza accanto ai parametri, e resta leggibile anche fuori
dal programma. Tutti i percorsi sono relativi: la cartella si puo' spostare,
zippare o allegare a un messaggio e il log continua a mostrare le immagini.

Le etichette stanno qui e non in `testi.py`: quelli sono messaggi che
viaggiano verso l'interfaccia, questo e' un file che l'utente apre da se'.
La lingua e' comunque quella della sessione.
"""
import html
import time
from pathlib import Path

from testi import lingua

ETICHETTE = {
    "titolo":        {"it": "Log di generazione", "en": "Generation log"},
    "tempi":         {"it": "Tempi", "en": "Timing"},
    "inizio":        {"it": "Inizio", "en": "Start"},
    "fine":          {"it": "Fine", "en": "End"},
    "durata":        {"it": "Durata totale", "en": "Total duration"},
    "inferenza":     {"it": "di cui inferenza", "en": "of which inference"},
    "ingresso":      {"it": "Sprite iniziale", "en": "Input sprite"},
    "originale":     {"it": "File originale", "en": "Original file"},
    "uscita":        {"it": "GIF in uscita", "en": "Output GIF"},
    "foglio":        {"it": "Sprite sheet", "en": "Sprite sheet"},
    "modello":       {"it": "Modello", "en": "Model"},
    "id":            {"it": "Identificativo", "en": "Identifier"},
    "backend":       {"it": "Backend", "en": "Backend"},
    "passi":         {"it": "Passi di campionamento", "en": "Sampling steps"},
    "seed":          {"it": "Seed", "en": "Seed"},
    "animazione":    {"it": "Animazione", "en": "Animation"},
    "secondi":       {"it": "Durata clip", "en": "Clip length"},
    "richiesti":     {"it": "richiesti", "en": "requested"},
    "fotogrammi":    {"it": "Frame generati", "en": "Generated frames"},
    "nel_foglio":    {"it": "Frame nello sheet", "en": "Frames in sheet"},
    "griglia":       {"it": "Griglia", "en": "Grid"},
    "fps_gif":       {"it": "Velocità GIF", "en": "GIF speed"},
    "risoluzione":   {"it": "Risoluzione generata", "en": "Generated resolution"},
    "formato":       {"it": "Formato", "en": "Aspect ratio"},
    "margine":       {"it": "Spazio intorno alla figura", "en": "Space around the figure"},
    "cella":         {"it": "Cella dello sheet", "en": "Sheet cell"},
    "fine_utile":    {"it": "Ultimo frame usato", "en": "Last frame used"},
    "scontorno":     {"it": "Scontorno", "en": "Background removal"},
    "attivo":        {"it": "Attivo", "en": "Enabled"},
    "colore":        {"it": "Colore di fondo scelto", "en": "Chosen background"},
    "via":           {"it": "Metodo", "en": "Method"},
    "via_tinta":     {"it": "tinta unita (chroma key)",
                      "en": "solid colour (chroma key)"},
    "via_chiaro":    {"it": "fondo chiaro, con rimozione ombre",
                      "en": "light background, shadow removal"},
    "tinta_rich":    {"it": "Tinta richiesta", "en": "Requested tint"},
    "tinta_mis":     {"it": "Tinta misurata sul 1° frame",
                      "en": "Tint measured on frame 1"},
    "tolleranza":    {"it": "Tolleranza tinta", "en": "Tint tolerance"},
    "spill":         {"it": "Rimozione riflessi di colore", "en": "Colour spill removal"},
    "filigrana":     {"it": "Filigrana", "en": "Watermark"},
    "prompt":        {"it": "Prompt", "en": "Prompt"},
    "si":            {"it": "sì", "en": "yes"},
    "no":            {"it": "no", "en": "no"},
}


def _e(chiave: str) -> str:
    voce = ETICHETTE[chiave]
    return voce.get(lingua()) or voce["it"]


def _data(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _durata(s: float) -> str:
    s = int(round(s))
    return "%d min %02d s" % (s // 60, s % 60) if s >= 60 else "%d s" % s


def _sino(v: bool) -> str:
    return _e("si") if v else _e("no")


def _righe(voci: list[tuple[str, str]]) -> str:
    """Voci gia' pronte per l'HTML: il valore e' gia' passato da escape."""
    return "\n".join("<tr><th>%s</th><td>%s</td></tr>" % (html.escape(k), v)
                     for k, v in voci)


def _campione(esa: str) -> str:
    return ('<span class="campione" style="background:%s"></span> <code>%s</code>'
            % (html.escape(esa), html.escape(esa)))


STILE = """
body{font:14px/1.45 system-ui,sans-serif;margin:0;background:#f4f4f6;color:#222}
main{max-width:980px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 4px} .sotto{color:#666;margin:0 0 20px}
.immagini{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
 gap:16px;margin-bottom:20px}
figure{margin:0;background:#fff;border-radius:8px;padding:12px;
 box-shadow:0 1px 3px #0002}
figcaption{font-weight:600;margin-bottom:8px}
figure img{display:block;width:100%;aspect-ratio:1;object-fit:contain;
 image-rendering:pixelated;border-radius:4px;
 background:repeating-conic-gradient(#ddd 0 25%,#fff 0 50%) 0 0/16px 16px}
section{background:#fff;border-radius:8px;padding:12px 16px;margin-bottom:16px;
 box-shadow:0 1px 3px #0002}
h2{font-size:16px;margin:4px 0 8px}
table{border-collapse:collapse;width:100%}
th{text-align:left;font-weight:500;color:#555;width:260px;padding:4px 8px 4px 0;
 vertical-align:top}
td{padding:4px 0}
pre{white-space:pre-wrap;background:#f7f7f9;border:1px solid #e3e3e8;
 border-radius:6px;padding:10px;margin:0;font-size:13px}
.campione{display:inline-block;width:14px;height:14px;border:1px solid #999;
 vertical-align:middle;border-radius:3px}
a{color:#2463c9}
"""


def scrivi(dest: Path, nome: str, dati: dict) -> Path:
    """Scrive `<nome>_log.html` in `dest` e ne restituisce il percorso.

    `dati` e' raccolto da `genera._esegui`; le chiavi usate sono quelle lette
    qui sotto. I file nominati (`sprite`, `gif`, `sheet`) devono stare in
    `dest`: nel log finisce solo il nome.
    """
    p = dati["piano"]
    sc = dati.get("scontorno")
    esc = html.escape

    tempi = [
        (_e("inizio"), _data(dati["inizio"])),
        (_e("fine"), _data(dati["fine"])),
        (_e("durata"), _durata(dati["fine"] - dati["inizio"])),
        (_e("inferenza"), _durata(dati["fine_inferenza"] - dati["inizio_inferenza"])),
    ]
    modello = [
        (_e("modello"), esc(dati["modello_nome"])),
        (_e("id"), "<code>%s</code>" % esc(dati["modello_id"])),
        (_e("backend"), esc(dati["backend"])),
    ]
    if dati.get("passi"):
        modello.append((_e("passi"), str(dati["passi"])))
    modello.append((_e("seed"), "<code>%d</code>" % dati["seed"]))

    animazione = [
        (_e("secondi"), "%.2f s <span class=sotto>(%s %.1f s)</span>" % (
            p["durata_effettiva_s"], _e("richiesti"), p["durata_richiesta_s"])),
        (_e("fotogrammi"), "%d @ %d fps" % (p["lunghezza"], p["fps"])),
        (_e("nel_foglio"), str(p["n_frame"])),
        (_e("griglia"), "%d × %d" % (p["colonne"], p["righe"])),
        # Quella reale, non quella chiesta: il GIF conta il ritardo in
        # centesimi di secondo e 12,5 fps diventano 12,5 solo per caso.
        (_e("fps_gif"), "%s fps" % dati.get("fps_gif", p["fps_riproduzione"])),
        (_e("fine_utile"), "%.2f s" % p["fine_utile_s"]),
        (_e("formato"), esc(p["formato"])),
        (_e("margine"), esc(dati.get("margine", "nessuno"))),
        (_e("risoluzione"), "%d × %d px" % (dati["larghezza"], dati["altezza"])),
        (_e("cella"), "%d × %d px" % tuple(dati["cella"])),
        (_e("filigrana"), _sino(dati.get("filigrana", False))),
    ]

    scontorno = [(_e("attivo"), _sino(sc is not None))]
    if sc:
        scontorno += [
            (_e("colore"), "<code>%s</code>" % esc(sc["colore"])),
            (_e("via"), _e("via_tinta") if sc["via"] == "tinta" else _e("via_chiaro")),
        ]
        if sc["via"] == "tinta":
            scontorno += [
                (_e("tinta_rich"), _campione(sc["tinta_richiesta"])),
                (_e("tinta_mis"), _campione(sc["tinta_misurata"])),
                (_e("tolleranza"), str(sc["tolleranza_tinta"])),
                (_e("spill"), _sino(sc["togli_spill"])),
            ]

    def figura(titolo: str, file: str) -> str:
        f = esc(file)
        return ('<figure><figcaption>%s</figcaption><a href="%s">'
                '<img src="%s" alt="%s"></a>'
                '</figure>' % (esc(titolo), f, f, f))

    corpo = f"""<!doctype html>
<html lang="{lingua()}"><head><meta charset="utf-8">
<title>{esc(nome)} — {_e("titolo")}</title>
<style>{STILE}</style></head><body><main>
<h1>{esc(nome)}</h1>
<p class="sotto">{_e("titolo")} · Sprite Sheep {esc(dati["versione"])}</p>
<div class="immagini">
{figura(_e("ingresso"), dati["sprite"])}
{figura(_e("uscita"), dati["gif"])}
{figura(_e("foglio"), dati["sheet"])}
</div>
<section><h2>{_e("tempi")}</h2><table>{_righe(tempi)}</table></section>
<section><h2>{_e("modello")}</h2><table>{_righe(modello)}</table></section>
<section><h2>{_e("animazione")}</h2><table>{_righe(animazione)}</table></section>
<section><h2>{_e("scontorno")}</h2><table>{_righe(scontorno)}</table></section>
<section><h2>{_e("prompt")}</h2><pre>{esc(dati["prompt"])}</pre></section>
<section><table>{_righe([(_e("originale"), "<code>%s</code>" % esc(dati["sprite_originale"]))])}</table></section>
</main></body></html>
"""
    uscita = dest / f"{nome}_log.html"
    uscita.write_text(corpo, encoding="utf-8")
    return uscita
