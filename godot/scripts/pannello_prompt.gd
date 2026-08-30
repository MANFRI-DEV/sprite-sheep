extends PanelContainer
## Requisito 3: prompt a campi con semaforo di validazione.
##
## L'utente compila i campi, il sidecar compone il testo e lo valida.
## Il testo resta modificabile a mano: in quel caso si valida quello scritto.

signal prompt_cambiato(testo: String, valido: bool)

@onready var _soggetto: TextEdit = %SoggettoEdit
@onready var _stile: LineEdit = %StileEdit
@onready var _sfondo: LineEdit = %SfondoEdit
@onready var _camera: OptionButton = %CameraOption
@onready var _num_passi: SpinBox = %NumPassiSpin
@onready var _passi: VBoxContainer = %Passi
@onready var _ciclico: CheckBox = %CiclicoCheck
@onready var _testo: TextEdit = %TestoEdit
@onready var _spia: ColorRect = %Spia
@onready var _esito: RichTextLabel = %EsitoLabel
@onready var _btn_componi: Button = %ComponiButton
@onready var _nota_modello: Label = %NotaModello

const CAMERE := {
	"Bloccata (consigliata)":
		"The camera is completely locked off with no pan, zoom, dolly, shake, cut or transition. The subject stays fully inside the frame at all times, centered, at a constant scale.",
	"Segue il soggetto":
		"The camera pans and tilts to follow the subject, keeping the whole body fully inside the frame with clear margin at all times. The subject is never cropped.",
}

const COLORI := {
	"verde": Color(0.28, 0.75, 0.4),
	"giallo": Color(0.9, 0.7, 0.25),
	"rosso": Color(0.85, 0.3, 0.3),
}

var _sidecar: Node
var _durata_s := 2.0
## Durata reale della clip: il modello accetta solo certe lunghezze, quindi
## e' quasi sempre maggiore di quella chiesta. Serve alla validazione.
var _durata_effettiva := 2.0
## Istante oltre il quale i frame vengono scartati: i beat devono chiudere qui.
var _fine_utile := 1.7
## Modello scelto: decide il dialetto del prompt (H3 e WAN vogliono testi diversi)
var _modello := ""
var _modificato_a_mano := false
var _in_validazione := false


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo


func imposta_durata(secondi: float) -> void:
	_durata_s = secondi
	_durata_effettiva = max(_durata_effettiva, secondi)
	_fine_utile = min(_fine_utile, _durata_effettiva * 0.85)
	_aggiorna_intervalli()
	_valida()


## La chiama il pannello Generazione quando conosce la lunghezza reale.
func imposta_tempi(effettiva: float, fine_utile: float) -> void:
	_durata_effettiva = effettiva
	_fine_utile = fine_utile
	_aggiorna_intervalli()
	_valida()


## La chiama la schermata quando cambia il modello attivo.
func imposta_modello(id_modello: String) -> void:
	if id_modello == _modello:
		return
	_modello = id_modello
	_aggiorna_nota_dialetto()
	# Il testo gia' composto e' nel dialetto del modello precedente: va rifatto,
	# a meno che l'utente l'abbia scritto lui.
	if not _modificato_a_mano and _testo.text.strip_edges() != "":
		_componi()
	else:
		_valida()


func _aggiorna_nota_dialetto() -> void:
	if _modello.begins_with("wan"):
		_nota_modello.text = tr("WAN: prosa unica, la sequenza va a parole (first, then, finally).")
	elif _modello == "":
		_nota_modello.text = ""
	else:
		_nota_modello.text = tr("MiniMax H3: blocchi con intestazioni e marcatori [0s-1s].")


func _ready() -> void:
	for etichetta in CAMERE:
		_camera.add_item(etichetta)
	_num_passi.value_changed.connect(func(_v: float) -> void: _ricostruisci_passi())
	_btn_componi.pressed.connect(_componi)
	_ricostruisci_passi()
	# Se l'utente tocca il testo generato, da li' in poi comanda lui
	_testo.text_changed.connect(func() -> void:
		_modificato_a_mano = true
		_valida())
	_imposta_spia("rosso", tr("Compila i campi e premi Componi."))


## Riempie i campi con l'esempio e compone subito il testo.
##
## Si compone invece di incollare un prompt pronto perche' il dialetto dipende
## dal modello attivo: lo stesso esempio va scritto in un modo per H3 e in un
## altro per WAN, e a saperlo e' il sidecar.
func precompila(d: Dictionary) -> void:
	if _soggetto.text.strip_edges() != "":
		return
	_soggetto.text = str(d.get("soggetto", ""))
	_stile.text = str(d.get("stile", ""))
	_sfondo.text = str(d.get("sfondo", ""))
	_ciclico.button_pressed = bool(d.get("ciclico", true))

	var passi: Array = d.get("passi", [])
	if not passi.is_empty():
		_num_passi.value = passi.size()
		_ricostruisci_passi()
		for i in mini(passi.size(), _passi.get_child_count()):
			_passi.get_child(i).get_meta("campo").text = str(passi[i])
	_componi()


