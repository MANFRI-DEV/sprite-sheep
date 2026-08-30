extends RefCounted
class_name ElencoFile
## Elenco dei file che compongono un modello, con stato e percorso.
##
## Sta in un file suo perche' il pannello Modelli era gia' oltre le duecento
## righe e questa e' una responsabilita' distinta: dire *cosa* c'e' su disco,
## mentre il pannello dice cosa fare.
##
## Tre scelte di presentazione, tutte per lo stesso motivo — l'elenco e' un
## dettaglio, non deve rubare la scena a "Scarica":
##
## 1. E' chiuso finche' i file sono tutti a posto, e si apre da solo quando
##    qualcosa manca o e' fallito. Chi non ha problemi non lo vede mai.
## 2. La cartella si scrive **una volta sola** in testa, non su ogni riga:
##    e' identica per tutti i file, e ripeterla quattro volte allungherebbe
##    ogni percorso oltre la larghezza del pannello senza aggiungere nulla.
## 3. Il messaggio d'errore sta sotto il file che l'ha prodotto, non in fondo
##    al modello: e' l'unico posto in cui si legge senza doverlo collegare.

const COLORI := {
	"presente": Color(0.36, 0.81, 0.49),
	"mancante": Color(0.49, 0.53, 0.60),
	"in_corso": Color(0.88, 0.71, 0.29),
	"errore":   Color(0.88, 0.36, 0.36),
}

## Pallino pieno per cio' che c'e', vuoto per cio' che manca: la forma
## distingue gli stati anche a chi non vede bene i colori.
const SIMBOLI := {
	"presente": "●", "mancante": "○", "in_corso": "◐", "errore": "✕",
}


## `tr()` e' un metodo di Node e da un contesto statico non si puo' chiamare.
## `TranslationServer.translate()` fa la stessa cosa senza pretendere un nodo.
static func TR(chiave: String) -> String:
	return TranslationServer.translate(chiave)


static func costruisci(m: Dictionary) -> Control:
	var file: Array = m.get("file", [])
	if file.is_empty():
		return Control.new()

	var presenti := 0
	var gb_presenti := 0.0
	var problemi := 0
	for f in file:
		if f.get("presente", false):
			presenti += 1
			gb_presenti += float(f.get("gb", 0))
		if str(f.get("stato", "")) in ["errore", "mancante"]:
			problemi += 1

	var radice := VBoxContainer.new()
	radice.add_theme_constant_override("separation", 2)

	var corpo := VBoxContainer.new()
	corpo.add_theme_constant_override("separation", 3)
	# Aperto solo se c'e' qualcosa da guardare. Un modello completo non ha
	# bisogno di mostrare quattro righe verdi a chi non le ha chieste.
	corpo.visible = problemi > 0

	radice.add_child(_intestazione(file.size(), presenti, gb_presenti,
		float(m.get("gb_totali", 0)), corpo))

	if file.size() > 0:
		corpo.add_child(_riga_cartella(str(file[0].get("locale", ""))))
	for f in file:
		corpo.add_child(_riga_file(f))
	radice.add_child(corpo)
	return radice


## Riga sempre visibile: apre e chiude, e da sola dice a che punto siamo.
static func _intestazione(totale: int, presenti: int, gb_ora: float,
		gb_tot: float, corpo: Control) -> Control:
	var b := Button.new()
	b.flat = true
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_size_override("font_size", 12)

	var aggiorna := func() -> void:
		b.text = "%s %s   %d/%d · %.1f / %.1f GB" % [
			"▾" if corpo.visible else "▸", TR("File del modello"),
			presenti, totale, gb_ora, gb_tot]
	aggiorna.call()
	b.pressed.connect(func() -> void:
		corpo.visible = not corpo.visible
		aggiorna.call())
	b.add_theme_color_override("font_color",
		Color(0.36, 0.81, 0.49) if presenti == totale else Color(0.55, 0.59, 0.66))
	return b


static func _riga_cartella(percorso_file: String) -> Control:
	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 6)

	var cartella := percorso_file.get_base_dir()

	var eti := Label.new()
	eti.text = TR("Cartella:")
	eti.add_theme_font_size_override("font_size", 10)
	eti.add_theme_color_override("font_color", Color(0.38, 0.41, 0.47))
	riga.add_child(eti)

	var et := Label.new()
	et.text = cartella
	et.tooltip_text = cartella
	et.add_theme_font_size_override("font_size", 10)
	et.add_theme_color_override("font_color", Color(0.55, 0.59, 0.66))
	# Il percorso e' lungo e non deve allargare il pannello: si tronca, e per
	# intero resta nel tooltip.
	et.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	et.clip_text = true
	et.custom_minimum_size = Vector2(120, 0)
	riga.add_child(et)

	# Il pulsante sta **accanto** al percorso, non spinto al bordo opposto del
	# pannello: separarli di mezzo schermo li fa leggere come due cose diverse,
	# e chi vuole aprire la cartella deve cercare dove sia finito il comando.
	var apri := Button.new()
	apri.text = TR("Apri")
	apri.tooltip_text = TR("Apri la cartella dei modelli")
	apri.add_theme_font_size_override("font_size", 10)
	apri.pressed.connect(func() -> void: OS.shell_open(cartella))
	riga.add_child(apri)

	var spinta := Control.new()
	spinta.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	riga.add_child(spinta)
	return riga


static func _riga_file(f: Dictionary) -> Control:
	var stato := str(f.get("stato", "mancante"))
	var colore: Color = COLORI.get(stato, COLORI["mancante"])

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 1)

	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 6)

	var punto := Label.new()
	punto.text = SIMBOLI.get(stato, "○")
	punto.add_theme_color_override("font_color", colore)
	punto.add_theme_font_size_override("font_size", 12)
	riga.add_child(punto)

	var nome := Label.new()
	nome.text = str(f.get("nome", ""))
	nome.tooltip_text = "%s\n%s" % [str(f.get("repo", "")), str(f.get("locale", ""))]
	nome.add_theme_font_size_override("font_size", 11)
	nome.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nome.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	nome.clip_text = true
	riga.add_child(nome)

	var peso := Label.new()
	peso.text = "%.1f GB" % float(f.get("gb", 0))
	peso.add_theme_font_size_override("font_size", 11)
	peso.add_theme_color_override("font_color", Color(0.49, 0.53, 0.60))
	riga.add_child(peso)

	var et_stato := Label.new()
	et_stato.text = _etichetta(stato)
	et_stato.custom_minimum_size = Vector2(86, 0)
	et_stato.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	et_stato.add_theme_font_size_override("font_size", 11)
	et_stato.add_theme_color_override("font_color", colore)
	riga.add_child(et_stato)
	box.add_child(riga)

	var errore := str(f.get("errore", ""))
	if errore != "":
		var e := Label.new()
		e.text = "     " + errore
		e.add_theme_font_size_override("font_size", 10)
		e.add_theme_color_override("font_color", COLORI["errore"])
		e.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		box.add_child(e)
	return box


static func _etichetta(stato: String) -> String:
	match stato:
		"presente": return TR("presente")
		"in_corso": return TR("in corso")
		"errore":   return TR("errore")
		_:          return TR("da scaricare")
