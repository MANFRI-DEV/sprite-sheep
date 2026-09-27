extends RefCounted
class_name Tema
## Palette "ardesia + verde" e tema Godot costruito da qui.
##
## I colori stanno tutti in questo file: cambiare palette vuol dire toccare le
## costanti qui sopra, non venti scene. Il verde e' l'unico accento, ed e' lo
## stesso del semaforo del prompt: il pulsante Genera e la spia "prompt valido"
## parlano cosi' la stessa lingua.

const FONDO      := Color("14161b")   # sfondo finestra
const BARRA      := Color("1a1d25")   # barra di stato
const CARTA      := Color("1d2029")   # pannelli
const CAMPO      := Color("232733")   # caselle di testo
const BORDO      := Color("2b3039")
const BORDO_VIVO := Color("3a414f")   # bordo al passaggio del mouse

# Il testo e' **bianco**. Era un grigio chiarissimo (e2e6ee), che su un fondo
# ardesia si legge bene su un monitor buono e sparisce su un portatile con la
# luminosita' a meta'. Le note secondarie erano piu' scure ancora (7f8798) ed
# erano la parte peggiore: spiegano cosa fa un comando, e chi ha davvero
# bisogno di leggerle e' chi non conosce il programma.
#
# La gerarchia resta — principale, secondario, spento — ma tutta piu' in alto.
const TESTO      := Color("ffffff")
const TENUE      := Color("c6ccd8")   # etichette, note
const SPENTO     := Color("8c94a4")   # comandi disabilitati

## Le stesse tinte per il BBCode dei RichTextLabel, che vuole il testo esadecimale.
const TESTO_HEX  := "#ffffff"
const TENUE_HEX  := "#c6ccd8"

const ACCENTO    := Color("5ccf7e")
const ACCENTO_SU := Color("6fdc8f")
const SU_ACCENTO := Color("0e2a18")   # testo sopra l'accento

const OK         := Color("5ccf7e")
const AVVISO     := Color("e0a840")
const ERRORE     := Color("e06060")


static func _riquadro(sfondo: Color, bordo: Color, raggio: int = 8,
		spessore: int = 1) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = sfondo
	s.border_color = bordo
	s.set_border_width_all(spessore)
	s.set_corner_radius_all(raggio)
	s.content_margin_left = 10
	s.content_margin_right = 10
	s.content_margin_top = 6
	s.content_margin_bottom = 6
	return s


static func costruisci() -> Theme:
	var t := Theme.new()
	t.default_font_size = 13

	t.set_stylebox("panel", "PanelContainer", _riquadro(CARTA, BORDO, 10))
	t.set_stylebox("panel", "Panel", _riquadro(CARTA, BORDO, 10))

	t.set_color("font_color", "Label", TESTO)
	t.set_color("default_color", "RichTextLabel", TESTO)
	t.set_stylebox("normal", "RichTextLabel", StyleBoxEmpty.new())

	_bottoni(t)
	_campi(t)

	var sep := StyleBoxLine.new()
	sep.color = BORDO
	sep.thickness = 1
	t.set_stylebox("separator", "HSeparator", sep)

	t.set_stylebox("background", "ProgressBar", _riquadro(CAMPO, BORDO, 4))
	var pieno := _riquadro(ACCENTO, ACCENTO, 4, 0)
	t.set_stylebox("fill", "ProgressBar", pieno)
	t.set_color("font_color", "ProgressBar", TESTO)

	t.set_stylebox("panel", "ScrollContainer", StyleBoxEmpty.new())

	# CheckBox e CheckButton derivano da Button: senza questo si vestono da
	# pulsante e sembrano due comandi diversi accanto alla spunta.
	for classe in ["CheckBox", "CheckButton"]:
		for stato in ["normal", "hover", "pressed", "disabled", "focus"]:
			t.set_stylebox(stato, classe, StyleBoxEmpty.new())
		t.set_color("font_color", classe, TESTO)
		t.set_color("font_hover_color", classe, TESTO)
		t.set_color("font_pressed_color", classe, TESTO)
		t.set_color("font_disabled_color", classe, SPENTO)
	return t


static func _bottoni(t: Theme) -> void:
	var normale := _riquadro(CAMPO, BORDO)
	var sopra := _riquadro(CAMPO, BORDO_VIVO)
	var premuto := _riquadro(BARRA, BORDO_VIVO)
	var spento := _riquadro(FONDO, BORDO)
	for n in ["normal", "hover", "pressed", "disabled", "focus"]:
		var s: StyleBoxFlat = {"normal": normale, "hover": sopra, "pressed": premuto,
			"disabled": spento, "focus": sopra}[n]
		s.content_margin_top = 7
		s.content_margin_bottom = 7
		t.set_stylebox(n, "Button", s)
	t.set_color("font_color", "Button", TESTO)
	t.set_color("font_hover_color", "Button", TESTO)
	t.set_color("font_pressed_color", "Button", ACCENTO)
	t.set_color("font_disabled_color", "Button", SPENTO)


static func _campi(t: Theme) -> void:
	for classe in ["LineEdit", "TextEdit", "SpinBox", "OptionButton"]:
		t.set_stylebox("normal", classe, _riquadro(CAMPO, BORDO, 6))
		t.set_stylebox("focus", classe, _riquadro(CAMPO, ACCENTO, 6))
		t.set_color("font_color", classe, TESTO)
		t.set_color("font_placeholder_color", classe, SPENTO)
		t.set_color("caret_color", classe, ACCENTO)
	t.set_stylebox("read_only", "LineEdit", _riquadro(FONDO, BORDO, 6))
	t.set_stylebox("read_only", "TextEdit", _riquadro(FONDO, BORDO, 6))


## Pulsante pieno, per l'unica azione principale della schermata.
static func accenta(b: Button) -> void:
	var pieno := _riquadro(ACCENTO, ACCENTO, 8, 0)
	var sopra := _riquadro(ACCENTO_SU, ACCENTO_SU, 8, 0)
	var spento := _riquadro(CAMPO, BORDO, 8)
	for s in [pieno, sopra, spento]:
		s.content_margin_top = 9
		s.content_margin_bottom = 9
	b.add_theme_stylebox_override("normal", pieno)
	b.add_theme_stylebox_override("hover", sopra)
	b.add_theme_stylebox_override("pressed", sopra)
	b.add_theme_stylebox_override("focus", pieno)
	b.add_theme_stylebox_override("disabled", spento)
	b.add_theme_color_override("font_color", SU_ACCENTO)
	b.add_theme_color_override("font_hover_color", SU_ACCENTO)
	b.add_theme_color_override("font_pressed_color", SU_ACCENTO)
	b.add_theme_color_override("font_disabled_color", SPENTO)
