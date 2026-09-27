"""Il sidecar rifiuta le richieste che non vengono dall'interfaccia?

Si avvia un sidecar vero, su una porta di prova e con un token noto, e gli si
mandano le richieste che una pagina web ostile manderebbe davvero. Il caso che
ha motivato tutto e' il quarto: una POST `text/plain` a `/licenza` con
`accetto: true`, che il browser invia senza preflight e che fino alla 0.0.5 il
sidecar eseguiva — accettando una licenza al posto dell'utente.

    python sidecar/test_sicurezza.py
"""
import http.client
import json
import os
import subprocess
import sys
import time
from pathlib import Path

QUI = Path(__file__).resolve().parent
PORTA = 8799
TOKEN = "prova-" + os.urandom(8).hex()


def chiedi(metodo: str, rotta: str, intestazioni: dict, corpo: str = "") -> int:
    c = http.client.HTTPConnection("127.0.0.1", PORTA, timeout=10)
    # `skip_host` per poter falsificare l'intestazione Host nel caso del DNS
    # rebinding: senza, http.client la scrive da solo.
    c.putrequest(metodo, rotta, skip_host=True)
    h = {"Host": "127.0.0.1:%d" % PORTA}
    h.update(intestazioni)
    for k, v in h.items():
        c.putheader(k, v)
    dati = corpo.encode("utf-8")
    if dati:
        c.putheader("Content-Length", str(len(dati)))
    c.endheaders(dati or None)
    r = c.getresponse()
    r.read()
    c.close()
    return r.status


CASI = [
    # (descrizione, metodo, rotta, intestazioni, corpo, stato atteso)
    ("interfaccia, con token", "GET", "/modelli",
     {"X-SpriteSheep-Token": TOKEN}, "", 200),
    ("senza token", "GET", "/modelli", {}, "", 403),
    ("token sbagliato", "GET", "/modelli",
     {"X-SpriteSheep-Token": "indovinato"}, "", 403),
    ("pagina web: POST text/plain a /licenza", "POST", "/licenza",
     {"Origin": "https://sito-ostile.example", "Content-Type": "text/plain"},
     json.dumps({"modello": "minimax_h3_fl2va", "accetto": True}), 403),
    ("pagina web anche col token giusto", "GET", "/modelli",
     {"Origin": "https://sito-ostile.example",
      "X-SpriteSheep-Token": TOKEN}, "", 403),
    ("DNS rebinding (Host estraneo)", "GET", "/modelli",
     {"Host": "sito-ostile.example:%d" % PORTA,
      "X-SpriteSheep-Token": TOKEN}, "", 403),
    ("/health senza token (serve a riconoscere un sidecar appeso)", "GET",
     "/health", {}, "", 200),
    ("/health da una pagina web", "GET", "/health",
     {"Origin": "https://sito-ostile.example"}, "", 403),
]


def main() -> int:
    env = dict(os.environ, SPRITESHEEP_TOKEN=TOKEN)
    proc = subprocess.Popen([sys.executable, str(QUI / "server.py"),
                             "--port", str(PORTA)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                chiedi("GET", "/health", {})
                break
            except OSError:
                time.sleep(0.5)
        else:
            print("il sidecar di prova non si e' avviato")
            return 1

        errori = 0
        for desc, metodo, rotta, h, corpo, atteso in CASI:
            avuto = chiedi(metodo, rotta, h, corpo)
            ok = avuto == atteso
            errori += not ok
            print("   %-58s %d %s" % (desc, avuto,
                                      "" if ok else "ERRORE: atteso %d" % atteso))
        print("\n%s" % ("tutto a posto" if not errori else "%d errori" % errori))
        return 1 if errori else 0
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
