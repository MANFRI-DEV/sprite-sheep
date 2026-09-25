"""Backend ponte: delega l'inferenza a una ComfyUI installata dall'utente.

Scelta di licenza: ComfyUI e' GPL-3.0. Sprite Sheep **non la ridistribuisce**
e non la incorpora: la trova sul sistema e ci parla via HTTP su localhost.
Non c'e' linking ne' distribuzione, quindi il copyleft non si estende a questo
software. Il prezzo e' che l'utente deve installarla: se ne occupa la procedura
guidata (`comfyui_setup.py`).

Il grafo viene costruito qui, con **soli nodi del core di ComfyUI**: nessun
custom node richiesto, cosi' la procedura guidata deve solo verificare che
ComfyUI ci sia e sia aggiornata.

Interfaccia rispettata: entra sprite + prompt, esce una lista di frame. Il
resto della catena non sa che dietro c'e' ComfyUI.
"""
import io
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

from testi import t

from . import Backend
from .comfy_ws import AscoltoComfy

COMFY = "http://127.0.0.1:8188"
COLONNE_STRIP = 8      # griglia di servizio per riportare indietro i frame

# Nodi usati dal grafo: tutti core. Serve alla procedura guidata per il controllo.
CLASSI_RICHIESTE = [
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage",
    "MiniMaxH3ImageToVideo", "KSamplerSelect", "BasicGuider", "BasicScheduler",
    "RandomNoise", "SamplerCustomAdvanced", "VAEDecode", "ImageGrid", "SaveImage",
]


# ----------------------------------------------------------------------
# Avanzamento: da quale nodo sta girando a che frazione del lavoro e' fatta.
#
# I pesi non sono uguali perche' i tempi non lo sono. Su una clip da 56 frame
# a 448x448 su una 3050, il campionamento si prende circa tre quarti del
# tempo e la decodifica VAE quasi tutto il resto; caricare i pesi pesa poco
# ma non zero, ed e' la parte in cui l'utente vede la barra ferma piu' a lungo
# la **prima** volta, perche' i 20 GB del modello arrivano da disco.
#
# Le frasi stanno in `testi.py` come tutto il resto di quello che l'utente
# legge: qui restano solo gli identificativi.
#
# nodo -> (inizio, peso, chiave del testo)
# ----------------------------------------------------------------------
FASI = {
    "1": (0.00, 0.06, "fase.unet"),
    "2": (0.06, 0.04, "fase.clip"),
    "3": (0.10, 0.01, "fase.vae"),
    "5": (0.11, 0.01, "fase.sprite"),
    "6": (0.12, 0.02, "fase.condizionamento"),
    "7": (0.14, 0.00, "fase.sampler"),
    "8": (0.14, 0.00, "fase.sampler"),
    "9": (0.14, 0.01, "fase.sampler"),
    "10": (0.15, 0.00, "fase.rumore"),
    "11": (0.15, 0.70, "fase.campiono"),
    "12": (0.85, 0.12, "fase.decodifico"),
    "13": (0.97, 0.01, "fase.striscia"),
    "14": (0.98, 0.01, "fase.salvo"),
}


