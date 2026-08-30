SPRITE SHEEP 0.0.1-pre-alpha
============================

Da uno sprite e un prompt genera uno sprite sheet animato e una GIF.

Questa build NON contiene dipendenze ne' modelli: si installano una volta sola,
seguendo i tre passi qui sotto. Il programma controlla da solo cosa manca e lo
dice nella finestra Impostazioni.


COSA C'E' NEL PACCHETTO
-----------------------
  SpriteSheep.exe    l'applicazione
  sidecar/           il motore Python (codice sorgente, leggibile)
  LEGGIMI.txt        questo file

Tieni la cartella sidecar/ accanto all'eseguibile: l'applicazione la cerca li'.


COSA DEVI INSTALLARE
--------------------

1) PYTHON 3.10 o superiore
   https://www.python.org/downloads/windows/
   Durante l'installazione spunta "Add python.exe to PATH".

   Poi, da un prompt dei comandi:
       pip install pillow numpy scipy huggingface_hub

   Sprite Sheep NON richiede PyTorch: il calcolo sulla GPU lo fa ComfyUI, che
   ha il suo ambiente separato.

2) COMFYUI
   https://github.com/comfyanonymous/ComfyUI/releases/latest
   Installala dove preferisci. Sprite Sheep la cerca da sola nelle cartelle
   piu' comuni; se non la trova, gliela indichi tu da Impostazioni.

   Serve una versione recente: i nodi usati (MiniMaxH3ImageToVideo,
   Wan22ImageToVideoLatent, ModelSamplingSD3) fanno parte del core di ComfyUI,
   quindi non devi installare alcun custom node.

3) UN MODELLO, a scelta
   Dal pannello Modelli hai due strade:

   - "Scarica": prende i pesi da HuggingFace. Prima ti mostra la licenza e ti
     chiede di accettarla.
   - "Seleziona cartella...": se i pesi ce li hai gia' (per esempio dentro
     models/ di ComfyUI) li collega senza copiarli e senza riscaricare nulla.

   WAN 2.2 TI2V 5B   16,9 GB   Apache 2.0, nessun vincolo territoriale.
                               Consigliato: sta comodo in 8 GB di VRAM,
                               circa 3 minuti e mezzo per 2 secondi di
                               animazione su una RTX 3050.

   MiniMax H3        38,9 GB   Qualita' piu' alta e piu' stabile, ma lento:
                               circa 10 minuti per gli stessi 2 secondi.
                               ATTENZIONE ALLA LICENZA: la MiniMax H3 Community
                               License esclude Unione Europea, Regno Unito,
                               Corea del Sud e Stati Uniti, e la clausola cita
                               anche gli output prodotti. Leggila prima di
                               accettarla; il programma te la mostra per intero.


REQUISITI HARDWARE
------------------
  GPU NVIDIA con almeno 8 GB di VRAM e driver CUDA.
  Senza GPU l'applicazione parte e te lo dice, ma generare e' impraticabile.
  Spazio su disco: 17 GB per WAN, 39 GB per H3.


EDIZIONE FREE
-------------
Ogni frame porta una filigrana: una lettera per frame, che scorrendo compone
"CREATED-WITH-SPRITESHEEP!". Nessun limite al numero di generazioni.


LINGUE
------
Italiano e inglese, dal selettore in alto a destra. Alla prima apertura segue
la lingua di Windows.


LICENZE DI TERZE PARTI
----------------------
ComfyUI e' software libero GPL-3.0 di terze parti. Sprite Sheep non lo
ridistribuisce e non lo incorpora: lo installi tu, e i due programmi si parlano
via HTTP su localhost.

I pesi dei modelli non sono inclusi e restano soggetti alle licenze dei
rispettivi autori, che il programma ti mostra prima del download.
