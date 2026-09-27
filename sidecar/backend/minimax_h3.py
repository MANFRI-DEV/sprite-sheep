"""Backend MiniMax H3 (image-to-video).

STATO: non ancora implementato. Il sampler va scritto contro i pesi veri, e
finche' non sono su disco non c'e' modo di verificarlo: preferisco un errore
onesto a del codice che sembra funzionare e non e' mai stato eseguito.

Vincoli gia' noti, da rispettare quando si implementa:
  - lunghezza valida 17k+5 (gia' gestita da parametri.lunghezza_valida)
  - larghezza e altezza multipli di 32, altrimenti il sampler va in errore
    di shape nel patchify 2x2
  - il primo frame viene stirato sulla tela; l'ultimo usa un ritaglio centrale
    che preserva le proporzioni
  - su 8 GB serve offload dinamico: il solo UNet pesa ~20 GB
"""
from . import Backend


class BackendMiniMaxH3(Backend):
    nome = "MiniMax H3"

    def genera(self, sprite: str, prompt: str, lunghezza: int,
               larghezza: int, altezza: int, seed: int,
               avanzamento=None, fermo=None) -> list:
        if larghezza % 32 or altezza % 32:
            raise ValueError(
                "MiniMax H3 richiede dimensioni multiple di 32: ricevuto %dx%d"
                % (larghezza, altezza))
        if (lunghezza - 5) % 17:
            raise ValueError(
                "MiniMax H3 richiede lunghezze 17k+5: ricevuto %d" % lunghezza)
        raise NotImplementedError(
            "Backend MiniMax H3 non ancora implementato. "
            "Il resto della catena (parametri, griglia, GIF) e' pronto e "
            "collaudato: manca solo il sampler, che va scritto e verificato "
            "con i pesi scaricati.")
