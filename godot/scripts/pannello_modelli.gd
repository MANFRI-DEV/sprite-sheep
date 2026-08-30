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


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo


func _ready() -> void:
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
		_lista.add_child(_riga(m))
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
		var colore := Color(0.6, 0.65, 0.72)
		var testo := _esito_cartella
		if testo.begins_with("[verde]"):
			colore = Color(0.35, 0.8, 0.45)
			testo = testo.trim_prefix("[verde]").trim_suffix("[/verde]")
		elif testo.begins_with("[rosso]"):
			colore = Color(0.9, 0.4, 0.4)
			testo = testo.trim_prefix("[rosso]").trim_suffix("[/rosso]")
		_lista.add_child(_etichetta(testo, colore))

	# La tendina mostra gia' una voce selezionata, ma `item_selected` scatta solo
	# al clic: senza questa riga, con un solo modello installato la schermata non
	# saprebbe mai quale modello e' attivo e il pulsante Genera resterebbe spento.
	_notifica_selezione()

	# Il polling costa: si tiene acceso solo mentre serve
	if qualcuno_scarica and _timer.is_stopped():
		_timer.start()
	elif not qualcuno_scarica and not _timer.is_stopped():
		_timer.stop()


## Etichetta piccola col bordo colorato, per marcare lo stato di un modello.
func _targhetta(testo: String, colore: Color) -> Control:
	var cornice := PanelContainer.new()
	cornice.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var stile := StyleBoxFlat.new()
	stile.bg_color = Color(colore.r, colore.g, colore.b, 0.16)
	stile.border_color = colore
	stile.set_border_width_all(1)
	stile.set_corner_radius_all(4)
	stile.content_margin_left = 7
	stile.content_margin_right = 7
	stile.content_margin_top = 1
	stile.content_margin_bottom = 1
	cornice.add_theme_stylebox_override("panel", stile)
	var et := Label.new()
	et.text = testo
	et.add_theme_font_size_override("font_size", 10)
	et.add_theme_color_override("font_color", colore)
	cornice.add_child(et)
	return cornice


