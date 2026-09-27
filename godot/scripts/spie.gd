class_name Spie
extends RefCounted
## Pallino + etichetta nella barra in alto: motore, ComfyUI, modello, edizione.
## Piu' compatto di un pannello e sempre visibile: il modello attivo, in
## particolare, prima non si vedeva.

var _riga: Container
var _spie := {}


func _init(riga: Container) -> void:
	_riga = riga


## Si passano le chiavi, non le stringhe tradotte: al momento della creazione
## il locale puo' essere ancora quello di partenza, e una tr() fatta adesso
## resterebbe congelata nella lingua sbagliata per tutta la sessione.
func crea(chiave: String, titolo_chiave: String) -> void:
	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 6)
	var punto := ColorRect.new()
	punto.custom_minimum_size = Vector2(8, 8)
	punto.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	punto.color = Tema.SPENTO
	riga.add_child(punto)
	var testo := Label.new()
	testo.text = TranslationServer.translate(titolo_chiave)
	testo.add_theme_font_size_override("font_size", 12)
	testo.add_theme_color_override("font_color", Tema.TENUE)
	riga.add_child(testo)
	_riga.add_child(riga)
	# Si conserva anche l'ultimo dettaglio: al cambio di lingua la spia va
	# riscritta per intero, e il dettaglio non sempre si puo' richiedere di nuovo.
	_spie[chiave] = {"punto": punto, "testo": testo,
		"titolo_chiave": titolo_chiave, "dettaglio": ""}


func imposta(chiave: String, colore: Color, dettaglio: String) -> void:
	var s: Dictionary = _spie[chiave]
	s["punto"].color = colore
	s["dettaglio"] = dettaglio
	_scrivi(s)


## Riscrive le spie nella lingua corrente, conservando stato e colore.
func ritraduci() -> void:
	for chiave in _spie:
		_scrivi(_spie[chiave])


func _scrivi(s: Dictionary) -> void:
	s["testo"].text = "%s: %s" % [TranslationServer.translate(s["titolo_chiave"]), s["dettaglio"]]
