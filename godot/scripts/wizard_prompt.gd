extends Window
class_name WizardPrompt
## Creazione guidata del prompt: una sezione per schermata.
##
## Sostituisce il grafo a blocchi della 0.9. Il grafo mostrava bene **quali**
## parti compongono un prompt, ma chiedeva di capirle tutte insieme prima di
## scriverne una: sei nodi, i fili, e nessun ordine suggerito. Chi apriva il
## programma la prima volta non sapeva da dove cominciare.
##
## Qui le stesse parti arrivano una per volta, in un ordine che e' anche quello
## in cui conviene pensarle: chi e' il soggetto, com'e' disegnato, cosa c'e'
## dietro, come guarda la camera, cosa succede e quando.
##
## **Il formato non cambia.** `campi()` restituisce le stesse chiavi che il
## sidecar leggeva dal grafo, e `prompt.componi()` non e' stato toccato.
## Cambiare interfaccia e servizio insieme avrebbe reso impossibile capire
## quale dei due ha rotto il prompt.
##
## La validazione gira **a ogni passo**, non solo alla fine: sapere che il
## prompt e' rotto quando si sono gia' compilate sei schermate non aiuta
## nessuno a capire quale delle sei.

signal completato(campi: Dictionary)

const CAMERE := {
	"Bloccata (consigliata)":
		"The camera is completely locked off with no pan, zoom, dolly, shake, cut or transition. The subject stays fully inside the frame at all times, centered, at a constant scale.",
	"Segue il soggetto":
		"The camera pans and tilts to follow the subject, keeping the whole body fully inside the frame with clear margin at all times. The subject is never cropped.",
}

## id, titolo, spiegazione, righe, esempio
const SEZIONI := [
	["soggetto", "Chi si vede", "Il soggetto dell'animazione, in inglese. Descrivilo come se l'altro non avesse davanti lo sprite.", 4,
		"a cartoon sheep with white wool and black legs, seen from the side"],
	["stile", "Com'e' disegnato", "Tratto, colori, resa. Serve a tenere il disegno uguale a se stesso in tutti i fotogrammi.", 3,
		"flat 2D cartoon style, thick black outlines, flat colors, no shading"],
	["sfondo", "Cosa c'e' dietro", "Un fondo a tinta unita si scontorna bene. Un fondo dettagliato no.", 2,
		"solid flat white background, evenly lit, exactly the same in every frame"],
]

var _pagine: Array[Control] = []
var _passo := 0
var _campi_dati: Dictionary = {}

var _titolo: Label
var _spiegazione: Label
var _corpo: VBoxContainer
var _avanzamento: Label
var _btn_indietro: Button
var _btn_avanti: Button
var _esito: RichTextLabel
var _spia: ColorRect

var _sidecar: Node
var _durata := 2.0
var _fine_utile := 1.7
var _modello := ""

var _campi: Dictionary = {}        # id -> TextEdit
var _camera: OptionButton
var _passi: EditorPassi
var _ciclico: CheckBox
var _anteprima: TextEdit


func _ready() -> void:
	title = tr("Wizard prompt creation")
	size = Vector2i(620, 560)
	unresizable = false
	exclusive = true
	close_requested.connect(hide)
	_costruisci()
	_mostra_passo(0)


func imposta(sidecar: Node, modello: String, durata: float, fine_utile: float) -> void:
	_sidecar = sidecar
	_modello = modello
	_durata = durata
	_fine_utile = fine_utile
	if _passi != null:
		_passi.imposta_tempi(durata, fine_utile)


