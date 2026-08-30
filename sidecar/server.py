"""Sidecar HTTP di Sprite Sheep.

Godot avvia questo processo e ci parla su localhost. Usa solo la stdlib:
niente fastapi/uvicorn, cosi' gira nel venv di ComfyUI senza installare nulla.

Avvio:
    python server.py [--port 8765]

Rotte:
    GET  /health     -> stato del sidecar e capacita' rilevate
    GET  /edizione   -> edizione attiva, filigrana, generazioni rimaste
    POST /analizza   -> ispeziona un'immagine (dimensioni, alfa, sfondo)
    POST /scontorna  -> rimuove lo sfondo, scrive un PNG con alfa
    POST /prompt     -> compone il prompt dai campi e lo valida (semaforo)
    GET  /modelli    -> catalogo con stato di installazione e download
    POST /licenza    -> registra l'accettazione della licenza di un modello
    POST /scarica    -> avvia il download (solo a licenza accettata)
    POST /cerca_modelli -> collega pesi gia' presenti in una cartella
    POST /lingua     -> imposta la lingua dei messaggi (it/en)
    POST /piano      -> durata + frame -> lunghezza valida, griglia, indici
    POST /genera     -> avvia la generazione (asincrona)
    GET  /genera     -> stato di un lavoro (?job=...)
    GET  /comfyui    -> passi della procedura guidata di installazione
    POST /comfyui    -> imposta il percorso oppure avvia ComfyUI
"""
import argparse
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Il Python incorporato nella distribuzione usa un file `._pth`, e quel file
# fissa sys.path per intero: la cartella dello script, che l'avvio normale
# metterebbe in testa, non c'e'. Senza questa riga gli import qui sotto
# falliscono con ModuleNotFoundError appena si esce dall'ambiente di sviluppo.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import comfyui_setup
import config
import edizione
import genera as genera_mod
import modelli
import parametri
import prompt as prompt_mod
import scontorno
import testi


def rileva_capacita() -> dict:
    """Cosa e' disponibile in questo ambiente. Non fa fallire il sidecar
    se torch manca: l'UI deve poter partire e dirlo all'utente.

    La GPU la si chiede a ComfyUI, non a torch. Il runtime distribuito con
    l'applicazione non ha PyTorch di proposito — sarebbero svariati GB per
    duplicare quello che ComfyUI ha gia' — e senza torch il sidecar
    concludeva "CUDA non disponibile" pur avendo una 3050 che lavorava.
    L'unico processo che sa davvero com'e' messa la GPU e' quello che ci
    calcola sopra.
    """
    cap = {"torch": None, "cuda": False, "gpu": None, "vram_mb": None,
           "fonte_gpu": None}
    try:
        import torch
        cap["torch"] = torch.__version__
        cap["cuda"] = bool(torch.cuda.is_available())
        if cap["cuda"]:
            cap["gpu"] = torch.cuda.get_device_name(0)
            cap["vram_mb"] = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
            cap["fonte_gpu"] = "torch"
    except Exception as e:
        cap["errore"] = f"{type(e).__name__}: {e}"

    if not cap["cuda"]:
        cap.update(_gpu_da_comfyui())

    # Le dipendenze vere vanno controllate all'avvio, non quando servono: se
    # huggingface_hub manca ce ne si accorgeva solo a download avviato, e il
    # sintomo era una barra ferma a zero senza spiegazione.
    import importlib.util
    mancanti = [nome for nome in ("huggingface_hub", "PIL", "numpy", "scipy")
                if importlib.util.find_spec(nome) is None]
    cap["dipendenze_mancanti"] = mancanti
    cap["puo_scaricare"] = "huggingface_hub" not in mancanti
    return cap


def _nome_gpu(grezzo: str) -> str:
    """Da "cuda:0 NVIDIA GeForce RTX 3050 : cudaMallocAsync" a
    "NVIDIA GeForce RTX 3050".

    ComfyUI impacchetta backend, indice e allocatore nello stesso campo. In una
    barra di stato serve il nome della scheda: il resto e' rumore.
    """
    import re
    s = re.sub(r"^\s*(cuda|cpu|mps|xpu|rocm)\s*:?\s*\d*\s*", "", grezzo,
               flags=re.I)
    s = re.sub(r"\s*:\s*[A-Za-z]+\s*$", "", s)   # via l'allocatore in coda
    return s.strip() or grezzo.strip()


def _gpu_da_comfyui() -> dict:
    """Nome e memoria della GPU secondo ComfyUI, se sta rispondendo.

    `comfyui_spenta` distingue i due casi che l'interfaccia deve raccontare in
    modo diverso: "non lo so ancora, accendi ComfyUI" non e' "non hai una GPU".
    """
    try:
        from backend.comfyui_bridge import _get
        d = _get("/system_stats")
    except Exception:
        return {"comfyui_spenta": True}

    for dev in d.get("devices", []):
        tipo = str(dev.get("type", "")).lower()
        nome = str(dev.get("name", ""))
        if tipo == "cpu" or nome.lower().startswith("cpu"):
            continue
        pulito = _nome_gpu(nome)
        return {
            "cuda": True,
            "gpu": pulito or nome,
            "vram_mb": int(dev.get("vram_total", 0)) // (1024 * 1024),
            "vram_libera_mb": int(dev.get("vram_free", 0)) // (1024 * 1024),
            "fonte_gpu": "comfyui",
            "comfyui_spenta": False,
        }
    return {"comfyui_spenta": False}


