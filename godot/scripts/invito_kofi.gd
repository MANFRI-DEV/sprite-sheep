class_name InvitoKofi
extends PanelContainer
## Una riga sotto l'animazione appena finita: chi vuole, puo' sostenere lo
## sviluppo di strumenti che girano in locale. Chi non vuole, non deve
## accorgersene.
##
## Per restare discreto:
## - solo dopo una generazione riuscita, mai durante l'attesa ne' dopo un
##   errore: chiedere mentre qualcosa non va e' fuori luogo;
## - mai alla prima generazione in assoluto: prima si mostra cosa fa il
##   programma, poi eventualmente si chiede;
## - al massimo una volta per sessione, e una × per chiuderla;
## - "Non mostrare piu'" la spegne per sempre, e la scelta si ricorda;
## - testo piccolo e tenue, nessun colore d'accento, nessuna finestra.

## Variabili e non costanti: i test le puntano altrove, per non toccare il
## contatore vero, che sta nella stessa cartella utente dell'app.
var memoria_conteggio := "user://generazioni_riuscite.cfg"
var memoria_spento := "user://invito_kofi.cfg"
## Generazioni riuscite prima di proporlo la prima volta.
const DOPO := 2

var _mostrato_in_sessione := false
var _testo := RichTextLabel.new()


func _ready() -> void:
	visible = false
	var stile := StyleBoxFlat.new()
	stile.bg_color = Color(1, 1, 1, 0.03)
	stile.border_color = Tema.BORDO
	stile.set_border_width_all(1)
	stile.set_corner_radius_all(6)
	stile.content_margin_left = 10
	stile.content_margin_right = 6
	stile.content_margin_top = 6
	stile.content_margin_bottom = 6
	add_theme_stylebox_override("panel", stile)

	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 8)
	add_child(riga)

	var icona := TextureRect.new()
	icona.texture = Collegamenti.ICONE["kofi"]
	icona.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icona.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icona.custom_minimum_size = Vector2(16, 16)
	icona.modulate = Tema.TENUE
	icona.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	riga.add_child(icona)

	_testo.bbcode_enabled = true
	_testo.fit_content = true
	_testo.scroll_active = false
	_testo.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_testo.add_theme_font_size_override("normal_font_size", 11)
	_testo.add_theme_color_override("default_color", Tema.TENUE)
	_testo.meta_clicked.connect(_su_link)
	riga.add_child(_testo)

	var chiudi := Button.new()
	chiudi.text = "×"
	chiudi.flat = true
	chiudi.tooltip_text = "Nascondi"
	chiudi.add_theme_color_override("font_color", Tema.SPENTO)
	chiudi.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	chiudi.pressed.connect(hide)
	riga.add_child(chiudi)
	_scrivi()


## Il BBCode non si traduce da solo: a lingua cambiata si riscrive.
func _scrivi() -> void:
	_testo.text = "%s [url=kofi]%s[/url]  ·  [url=mai]%s[/url]" % [
		tr("Creata sul tuo PC, senza cloud. Se Sprite Sheep ti è utile, puoi sostenere lo sviluppo di strumenti locali con un caffè su"),
		"Ko-fi", tr("Non mostrare più")]


func _notification(cosa: int) -> void:
	if cosa == NOTIFICATION_TRANSLATION_CHANGED and is_node_ready():
		_scrivi()


## Da chiamare a ogni generazione riuscita. Decide da solo se farsi vedere.
func proponi() -> void:
	var fatte := int(Memoria.leggi(memoria_conteggio, "0")) + 1
	Memoria.scrivi(memoria_conteggio, str(fatte))
	if Memoria.leggi(memoria_spento, "") == "mai" or _mostrato_in_sessione or fatte < DOPO:
		return
	_mostrato_in_sessione = true
	visible = true


## Una nuova generazione e' partita: l'invito di prima non c'entra piu'.
func nascondi() -> void:
	visible = false


func _su_link(meta) -> void:
	match str(meta):
		"kofi":
			OS.shell_open(Collegamenti.KOFI)
		"mai":
			Memoria.scrivi(memoria_spento, "mai")
			hide()
