extends PanelContainer
## Procedura guidata per ComfyUI.
##
## ComfyUI e' GPL-3.0 e non viene ridistribuita con Sprite Sheep: se la
## installa l'utente. Questo pannello dice cosa manca e come rimediare,
## un passo alla volta.

signal setup_cambiato(pronto: bool)

@onready var _passi: VBoxContainer = %Passi
@onready var _riassunto: RichTextLabel = %Riassunto
@onready var _btn_avvia: Button = %AvviaButton
@onready var _btn_cartella: Button = %CartellaButton
@onready var _btn_ricontrolla: Button = %RicontrollaButton
@onready var _dlg: FileDialog = %CartellaDialog

const ICONE := {"ok": "✔", "azione": "!", "attesa": "·"}
const COLORI := {
	"ok": Color(0.35, 0.8, 0.45),
	"azione": Color(0.9, 0.65, 0.25),
	"attesa": Color(0.45, 0.5, 0.58),
}

var _sidecar: Node
var _timer: Timer
## Avvio in corso: ComfyUI parte senza finestra di console, quindi l'unico
## segno di vita che l'utente ha e' questa scritta.
var _in_avvio := false
var _secondi := 0
var _puntini: Timer


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo


func _ready() -> void:
	_btn_ricontrolla.pressed.connect(aggiorna)
	_btn_cartella.pressed.connect(_dlg.popup_centered_ratio.bind(0.7))
	_btn_avvia.pressed.connect(_avvia)
	_dlg.dir_selected.connect(_imposta_cartella)

	# Dopo "Avvia" ComfyUI ci mette circa un minuto: si ricontrolla da soli
	_timer = Timer.new()
	_timer.wait_time = 5.0
	_timer.timeout.connect(aggiorna)
	add_child(_timer)

	# I puntini che si muovono dicono "sto lavorando" meglio di una scritta ferma
	_puntini = Timer.new()
	_puntini.wait_time = 1.0
	_puntini.timeout.connect(_anima_attesa)
	add_child(_puntini)


func aggiorna() -> void:
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.get_json("/comfyui")
	if not r.get("ok", false):
		return
	var s: Dictionary = r.get("setup", {})
	_disegna(s)

	var pronto: bool = s.get("pronto", false)
	setup_cambiato.emit(pronto)
	if s.get("in_esecuzione", false) and _in_avvio:
		_fine_attesa()
	if pronto and not _timer.is_stopped():
		_timer.stop()


func _disegna(s: Dictionary) -> void:
	for c in _passi.get_children():
		c.queue_free()

	for p in s.get("passi", []):
		var esito := str(p.get("esito", "attesa"))
		var riga := HBoxContainer.new()
		riga.add_theme_constant_override("separation", 8)

		var icona := Label.new()
		icona.text = ICONE.get(esito, "·")
		icona.custom_minimum_size = Vector2(16, 0)
		icona.add_theme_color_override("font_color", COLORI.get(esito, Color.GRAY))
		riga.add_child(icona)

		var col := VBoxContainer.new()
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		col.add_theme_constant_override("separation", 2)

		var tit := Label.new()
		tit.text = str(p.get("titolo", ""))
		tit.add_theme_color_override("font_color", COLORI.get(esito, Color.GRAY))
		col.add_child(tit)

		var det := Label.new()
		det.text = str(p.get("dettaglio", ""))
		det.add_theme_font_size_override("font_size", 11)
		det.add_theme_color_override("font_color", Color(0.55, 0.6, 0.68))
		det.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		col.add_child(det)

		if p.get("istruzione", null) != null:
			var ist := Label.new()
			ist.text = str(p["istruzione"])
			ist.add_theme_font_size_override("font_size", 11)
			ist.add_theme_color_override("font_color", Color(0.85, 0.72, 0.4))
			ist.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			col.add_child(ist)

		if p.get("link", null) != null:
			var lk := LinkButton.new()
			lk.text = str(p["link"])
			lk.uri = str(p["link"])
			lk.add_theme_font_size_override("font_size", 11)
			col.add_child(lk)

		riga.add_child(col)
		_passi.add_child(riga)

	# Durante l'attesa comanda `_anima_attesa`: il ricontrollo ogni 5 s
	# cancellerebbe la scritta di caricamento un istante dopo averla scritta.
	if _in_avvio:
		return

	# `avviabile` e' falso anche quando ComfyUI c'e' ed e' configurata: le
	# installazioni **Desktop** non si avviano da qui, perche' il codice non sta
	# nella cartella che l'utente ha scelto. Il pulsante resta spento e il passo
	# spiega di aprirla dalla sua applicazione.
	var acceso: bool = s.get("in_esecuzione", false)
	_btn_avvia.disabled = acceso or not s.get("avviabile", false)
	_btn_avvia.text = tr("ComfyUI in esecuzione") if acceso else tr("Avvia ComfyUI")

	if s.get("pronto", false):
		_riassunto.text = "[color=#5cc76e]%s[/color]\n[color=#7d8695]%s[/color]" % [
			tr("Tutto pronto: puoi generare."), str(s.get("nota_licenza", ""))]
	else:
		_riassunto.text = "[color=#7d8695]%s[/color]" % str(s.get("nota_licenza", ""))


## Scritta di attesa. ComfyUI viene lanciata senza console (vedi
## `comfyui_setup.avvia`): senza questa riga l'utente non vedrebbe nulla
## accadere per un minuto intero.
func _anima_attesa() -> void:
	if not _in_avvio:
		return
	_secondi += 1
	var punti := ".".repeat(1 + (_secondi % 3))
	_riassunto.text = "[color=#e0a040][b]%s%s[/b][/color]\n[color=#7d8695]%s[/color]" % [
		tr("COMFYUI IN CARICAMENTO"), punti,
		tr("%d s — di solito ci vuole circa un minuto") % _secondi]
	_btn_avvia.text = tr("Caricamento...")
	_btn_avvia.disabled = true


func _fine_attesa() -> void:
	_in_avvio = false
	_puntini.stop()


func _imposta_cartella(percorso: String) -> void:
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.post_json("/comfyui",
		{"azione": "percorso", "percorso": percorso})
	if not r.get("ok", false):
		_riassunto.text = "[color=#e06060]%s[/color]" % r.get("errore", "")
		return
	aggiorna()


func _avvia() -> void:
	if _sidecar == null:
		return
	_btn_avvia.disabled = true
	_btn_avvia.text = tr("Caricamento...")
	var r: Dictionary = await _sidecar.post_json("/comfyui", {"azione": "avvia"})
	if not r.get("ok", false):
		_fine_attesa()
		_riassunto.text = "[color=#e06060]%s[/color]" % r.get("errore", "")
		_btn_avvia.disabled = false
		_btn_avvia.text = tr("Avvia ComfyUI")
		return
	_in_avvio = true
	_secondi = 0
	_puntini.start()
	_anima_attesa()
	_timer.start()