func _costruisci() -> void:
	var m := MarginContainer.new()
	m.set_anchors_preset(Control.PRESET_FULL_RECT)
	for lato in ["left", "top", "right", "bottom"]:
		m.add_theme_constant_override("margin_" + lato, 18)
	add_child(m)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	m.add_child(col)

	_avanzamento = Label.new()
	_avanzamento.add_theme_font_size_override("font_size", 11)
	_avanzamento.add_theme_color_override("font_color", Color(0.776, 0.8, 0.847))
	col.add_child(_avanzamento)

	_titolo = Label.new()
	_titolo.add_theme_font_size_override("font_size", 18)
	col.add_child(_titolo)

	_spiegazione = Label.new()
	_spiegazione.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_spiegazione.add_theme_color_override("font_color", Color(0.82, 0.85, 0.89))
	col.add_child(_spiegazione)

	_corpo = VBoxContainer.new()
	_corpo.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_corpo.add_theme_constant_override("separation", 8)
	col.add_child(_corpo)

	var riga_esito := HBoxContainer.new()
	riga_esito.add_theme_constant_override("separation", 8)
	_spia = ColorRect.new()
	_spia.custom_minimum_size = Vector2(10, 10)
	_spia.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	riga_esito.add_child(_spia)
	_esito = RichTextLabel.new()
	_esito.bbcode_enabled = true
	_esito.fit_content = true
	_esito.custom_minimum_size = Vector2(0, 34)
	_esito.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	riga_esito.add_child(_esito)
	col.add_child(riga_esito)

	var barra := HBoxContainer.new()
	barra.add_theme_constant_override("separation", 8)
	_btn_indietro = Button.new()
	_btn_indietro.text = tr("Indietro")
	_btn_indietro.pressed.connect(func() -> void: _mostra_passo(_passo - 1))
	barra.add_child(_btn_indietro)
	var vuoto := Control.new()
	vuoto.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	barra.add_child(vuoto)
	_btn_avanti = Button.new()
	_btn_avanti.text = tr("Avanti")
	_btn_avanti.pressed.connect(_avanti)
	barra.add_child(_btn_avanti)
	col.add_child(barra)

	_costruisci_pagine()


func _costruisci_pagine() -> void:
	for s in SEZIONI:
		var p := VBoxContainer.new()
		p.size_flags_vertical = Control.SIZE_EXPAND_FILL
		var t := TextEdit.new()
		t.custom_minimum_size = Vector2(0, 26 * int(s[3]))
		t.size_flags_vertical = Control.SIZE_EXPAND_FILL
		t.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
		t.placeholder_text = str(s[4])
		t.text_changed.connect(_valida)
		p.add_child(t)
		_campi[s[0]] = t
		_aggiungi_pagina(p)

	var pc := VBoxContainer.new()
	_camera = OptionButton.new()
	for nome in CAMERE:
		_camera.add_item(tr(nome))
	_camera.item_selected.connect(func(_i: int) -> void: _valida())
	pc.add_child(_camera)
	_aggiungi_pagina(pc)

	var pp := VBoxContainer.new()
	pp.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_passi = EditorPassi.new()
	_passi.modificato.connect(_valida)
	pp.add_child(_passi)
	_ciclico = CheckBox.new()
	_ciclico.text = tr("Ciclo chiuso (l'ultimo fotogramma torna al primo)")
	_ciclico.button_pressed = true
	_ciclico.toggled.connect(func(_v: bool) -> void: _valida())
	pp.add_child(_ciclico)
	_aggiungi_pagina(pp)

	var pr := VBoxContainer.new()
	pr.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_anteprima = TextEdit.new()
	_anteprima.editable = false
	_anteprima.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	_anteprima.size_flags_vertical = Control.SIZE_EXPAND_FILL
	pr.add_child(_anteprima)
	_aggiungi_pagina(pr)


func _aggiungi_pagina(p: Control) -> void:
	p.visible = false
	_corpo.add_child(p)
	_pagine.append(p)


func _intestazione(i: int) -> Array:
	if i < SEZIONI.size():
		return [tr(str(SEZIONI[i][1])), tr(str(SEZIONI[i][2]))]
	if i == SEZIONI.size():
		return [tr("Come guarda la camera"),
			tr("Per uno sprite sheet serve la camera bloccata: se l'inquadratura si muove, il soggetto cambia scala da un fotogramma all'altro.")]
	if i == SEZIONI.size() + 1:
		return [tr("Cosa succede, e quando"),
			tr("Da 1 a 8 passi. La durata si divide fra tutti: aggiungerne uno riscrive i tempi degli altri.")]
	return [tr("Il prompt"), tr("Questo e' il testo che andra' al modello. Si puo' ancora modificare a mano dopo aver chiuso.")]


