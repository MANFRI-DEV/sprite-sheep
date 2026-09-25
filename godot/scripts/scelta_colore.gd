extends VBoxContainer
class_name SceltaColore
## Quale colore togliere dallo sfondo, e con quanta tolleranza.
##
## Fino alla 0.0.4 lo scontorno presumeva **sfondo chiaro** e non c'era niente
## da scegliere: chi partiva da un green screen non aveva modo di dirlo.
##
## Tre modi di indicare il colore, in ordine di quanto si usano:
##
##   auto        misurato dai quattro angoli. Va bene quasi sempre, ed e' il
##               default proprio per questo
##   preset      "verde", "magenta"...: si dice *quale* colore e' il fondo, e
##               qual e' esattamente quel colore lo misura il sidecar. Senza
##               questo aggancio i preset sarebbero inutili, perche' un green
##               screen reale sta a 67 di distanza dal verde canonico
##   contagocce  clic sull'anteprima. L'unico che funziona quando il fondo non
##               tocca gli angoli
##
## La tolleranza e' una sola perche' all'utente ne serve una sola: e' il raggio
## largo, quello stretto il sidecar lo ricava da questo.

signal cambiato

const VOCI := [
	["auto", "Automatico (misura dagli angoli)"],
	["verde", "Verde (chroma key)"],
	["magenta", "Magenta"],
	["blu", "Blu"],
	["bianco", "Bianco"],
	["nero", "Nero"],
]

## Voce aggiunta in coda solo quando il contagocce viene usato: metterla
## sempre significherebbe offrire una scelta che non ha ancora un colore.
const VOCE_PRELEVATO := "Prelevato dall'immagine"

var _opzioni: OptionButton
var _campione: ColorRect
var _cursore: HSlider
var _valore: Label
var _prelevato := ""


func _ready() -> void:
	add_theme_constant_override("separation", 6)

	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 8)
	add_child(riga)

	var l := Label.new()
	l.text = tr("Sfondo da togliere")
	riga.add_child(l)

	_opzioni = OptionButton.new()
	_opzioni.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for v in VOCI:
		_opzioni.add_item(tr(v[1]))
	_opzioni.item_selected.connect(func(_i: int) -> void: cambiato.emit())
	riga.add_child(_opzioni)

	_campione = ColorRect.new()
	_campione.custom_minimum_size = Vector2(26, 22)
	_campione.color = Color(0.2, 0.2, 0.24)
	_campione.tooltip_text = tr("Colore che verra' tolto")
	riga.add_child(_campione)

	var riga2 := HBoxContainer.new()
	riga2.add_theme_constant_override("separation", 8)
	add_child(riga2)

	var l2 := Label.new()
	l2.text = tr("Tolleranza")
	riga2.add_child(l2)

	_cursore = HSlider.new()
	_cursore.min_value = 15
	_cursore.max_value = 130
	_cursore.step = 1
	_cursore.value = 66
	_cursore.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_cursore.value_changed.connect(_su_cursore)
	riga2.add_child(_cursore)

	_valore = Label.new()
	_valore.custom_minimum_size = Vector2(32, 0)
	_valore.text = "66"
	riga2.add_child(_valore)

	var nota := Label.new()
	nota.text = tr("Clicca sull'anteprima per prelevare il colore dello sfondo.")
	nota.add_theme_font_size_override("font_size", 11)
	nota.add_theme_color_override("font_color", Color(0.776, 0.8, 0.847))
	nota.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(nota)


func _su_cursore(v: float) -> void:
	_valore.text = "%d" % int(v)
	cambiato.emit()


## Chiamata dal contagocce. Il colore arriva gia' letto dal pixel: qui si
## aggiunge (una volta sola) la voce in fondo e la si seleziona.
func preleva(c: Color) -> void:
	_prelevato = "#%02X%02X%02X" % [int(c.r8), int(c.g8), int(c.b8)]
	if _opzioni.item_count == VOCI.size():
		_opzioni.add_item(tr(VOCE_PRELEVATO))
	_opzioni.set_item_text(VOCI.size(), "%s  %s" % [tr(VOCE_PRELEVATO), _prelevato])
	_opzioni.select(VOCI.size())
	_campione.color = c
	cambiato.emit()


## Il colore misurato dal sidecar, mostrato nel campione quando si e' su auto.
## Senza, "automatico" non dice mai *quale* colore ha trovato, ed e' la prima
## cosa da guardare quando il risultato non torna.
func mostra_misurato(esadecimale: String) -> void:
	if _opzioni.selected == 0 and esadecimale.begins_with("#"):
		_campione.color = Color.html(esadecimale)


func colore() -> String:
	var i := _opzioni.selected
	if i < 0:
		return "auto"
	if i >= VOCI.size():
		return _prelevato
	return str(VOCI[i][0])


func tolleranza() -> int:
	return int(_cursore.value)
