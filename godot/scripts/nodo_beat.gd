extends GraphNode
class_name NodoBeat
## Il rettangolo dei tempi: tutte le azioni in sequenza, in un blocco solo.
##
## I beat non sono blocchi separati come le altre sezioni, e non e' una scelta
## grafica. Un beat **non esiste da solo**: il suo intervallo dipende da quanti
## altri ce ne sono, perche' la durata utile della clip viene divisa fra tutti.
## Aggiungere una riga riscrive i tempi di tutte le altre. Con un nodo per beat
## quella dipendenza sarebbe invisibile, e sposterebbe sull'utente il compito
## di tenere i tempi coerenti.
##
## Da qui i due pulsanti: `+` aggiunge una riga in fondo, `−` toglie l'ultima.
## Gli intervalli si ricalcolano da soli a ogni cambiamento.

signal modificato

const COLORE_FILO := Color(0.45, 0.7, 0.95)
const MAX_BEAT := 8

## Istante oltre il quale i fotogrammi vengono scartati: i beat devono
## chiudersi entro quello, non entro la durata nominale della clip.
var fine_utile := 1.7
## La durata che l'utente ha chiesto: e' quella che mostriamo, perche' e' il
## tempo che vedra' nella GIF.
var durata := 2.0

var _righe: VBoxContainer
var _conta: Label


func costruisci() -> void:
	title = tr("Tempi")
	resizable = true
	custom_minimum_size = Vector2(360, 0)

	var barra := HBoxContainer.new()
	barra.add_theme_constant_override("separation", 6)
	_conta = Label.new()
	_conta.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_conta.add_theme_font_size_override("font_size", 11)
	barra.add_child(_conta)
	barra.add_child(_pulsante("−", _togli))
	barra.add_child(_pulsante("+", _aggiungi))
	add_child(barra)

	_righe = VBoxContainer.new()
	_righe.add_theme_constant_override("separation", 4)
	add_child(_righe)

	# L'uscita sta sulla prima riga, quella della barra: e' l'unica che esiste
	# di sicuro, mentre le righe dei beat vanno e vengono.
	set_slot(0, false, 0, COLORE_FILO, true, 0, COLORE_FILO)

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
	if _righe.get_child_count() >= MAX_BEAT:
		return
	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 6)

	var tempo := Label.new()
	tempo.name = "Tempo"
	tempo.custom_minimum_size = Vector2(84, 0)
	tempo.add_theme_font_size_override("font_size", 11)
	tempo.add_theme_color_override("font_color", COLORE_FILO)
	riga.add_child(tempo)

	var campo := TextEdit.new()
	campo.custom_minimum_size = Vector2(0, 42)
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
		return                     # un prompt senza nemmeno un beat non esiste
	var ultima := _righe.get_child(n - 1)
	_righe.remove_child(ultima)
	ultima.queue_free()
	_rinfresca()
	modificato.emit()


func imposta_tempi(durata_chiesta: float, fine: float) -> void:
	durata = durata_chiesta
	fine_utile = fine
	_rinfresca()


## Riempie le righe con i testi dati, adattando il numero di righe.
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


## I beat, con gli estremi nel tempo **della clip generata**: sono quelli che
## finiscono nel prompt. Gli intervalli mostrati a schermo sono altri, vedi
## `_rinfresca`.
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


func _rinfresca() -> void:
	var n: int = maxi(1, _righe.get_child_count())
	for i in _righe.get_child_count():
		# A schermo si mostra il tempo dell'animazione finale, non quello
		# della clip: e' quello che l'utente riconoscera' guardando la GIF.
		var eti: Label = _righe.get_child(i).get_node("Tempo")
		eti.text = "%.1f–%.1f s" % [snappedf(durata * i / n, 0.1),
									snappedf(durata * (i + 1) / n, 0.1)]
	_conta.text = tr("%d passi su %.1f s") % [n, durata]
