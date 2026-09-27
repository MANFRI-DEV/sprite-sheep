extends PanelContainer
## Requisito 4: wizard modelli con accettazione licenza obbligatoria.
##
## Il download e' rifiutato dal sidecar finche' la licenza non risulta
## accettata: qui l'interfaccia rende visibile quel vincolo, non lo sostituisce.

signal modello_scelto(id_modello: String, installato: bool)

## Modello proposto alla prima apertura, fra quelli installati. La scelta
## dell'utente ha comunque la precedenza: viene ricordata e ripristinata.
const MODELLO_PREFERITO := "minimax_h3_fl2va"
const MEMORIA_MODELLO := "user://modello.cfg"

@onready var _lista: VBoxContainer = %ListaModelli
@onready var _tendina: OptionButton = %ModelloOption
@onready var _dlg: AcceptDialog = %LicenzaDialog
@onready var _dlg_testo: RichTextLabel = %LicenzaTesto
@onready var _dlg_spunta: CheckBox = %LicenzaCheck
@onready var _dlg_link: LinkButton = %LicenzaLink
@onready var _dlg_cartella: FileDialog = %CartellaModelliDialog

var _sidecar: Node
var _modelli: Array = []
var _in_licenza := ""
var _timer: Timer
## Ultimo id comunicato alla schermata, per non ripetere lo stesso segnale
## a ogni ridisegno (il timer ne fa uno ogni 1.5s durante i download).
var _emesso := ""
## Modello per cui si sta scegliendo la cartella
var _in_cartella := ""
## Ultimo esito della ricerca su cartella, mostrato sotto la lista
var _esito_cartella := ""
## Cosa fanno i pulsanti delle righe: le righe le costruisce `RigaModello`.
var _azioni := {}


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo


func _ready() -> void:
	_azioni = {"scarica": _scarica, "licenza": _apri_licenza, "cartella": _scegli_cartella}
	_dlg.confirmed.connect(_conferma_licenza)
	_dlg_spunta.toggled.connect(func(v: bool) -> void: _dlg.get_ok_button().disabled = not v)
	_tendina.item_selected.connect(_su_selezione)
	_dlg_cartella.dir_selected.connect(_usa_cartella)

	# Ricarica periodica: serve a far avanzare le barre di download
	_timer = Timer.new()
	_timer.wait_time = 1.5
	_timer.timeout.connect(aggiorna)
	add_child(_timer)


func aggiorna() -> void:
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.get_json("/modelli")
	if not r.get("ok", false):
		return
	_modelli = r.get("modelli", [])
	_disegna()


func _disegna() -> void:
	for c in _lista.get_children():
		c.queue_free()
	var indice_tendina := _tendina.selected
	_tendina.clear()

	var qualcuno_scarica := false
	for m in _modelli:
		_lista.add_child(RigaModello.costruisci(m, _azioni))
		if m.get("installato", false):
			_tendina.add_item(str(m["nome"]))
			_tendina.set_item_metadata(_tendina.item_count - 1, str(m["id"]))
		if m.get("download", {}).get("attivo", false):
			qualcuno_scarica = true

	if _tendina.item_count == 0:
		_tendina.add_item(tr("nessun modello installato"))
		_tendina.disabled = true
	else:
		_tendina.disabled = false
		if indice_tendina < 0:
			# Primo disegno: nessuna selezione da conservare. Si riprende
			# l'ultima scelta, o in mancanza il modello preferito.
			_tendina.selected = _indice_iniziale()
		else:
			_tendina.selected = clampi(indice_tendina, 0, _tendina.item_count - 1)

	if _esito_cartella != "":
		var colore := Color(0.776, 0.8, 0.847)
		var testo := _esito_cartella
		if testo.begins_with("[verde]"):
			colore = Color(0.35, 0.8, 0.45)
			testo = testo.trim_prefix("[verde]").trim_suffix("[/verde]")
		elif testo.begins_with("[rosso]"):
			colore = Color(0.9, 0.4, 0.4)
			testo = testo.trim_prefix("[rosso]").trim_suffix("[/rosso]")
		_lista.add_child(RigaModello.etichetta(testo, colore))

	# La tendina mostra gia' una voce selezionata, ma `item_selected` scatta solo
	# al clic: senza questa riga, con un solo modello installato la schermata non
	# saprebbe mai quale modello e' attivo e il pulsante Genera resterebbe spento.
	_notifica_selezione()

	# Il polling costa: si tiene acceso solo mentre serve
	if qualcuno_scarica and _timer.is_stopped():
		_timer.start()
	elif not qualcuno_scarica and not _timer.is_stopped():
		_timer.stop()