func _mostra_passo(i: int) -> void:
	_passo = clampi(i, 0, _pagine.size() - 1)
	for k in _pagine.size():
		_pagine[k].visible = (k == _passo)
	var intest := _intestazione(_passo)
	_titolo.text = intest[0]
	_spiegazione.text = intest[1]
	_avanzamento.text = tr("Passo %d di %d") % [_passo + 1, _pagine.size()]
	_btn_indietro.disabled = _passo == 0
	_btn_avanti.text = tr("Usa questo prompt") if _ultima() else tr("Avanti")
	if _ultima():
		_componi_anteprima()
	else:
		_valida()


func numero_pagine() -> int:
	return _pagine.size()


func _ultima() -> bool:
	return _passo == _pagine.size() - 1


func _avanti() -> void:
	if _ultima():
		completato.emit(campi())
		hide()
		return
	_mostra_passo(_passo + 1)


## Le stesse chiavi che il sidecar leggeva dal grafo.
func campi() -> Dictionary:
	var fuori := {}
	for id in _campi:
		fuori[id] = (_campi[id] as TextEdit).text.strip_edges()
	fuori["camera"] = CAMERE.values()[maxi(0, _camera.selected)]
	fuori["beat"] = _passi.beat()
	fuori["ciclico"] = _ciclico.button_pressed
	return fuori


func precompila(d: Dictionary) -> void:
	for id in _campi:
		if d.has(id):
			(_campi[id] as TextEdit).text = str(d[id])
	var passi: Array = d.get("passi", [])
	if not passi.is_empty():
		_passi.imposta_passi(passi)
	_ciclico.button_pressed = bool(d.get("ciclico", true))


func vuoto() -> bool:
	return (_campi["soggetto"] as TextEdit).text.strip_edges() == ""


## Validazione a ogni passo. Il sidecar e' lo stesso di prima: si manda quello
## che c'e' finora e si mostra cosa ne pensa.
func _valida() -> void:
	if _sidecar == null or not visible:
		return
	var r: Dictionary = await _sidecar.post_json("/prompt", {
		"campi": campi(), "durata_s": _durata, "modello": _modello})
	if not r.get("ok", false):
		_semaforo("rosso", str(r.get("errore", tr("composizione fallita"))))
		return
	_mostra_validazione(r.get("validazione", {}))


func _componi_anteprima() -> void:
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.post_json("/prompt", {
		"campi": campi(), "durata_s": _durata, "modello": _modello})
	if not r.get("ok", false):
		_semaforo("rosso", str(r.get("errore", tr("composizione fallita"))))
		return
	_anteprima.text = str(r.get("testo", ""))
	_mostra_validazione(r.get("validazione", {}))


func _mostra_validazione(v: Dictionary) -> void:
	var righe := []
	for p in v.get("problemi", []):
		righe.append("[color=#e06060]• %s[/color]" % p)
	for a in v.get("avvisi", []):
		righe.append("[color=#e0a040]• %s[/color]" % a)
	if righe.is_empty():
		righe.append("[color=#5cc76e]%s[/color]" % (tr("A posto: %d passi, chiude a %.1fs.")
			% [int(v.get("n_beat", 0)), float(v.get("fine_beat_s", 0))]))
	_semaforo(str(v.get("semaforo", "rosso")), "\n".join(righe))


func _semaforo(stato: String, messaggio: String) -> void:
	var colori := {
		"verde": Color(0.28, 0.75, 0.4),
		"giallo": Color(0.9, 0.7, 0.25),
		"rosso": Color(0.85, 0.3, 0.3),
	}
	_spia.color = colori.get(stato, colori["rosso"])
	_esito.text = messaggio


## Riapre sempre dalla prima schermata: il wizard e' una procedura, e
## riprenderla a meta' senza aver visto le prime risposte confonde.
func apri() -> void:
	_mostra_passo(0)
	popup_centered()