func _riga(m: Dictionary) -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 4)

	# Titolo e stato sulla stessa riga: l'etichetta deve stare accanto al nome,
	# non sotto, altrimenti chi scorre l'elenco la salta.
	var riga_titolo := HBoxContainer.new()
	riga_titolo.add_theme_constant_override("separation", 8)
	var titolo := Label.new()
	titolo.text = "%s — %.1f GB" % [m["nome"], float(m["gb_totali"])]
	riga_titolo.add_child(titolo)
	if str(m.get("stato_sviluppo", "")) == "in_lavorazione":
		riga_titolo.add_child(_targhetta(tr("IN LAVORAZIONE"),
			Color(0.88, 0.66, 0.25)))
	box.add_child(riga_titolo)

	var desc := Label.new()
	desc.text = str(m["descrizione"])
	desc.add_theme_font_size_override("font_size", 11)
	desc.add_theme_color_override("font_color", Color(0.6, 0.65, 0.72))
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(desc)

	# L'elenco dei file sta fra la descrizione e i comandi: prima cosa c'e',
	# poi cosa si puo' fare. E' l'ordine in cui la domanda si pone.
	box.add_child(ElencoFile.costruisci(m))

	var dl: Dictionary = m.get("download", {})
	if m.get("installato", false):
		box.add_child(_etichetta(tr("Installato"), Color(0.35, 0.8, 0.45)))
	elif dl.get("attivo", false):
		# La barra misura l'intero scaricamento, non il file in corso: con file
		# da 19,5 a 0,6 GB il conteggio "2 di 4" non dice quanto manca, perche'
		# i file non pesano uguale. La percentuale e' pesata sui GB.
		var pct := float(dl.get("percentuale", 0.0))
		var barra := ProgressBar.new()
		barra.max_value = 100.0
		barra.step = 0.1
		barra.value = pct
		barra.show_percentage = false
		box.add_child(barra)

		var riga_pct := HBoxContainer.new()
		riga_pct.add_theme_constant_override("separation", 8)
		var grande := Label.new()
		grande.text = "%.1f%%" % pct
		grande.add_theme_font_size_override("font_size", 16)
		grande.add_theme_color_override("font_color", Color(0.85, 0.75, 0.35))
		riga_pct.add_child(grande)
		var totali := Label.new()
		totali.text = tr("%.1f di %.1f GB") % [
			float(dl.get("gb_scaricati", 0.0)), float(dl.get("gb_totali", 0.0))]
		totali.add_theme_font_size_override("font_size", 12)
		totali.add_theme_color_override("font_color", Color(0.6, 0.65, 0.72))
		totali.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		riga_pct.add_child(totali)
		box.add_child(riga_pct)

		box.add_child(_etichetta(tr("File %d di %d: %s (%.1f di %.1f GB)") % [
			int(dl.get("indice", 0)), int(dl.get("totale", 1)),
			dl.get("file_corrente", "..."),
			float(dl.get("gb_fatti", 0.0)), float(dl.get("gb_file", 0.0))],
			Color(0.6, 0.65, 0.72)))
	elif dl.get("errore", null) != null:
		box.add_child(_etichetta(tr("Errore: %s") % dl["errore"], Color(0.9, 0.4, 0.4)))
	else:
		# Due strade: scaricare da HuggingFace, oppure collegare i pesi che
		# l'utente ha gia' (di solito dentro una ComfyUI). La seconda evita
		# decine di GB di download inutile.
		var riga := HBoxContainer.new()
		riga.add_theme_constant_override("separation", 8)

		var btn := Button.new()
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if m.get("licenza_accettata", false):
			var mancano := 0
			for f in m.get("file", []):
				if not f.get("presente", false):
					mancano += 1
			var tot: int = m.get("file", []).size()
			# Il download salta i file gia' presenti: dirlo evita che chi ha
			# venti giga sul disco tema di riscaricarli.
			btn.text = tr("Scarica") if mancano == tot 				else tr("Scarica i %d file mancanti") % mancano
			btn.pressed.connect(_scarica.bind(str(m["id"])))
		else:
			btn.text = tr("Leggi licenza e installa")
			btn.pressed.connect(_apri_licenza.bind(str(m["id"])))
		riga.add_child(btn)

		var btn_cart := Button.new()
		btn_cart.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		btn_cart.text = tr("Seleziona cartella...")
		btn_cart.tooltip_text = tr("Indica una cartella che contiene gia' questi file "
			+ "(per esempio models/ di ComfyUI): vengono collegati, non copiati.")
		btn_cart.pressed.connect(_scegli_cartella.bind(str(m["id"])))
		riga.add_child(btn_cart)

		box.add_child(riga)

	box.add_child(HSeparator.new())
	return box


func _etichetta(testo: String, colore: Color) -> Label:
	var l := Label.new()
	l.text = testo
	l.add_theme_color_override("font_color", colore)
	l.add_theme_font_size_override("font_size", 12)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


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
	for voluto in [_modello_ricordato(), MODELLO_PREFERITO]:
		if voluto == "":
			continue
		for i in _tendina.item_count:
			if str(_tendina.get_item_metadata(i)) == voluto:
				return i
	return 0


func _modello_ricordato() -> String:
	if not FileAccess.file_exists(MEMORIA_MODELLO):
		return ""
	var f := FileAccess.open(MEMORIA_MODELLO, FileAccess.READ)
	return "" if f == null else f.get_as_text().strip_edges()


func _ricorda_modello(id_modello: String) -> void:
	if id_modello == "":
		return
	var f := FileAccess.open(MEMORIA_MODELLO, FileAccess.WRITE)
	if f != null:
		f.store_string(id_modello)


## Comunica alla schermata il modello attivo, ma solo se e' cambiato davvero.
func _notifica_selezione() -> void:
	var id_modello: String = modello_attivo()
	if id_modello == _emesso:
		return
	_emesso = id_modello
	_ricorda_modello(id_modello)
	modello_scelto.emit(id_modello, id_modello != "")


func modello_attivo() -> String:
	if _tendina.disabled or _tendina.selected < 0:
		return ""
	return str(_tendina.get_item_metadata(_tendina.selected))