def _post(rotta: str, corpo: dict) -> dict:
    req = urllib.request.Request(
        COMFY + rotta, data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        # Quando ComfyUI rifiuta un grafo risponde 400 **con il motivo nel
        # corpo**, e urllib lo tiene nell'eccezione senza che nessuno lo legga:
        # saliva solo "HTTP Error 400: Bad Request", che a un utente non dice
        # niente e a noi nemmeno. Il motivo tipico e' che il file dei pesi non
        # sta nella cartella di ComfyUI, quindi il nome non e' fra i valori
        # ammessi dal nodo e la validazione lo scarta.
        raise RuntimeError(t("gen.grafo_rifiutato",
                             dettaglio=_dettaglio_errore(e))) from None


def _dettaglio_errore(e: urllib.error.HTTPError) -> str:
    """Il perche' del rifiuto, estratto dal corpo della risposta di ComfyUI.

    Il corpo ha due parti utili: `error` con il messaggio generale e
    `node_errors` con un errore per nodo. Quello che serve davvero e' il
    `details` dei nodi ("unet_name: '...' not in []"): dice quale file non
    viene visto e da quale nodo.
    """
    try:
        corpo = json.loads(e.read().decode("utf-8", "replace"))
    except Exception:
        return "HTTP %s" % e.code

    pezzi = []
    generale = corpo.get("error") or {}
    if isinstance(generale, dict):
        for chiave in ("message", "details"):
            v = str(generale.get(chiave) or "").strip()
            if v and v not in pezzi:
                pezzi.append(v)

    for nodo, info in (corpo.get("node_errors") or {}).items():
        classe = (info or {}).get("class_type") or nodo
        for err in (info or {}).get("errors") or []:
            v = str(err.get("details") or err.get("message") or "").strip()
            if v:
                pezzi.append("%s: %s" % (classe, v))

    return " — ".join(pezzi) if pezzi else "HTTP %s" % e.code


def _get(rotta: str, timeout: int = 60) -> dict:
    return json.load(urllib.request.urlopen(COMFY + rotta, timeout=timeout))


class Annullato(RuntimeError):
    """L'utente ha fermato la generazione. Non e' un guasto, e non va
    raccontato come tale: l'interfaccia lo mostra come stato, non come errore
    con traccia da copiare."""


def annulla_prompt(job: str) -> None:
    """Toglie il lavoro dalla coda di ComfyUI e ferma quello in esecuzione.

    Servono due chiamate perche' il lavoro puo' trovarsi in due posti: ancora
    in coda (lo toglie `/queue`) oppure gia' sulla GPU (lo ferma
    `/interrupt`, al primo confine fra un passo e l'altro — fino a una
    trentina di secondi con FastH3 su una 3050). Le si fanno entrambe senza
    chiedersi dove sia: sbagliarsi costa una richiesta a vuoto, indovinare
    costerebbe una GPU che continua a macinare per niente.

    `/interrupt` ferma **quello che sta girando**, qualunque sia. Qui e'
    accettabile perche' la GPU la usa un lavoro alla volta, e quello e' il
    nostro; il giorno che ci fosse una coda di piu' lavori andra' ristretto.
    """
    for rotta, corpo in (("/queue", {"delete": [job]}), ("/interrupt", {})):
        try:
            _post(rotta, corpo)
        except Exception:
            pass


def comfy_disponibile() -> bool:
    try:
        _get("/system_stats")
        return True
    except Exception:
        return False


def carica_immagine(percorso: Path) -> str:
    """Manda lo sprite a ComfyUI con la sua stessa API di caricamento.

    Prima lo si copiava in `<cartella indovinata>/input/`. La cartella la
    indicava la procedura guidata, e non e' detto che sia quella che ComfyUI
    legge davvero: Desktop tiene i propri dati altrove, `--input-directory`
    la sposta, e `extra_model_paths.yaml` puo' spostare tutto. Quando non
    coincidono, ComfyUI risponde `Invalid image file` su un file che sul disco
    c'e' eccome — solo non dove lui guarda.

    `POST /upload/image` non ha questo problema: e' ComfyUI stessa a scrivere
    il file dove lo cerchera' poi, e a dirci con che nome.
    """
    nome = "spritesheep_" + percorso.name
    confine = "----SpriteSheep%d" % int(time.time() * 1000)
    corpo = b"".join([
        ("--%s\r\n" % confine).encode(),
        ('Content-Disposition: form-data; name="image"; filename="%s"\r\n'
         % nome).encode("utf-8"),
        b"Content-Type: application/octet-stream\r\n\r\n",
        percorso.read_bytes(), b"\r\n",
        ("--%s\r\n" % confine).encode(),
        b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        ("--%s--\r\n" % confine).encode(),
    ])
    req = urllib.request.Request(
        COMFY + "/upload/image", data=corpo,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % confine})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    sotto = r.get("subfolder") or ""
    return "%s/%s" % (sotto, r["name"]) if sotto else r["name"]


