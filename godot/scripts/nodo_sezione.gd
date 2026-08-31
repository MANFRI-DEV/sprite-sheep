extends GraphNode
class_name NodoSezione
## Un blocco del prompt: un titolo, un campo, un'uscita da collegare.
##
## Il testo del prompt e' fatto di parti che il modello vuole in un ordine
## preciso — chi e' il soggetto, con che stile, su che sfondo, come si comporta
## la camera. Finche' erano campi impilati in una colonna, quell'ordine era
## implicito e la parte che contava — **cosa entra nel prompt e cosa no** — non
## si vedeva affatto: un campo vuoto e un campo escluso erano la stessa cosa.
##
## Qui un blocco entra nel prompt se il suo filo arriva al nodo Prompt. Vale la
## pena averlo reso visibile: scollegare "Sfondo" per provare senza, e
## ricollegarlo, e' il gesto che si fa piu' spesso mentre si cerca un prompt che
## funzioni.

signal modificato

const COLORE_FILO := Color(0.45, 0.7, 0.95)

var chiave := ""
var _campo: Control


func costruisci(id: String, titolo: String, suggerimento: String,
		righe: int = 3) -> void:
	chiave = id
	title = titolo
	resizable = true
	custom_minimum_size = Vector2(260, 0)

	var t := TextEdit.new()
	t.placeholder_text = suggerimento
	t.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	t.custom_minimum_size = Vector2(0, righe * 22)
	t.size_flags_vertical = Control.SIZE_EXPAND_FILL
	t.text_changed.connect(func() -> void: modificato.emit())
	add_child(t)
	_campo = t

	# Uscita sulla riga 0, nessun ingresso: un blocco di testo non riceve
	# niente da altri blocchi, li' finisce solo dentro al prompt.
	set_slot(0, false, 0, COLORE_FILO, true, 0, COLORE_FILO)


## Variante a scelta fissa, per la camera: le formule che funzionano sono due,
## e lasciarle scrivere a mano invita a riscriverle peggio.
func costruisci_scelta(id: String, titolo: String, voci: Dictionary) -> void:
	chiave = id
	title = titolo
	custom_minimum_size = Vector2(260, 0)

	var o := OptionButton.new()
	for etichetta in voci:
		o.add_item(etichetta)
	o.set_meta("voci", voci)
	o.item_selected.connect(func(_i: int) -> void: modificato.emit())
	add_child(o)
	_campo = o

	set_slot(0, false, 0, COLORE_FILO, true, 0, COLORE_FILO)


func valore() -> String:
	if _campo is TextEdit:
		return _campo.text
	if _campo is OptionButton:
		var voci: Dictionary = _campo.get_meta("voci", {})
		return str(voci.get(_campo.get_item_text(maxi(_campo.selected, 0)), ""))
	return ""


func imposta_valore(testo: String) -> void:
	if _campo is TextEdit:
		_campo.text = testo