class Server(ThreadingHTTPServer):
    # Su Windows SO_REUSEADDR lascia legare piu' processi alla stessa porta:
    # le richieste finirebbero a caso su uno qualsiasi. Meglio fallire subito.
    allow_reuse_address = False
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    server_version = f"SpriteSheep/{config.VERSION}"

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/health":
            self._json(200, {
                "ok": True,
                "app": config.APP_NAME,
                "version": config.VERSION,
                "python": sys.version.split()[0],
                "models_dir": str(config.MODELS_DIR),
                "output_dir": str(config.OUTPUT_DIR),
                "capacita": rileva_capacita(),
                "bypass_licenze": bool(getattr(config, "BYPASS_LICENZE", False)),
                "edizione": edizione.stato(),
                "lingua": testi.lingua(),
            })
        elif self.path.split("?")[0] == "/edizione":
            self._json(200, {"ok": True, "edizione": edizione.stato()})
        elif self.path.split("?")[0] == "/modelli":
            self._json(200, {"ok": True, "modelli": modelli.elenco()})
        elif self.path.split("?")[0] == "/comfyui":
            self._json(200, {"ok": True, "setup": comfyui_setup.stato()})
        elif self.path.split("?")[0] == "/genera":
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            self._json(200, {"ok": True,
                             "stato": genera_mod.stato((q.get("job") or [""])[0])})
        else:
            self._json(404, {"ok": False, "errore": "rotta sconosciuta"})

    def _leggi_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_POST(self) -> None:
        rotta = self.path.split("?")[0]
        try:
            dati = self._leggi_json()
        except Exception as e:
            self._json(400, {"ok": False, "errore": f"JSON non valido: {e}"})
            return

        try:
            if rotta == "/analizza":
                src = dati.get("sorgente", "")
                if not src or not Path(src).is_file():
                    self._json(400, {"ok": False, "errore": "sorgente inesistente"})
                    return
                self._json(200, {"ok": True, "info": scontorno.analizza(src)})

            elif rotta == "/scontorna":
                src = dati.get("sorgente", "")
                if not src or not Path(src).is_file():
                    self._json(400, {"ok": False, "errore": "sorgente inesistente"})
                    return
                dst = dati.get("destinazione") or str(
                    config.CACHE_DIR / (Path(src).stem + "_scontornato.png"))
                res = scontorno.scontorna(
                    src, dst,
                    tolleranza=int(dati.get("tolleranza", 225)),
                    rimuovi_ombra=bool(dati.get("rimuovi_ombra", True)),
                )
                self._json(200, {"ok": True, "risultato": res})

            elif rotta == "/prompt":
                durata = float(dati.get("durata_s", 2.0))
                # Il modello decide il dialetto: H3 e WAN vogliono prompt diversi.
                mod = dati.get("modello") or None
                # Se arriva gia' un testo (l'utente l'ha modificato a mano)
                # si valida quello; altrimenti si compone dai campi.
                testo = dati.get("testo")
                if not testo:
                    testo = prompt_mod.componi(dati.get("campi", {}), mod)
                self._json(200, {
                    "ok": True,
                    "testo": testo,
                    "validazione": prompt_mod.valida(testo, durata, mod),
                })

            elif rotta == "/licenza":
                mid = dati.get("modello", "")
                if mid not in modelli.CATALOGO:
                    self._json(400, {"ok": False, "errore": "modello sconosciuto"})
                    return
                if not bool(dati.get("accetto", False)):
                    self._json(400, {"ok": False,
                                     "errore": "accettazione esplicita mancante"})
                    return
                self._json(200, {"ok": True, "registrato": modelli.accetta_licenza(mid)})

            elif rotta == "/scarica":
                self._json(200, modelli.avvia_download(dati.get("modello", "")))

            elif rotta == "/lingua":
                # Una lingua per sessione: l'app e' locale e monoutente.
                self._json(200, {"ok": True,
                                 "lingua": testi.imposta_lingua(dati.get("lingua", "it"))})

            elif rotta == "/cerca_modelli":
                # Pesi gia' sul disco dell'utente: si collegano, non si copiano.
                self._json(200, modelli.cerca_in_cartella(
                    dati.get("modello", ""), dati.get("cartella", "")))

            elif rotta == "/piano":
                self._json(200, {"ok": True, "piano": parametri.piano(
                    dati.get("modello", ""),
                    float(dati.get("durata_s", 2.0)),
                    int(dati.get("n_frame", 25)))})

            elif rotta == "/genera":
                self._json(200, genera_mod.avvia(dati))

            elif rotta == "/comfyui":
                azione = dati.get("azione", "")
                if azione == "percorso":
                    self._json(200, comfyui_setup.imposta_percorso(dati.get("percorso", "")))
                elif azione == "avvia":
                    self._json(200, comfyui_setup.avvia())
                else:
                    self._json(400, {"ok": False,
                                     "errore": "azione: 'percorso' oppure 'avvia'"})

            else:
                self._json(404, {"ok": False, "errore": "rotta sconosciuta"})

        except Exception as e:
            # L'UI deve poter mostrare il motivo, non un generico "errore"
            sys.stderr.write(traceback.format_exc())
            self._json(500, {"ok": False, "errore": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        # Log compatto su stderr: Godot lo legge dal processo figlio
        sys.stderr.write(f"[sidecar] {fmt % args}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Sidecar di Sprite Sheep")
    ap.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    args = ap.parse_args()

    try:
        srv = Server((config.HOST, args.port), Handler)
    except OSError as e:
        print(f"SPRITESHEEP_PORTA_OCCUPATA {config.HOST}:{args.port} ({e})", flush=True)
        sys.exit(2)
    # Riga sentinella: Godot aspetta questa prima di considerarlo pronto
    print(f"SPRITESHEEP_READY {config.HOST}:{args.port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