def scarica_uscita(im: dict) -> bytes:
    """I byte di un'immagine prodotta, chiesti a ComfyUI invece che al disco.

    Stessa ragione del caricamento: la cartella `output/` che vediamo noi puo'
    non essere quella in cui ComfyUI scrive.
    """
    q = urllib.parse.urlencode({"filename": im["filename"],
                                "subfolder": im.get("subfolder", ""),
                                "type": im.get("type", "output")})
    with urllib.request.urlopen(COMFY + "/view?" + q, timeout=300) as r:
        return r.read()


def _valori_ammessi(classe: str, campo: str) -> list[str]:
    """L'elenco di file che un nodo accetta davvero, chiesto a ComfyUI."""
    try:
        info = _get("/object_info/%s" % classe, timeout=30)
    except Exception:
        return []
    sezione = (info.get(classe) or {}).get("input") or {}
    for gruppo in ("required", "optional"):
        voce = (sezione.get(gruppo) or {}).get(campo)
        if isinstance(voce, list) and voce and isinstance(voce[0], list):
            return [str(x) for x in voce[0]]
    return []


def _somiglia(nome: str, obbligatorie: tuple, evita: tuple) -> bool:
    b = nome.lower()
    return all(k in b for k in obbligatorie) and not any(k in b for k in evita)


def _scegli(classe: str, campo: str, atteso: str,
            obbligatorie: tuple, evita: tuple = ()) -> str:
    """Il nome da mettere nel grafo: quello atteso se c'e', altrimenti la
    variante equivalente che ComfyUI ha davvero.

    I nomi dei pesi erano scritti nel codice, esatti fino al suffisso di
    quantizzazione. Chi aveva gia' MiniMax H3 in ComfyUI, ma nella versione
    `int8_convrot` invece di `fp8_scaled`, si vedeva rifiutare il grafo pur
    avendo il modello giusto installato — e la soluzione suggerita, scaricare
    i pesi, gli avrebbe fatto riprendere venti giga di un modello che aveva.

    Il nome esatto resta la prima scelta, perche' e' quello provato. Se manca,
    si accetta un file della stessa famiglia e ruolo.
    """
    ammessi = _valori_ammessi(classe, campo)
    if atteso in ammessi:
        return atteso
    candidati = [n for n in ammessi if _somiglia(n, obbligatorie, evita)]
    if candidati:
        # A parita' di famiglia si preferisce il nome piu' corto: le varianti
        # aggiungono suffissi, e il piu' corto e' di solito quello base.
        return sorted(candidati, key=lambda n: (len(n), n))[0]
    raise RuntimeError(t("gen.pesi_assenti", campo=campo, atteso=atteso,
                         elenco=", ".join(ammessi) or "—"))


def costruisci_grafo(immagine: str, prompt: str, lunghezza: int,
                     larghezza: int, altezza: int, seed: int,
                     modelli: dict, passi: int = 20) -> dict:
    """Grafo in formato API, soli nodi core."""
    righe = math.ceil(lunghezza / COLONNE_STRIP)
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": modelli["diffusion"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": modelli["text_encoder"], "type": "minimax", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": modelli["vae"]}},
        # Il VAE audio non entra nel grafo: il nodo H3 di ComfyUI espone un solo
        # ingresso `vae`, quello video, usato sia qui sia in decodifica.
        "5": {"class_type": "LoadImage", "inputs": {"image": immagine}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0],
            "first_frame": ["5", 0], "prompt": prompt,
            "width": larghezza, "height": altezza, "length": lunghezza}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "8": {"class_type": "BasicGuider", "inputs": {
            "model": ["1", 0], "conditioning": ["6", 0]}},
        "9": {"class_type": "BasicScheduler", "inputs": {
            "model": ["1", 0], "scheduler": "simple", "steps": passi, "denoise": 1.0}},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": int(seed)}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["10", 0], "guider": ["8", 0], "sampler": ["7", 0],
            "sigmas": ["9", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {
            "samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "ImageGrid", "inputs": {
            "images": ["12", 0], "columns": COLONNE_STRIP,
            "cell_width": larghezza, "cell_height": altezza, "padding": 0}},
        "14": {"class_type": "SaveImage", "inputs": {
            "images": ["13", 0], "filename_prefix": "SpriteSheep/raw"}},
    }, righe


