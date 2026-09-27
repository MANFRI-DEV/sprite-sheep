"""Client WebSocket minimo per l'avanzamento di ComfyUI.

## Perche' esiste

Fino alla 0.0.4 la barra restava a meta' per tutta l'inferenza: il ponte
chiamava `avanzamento(0.5)` e poi non aveva altro da dire. Su una generazione
da dieci minuti, una barra ferma e' indistinguibile da un programma bloccato.

Il dato vero c'e', ma **su HTTP non esiste**. `/history` dice solo se il lavoro
e' finito; `/queue` quanti ne restano. Quale nodo sta girando e a che punto e'
il sampler passano solo dal WebSocket.

## Perche' scritto a mano

Aggiungere `websocket-client` avrebbe messo una dipendenza in piu' a carico
dell'utente, che deve gia' installare pillow, numpy, scipy e huggingface_hub.
Per leggere messaggi di testo da un server locale serve poco: handshake HTTP
con la chiave in base64, poi i frame. Sono un centinaio di righe contro un
pacchetto e una riga in piu' nei requisiti.

Si legge e basta: non si manda mai niente al server oltre l'handshake, quindi
il mascheramento dei frame in uscita — la parte fastidiosa del protocollo —
non serve.

## Cosa non fa

Non gestisce i frame frammentati con payload sopra i 64 KB di continuazione
complessa, ne' le estensioni (compressione per messaggio). ComfyUI non le usa
per questi messaggi. Se un frame non si capisce, si smette di leggere e si
torna al comportamento di prima: **la generazione non deve dipendere dalla
barra**, e un avanzamento che si rompe non puo' portarsi via dieci minuti di
GPU.
"""
import base64
import json
import os
import socket
import struct
import threading
import urllib.parse


class AscoltoComfy:
    """Ascolta il WebSocket di ComfyUI e riferisce cosa sta succedendo.

    Si usa come contesto:

        with AscoltoComfy(url, client_id, su_evento):
            ...lancia il lavoro e aspetta...
    """

    def __init__(self, url_http: str, client_id: str, su_evento) -> None:
        self.url = url_http
        self.client_id = client_id
        self.su_evento = su_evento
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._fermo = threading.Event()

    # ------------------------------------------------------------------
    # Ciclo di vita
    # ------------------------------------------------------------------
    def __enter__(self) -> "AscoltoComfy":
        try:
            self._apri()
        except Exception:
            # Nessun avanzamento dettagliato, ma il lavoro va avanti lo stesso.
            self._sock = None
            return self
        self._thread = threading.Thread(target=self._ascolta, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_) -> None:
        self._fermo.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Handshake
    # ------------------------------------------------------------------
    def _apri(self) -> None:
        p = urllib.parse.urlparse(self.url)
        host = p.hostname or "127.0.0.1"
        porta = p.port or (443 if p.scheme == "https" else 80)

        s = socket.create_connection((host, porta), timeout=10)
        s.settimeout(5.0)
        chiave = base64.b64encode(os.urandom(16)).decode()
        richiesta = (
            "GET /ws?clientId=%s HTTP/1.1\r\n"
            "Host: %s:%d\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ) % (urllib.parse.quote(self.client_id), host, porta, chiave)
        s.sendall(richiesta.encode())

        # La risposta puo' arrivare spezzata: si legge finche' non si vede la
        # riga vuota che chiude le intestazioni.
        dati = b""
        while b"\r\n\r\n" not in dati:
            pezzo = s.recv(4096)
            if not pezzo:
                raise ConnectionError("handshake interrotto")
            dati += pezzo
            if len(dati) > 65536:
                raise ConnectionError("intestazioni troppo lunghe")
        if b"101" not in dati.split(b"\r\n", 1)[0]:
            raise ConnectionError("upgrade rifiutato: %r" % dati[:80])

        self._sock = s
        self._resto = dati.split(b"\r\n\r\n", 1)[1]

    # ------------------------------------------------------------------
    # Lettura dei frame
    # ------------------------------------------------------------------
    def _leggi(self, n: int) -> bytes:
        """n byte esatti, tenendo conto di quanto e' gia' arrivato con le
        intestazioni: il primo frame viaggia spesso nello stesso pacchetto.

        **Un silenzio non e' una fine.** Il socket ha cinque secondi di
        timeout, e fra un nodo e l'altro ComfyUI puo' stare zitto per minuti:
        caricare ventidue giga di pesi da disco ne prende tre. Trattando il
        timeout come errore l'ascolto moriva li' — e moriva **sempre nello
        stesso punto**, subito prima del campionamento, che e' l'unica fase
        per cui la barra serviva davvero. Da fuori sembrava che ComfyUI non
        riportasse i passi; era il lettore che se n'era andato.
        """
        fuori = b""
        if self._resto:
            fuori = self._resto[:n]
            self._resto = self._resto[n:]
        while len(fuori) < n:
            if self._fermo.is_set() or self._sock is None:
                raise ConnectionError("chiuso")
            try:
                pezzo = self._sock.recv(n - len(fuori))
            except TimeoutError:
                continue          # nessun dato per ora: si aspetta ancora
            except OSError as e:
                # `socket.timeout` e' TimeoutError da Python 3.10, ma su
                # Windows certi attesi scadono come OSError con errno 10060.
                if getattr(e, "errno", None) in (10060, 10035):
                    continue
                raise
            if not pezzo:
                raise ConnectionError("connessione chiusa")
            fuori += pezzo
        return fuori

    def _frame(self) -> tuple[int, bytes]:
        b0, b1 = self._leggi(2)
        opcode = b0 & 0x0F
        lunghezza = b1 & 0x7F
        if lunghezza == 126:
            lunghezza = struct.unpack(">H", self._leggi(2))[0]
        elif lunghezza == 127:
            lunghezza = struct.unpack(">Q", self._leggi(8))[0]
        # Il server non maschera mai: se lo facesse, il bit sarebbe acceso e
        # andrebbe letta anche la chiave. Meglio accorgersene che leggere
        # payload sfasato.
        if b1 & 0x80:
            self._leggi(4)
        return opcode, self._leggi(lunghezza)

    def _ascolta(self) -> None:
        try:
            while not self._fermo.is_set():
                opcode, corpo = self._frame()
                if opcode == 0x8:            # close
                    return
                if opcode != 0x1:            # binario: sono le anteprime
                    continue
                try:
                    messaggio = json.loads(corpo.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                self.su_evento(messaggio)
        except Exception:
            # Silenzio di proposito: qui si perde solo il dettaglio della
            # barra, e farlo salire fermerebbe una generazione sana.
            return
