extends SceneTree
## Le due lingue risolvono davvero, e risolvono in modo diverso?
##
## Il csv puo' essere a posto e i .translation compilati restare indietro: sono
## risorse generate all'importazione, e se l'importazione non e' stata rifatta
## l'interfaccia mostra le stringhe vecchie senza dirlo.
##
##     Godot --headless --path godot --script test_lingue.gd

func _initialize() -> void:
	var esito := 0
	var csv := FileAccess.open("res://traduzioni.csv", FileAccess.READ)
	var testa := csv.get_csv_line()
	var chiavi: Array[String] = []
	var atteso := {"it": {}, "en": {}}
	while not csv.eof_reached():
		var r := csv.get_csv_line()
		if r.size() < 3 or r[0].strip_edges() == "":
			continue
		chiavi.append(r[0])
		atteso["it"][r[0]] = r[1]
		atteso["en"][r[0]] = r[2]
	print("intestazione=", testa, "  chiavi=", chiavi.size())

	for lingua: String in ["it", "en"]:
		TranslationServer.set_locale(lingua)
		var mancano := 0
		var sbagliate := 0
		for k in chiavi:
			var t := tr(k)
			if t == k and atteso[lingua][k] != k:
				mancano += 1
				if mancano <= 3:
					printerr("  [%s] non tradotta: %s" % [lingua, k])
			elif t != atteso[lingua][k]:
				sbagliate += 1
				if sbagliate <= 3:
					printerr("  [%s] %s -> atteso [%s], ottenuto [%s]"
						% [lingua, k, atteso[lingua][k], t])
		print("%s: %d chiavi, non tradotte %d, diverse dal csv %d"
			% [lingua, chiavi.size(), mancano, sbagliate])
		if mancano > 0 or sbagliate > 0:
			esito = 1

	# Le due lingue devono differire davvero: se il file inglese fosse una copia
	# di quello italiano il controllo di sopra passerebbe lo stesso.
	TranslationServer.set_locale("it")
	var a := tr("Scegli immagine...")
	TranslationServer.set_locale("en")
	var b := tr("Scegli immagine...")
	print("campione  it=[%s]  en=[%s]" % [a, b])
	if a == b:
		printerr("le due lingue danno lo stesso testo")
		esito = 1

	print("ESITO: ", "ok" if esito == 0 else "FALLITO")
	quit(esito)