func _campi() -> Dictionary:
	# Un passo = un beat. Gli intervalli li mostra l'interfaccia, cosi'
	# l'utente vede esattamente quanto dura ogni azione che scrive.
	var beat := []
	for i in _passi.get_child_count():
		var campo: TextEdit = _passi.get_child(i).get_meta("campo")
		var testo := campo.text.strip_edges()
		if testo == "":
			continue
		var iv: Array = _intervallo_clip(i)
		beat.append({"da": iv[0], "a": iv[1], "testo": testo})
	return {
		"soggetto": _soggetto.text,
		"stile": _stile.text,
		"sfondo": _sfondo.text,
		"camera": CAMERE.get(_camera.get_item_text(max(_camera.selected, 0)), ""),
		"beat": beat,
		"ciclico": _ciclico.button_pressed,
	}


func _componi() -> void:
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.post_json("/prompt", {
		"campi": _campi(), "durata_s": _durata_effettiva, "modello": _modello})
	if not r.get("ok", false):
		_imposta_spia("rosso", r.get("errore", tr("composizione fallita")))
		return
	_modificato_a_mano = false
	_testo.text = str(r.get("testo", ""))
	_mostra(r.get("validazione", {}))


func _valida() -> void:
	if _sidecar == null or _in_validazione:
		return
	_in_validazione = true
	var corpo := {"durata_s": _durata_effettiva, "modello": _modello}
	if _modificato_a_mano:
		corpo["testo"] = _testo.text
	else:
		corpo["campi"] = _campi()
	var r: Dictionary = await _sidecar.post_json("/prompt", corpo)
	_in_validazione = false
	if r.get("ok", false):
		_mostra(r.get("validazione", {}))


func _mostra(v: Dictionary) -> void:
	var righe := []
	for p in v.get("problemi", []):
		righe.append("[color=#e06060]• %s[/color]" % p)
	for a in v.get("avvisi", []):
		righe.append("[color=#e0a040]• %s[/color]" % a)
	if righe.is_empty():
		righe.append("[color=#5cc76e]Prompt valido: %d beat, chiude a %.1fs.[/color]"
			% [int(v.get("n_beat", 0)), float(v.get("fine_beat_s", 0))])
	_imposta_spia(str(v.get("semaforo", "rosso")), "\n".join(righe))
	prompt_cambiato.emit(_testo.text, bool(v.get("generabile", false)))


func _imposta_spia(semaforo: String, messaggio: String) -> void:
	_spia.color = COLORI.get(semaforo, COLORI["rosso"])
	_esito.text = messaggio


## Estremi del passo i nel tempo dell'animazione finale: e' quello che l'utente
## ha chiesto e quello che vedra' nella GIF.
func _intervallo(i: int) -> Array:
	var n: int = maxi(1, _passi.get_child_count())
	return [snappedf(_durata_s * i / n, 0.1),
			snappedf(_durata_s * (i + 1) / n, 0.1)]


## Gli stessi estremi nel tempo della clip generata. Non coincidono: il modello
## produce una clip piu' lunga di quella chiesta e l'ultimo ~15% dei frame viene
## scartato, quindi i beat vanno compressi nella finestra che finisce nel foglio.
func _intervallo_clip(i: int) -> Array:
	var n: int = maxi(1, _passi.get_child_count())
	return [snappedf(_fine_utile * i / n, 0.01),
			snappedf(_fine_utile * (i + 1) / n, 0.01)]


## Ricrea le righe conservando i testi gia' scritti.
func _ricostruisci_passi() -> void:
	var precedenti := []
	for c in _passi.get_children():
		precedenti.append(c.get_meta("campo").text)
		_passi.remove_child(c)
		c.queue_free()

	for i in int(_num_passi.value):
		var riga := HBoxContainer.new()
		riga.add_theme_constant_override("separation", 8)

		var tempo := Label.new()
		tempo.name = "Tempo"
		tempo.custom_minimum_size = Vector2(86, 0)
		tempo.add_theme_font_size_override("font_size", 11)
		tempo.add_theme_color_override("font_color", Color(0.45, 0.7, 0.95))
		riga.add_child(tempo)

		var campo := TextEdit.new()
		campo.custom_minimum_size = Vector2(0, 40)
		campo.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		campo.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
		campo.placeholder_text = tr("cosa succede in questo passo")
		if i < precedenti.size():
			campo.text = str(precedenti[i])
		campo.text_changed.connect(_valida)
		riga.add_child(campo)

		riga.set_meta("campo", campo)
		_passi.add_child(riga)

	_aggiorna_intervalli()
	_valida()


func _aggiorna_intervalli() -> void:
	if _passi == null:
		return
	for i in _passi.get_child_count():
		var iv: Array = _intervallo(i)
		var etichetta: Label = _passi.get_child(i).get_node("Tempo")
		etichetta.text = "%.1f–%.1f s" % [iv[0], iv[1]]


func testo_prompt() -> String:
	return _testo.text