func _apri_licenza(id_modello: String) -> void:
	var m: Dictionary = {}
	for x in _modelli:
		if str(x["id"]) == id_modello:
			m = x
	if m.is_empty():
		return
	_in_licenza = id_modello
	var lic: Dictionary = m["licenza"]

	var righe := ["[b]%s[/b]\n" % lic["nome"], str(lic["riassunto"])]
	var avv: Array = lic.get("avvertenze", [])
	if not avv.is_empty():
		righe.append("\n[color=#e0a040][b]Attenzione[/b][/color]")
		for a in avv:
			righe.append("[color=#e0a040]• %s[/color]" % a)
	_dlg_testo.text = "\n".join(righe)

	_dlg_link.text = str(lic["url"])
	_dlg_link.uri = str(lic["url"])
	_dlg_spunta.button_pressed = false
	_dlg.get_ok_button().disabled = true
	_dlg.title = "Licenza — %s" % m["nome"]
	_dlg.popup_centered(Vector2i(720, 460))


func _conferma_licenza() -> void:
	if _in_licenza == "" or _sidecar == null:
		return
	var r: Dictionary = await _sidecar.post_json("/licenza",
		{"modello": _in_licenza, "accetto": _dlg_spunta.button_pressed})
	if r.get("ok", false):
		_scarica(_in_licenza)
	_in_licenza = ""


## Chiede una cartella dove i pesi esistono gia'.
func _scegli_cartella(id_modello: String) -> void:
	_in_cartella = id_modello
	_dlg_cartella.title = tr("Cartella con i modelli — %s") % id_modello
	_dlg_cartella.popup_centered(Vector2i(760, 520))


func _usa_cartella(percorso: String) -> void:
	if _in_cartella == "" or _sidecar == null:
		return
	var id_modello := _in_cartella
	_in_cartella = ""
	_esito_cartella = tr("Cerco i file in %s...") % percorso
	_disegna()

	var r: Dictionary = await _sidecar.post_json("/cerca_modelli",
		{"modello": id_modello, "cartella": percorso})
	var collegati: Array = r.get("collegati", [])
	if r.get("ok", false):
		_esito_cartella = "[verde]%d file collegati da %s[/verde]" % [collegati.size(), percorso]
	else:
		_esito_cartella = "[rosso]%s[/rosso]" % str(r.get("errore", tr("cartella non utilizzabile")))
	aggiorna()


func _scarica(id_modello: String) -> void:
	if _sidecar == null:
		return
	await _sidecar.post_json("/scarica", {"modello": id_modello})
	_timer.start()
	aggiorna()


func _su_selezione(_i: int) -> void:
	_notifica_selezione()


## Posizione in tendina del modello da proporre: l'ultimo usato se e' ancora
## installato, altrimenti il preferito, altrimenti il primo che c'e'.
func _indice_iniziale() -> int:
	for voluto in [Memoria.leggi(MEMORIA_MODELLO, ""), MODELLO_PREFERITO]:
		if voluto == "":
			continue
		for i in _tendina.item_count:
			if str(_tendina.get_item_metadata(i)) == voluto:
				return i
	return 0


## Comunica alla schermata il modello attivo, ma solo se e' cambiato davvero.
func _notifica_selezione() -> void:
	var id_modello: String = modello_attivo()
	if id_modello == _emesso:
		return
	_emesso = id_modello
	if id_modello != "":
		Memoria.scrivi(MEMORIA_MODELLO, id_modello)
	modello_scelto.emit(id_modello, id_modello != "")


func modello_attivo() -> String:
	if _tendina.disabled or _tendina.selected < 0:
		return ""
	return str(_tendina.get_item_metadata(_tendina.selected))
