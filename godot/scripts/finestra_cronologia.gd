extends Window
## Cronologia delle generazioni, con "rigenera con un altro seme".
##
## L'elenco lo tiene il sidecar leggendo i `meta.json` delle cartelle di
## output: se l'utente cancella una cartella a mano, sparisce anche da qui.
## Rigenerare usa la copia dello sprite salvata nella cartella, non il file
## originale, che nel frattempo puo' essere stato spostato o ridisegnato.

## Un lavoro rigenerato e' partito: lo segue il pannello Generazione.
signal rigenerata(job: String)

const MINIATURA := 64
## Oltre queste, le miniature non si caricano: leggere duecento sheet da disco
## all'apertura bloccherebbe la finestra per secondi.
const MAX_MINIATURE := 40

var _sidecar: Node
var _voci: Array = []
var _lista := ItemList.new()
var _dettaglio := RichTextLabel.new()
var _btn_cartella := Button.new()
var _btn_log := Button.new()
var _btn_rigenera := Button.new()


func imposta(sidecar: Node) -> void:
	_sidecar = sidecar


func _ready() -> void:
	title = "Cronologia"
	transient = true
	visible = false
	close_requested.connect(hide)

	var fondo := ColorRect.new()
	fondo.color = Tema.FONDO
	fondo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(fondo)
	var margine := MarginContainer.new()
	margine.set_anchors_preset(Control.PRESET_FULL_RECT)
	for lato in ["left", "top", "right", "bottom"]:
		margine.add_theme_constant_override("margin_" + lato, 12)
	add_child(margine)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 8)
	margine.add_child(col)

	_lista.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_lista.fixed_icon_size = Vector2i(MINIATURA, MINIATURA)
	_lista.item_selected.connect(_su_scelta)
	_lista.item_activated.connect(func(_i: int) -> void: _apri("log"))
	col.add_child(_lista)

	_dettaglio.bbcode_enabled = true
	_dettaglio.fit_content = true
	_dettaglio.selection_enabled = true
	_dettaglio.custom_minimum_size = Vector2(0, 64)
	col.add_child(_dettaglio)

	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 8)
	_btn_cartella.text = "Apri cartella"
	_btn_cartella.pressed.connect(func() -> void: _apri("cartella"))
	_btn_log.text = "Apri log"
	_btn_log.pressed.connect(func() -> void: _apri("log"))
	_btn_rigenera.text = "Rigenera con un altro seme"
	_btn_rigenera.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_btn_rigenera.pressed.connect(_rigenera)
	Tema.accenta(_btn_rigenera)
	for b in [_btn_cartella, _btn_log, _btn_rigenera]:
		riga.add_child(b)
	col.add_child(riga)
	_abilita(false, false)


func apri() -> void:
	popup_centered(Vector2i(720, 640))
	_lista.clear()
	_dettaglio.text = tr("Carico...")
	_abilita(false, false)
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.get_json("/storico")
	_voci = r.get("voci", [])
	_lista.clear()
	for i in _voci.size():
		var v: Dictionary = _voci[i]
		var testo := "%s   %s" % [v.get("data", ""), v.get("nome", "")]
		if v.has("modello"):
			# Una riga sola: l'ItemList ignora gli a capo, e nome e dettagli
			# finivano attaccati ("lotto_idleMiniMax H3"). Dal JSON i numeri
			# arrivano float: senza %d si leggeva "16.0 frame", "seme 1234.0".
			testo += "   ·   %s · %s · %.1f s · %s · %s %d" % [
				v.get("modello", ""), v.get("formato", ""), float(v.get("durata_s", 0)),
				tr("%d frame") % int(v.get("n_frame", 0)), tr("seme"), int(v.get("seed", 0))]
		_lista.add_item(testo, _miniatura(v) if i < MAX_MINIATURE else null)
	_dettaglio.text = tr("Nessuna generazione ancora.") if _voci.is_empty() \
		else tr("Doppio clic per aprire il log.")


## Il foglio intero rimpicciolito: Godot non decodifica le GIF, e il foglio e'
## comunque la cosa che l'utente riconosce a colpo d'occhio.
func _miniatura(v: Dictionary) -> Texture2D:
	var percorso := str(v.get("sheet", ""))
	if percorso == "" or not FileAccess.file_exists(percorso):
		return null
	var img := Image.load_from_file(percorso)
	if img == null:
		return null
	var lato := maxi(img.get_width(), img.get_height())
	img.resize(maxi(1, img.get_width() * MINIATURA / lato),
		maxi(1, img.get_height() * MINIATURA / lato), Image.INTERPOLATE_BILINEAR)
	return ImageTexture.create_from_image(img)


func _scelta() -> Dictionary:
	var s := _lista.get_selected_items()
	return _voci[s[0]] if s.size() > 0 and s[0] < _voci.size() else {}


func _su_scelta(_i: int) -> void:
	var v := _scelta()
	_dettaglio.text = "[color=#c6ccd8]%s[/color]" % str(v.get("prompt", "")).replace("[", "[lb]")
	_abilita(true, bool(v.get("rigenerabile", false)))


func _abilita(scelta: bool, rigenerabile: bool) -> void:
	_btn_cartella.disabled = not scelta
	_btn_log.disabled = not scelta or not _scelta().has("log")
	_btn_rigenera.disabled = not rigenerabile


func _apri(cosa: String) -> void:
	var v := _scelta()
	var percorso := str(v.get(cosa, ""))
	if percorso != "":
		OS.shell_open(percorso)


func _rigenera() -> void:
	var v := _scelta()
	if v.is_empty() or _sidecar == null:
		return
	_btn_rigenera.disabled = true
	var r: Dictionary = await _sidecar.post_json("/rigenera",
		{"cartella": v.get("cartella", ""), "seed": 0})
	if not r.get("ok", false):
		_dettaglio.text = "[color=#e06060]%s[/color]" % str(r.get("errore", ""))
		_btn_rigenera.disabled = false
		return
	rigenerata.emit(str(r.get("job", "")))
	hide()
