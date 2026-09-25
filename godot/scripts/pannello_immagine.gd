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
var _colore: SceltaColore
## L'immagine sorgente tenuta in memoria: serve al contagocce, che deve
## leggere il pixel **originale** e non quello che si vede a schermo, scalato
## e filtrato dal TextureRect.
var _img_sorgente: Image = null


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo


func _ready() -> void:
	%SfogliaButton.pressed.connect(_sfoglia)
	_dialogo.file_selected.connect(_carica)
	_spunta.toggled.connect(_su_spunta)
	_btn_applica.pressed.connect(_applica_scontorno)
	get_viewport().files_dropped.connect(_su_file_trascinati)

	_colore = SceltaColore.new()
	# Sopra il pulsante, sotto la spunta: si sceglie cosa togliere prima di
	# dire di toglierlo.
	_spunta.get_parent().add_child(_colore)
	_spunta.get_parent().move_child(_colore, _btn_applica.get_index())
	_colore.cambiato.connect(_aggiorna_ui)

	_anteprima.gui_input.connect(_su_clic_anteprima)
	_anteprima.mouse_default_cursor_shape = Control.CURSOR_CROSS
	_aggiorna_ui()


## Contagocce: il colore si prende dal pixel dell'immagine vera.
##
## La conversione passa per il rettangolo **effettivamente occupato** dalla
## texture dentro il TextureRect, non per le dimensioni del controllo: con
## `stretch_mode` che conserva le proporzioni restano bande vuote ai lati, e
## una proporzione diretta leggerebbe il pixel sbagliato di parecchio.
func _su_clic_anteprima(evento: InputEvent) -> void:
	if _img_sorgente == null:
		return
	var m := evento as InputEventMouseButton
	if m == null or not m.pressed or m.button_index != MOUSE_BUTTON_LEFT:
		return

	var iw := float(_img_sorgente.get_width())
	var ih := float(_img_sorgente.get_height())
	var q: float = min(_anteprima.size.x / iw, _anteprima.size.y / ih)
	var disegnata := Vector2(iw, ih) * q
	var origine := (_anteprima.size - disegnata) * 0.5
	var dentro := (m.position - origine) / q
	if dentro.x < 0 or dentro.y < 0 or dentro.x >= iw or dentro.y >= ih:
		return
	_colore.preleva(_img_sorgente.get_pixel(int(dentro.x), int(dentro.y)))


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
	# Il contagocce legge sempre l'originale, anche dopo che l'anteprima e'
	# passata a mostrare il risultato scontornato: prelevare dal PNG con alfa
	# darebbe il colore gia' tolto, cioe' niente.
	_img_sorgente = tex.get_image()
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

	_colore.mostra_misurato(str(i.get("colore_sfondo", "")))
	if i.get("ha_canale_alfa", false) and float(i.get("trasparenti_pct", 0)) > 1.0:
		righe.append(tr("Sfondo gia' trasparente (%.0f%%)") % i.get("trasparenti_pct", 0))
		_spunta.button_pressed = false
	elif i.get("sfondo_tinta_unita", false):
		# Non si dice piu' "chiaro": il fondo puo' essere verde, magenta o
		# nero, e quello che conta e' che sia **uno solo**.
		righe.append(tr("Sfondo a tinta unita %s: rimozione consigliata")
			% str(i.get("colore_sfondo", "")))
		_spunta.button_pressed = true
	else:
		righe.append(tr("Gli angoli non concordano (scarto %.0f): usa il contagocce")
			% float(i.get("scarto_angoli", 0)))

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
		"colore": _colore.colore(),
		"tolleranza_tinta": _colore.tolleranza(),
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
	_colore.mostra_misurato(str(res.get("colore_sfondo", "")))
	# Il colore tolto va detto sempre, non solo su "automatico": quando il
	# risultato non e' quello atteso e' la prima cosa da guardare.
	_info_lbl.text = "[color=#5cc76e]%s[/color]\n[color=#c6ccd8]%s[/color]" % [
		tr("Sfondo rimosso — %.0f%% trasparente") % res.get("trasparenti_pct", 0),
		tr("colore tolto %s · bordo sfumato %.1f%%") % [
			str(res.get("colore_sfondo", "?")),
			float(res.get("bordo_sfumato_pct", 0))]]
	_aggiorna_ui()
	immagine_pronta.emit(_in_uso, res)


func _aggiorna_ui() -> void:
	var ha_file := _originale != ""
	_spunta.disabled = not ha_file
	_btn_applica.disabled = not (ha_file and _spunta.button_pressed)


## Percorso da usare a valle: scontornato se applicato, altrimenti l'originale.
func percorso_attivo() -> String:
	return _in_uso


## Il colore scelto qui vale anche per i **frame generati**: il prompt chiede
## quel fondo, quindi la clip esce con lo stesso, e scontornarla con un colore
## diverso da quello dello sprite sarebbe incoerente.
func colore_sfondo() -> String:
	return "auto" if _colore == null else _colore.colore()