class BackendComfyUIH3(Backend):
    nome = "MiniMax H3 via ComfyUI"

    ## Passi di campionamento. Venti e' il numero su cui H3 e' tarato: sotto,
    ## il movimento si sfalda. La variante distillata ne vuole otto e basta.
    PASSI = 20

    # Nomi preferiti: sono quelli che il programma scarica e su cui e' provato.
    # Non sono gli unici accettati — `_scegli` ripiega su una variante dello
    # stesso modello se ComfyUI ha quella.
    MODELLI = {
        "diffusion": "minimax_h3_fl2va_pruned_fp8_scaled.safetensors",
        "text_encoder": "qwen3vl_32b_minimax_h3_int4_convrot.safetensors",
        "vae": "minimax_h3_video_vae_fp16.safetensors",
    }

    ## Come si riconosce un file dello stesso ruolo quando il nome esatto manca.
    ## Il VAE audio esiste e sta nella stessa cartella del VAE video: va escluso
    ## esplicitamente, altrimenti puo' vincere lui perche' ha il nome piu' corto.
    FAMIGLIA = {
        # `fl2va` e' obbligatorio, non decorativo: nella stessa cartella puo'
        # esserci `minimax_h3_ref2va`, che e' un altro compito — reference to
        # video invece di first-last to video. Accettarlo non darebbe errore,
        # darebbe un'animazione sbagliata, che e' peggio.
        "diffusion": (("UNETLoader", "unet_name"),
                      ("minimax", "fl2va"), ("vae", "clip", "qwen")),
        "text_encoder": (("CLIPLoader", "clip_name"),
                         ("qwen", "minimax"), ()),
        "vae": (("VAELoader", "vae_name"),
                ("minimax", "vae"), ("audio",)),
    }

    def _modelli_disponibili(self) -> dict:
        """Risolve i tre pesi contro quello che ComfyUI espone davvero."""
        scelti = {}
        for ruolo, (dove, obbligatorie, evita) in self.FAMIGLIA.items():
            classe, campo = dove
            scelti[ruolo] = _scegli(classe, campo, self.MODELLI[ruolo],
                                    obbligatorie, evita)
        return scelti

    def genera(self, sprite: str, prompt: str, lunghezza: int,
               larghezza: int, altezza: int, seed: int,
               avanzamento=None, fermo=None) -> list:
        if not comfy_disponibile():
            raise RuntimeError(t("gen.comfy_muta", url=COMFY))

        nome_in = carica_immagine(Path(sprite))

        grafo, righe = costruisci_grafo(
            nome_in, prompt, lunghezza, larghezza, altezza,
            int(seed) or int(time.time()), self._modelli_disponibili(),
            passi=self.PASSI)

        # Il client_id serve a due cose: ComfyUI indirizza a noi gli eventi del
        # WebSocket invece di mandarli a chiunque ascolti, e in quegli eventi
        # riconosciamo il nostro lavoro fra gli altri in coda.
        client_id = str(uuid.uuid4())
        racconto = _Racconto(avanzamento)

        with AscoltoComfy(COMFY, client_id, racconto.evento):
            r = _post("/prompt", {"prompt": grafo, "client_id": client_id})
            job = r.get("prompt_id")
            if not job:
                raise RuntimeError(t("gen.grafo_rifiutato", dettaglio=r))
            racconto.job = job
            file_out = self._attendi(job, avanzamento, fermo)

        strip = Image.open(io.BytesIO(scarica_uscita(file_out))).convert("RGBA")
        cw, ch = strip.width // COLONNE_STRIP, strip.height // righe
        frames = []
        for i in range(lunghezza):
            r_i, c_i = divmod(i, COLONNE_STRIP)
            frames.append(strip.crop((c_i * cw, r_i * ch, (c_i + 1) * cw, (r_i + 1) * ch)))
        if avanzamento:
            avanzamento(1.0, t("fase.pronto"))
        return frames

    def _attendi(self, job: str, avanzamento, fermo=None) -> dict:
        file_out = None
        # ---------------------------------------------------------------
        # Attesa a scadenza, non a numero di giri: ogni tentativo puo'
        # costare fino al proprio timeout, quindi contare le iterazioni non
        # dice quanto tempo e' passato davvero.
        #
        # Mentre decodifica il VAE, ComfyUI tiene la GPU al 100% e il suo
        # server HTTP smette di rispondere per decine di secondi. Prima qui
        # si catturava solo HTTPError: un timeout saliva e buttava via la
        # generazione, con dieci minuti di GPU gia' spesi. Un timeout non
        # e' un fallimento, e' "adesso e' occupata".
        # ---------------------------------------------------------------
        scadenza = time.time() + 2 * 3600
        muti = 0
        while time.time() < scadenza:
            time.sleep(2.0)
            # Si controlla a ogni giro, cioe' ogni due secondi: e' il ritardo
            # massimo fra il clic su Annulla e la richiesta a ComfyUI.
            if fermo is not None and fermo.is_set():
                annulla_prompt(job)
                raise Annullato(t("gen.annullato"))
            try:
                st = _get("/history/%s" % job, timeout=30)
                muti = 0
            except urllib.error.HTTPError:
                continue
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                # Se pero' non risponde per un quarto d'ora di fila, e'
                # caduta davvero e continuare non serve a nessuno.
                muti += 1
                if muti >= 30:
                    raise RuntimeError(
                        t("gen.comfy_muta", url=COMFY)) from e
                continue
            if job not in st:
                # Niente `avanzamento` qui: lo sta gia' raccontando il
                # WebSocket, e sovrascriverlo con un 0,5 fisso ogni due secondi
                # riporterebbe la barra indietro a ogni giro. E' esattamente il
                # difetto che questa versione toglie.
                continue
            voce = st[job]
            if voce.get("status", {}).get("status_str") == "error":
                raise RuntimeError(t("gen.comfy_fallita", dettaglio=voce.get("status")))
            for uscita in voce.get("outputs", {}).values():
                for im in uscita.get("images", []):
                    file_out = im
            if file_out:
                break
        if not file_out:
            raise RuntimeError(t("gen.nessuna_immagine"))
        return file_out


