extends VBoxContainer
class_name EditorPassi
## Le azioni in sequenza, tutte in un blocco solo.
##
## I passi non sono campi indipendenti, e non e' una scelta grafica. Un passo
## **non esiste da solo**: il suo intervallo dipende da quanti altri ce ne
## sono, perche' la durata utile della clip viene divisa fra tutti. Aggiungere
## una riga riscrive i tempi di tutte le altre. Tenendoli separati quella
## dipendenza sarebbe invisibile, e il compito di mantenere i tempi coerenti
## finirebbe addosso all'utente.
##
## Due orologi, e non coincidono:
##   a schermo   il tempo dell'**animazione finale**, quello che si vedra' nella
##               GIF: e' cio' che l'utente ha chiesto
##   nel prompt  il tempo **clip**, compresso sulla finestra utile, perche' il
##               modello genera piu' lungo e l'ultimo ~15% viene scartato
##
## Nasce da `NodoBeat`, che era un nodo del grafo. Qui non eredita piu' da
## GraphNode: il wizard e' una finestra normale e un GraphNode fuori da una
## GraphEdit non si disegna.

signal modificato

const COLORE_TEMPO := Color(0.45, 0.7, 0.95)
const MAX_PASSI := 8

var fine_utile := 1.7
var durata := 2.0

var _righe: VBoxContainer
var _conta: Label


func _ready() -> void:
	add_theme_constant_override("separation", 6)

	var barra := HBoxContainer.new()
	barra.add_theme_constant_override("separation", 6)
	_conta = Label.new()
	_conta.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_conta.add_theme_font_size_override("font_size", 11)
	barra.add_child(_conta)
	barra.add_child(_pulsante("−", _togli))
	barra.add_child(_pulsante("+", func() -> void: _aggiungi()))
	add_child(barra)

	_righe = VBoxContainer.new()
	_righe.add_theme_constant_override("separation", 4)
	add_child(_righe)

	for i in 4:
		_aggiungi(false)
	_rinfresca()


func _pulsante(testo: String, azione: Callable) -> Button:
	var b := Button.new()
	b.text = testo
	b.custom_minimum_size = Vector2(30, 0)
	b.pressed.connect(azione)
	return b


func _aggiungi(avvisa := true) -> void:
	if _righe.get_child_count() >= MAX_PASSI:
		return
	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 6)

	var tempo := Label.new()
	tempo.name = "Tempo"
	tempo.custom_minimum_size = Vector2(84, 0)
	tempo.add_theme_font_size_override("font_size", 11)
	tempo.add_theme_color_override("font_color", COLORE_TEMPO)
	riga.add_child(tempo)

	var campo := TextEdit.new()
	campo.custom_minimum_size = Vector2(0, 46)
	campo.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	campo.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	campo.placeholder_text = tr("cosa succede in questo passo")
	campo.text_changed.connect(func() -> void: modificato.emit())
	riga.add_child(campo)
	riga.set_meta("campo", campo)

	_righe.add_child(riga)
	_rinfresca()
	if avvisa:
		modificato.emit()


func _togli() -> void:
	var n := _righe.get_child_count()
	if n <= 1:
		return                     # un prompt senza nemmeno un passo non esiste
	var ultima := _righe.get_child(n - 1)
	_righe.remove_child(ultima)
	ultima.queue_free()
	_rinfresca()
	modificato.emit()


func imposta_tempi(durata_chiesta: float, fine: float) -> void:
	durata = durata_chiesta
	fine_utile = fine
	_rinfresca()


func imposta_passi(passi: Array) -> void:
	while _righe.get_child_count() > passi.size():
		var u := _righe.get_child(_righe.get_child_count() - 1)
		_righe.remove_child(u)
		u.queue_free()
	while _righe.get_child_count() < passi.size():
		_aggiungi(false)
	for i in passi.size():
		_righe.get_child(i).get_meta("campo").text = str(passi[i])
	_rinfresca()


## I passi nel tempo **della clip generata**: sono quelli che finiscono nel
## prompt. Gli intervalli mostrati a schermo sono altri, vedi `_rinfresca`.
func beat() -> Array:
	var n: int = maxi(1, _righe.get_child_count())
	var fuori := []
	for i in _righe.get_child_count():
		var testo: String = _righe.get_child(i).get_meta("campo").text.strip_edges()
		if testo == "":
			continue
		fuori.append({
			"da": snappedf(fine_utile * i / n, 0.01),
			"a": snappedf(fine_utile * (i + 1) / n, 0.01),
			"testo": testo})
	return fuori


func quanti_compilati() -> int:
	return beat().size()


func _rinfresca() -> void:
	var n: int = maxi(1, _righe.get_child_count())
	for i in _righe.get_child_count():
		var eti: Label = _righe.get_child(i).get_node("Tempo")
		eti.text = "%.1f–%.1f s" % [snappedf(durata * i / n, 0.1),
									snappedf(durata * (i + 1) / n, 0.1)]
	if _conta != null:
		_conta.text = tr("%d passi su %.1f s") % [n, durata]
