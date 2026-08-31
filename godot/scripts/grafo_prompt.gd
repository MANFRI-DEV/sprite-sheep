extends GraphEdit
class_name GrafoPrompt
## La tela dei blocchi. Costruisce i nodi, tiene i collegamenti, e produce il
## dizionario che il sidecar sa gia' leggere.
##
## Il formato inviato al sidecar **non cambia**: `campi()` restituisce le
## stesse chiavi di prima. Cambia solo come l'utente ci arriva. Riscrivere
## anche il servizio avrebbe voluto dire cambiare due cose insieme e non sapere
## quale delle due ha rotto il prompt.
##
## Un blocco scollegato viene semplicemente omesso. E' l'unica cosa che i fili
## decidono, ed e' voluto: un grafo in cui i fili possono anche riordinare i
## blocchi sembrerebbe piu' potente, ma l'ordine delle sezioni non e' libero —
## il modello vuole l'intestazione prima dei beat e l'audio in fondo. Fili che
## promettono un ordine che poi viene ignorato sarebbero una bugia.

signal modificato

const SEZIONI := [
	# id, titolo, suggerimento, righe
	["soggetto", "Soggetto", "chi o cosa si vede, in inglese", 4],
	["stile", "Stile", "tratto, colori, resa", 3],
	["sfondo", "Sfondo", "fondo pieno, tinta unita", 2],
]

const CAMERE := {
	"Bloccata (consigliata)":
		"The camera is completely locked off with no pan, zoom, dolly, shake, cut or transition. The subject stays fully inside the frame at all times, centered, at a constant scale.",
	"Segue il soggetto":
		"The camera pans and tilts to follow the subject, keeping the whole body fully inside the frame with clear margin at all times. The subject is never cropped.",
}

var _sezioni: Dictionary = {}          # id -> NodoSezione
var _beat: NodoBeat
var _uscita: GraphNode
var _ordine: Array = []                # id nell'ordine degli ingressi di _uscita


func _ready() -> void:
	right_disconnects = true
	show_grid = true
	connection_request.connect(_collega)
	# `disconnect_node` e' il **metodo** che stacca un filo; il segnale che
	# avvisa della richiesta si chiama `disconnection_request`. Collegarsi al
	# primo non da' un errore di nome ma "Cannot find member connect in base
	# Callable", che dice la verita' in un modo in cui non la si riconosce.
	disconnection_request.connect(_scollega)
	_costruisci()


func _costruisci() -> void:
	var y := 40.0
	for s in SEZIONI:
		var n := NodoSezione.new()
		add_child(n)
		n.costruisci(s[0], tr(s[1]), tr(s[2]), int(s[3]))
		n.position_offset = Vector2(40, y)
		n.modificato.connect(func() -> void: modificato.emit())
		_sezioni[s[0]] = n
		y += 150

	var cam := NodoSezione.new()
	add_child(cam)
	cam.costruisci_scelta("camera", tr("Camera"), CAMERE)
	cam.position_offset = Vector2(40, y)
	cam.modificato.connect(func() -> void: modificato.emit())
	_sezioni["camera"] = cam

	_beat = NodoBeat.new()
	add_child(_beat)
	_beat.costruisci()
	_beat.position_offset = Vector2(40, y + 120)
	_beat.modificato.connect(func() -> void: modificato.emit())

	_costruisci_uscita()
	_collega_tutto()


## Il nodo che raccoglie: un ingresso per sezione, etichettato. E' la stessa
## forma dei nodi di ComfyUI, e si legge allo stesso modo — cosa manca si vede
## dal filo che non c'e'.
func _costruisci_uscita() -> void:
	_uscita = GraphNode.new()
	add_child(_uscita)
	_uscita.title = tr("Prompt")
	_uscita.position_offset = Vector2(400, 120)
	_uscita.custom_minimum_size = Vector2(190, 0)

	_ordine = ["soggetto", "stile", "sfondo", "camera", "beat"]
	var etichette := [tr("Soggetto"), tr("Stile"), tr("Sfondo"),
		tr("Camera"), tr("Tempi")]
	for i in _ordine.size():
		var l := Label.new()
		l.text = etichette[i]
		l.add_theme_font_size_override("font_size", 12)
		_uscita.add_child(l)
		_uscita.set_slot(i, true, 0, NodoSezione.COLORE_FILO,
			false, 0, NodoSezione.COLORE_FILO)

	var c := CheckBox.new()
	c.name = "Ciclico"
	c.text = tr("Ciclo chiuso")
	c.button_pressed = true
	c.toggled.connect(func(_v: bool) -> void: modificato.emit())
	_uscita.add_child(c)


func _collega_tutto() -> void:
	for i in _ordine.size():
		var id: String = _ordine[i]
		var da: GraphNode = _beat if id == "beat" else _sezioni[id]
		connect_node(da.name, 0, _uscita.name, i)


func _collega(da: StringName, uscita_da: int, a: StringName, ingresso_a: int) -> void:
	# Un ingresso accetta un filo solo: due sezioni nello stesso posto del
	# prompt non vorrebbero dire niente.
	for c in get_connection_list():
		if c["to_node"] == a and c["to_port"] == ingresso_a:
			disconnect_node(c["from_node"], c["from_port"], c["to_node"], c["to_port"])
	connect_node(da, uscita_da, a, ingresso_a)
	modificato.emit()


func _scollega(da: StringName, uscita_da: int, a: StringName, ingresso_a: int) -> void:
	disconnect_node(da, uscita_da, a, ingresso_a)
	modificato.emit()


func _collegato(id: String) -> bool:
	var nodo: GraphNode = _beat if id == "beat" else _sezioni.get(id)
	if nodo == null:
		return false
	for c in get_connection_list():
		if c["from_node"] == nodo.name and c["to_node"] == _uscita.name:
			return true
	return false


func imposta_tempi(durata: float, fine_utile: float) -> void:
	_beat.imposta_tempi(durata, fine_utile)


func precompila(d: Dictionary) -> void:
	for id in _sezioni:
		if d.has(id):
			_sezioni[id].imposta_valore(str(d[id]))
	var passi: Array = d.get("passi", [])
	if not passi.is_empty():
		_beat.imposta_passi(passi)
	var c: CheckBox = _uscita.get_node("Ciclico")
	c.button_pressed = bool(d.get("ciclico", true))


func vuoto() -> bool:
	return _sezioni["soggetto"].valore().strip_edges() == ""


## Le stesse chiavi che il sidecar leggeva prima. Una sezione scollegata esce
## come stringa vuota, che e' gia' il modo in cui il servizio la ignora.
func campi() -> Dictionary:
	var fuori := {}
	for id in _sezioni:
		fuori[id] = _sezioni[id].valore() if _collegato(id) else ""
	fuori["beat"] = _beat.beat() if _collegato("beat") else []
	fuori["ciclico"] = (_uscita.get_node("Ciclico") as CheckBox).button_pressed
	return fuori