class _Racconto:
    """Traduce gli eventi di ComfyUI in una frazione e una frase.

    Tiene l'ultima frazione detta e non torna mai indietro: gli eventi possono
    arrivare fuori ordine — un `progress` di un nodo gia' finito, un
    `executing` che riapre un nodo precedente — e una barra che rincula e'
    peggio di una ferma, perche' sembra che il lavoro si stia disfacendo.
    """

    def __init__(self, avanzamento) -> None:
        self.avanzamento = avanzamento
        self.job = None
        self._ultima = 0.0

    def _dire(self, frazione: float, frase: str) -> None:
        if self.avanzamento is None:
            return
        self._ultima = max(self._ultima, min(frazione, 0.999))
        self.avanzamento(self._ultima, frase)

    def evento(self, m: dict) -> None:
        tipo = m.get("type")
        d = m.get("data") or {}
        # Gli eventi di altri lavori in coda non ci riguardano. Il controllo
        # salta finche' non conosciamo il nostro id: i primi messaggi arrivano
        # prima che `/prompt` abbia risposto.
        if self.job and d.get("prompt_id") and d["prompt_id"] != self.job:
            return

        if tipo == "executing":
            nodo = d.get("node")
            if nodo is None:
                return
            inizio, _peso, chiave = FASI.get(str(nodo), (self._ultima, 0.0, ""))
            if chiave:
                self._dire(inizio, t(chiave))

        elif tipo == "progress":
            # Forma vecchia: un nodo per messaggio.
            self._passo(str(d.get("node") or "11"), d)

        elif tipo == "progress_state":
            # Forma nuova (ComfyUI 2025+): lo stato di **tutti** i nodi in un
            # messaggio solo. Interessa quello che sta girando; gli altri sono
            # gia' finiti o non ancora partiti, e prenderne uno a caso farebbe
            # ballare la barra avanti e indietro.
            #
            # Sostenere tutt'e due le forme non e' pignoleria: un utente con
            # una ComfyUI piu' vecchia riceve solo `progress`, e senza il ramo
            # di sopra la barra tornerebbe muta proprio per lui.
            for nodo, stato in (d.get("nodes") or {}).items():
                if (stato or {}).get("state") == "running":
                    self._passo(str(nodo), stato)

        elif tipo == "execution_cached":
            # Nodi saltati perche' il risultato e' gia' in memoria: senza
            # questo la barra resta al punto del primo nodo saltato finche'
            # non parte il campionamento, che e' proprio il caso della seconda
            # generazione di fila.
            for nodo in d.get("nodes") or []:
                inizio, peso, _f = FASI.get(str(nodo), (0.0, 0.0, ""))
                self._dire(inizio + peso, t("fase.cache"))

    def _passo(self, nodo: str, d: dict) -> None:
        massimo = float(d.get("max") or 0)
        if massimo <= 0:
            return
        inizio, peso, chiave = FASI.get(nodo, (self._ultima, 0.0, "fase.elaboro"))
        valore = float(d.get("value") or 0)
        quota = min(1.0, valore / massimo)
        # Il conteggio si mostra solo quando ha piu' di un passo: "1/1" per un
        # nodo che o e' fermo o e' finito non dice niente a nessuno.
        frase = t(chiave or "fase.elaboro")
        if massimo > 1:
            frase = "%s %d/%d" % (frase, int(valore), int(massimo))
        self._dire(inizio + peso * quota, frase)


