"""Backend WAN 2.2 TI2V 5B (image-to-video).

STATO: non ancora implementato, come per H3. Vale la stessa scelta: nessun
codice non eseguito spacciato per funzionante.

Vincoli noti:
  - lunghezza valida 4n+1 (gia' gestita da parametri.lunghezza_valida)
  - modello da 5B: sta in 8 GB di VRAM con offload moderato, molto piu'
    leggero di H3
  - text encoder umt5-xxl separato dal modello di diffusione
"""
from . import Backend


class BackendWan22(Backend):
    nome = "WAN 2.2 TI2V 5B"

    def genera(self, sprite: str, prompt: str, lunghezza: int,
               larghezza: int, altezza: int, seed: int,
               avanzamento=None) -> list:
        if (lunghezza - 1) % 4:
            raise ValueError(
                "WAN richiede lunghezze 4n+1: ricevuto %d" % lunghezza)
        raise NotImplementedError(
            "Backend WAN 2.2 non ancora implementato. "
            "Il resto della catena (parametri, griglia, GIF) e' pronto e "
            "collaudato: manca solo il sampler, che va scritto e verificato "
            "con i pesi scaricati.")
