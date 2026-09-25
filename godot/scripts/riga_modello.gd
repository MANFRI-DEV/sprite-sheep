class_name RigaModello
## La scheda di un modello nel pannello Modelli: nome, stato, file, e i comandi
## che servono a quello stato (scarica, licenza, cartella, avanzamento).
##
## Solo costruzione di nodi: cosa fanno i pulsanti lo decide il pannello, che
## passa le sue funzioni in `azioni`.


static func _t(testo: String) -> String:
	return TranslationServer.translate(testo)


## Etichetta piccola col bordo colorato, per marcare lo stato di un modello.
static func _targhetta(testo: String, colore: Color) -> Control:
	var cornice := PanelContainer.new()
	cornice.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var stile := StyleBoxFlat.new()
	stile.bg_color = Color(colore.r, colore.g, colore.b, 0.16)
	stile.border_color = colore
	stile.set_border_width_all(1)
	stile.set_corner_radius_all(4)
	stile.content_margin_left = 7
	stile.content_margin_right = 7
	stile.content_margin_top = 1
	stile.content_margin_bottom = 1
	cornice.add_theme_stylebox_override("panel", stile)
	var et := Label.new()
	et.text = testo
	et.add_theme_font_size_override("font_size", 10)
	et.add_theme_color_override("font_color", colore)
	cornice.add_child(et)
	return cornice


## `azioni`: Callable per "scarica", "licenza" e "cartella", ognuna
## chiamata con l'id del modello.
static func costruisci(m: Dictionary, azioni: Dictionary) -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 4)

	# Titolo e stato sulla stessa riga: l'etichetta deve stare accanto al nome,
	# non sotto, altrimenti chi scorre l'elenco la salta.
	var riga_titolo := HBoxContainer.new()
	riga_titolo.add_theme_constant_override("separation", 8)
	var titolo := Label.new()
	titolo.text = "%s — %.1f GB" % [m["nome"], float(m["gb_totali"])]
	riga_titolo.add_child(titolo)
	if str(m.get("stato_sviluppo", "")) == "in_lavorazione":
		riga_titolo.add_child(_targhetta(_t("IN LAVORAZIONE"),
			Color(0.88, 0.66, 0.25)))
	box.add_child(riga_titolo)

	var desc := Label.new()
	desc.text = str(m["descrizione"])
	desc.add_theme_font_size_override("font_size", 11)
	desc.add_theme_color_override("font_color", Color(0.776, 0.8, 0.847))
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(desc)

	# L'elenco dei file sta fra la descrizione e i comandi: prima cosa c'e',
	# poi cosa si puo' fare. E' l'ordine in cui la domanda si pone.
	box.add_child(ElencoFile.costruisci(m))

	var dl: Dictionary = m.get("download", {})
	if m.get("installato", false):
		box.add_child(etichetta(_t("Installato"), Color(0.35, 0.8, 0.45)))
	elif dl.get("attivo", false):
		# La barra misura l'intero scaricamento, non il file in corso: con file
		# da 19,5 a 0,6 GB il conteggio "2 di 4" non dice quanto manca, perche'
		# i file non pesano uguale. La percentuale e' pesata sui GB.
		var pct := float(dl.get("percentuale", 0.0))
		var barra := ProgressBar.new()
		barra.max_value = 100.0
		barra.step = 0.1
		barra.value = pct
		barra.show_percentage = false
		box.add_child(barra)

		var riga_pct := HBoxContainer.new()
		riga_pct.add_theme_constant_override("separation", 8)
		var grande := Label.new()
		grande.text = "%.1f%%" % pct
		grande.add_theme_font_size_override("font_size", 16)
		grande.add_theme_color_override("font_color", Color(0.85, 0.75, 0.35))
		riga_pct.add_child(grande)
		var totali := Label.new()
		totali.text = _t("%.1f di %.1f GB") % [
			float(dl.get("gb_scaricati", 0.0)), float(dl.get("gb_totali", 0.0))]
		totali.add_theme_font_size_override("font_size", 12)
		totali.add_theme_color_override("font_color", Color(0.776, 0.8, 0.847))
		totali.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		riga_pct.add_child(totali)
		box.add_child(riga_pct)

		box.add_child(etichetta(_t("File %d di %d: %s (%.1f di %.1f GB)") % [
			int(dl.get("indice", 0)), int(dl.get("totale", 1)),
			dl.get("file_corrente", "..."),
			float(dl.get("gb_fatti", 0.0)), float(dl.get("gb_file", 0.0))],
			Color(0.776, 0.8, 0.847)))
	elif dl.get("errore", null) != null:
		box.add_child(etichetta(_t("Errore: %s") % dl["errore"], Color(0.9, 0.4, 0.4)))
	else:
		# Due strade: scaricare da HuggingFace, oppure collegare i pesi che
		# l'utente ha gia' (di solito dentro una ComfyUI). La seconda evita
		# decine di GB di download inutile.
		var riga := HBoxContainer.new()
		riga.add_theme_constant_override("separation", 8)

		var btn := Button.new()
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if m.get("licenza_accettata", false):
			var mancano := 0
			for f in m.get("file", []):
				if not f.get("presente", false):
					mancano += 1
			var tot: int = m.get("file", []).size()
			# Il download salta i file gia' presenti: dirlo evita che chi ha
			# venti giga sul disco tema di riscaricarli.
			btn.text = _t("Scarica") if mancano == tot \
				else _t("Scarica i %d file mancanti") % mancano
			btn.pressed.connect(azioni["scarica"].bind(str(m["id"])))
		else:
			btn.text = _t("Leggi licenza e installa")
			btn.pressed.connect(azioni["licenza"].bind(str(m["id"])))
		riga.add_child(btn)

		var btn_cart := Button.new()
		btn_cart.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		btn_cart.text = _t("Seleziona cartella...")
		btn_cart.tooltip_text = _t("Indica una cartella che contiene gia' questi file "
			+ "(per esempio models/ di ComfyUI): vengono collegati, non copiati.")
		btn_cart.pressed.connect(azioni["cartella"].bind(str(m["id"])))
		riga.add_child(btn_cart)

		box.add_child(riga)

	box.add_child(HSeparator.new())
	return box


static func etichetta(testo: String, colore: Color) -> Label:
	var l := Label.new()
	l.text = testo
	l.add_theme_color_override("font_color", colore)
	l.add_theme_font_size_override("font_size", 12)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l
