extends OptionButton
## Selettore di lingua. La scelta vale per l'interfaccia (TranslationServer) e
## per i messaggi del sidecar, che arrivano gia' scritti e quindi vanno
## tradotti alla fonte: chi ascolta `lingua_cambiata` avvisa anche il processo
## Python e ridisegna quello che il sidecar ha scritto.

signal lingua_cambiata(codice: String)

const LINGUE := [["it", "Italiano"], ["en", "Inglese"]]
const MEMORIA := "user://lingua.cfg"


## Riempie la tendina e applica la lingua salvata. La chiama la schermata
## principale quando ha collegato il segnale, non `_ready`: altrimenti la
## prima applicazione non la sentirebbe nessuno.
func prepara() -> void:
	var salvata := lingua_salvata()
	for i in LINGUE.size():
		add_item(tr(LINGUE[i][1]))
		set_item_metadata(i, LINGUE[i][0])
		if LINGUE[i][0] == salvata:
			selected = i
	item_selected.connect(func(i: int) -> void: applica(str(get_item_metadata(i))))
	applica(salvata)


static func lingua_salvata() -> String:
	# Prima apertura: si segue la lingua del sistema.
	var sistema := "it" if OS.get_locale().begins_with("it") else "en"
	var v := Memoria.leggi(MEMORIA, sistema)
	return v if v == "it" or v == "en" else sistema


func applica(codice: String) -> void:
	TranslationServer.set_locale(codice)
	Memoria.scrivi(MEMORIA, codice)
	# le voci del selettore sono a loro volta tradotte
	for i in LINGUE.size():
		set_item_text(i, tr(LINGUE[i][1]))
	lingua_cambiata.emit(codice)
