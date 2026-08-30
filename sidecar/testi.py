"""Testi rivolti all'utente, in italiano e inglese.

Perche' qui e non sparsi nei moduli: i messaggi del sidecar arrivano
all'interfaccia gia' scritti (spesso con numeri dentro), quindi Godot non
potrebbe tradurli. Tradurli alla fonte e' l'unico modo che non richiede di
inventare un protocollo di chiavi e segnaposti fra i due processi.

La lingua e' una sola per sessione: l'applicazione e' locale e monoutente.
La imposta l'interfaccia con `POST /lingua`.

Uso:
    from testi import t
    t("comfy.installata")                       -> stringa
    t("prompt.beat_oltre", fine=2.1, durata=2)  -> stringa con valori
"""

LINGUE = ("it", "en")
_lingua = "it"


def imposta_lingua(codice: str) -> str:
    global _lingua
    _lingua = codice if codice in LINGUE else "it"
    return _lingua


def lingua() -> str:
    return _lingua


def t(chiave: str, **valori) -> str:
    voce = TESTI.get(chiave)
    if voce is None:
        return chiave                      # meglio la chiave nuda di un vuoto
    testo = voce.get(_lingua) or voce.get("it") or chiave
    try:
        return testo.format(**valori) if valori else testo
    except (KeyError, IndexError, ValueError):
        return testo