class BackendComfyUIH3Fast(BackendComfyUIH3):
    """FastH3: lo stesso H3, distillato per chiudere in otto passi.

    Non cambia il grafo, non cambia il dialetto del prompt, non cambiano le
    lunghezze valide della clip. Cambiano due cose sole:

        il checkpoint   `fastvideo_fasth3_8step_v2_pruned_int8_convrot`
        i passi         otto invece di venti

    Da cui tutto il resto: a parita' di clip il campionamento e' **due volte e
    mezzo piu' corto**, e il campionamento e' circa tre quarti del tempo totale.

    Il prezzo lo dichiarano gli autori del modello e vale la pena ripeterlo:
    movimento difficile, dettaglio fine e audio restano sotto al modello pieno.
    Per uno sprite sheet — figura sola, fondo piatto, gesto largo — e' il
    compromesso giusto; per una clip cinematografica probabilmente no.
    """

    nome = "MiniMax H3 Fast via ComfyUI"
    PASSI = 8

    MODELLI = dict(BackendComfyUIH3.MODELLI,
                   diffusion="fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors")

    # Il riconoscimento per famiglia va riscritto solo per il checkpoint: il
    # nome non contiene ne' `minimax` ne' `fl2va`, quindi con le regole del
    # modello pieno verrebbe scartato e si finirebbe per generare con l'altro
    # senza che nessuno se ne accorga — stesso grafo, stessa uscita, dieci
    # minuti invece di quattro.
    FAMIGLIA = dict(BackendComfyUIH3.FAMIGLIA,
                    diffusion=(("UNETLoader", "unet_name"),
                               ("fasth3",), ("vae", "clip", "qwen")))
