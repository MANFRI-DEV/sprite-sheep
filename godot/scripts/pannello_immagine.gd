extends PanelContainer
## Requisito 2: scelta dello sprite sorgente.
##
## Carica un'immagine, la analizza tramite il sidecar, avvisa se non e'
## quadrata e permette di rimuovere lo sfondo con una spunta.

signal immagine_pronta(percorso: String, info: Dictionary)

@onready var _anteprima: TextureRect = %Anteprima
@onready var _percorso_lbl: Label = %PercorsoLabel
@onready var _info_lbl: RichTextLabel = %InfoLabel
@onready var _spunta: CheckBox = %RimuoviSfondoCheck
@onready var _btn_applica: Button = %ApplicaButton
@onready var _dialogo: FileDialog = %FileDialog

var _sidecar: Node
var _originale := ""      ## file scelto dall'utente, mai modificato
var _in_uso := ""         ## file effettivamente passato alla generazione


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo


func _ready() -> void:
	%SfogliaButton.pressed.connect(_sfoglia)
	_dialogo.file_selected.connect(_carica)
	_spunta.toggled.connect(_su_spunta)
	_btn_applica.pressed.connect(_applica_scontorno)
	get_viewport().files_dropped.connect(_su_file_trascinati)
	_aggiorna_ui()


## Il selettore del sistema operativo quando c'e', quello di Godot altrimenti.
##
## Su Windows si ottiene la finestra vera: accesso rapido, percorsi recenti,
## anteprime, ricerca. Quella di Godot le ha tutte in meno, e su un programma
## che si apre col tasto "Scegli immagine" e' la prima cosa che si nota.
func _sfoglia() -> void:
	if DisplayServer.has_feature(DisplayServer.FEATURE_NATIVE_DIALOG_FILE):
		DisplayServer.file_dialog_show(
			tr("Scegli lo sprite sorgente"),
			_cartella_iniziale(), "", false,
			DisplayServer.FILE_DIALOG_MODE_OPEN_FILE,
			["*.png,*.jpg,*.jpeg,*.webp ; %s" % tr("Immagini")],
			_su_dialogo_nativo)
		return
	_dialogo.popup_centered_ratio(0.7)


## Si riparte da dove si era arrivati: chi carica sprite li tiene tutti insieme.
func _cartella_iniziale() -> String:
	if _originale != "":
		return _originale.get_base_dir()
	return OS.get_system_dir(OS.SYSTEM_DIR_PICTURES)


func _su_dialogo_nativo(esito: bool, percorsi: PackedStringArray,
		_filtro: int) -> void:
	if esito and not percorsi.is_empty():
		_carica(percorsi[0])


## Trascinamento da Esplora risorse. Si accetta il primo file leggibile e si
## ignorano gli altri: il pannello tiene uno sprite per volta, e prendere
## l'ultimo di una selezione multipla sarebbe una scelta arbitraria.
func _su_file_trascinati(percorsi: PackedStringArray) -> void:
	if not is_visible_in_tree():
		return
	for p in percorsi:
		if p.get_extension().to_lower() in ["png", "jpg", "jpeg", "webp"]:
			_carica(p)
			return
	_info_lbl.text = "[color=#e0a040]%s[/color]" % tr(
		"Trascina un'immagine PNG, JPG o WEBP.")


## Sprite di esempio alla prima apertura. Passa dallo stesso `_carica` di un
## file scelto a mano: se l'esempio si rompe, si rompe anche il caso normale.
func carica_predefinito(percorso: String) -> void:
	if percorso == "" or _originale != "":
		return
	_carica(percorso)


func _carica(percorso: String) -> void:
	var tex := _carica_texture(percorso)
	if tex == null:
		_info_lbl.text = "[color=#e06060]%s[/color]" % tr("Formato non leggibile.")
		return
	_originale = percorso
	_in_uso = percorso
	_anteprima.texture = tex
	_percorso_lbl.text = percorso.get_file()
	_analizza()


## Legge PNG/JPG/WEBP da disco, fuori da res://
func _carica_texture(percorso: String) -> Texture2D:
	var img := Image.new()
	if img.load(percorso) != OK:
		return null
	return ImageTexture.create_from_image(img)


func _analizza() -> void:
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.post_json("/analizza", {"sorgente": _originale})
	if not r.get("ok", false):
		_info_lbl.text = "[color=#e06060]%s[/color]" % r.get("errore", tr("analisi fallita"))
		return
	var i: Dictionary = r.get("info", {})
	var righe := []

	var w := int(i.get("larghezza", 0))
	var h := int(i.get("altezza", 0))
	if i.get("quadrata", false):
		righe.append("[color=#5cc76e]%s[/color]" % (tr("%d x %d, quadrata") % [w, h]))
	else:
		# Non blocchiamo: il modello genera comunque su tela quadrata,
		# ma il soggetto verrebbe deformato. Meglio dirlo prima.
		righe.append("[color=#e0a040]%s[/color]"
			% (tr("%d x %d — non quadrata, verra' deformata") % [w, h]))

	if i.get("ha_canale_alfa", false) and float(i.get("trasparenti_pct", 0)) > 1.0:
		righe.append(tr("Sfondo gia' trasparente (%.0f%%)") % i.get("trasparenti_pct", 0))
		_spunta.button_pressed = false
	elif i.get("sfondo_uniforme_chiaro", false):
		righe.append(tr("Sfondo chiaro uniforme: rimozione consigliata"))
		_spunta.button_pressed = true
	else:
		righe.append(tr("Sfondo non uniforme: la rimozione potrebbe essere imprecisa"))

	_info_lbl.text = "\n".join(righe)
	_aggiorna_ui()
	immagine_pronta.emit(_in_uso, i)


func _su_spunta(_premuto: bool) -> void:
	_aggiorna_ui()


func _applica_scontorno() -> void:
	if _originale == "" or _sidecar == null:
		return
	_btn_applica.disabled = true
	_btn_applica.text = tr("Scontorno in corso...")

	var r: Dictionary = await _sidecar.post_json("/scontorna", {
		"sorgente": _originale,
		"rimuovi_ombra": true,
	})

	_btn_applica.text = tr("Scontorna adesso")
	if not r.get("ok", false):
		_info_lbl.text = "[color=#e06060]%s[/color]" % r.get("errore", tr("scontorno fallito"))
		_aggiorna_ui()
		return

	var res: Dictionary = r.get("risultato", {})
	_in_uso = str(res.get("destinazione", _originale))
	var tex := _carica_texture(_in_uso)
	if tex != null:
		_anteprima.texture = tex
	_info_lbl.text = "[color=#5cc76e]%s[/color]" \
		% (tr("Sfondo rimosso — %.0f%% trasparente") % res.get("trasparenti_pct", 0))
	_aggiorna_ui()
	immagine_pronta.emit(_in_uso, res)


func _aggiorna_ui() -> void:
	var ha_file := _originale != ""
	_spunta.disabled = not ha_file
	_btn_applica.disabled = not (ha_file and _spunta.button_pressed)


## Percorso da usare a valle: scontornato se applicato, altrimenti l'originale.
func percorso_attivo() -> String:
	return _in_uso
