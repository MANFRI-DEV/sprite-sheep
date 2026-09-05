"""Cosa dichiara di se' questa build.

Fino alla 0.9 qui viveva una doppia edizione: `free` con la filigrana su ogni
fotogramma, `premium` senza. Dalla **0.0.1 pre-alpha** l'edizione e' una sola,
senza filigrana, e il modulo resta solo per due ragioni concrete:

1. `server.py` espone `edizione.stato()` su `/health`, e la finestra
   Impostazioni ci legge nome e versione. Toglierlo del tutto vorrebbe dire
   cambiare anche l'interfaccia per un guadagno nullo.
2. `genera.py` interroga `FILIGRANA` prima di applicarla. Lasciata a `False`
   costante, la filigrana e' un `if` che non scatta mai: il codice che la
   disegna resta in `filigrana.py`, spento ma intatto, e non c'e' un ramo
   morto sparso per il resto del programma.

Il contatore orario, gia' disattivato in 0.9, e' stato tolto: contava su un
file locale che chiunque poteva cancellare, quindi non proteggeva nulla e
intralciava le prove.
"""

VERSIONE = "0.0.4-pre-alpha"
NOME_EDIZIONE = "Pre-alpha %s" % VERSIONE

## Nessuna filigrana. La costante resta perche' `genera.py` la interroga, e
## perche' riaccenderla un domani sia una riga sola e non una caccia.
FILIGRANA = False
FILIGRANA_TESTO = "CREATED-WITH-SPRITESHEEP!"


def stato() -> dict:
    """Quel che il sidecar racconta di se' a chi lo interroga.

    Le chiavi `limite`, `usate`, `restanti` e `attesa_s` restano nella
    risposta, sempre nulle: l'interfaccia le legge gia' e cambiare la forma
    del messaggio per togliere quattro campi inerti costerebbe piu' di quanto
    valga.
    """
    return {
        "versione": VERSIONE,
        "nome": NOME_EDIZIONE,
        "filigrana": FILIGRANA,
        "limite": None,
        "usate": 0,
        "restanti": None,
        "attesa_s": 0,
    }


def consuma() -> dict:
    """Registrava una generazione contro il tetto orario. Ora non c'e' tetto.

    La funzione resta perche' `genera.py` la chiama prima di ogni lavoro: e' il
    punto in cui un domani si rimetterebbe un limite, una quota o un
    controllo di licenza, e averlo gia' cablato costa zero.
    """
    return {"ok": True}
