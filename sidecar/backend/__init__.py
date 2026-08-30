"""Backend di inferenza, uno per famiglia di modello.

Ogni backend espone un solo metodo, `genera(...) -> list[Image]`. Tutto il
resto della catena (selezione frame, griglia, GIF) non sa quale modello sia
stato usato: e' quello che rende i backend davvero intercambiabili.
"""
from pathlib import Path


class Backend:
    """Interfaccia comune. Un backend restituisce i frame, nient'altro."""

    nome = "base"

    def __init__(self, cartella_modello: Path):
        self.cartella = Path(cartella_modello)

    def genera(self, sprite: str, prompt: str, lunghezza: int,
               larghezza: int, altezza: int, seed: int,
               avanzamento=None) -> list:
        raise NotImplementedError


def ottieni_backend(model_id: str, cartella: Path) -> Backend:
    if model_id.startswith("minimax_h3"):
        # Finche' il sampler nativo non c'e', se una ComfyUI e' in ascolto
        # si usa quella: meglio un ponte funzionante di un errore.
        from .comfyui_bridge import BackendComfyUIH3, comfy_disponibile
        if comfy_disponibile():
            return BackendComfyUIH3(cartella)
        from .minimax_h3 import BackendMiniMaxH3
        return BackendMiniMaxH3(cartella)
    if model_id.startswith("wan22"):
        # Stessa logica di H3: se una ComfyUI e' in ascolto si passa da li'.
        from .comfyui_bridge import comfy_disponibile
        if comfy_disponibile():
            from .comfyui_wan import BackendComfyUIWan22
            return BackendComfyUIWan22(cartella)
        from .wan22 import BackendWan22
        return BackendWan22(cartella)
    raise KeyError("nessun backend per il modello '%s'" % model_id)
