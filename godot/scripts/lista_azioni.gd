extends VBoxContainer
## Coda di azioni dello stesso personaggio: idle, walk, attacco...
##
## Generate insieme costano un solo caricamento dei pesi: su una 3050 sono sei
## minuti risparmiati per ogni azione dopo la prima. Ogni voce tiene il suo
## prompt, durata e frame; sprite, modello, formato e scontorno sono quelli
## del momento in cui si preme Genera, perche' sono del personaggio e non
## dell'azione.

## L'utente vuole mettere in coda l'azione che ha appena preparato: i dati li
## ha il pannello Generazione, che risponde con `aggiungi`.
signal aggiunta_richiesta
signal cambiata

var _lista := ItemList.new()
var _btn_aggiungi := Button.new()
var _btn_togli := Button.new()
var _btn_svuota := Button.new()
var _azioni: Array[Dictionary] = []


func _ready() -> void:
	add_theme_constant_override("separation", 4)
	var titolo := Label.new()
	titolo.text = "Coda di azioni per questo personaggio"
	titolo.add_theme_font_size_override("font_size", 12)
	titolo.add_theme_color_override("font_color", Color(0.776, 0.8, 0.847))
	add_child(titolo)

	_lista.custom_minimum_size = Vector2(0, 72)
	_lista.auto_height = true
	_lista.visible = false
	_lista.item_selected.connect(func(_i: int) -> void: _btn_togli.disabled = false)
	add_child(_lista)

	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 6)
	_btn_aggiungi.text = "Aggiungi alla coda"
	_btn_aggiungi.tooltip_text = "Metti in coda l'azione con nome, prompt, durata e frame attuali. Poi prepara la prossima."
	_btn_aggiungi.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_btn_aggiungi.pressed.connect(func() -> void: aggiunta_richiesta.emit())
	_btn_togli.text = "Togli"
	_btn_togli.disabled = true
	_btn_togli.pressed.connect(_togli)
	_btn_svuota.text = "Svuota"
	_btn_svuota.pressed.connect(svuota)
	for b in [_btn_aggiungi, _btn_togli, _btn_svuota]:
		riga.add_child(b)
	add_child(riga)
	_aggiorna()


## Chiamato dal pannello Generazione con nome, prompt, durata_s, n_frame.
func aggiungi(azione: Dictionary) -> void:
	_azioni.append(azione)
	_aggiorna()


func azioni() -> Array[Dictionary]:
	return _azioni.duplicate()


func svuota() -> void:
	_azioni.clear()
	_aggiorna()


func puo_aggiungere(si: bool) -> void:
	_btn_aggiungi.disabled = not si


func _togli() -> void:
	var scelte := _lista.get_selected_items()
	if scelte.size() > 0:
		_azioni.remove_at(scelte[0])
	_aggiorna()


func _aggiorna() -> void:
	_lista.clear()
	for a in _azioni:
		_lista.add_item("%s · %.1f s · %s" % [a["nome"], float(a["durata_s"]),
			tr("%d frame") % int(a["n_frame"])])
	_lista.visible = not _azioni.is_empty()
	_btn_togli.disabled = true
	_btn_svuota.disabled = _azioni.is_empty()
	cambiata.emit()