TESTI: dict[str, dict[str, str]] = {
    # --- procedura guidata ComfyUI -----------------------------------------
    "comfy.installata.titolo": {
        "it": "ComfyUI installata",
        "en": "ComfyUI installed"},
    "comfy.installata.assente": {
        "it": "non trovata nelle cartelle abituali",
        "en": "not found in the usual folders"},
    "comfy.installata.istruzione": {
        "it": "Scarica ComfyUI e installala, poi indica qui la cartella che contiene main.py.",
        "en": "Download and install ComfyUI, then point here to the folder containing main.py."},
    "comfy.avviata.titolo": {
        "it": "ComfyUI in esecuzione",
        "en": "ComfyUI running"},
    "comfy.avviata.si": {
        "it": "in ascolto su 127.0.0.1:8188",
        "en": "listening on 127.0.0.1:8188"},
    "comfy.avviata.no": {
        "it": "non risponde",
        "en": "not responding"},
    "comfy.avviata.premi": {
        "it": "Premi Avvia ComfyUI.",
        "en": "Press Start ComfyUI."},
    "comfy.avviata.prima": {
        "it": "Prima completa il passo precedente.",
        "en": "Complete the previous step first."},
    "comfy.nodi.titolo": {
        "it": "Nodi richiesti presenti",
        "en": "Required nodes present"},
    "comfy.nodi.irraggiungibile": {
        "it": "ComfyUI non raggiungibile",
        "en": "ComfyUI unreachable"},
    "comfy.nodi.ok": {
        "it": "tutti presenti (solo nodi del core)",
        "en": "all present (core nodes only)"},
    "comfy.nodi.mancano": {
        "it": "mancano: {elenco}",
        "en": "missing: {elenco}"},
    "comfy.nodi.istruzione": {
        "it": "Aggiorna ComfyUI all'ultima versione: questi nodi fanno parte del core.",
        "en": "Update ComfyUI to the latest version: these nodes are part of the core."},
    "comfy.modelli.titolo": {
        "it": "Modelli",
        "en": "Models"},
    "comfy.modelli.presenti": {
        "it": "presenti",
        "en": "present"},
    "comfy.modelli.mancano": {
        "it": "mancano {n} file",
        "en": "{n} files missing"},
    "comfy.modelli.istruzione": {
        "it": "Scaricali dal pannello Modelli, oppure indica una cartella che li contiene gia'.",
        "en": "Download them from the Models panel, or point to a folder that already has them."},
    "comfy.nota_licenza": {
        "it": ("ComfyUI e' software libero GPL-3.0 di terze parti. Sprite Sheep "
               "non lo ridistribuisce: lo usi tu, installato da te."),
        "en": ("ComfyUI is third-party GPL-3.0 free software. Sprite Sheep does "
               "not redistribute it: you install and run it yourself.")},
    "comfy.err.no_main": {
        "it": "in questa cartella non c'e' main.py di ComfyUI",
        "en": "this folder does not contain ComfyUI's main.py"},
    "comfy.err.non_trovata": {
        "it": "ComfyUI non trovata: indica la cartella",
        "en": "ComfyUI not found: select the folder"},
    "comfy.err.no_python": {
        "it": "interprete Python di ComfyUI non trovato in {base}",
        "en": "ComfyUI's Python interpreter not found in {base}"},
    "comfy.nota_avvio": {
        "it": "L'avvio richiede circa un minuto.",
        "en": "Startup takes about a minute."},

    # --- modelli ------------------------------------------------------------
    # WAN e' installabile ma la catena non e' ancora affidabile: il decode del
    # VAE su 8 GB di VRAM va in thrashing e non chiude. Finche' resta cosi', il
    # pannello lo dichiara "in lavorazione" invece di consigliarlo.
    "mod.wan.descrizione": {
        "it": "Modello video 5B. In lavorazione: la generazione non e' ancora affidabile.",
        "en": "5B video model. In progress: generation is not reliable yet."},
    "mod.h3.descrizione": {
        "it": "Qualita' alta, ma pesante: ~40 GB e generazioni lente su 8 GB.",
        "en": "High quality but heavy: ~40 GB and slow generation on 8 GB."},
    "mod.err.sconosciuto": {
        "it": "modello sconosciuto",
        "en": "unknown model"},
    "mod.err.licenza": {
        "it": "licenza non accettata: leggila e accettala prima di scaricare",
        "en": "licence not accepted: read and accept it before downloading"},
    "mod.err.cartella": {
        "it": "cartella inesistente: {cartella}",
        "en": "folder does not exist: {cartella}"},
    "mod.err.mancanti": {
        "it": "in questa cartella mancano {n} file su {tot}: {elenco}",
        "en": "this folder is missing {n} of {tot} files: {elenco}"},
    "mod.non_installato": {
        "it": ("modello '{id}' non installato: mancano {n} file ({primo}...). "
               "Scaricalo dal pannello Modelli."),
        "en": ("model '{id}' is not installed: {n} files missing ({primo}...). "
               "Download it from the Models panel.")},

    # --- prompt -------------------------------------------------------------
    "prompt.corto": {
        "it": "Prompt troppo corto: descrivi almeno soggetto e azione.",
        "en": "Prompt too short: describe at least the subject and the action."},
    "prompt.manca_blocco": {
        "it": "Manca il blocco '{blocco}'.",
        "en": "Missing the '{blocco}' block."},
    "prompt.no_beat": {
        "it": "Nessun beat temporale: serve almeno un blocco [0s-2s].",
        "en": "No time beat: at least one [0s-2s] block is required."},
    "prompt.beat_oltre": {
        "it": "I beat arrivano a {fine}s ma la durata scelta e' {durata}s.",
        "en": "Beats reach {fine}s but the chosen duration is {durata}s."},
    "prompt.beat_vicino": {
        "it": ("I beat finiscono a {fine}s, molto vicino a {durata}s: il ritorno "
               "alla posa iniziale rischia di cadere nei frame scartati. Meglio "
               "chiudere entro {limite}s."),
        "en": ("Beats end at {fine}s, very close to {durata}s: the return to the "
               "starting pose risks falling into the discarded frames. Better to "
               "close by {limite}s.")},
    "prompt.beat_invalido": {
        "it": "Beat non valido: [{da}s-{a}s].",
        "en": "Invalid beat: [{da}s-{a}s]."},
    "prompt.negati": {
        "it": ("Oggetti nominati per negarli ({elenco}): il modello li disegnera' "
               "comunque. Toglili del tutto, oppure dichiarali e vincolane il colore."),
        "en": ("Objects named in order to negate them ({elenco}): the model will "
               "draw them anyway. Remove them entirely, or declare them and "
               "constrain their colour.")},
    "prompt.no_identita": {
        "it": "Non dichiari che il soggetto resta identico in ogni frame.",
        "en": "You do not state that the subject stays identical in every frame."},
    "prompt.no_camera": {
        "it": "Non dichiari il comportamento della camera.",
        "en": "You do not state the camera behaviour."},
    "prompt.no_sfondo": {
        "it": "Non descrivi lo sfondo.",
        "en": "You do not describe the background."},
    "prompt.wan_intestazioni": {
        "it": ("Il testo usa le intestazioni di MiniMax H3: l'encoder di WAN non "
               "le conosce. Ricomponi il prompt con WAN selezionato."),
        "en": ("The text uses MiniMax H3 headers: WAN's encoder does not know "
               "them. Recompose the prompt with WAN selected.")},
    "prompt.wan_marcatori": {
        "it": ("I marcatori [0s-1s] non li interpreta: WAN vuole la sequenza "
               "scritta a parole (first, then, finally)."),
        "en": ("It does not read [0s-1s] markers: WAN wants the sequence written "
               "out in words (first, then, finally).")},

    # --- generazione --------------------------------------------------------
    "gen.campo_mancante": {
        "it": "campo mancante: {campo}",
        "en": "missing field: {campo}"},
    "gen.sprite_assente": {
        "it": "sprite inesistente",
        "en": "sprite does not exist"},
    "gen.comfy_muta": {
        "it": ("ComfyUI non risponde su {url}. Aprila dalla procedura guidata "
               "prima di generare."),
        "en": ("ComfyUI is not responding at {url}. Start it from the wizard "
               "before generating.")},
    "gen.grafo_rifiutato": {
        "it": "ComfyUI ha rifiutato il grafo: {dettaglio}",
        "en": "ComfyUI rejected the graph: {dettaglio}"},
    "gen.comfy_fallita": {
        "it": "ComfyUI ha fallito: {dettaglio}",
        "en": "ComfyUI failed: {dettaglio}"},
    "gen.nessuna_immagine": {
        "it": "ComfyUI non ha prodotto immagini entro il tempo massimo",
        "en": "ComfyUI produced no images within the time limit"},
    "gen.lunghezza_wan": {
        "it": "WAN richiede lunghezze 4n+1: ricevuto {n}",
        "en": "WAN requires 4n+1 lengths: got {n}"},
    "gen.cartella_ignota": {
        "it": "cartella di ComfyUI sconosciuta: indicala nella procedura guidata",
        "en": "ComfyUI folder unknown: set it in the wizard"},

    # --- licenze ------------------------------------------------------------
    # Sono il testo che l'utente deve leggere prima di scaricare: lasciarlo in
    # italiano a chi ha scelto l'inglese significa fargli accettare qualcosa
    # che non ha capito. Il riassunto non sostituisce la licenza, e lo dice.
    "lic.apache.riassunto": {
        "it": ("Licenza permissiva. Uso commerciale, modifica e ridistribuzione "
               "consentiti. Obbligo: conservare avviso di copyright e testo della "
               "licenza quando ridistribuisci i pesi, e dichiarare le modifiche."),
        "en": ("Permissive licence. Commercial use, modification and "
               "redistribution are allowed. Requirements: keep the copyright "
               "notice and the licence text when you redistribute the weights, "
               "and state your changes.")},
    "lic.h3.riassunto": {
        "it": ("Non e' una licenza open source approvata OSI. Consente l'uso dei "
               "pesi entro limiti precisi, con obbligo di attribuzione visibile "
               "\"MiniMax H3\" nei prodotti commerciali."),
        "en": ("This is not an OSI-approved open source licence. It allows use "
               "of the weights within strict limits, and requires visible "
               "\"MiniMax H3\" attribution in commercial products.")},
    "lic.h3.territorio": {
        "it": ("TERRITORIO: la licenza vale nel mondo ESCLUSI Unione Europea, "
               "Regno Unito, Corea del Sud e Stati Uniti. In quei territori il "
               "deployment locale dei pesi aperti non e' coperto, e la clausola "
               "cita anche gli output prodotti."),
        "en": ("TERRITORY: the licence covers the world EXCEPT the European "
               "Union, the United Kingdom, South Korea and the United States. "
               "In those territories local deployment of the open weights is "
               "not covered, and the clause also names the outputs produced.")},
    "lic.h3.ricavi": {
        "it": ("Le aziende oltre 20 milioni di dollari di ricavi annui devono "
               "chiedere un'autorizzazione scritta separata."),
        "en": ("Companies above 20 million USD in annual revenue must request "
               "separate written authorisation.")},
    "lic.h3.no_training": {
        "it": ("Vietato usare i pesi o i loro output per migliorare altri modelli "
               "di intelligenza artificiale."),
        "en": ("Using the weights or their outputs to improve other artificial "
               "intelligence models is forbidden.")},
    "mod.err.parziale": {
        "it": "{n} file su {tot} non scaricati: usa Riprova per completare",
        "en": "{n} of {tot} files not downloaded: use Retry to complete"},
    "mod.stato.presente": {"it": "presente", "en": "present"},
    "mod.stato.mancante": {"it": "da scaricare", "en": "to download"},
    "mod.stato.in_corso": {"it": "in corso", "en": "downloading"},
    "mod.stato.errore": {"it": "errore", "en": "failed"},

    "lic.non_parere_legale": {
        "it": "Questo riassunto non e' un parere legale: leggi il testo completo.",
        "en": "This summary is not legal advice: read the full text."},
}
