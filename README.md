# Sprite Sheep

Da uno sprite e un prompt genera uno **sprite sheet animato** e una GIF, in
locale, usando modelli di diffusione video.

> **Pre-alpha 0.0.2.** Funziona, ma ha spigoli. Le interfacce e i formati
> possono cambiare senza preavviso.

![Sprite Sheep](schermata.png)

## Cosa fa

Carichi il disegno di un personaggio, scrivi cosa deve fare, e ottieni una
griglia 5×5 di 25 fotogrammi con lo sfondo trasparente, più l'anteprima
animata. Il modello video genera il movimento; il programma ritaglia i
fotogrammi, li scontorna e li compone.

## Come è fatto

Due pezzi che parlano fra loro su `localhost`:

| | |
|---|---|
| `godot/` | l'interfaccia, in Godot 4.6 |
| `sidecar/` | il servizio Python che fa l'inferenza |

Godot **non può** fare inferenza: servono PyTorch e CUDA. Avvia quindi il
sidecar come processo figlio e ci dialoga via HTTP. Il calcolo pesante lo fa
ComfyUI, che ha il suo ambiente.

## Cosa serve per usarlo

1. **ComfyUI** installato e funzionante
2. **Un modello** fra quelli supportati, scaricabile dal programma stesso
3. Una GPU NVIDIA con almeno 8 GB di VRAM

Il programma controlla da solo cosa manca e lo dice nella finestra
Impostazioni.

### Modelli

| Modello | Peso | Licenza |
|---|---|---|
| MiniMax H3 | 38,9 GB | Community License — **esclude UE, Regno Unito, Corea del Sud, Stati Uniti**, e la clausola cita anche gli output |
| WAN 2.2 | 16,9 GB | Apache 2.0, nessun vincolo territoriale |

WAN 2.2 è **in lavorazione**: il decode del VAE va in stallo sotto gli 8 GB di
VRAM. Selezionabile, ma non ancora affidabile.

Il programma mostra la licenza per intero e blocca il download finché non la
accetti. **Leggila**: quella di MiniMax H3 ha restrizioni territoriali che
riguardano anche ciò che produci.

## Compilare

```
python build_runtime.py     # runtime Python incorporato
python build_licenze.py     # licenze delle dipendenze
python build.py             # esporta l'eseguibile e fa lo zip
```

Serve Godot 4.6.1 in `C:\GODOT\`. Il percorso è in cima a `build.py`.

## Licenze di terze parti

`THIRD-PARTY-LICENCES.txt`, generato da `build_licenze.py`, elenca ogni
dipendenza con la sua licenza. Finisce dentro il pacchetto distribuito.

## Storia

Fino alla 0.9 esistevano due edizioni, una con la filigrana su ogni fotogramma
e una senza. Dalla 0.0.1 pre-alpha l'edizione è **una sola, senza filigrana**.
La numerazione riparte da zero perché il progetto riparte da zero: quello che
c'era prima era un prototipo con un modello commerciale addosso, questo è il
programma.
