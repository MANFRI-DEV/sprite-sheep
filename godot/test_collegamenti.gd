extends SceneTree
## Controlla che i pulsanti esterni siano configurati davvero.
##
## Un pulsante spento e uno acceso si distinguono a colpo d'occhio, ma un
## pulsante acceso che apre l'indirizzo sbagliato no: la verifica a mano
## consiste nel premerlo e guardare dove porta, e nessuno lo rifa' a ogni
## build. Qui si guarda l'unica cosa che conta, cioe' cosa c'e' scritto
## nell'indirizzo, e se il segno accanto al nome e' stato caricato.
##
## Le due scene si controllano **tutte e due**. Aggiungendo Instagram e'
## bastato dimenticarne una per avere tre pulsanti in testata e quattro nello
## splash, o viceversa, senza nessun errore a dirlo.
##
##     godot --headless --path godot --script test_collegamenti.gd

func _init() -> void:
	var errori := 0
	for voce in Collegamenti.VOCI:
		var nome: String = voce[0]
		var url: String = voce[2]
		var ico: Texture2D = Collegamenti.icona(nome)
		var segno := "spento"
		if Collegamenti.attivo(url):
			segno = "acceso"
		print("%-10s %-8s icona=%s  %s" % [
			nome, segno,
			"no" if ico == null else "%dx%d" % [ico.get_width(), ico.get_height()],
			url if url != "" else "(nessun indirizzo)"])
		if url != "" and not Collegamenti.attivo(url):
			print("   ERRORE: indirizzo presente ma non https")
			errori += 1
		# Il segno deve esserci anche quando l'indirizzo manca: e' il pulsante
		# spento quello che ha piu' bisogno di dire di cosa parla.
		if ico == null:
			print("   ERRORE: nessuna icona per %s" % nome)
			errori += 1

	# Lo splash si monta davvero: e' una scena chiusa, non avvia niente, e
	# montarla e' l'unico modo di vedere che `prepara` trova i nodi e li
	# accende.
	var splash: Node = load("res://scenes/splash.tscn").instantiate()
	root.add_child(splash)
	await process_frame
	var riga: Node = splash.find_child("CollegamentiRiga", true, false)
	if riga == null:
		print("\nERRORE: nessuna CollegamentiRiga nello splash")
		errori += 1
	else:
		print("\nsplash.tscn — %d pulsanti preparati"
			% Collegamenti.prepara(riga))
		for voce in Collegamenti.VOCI:
			var b: Button = riga.get_node_or_null(NodePath(voce[1])) as Button
			if b == null:
				print("   ERRORE: manca %s" % voce[1])
				errori += 1
				continue
			print("   %-20s disabled=%s icona=%s" % [
				b.name, b.disabled, "si" if b.icon != null else "no"])

	# La testata invece si legge, non si monta: `main.tscn` all'avvio accende
	# il sidecar, cioe' un processo Python e una porta aperta, e un test non
	# deve lasciarsi dietro roba accesa. Il primo tentativo la istanziava e
	# restava appeso finche' non l'ho ucciso a mano. Quello che serve sapere
	# — che i pulsanti ci siano tutti — sta nel file.
	var testo: String = FileAccess.get_file_as_string("res://scenes/main.tscn")
	print("\nmain.tscn")
	for voce in Collegamenti.VOCI:
		var c := '[node name="%s" type="Button"' % voce[1]
		var dentro := testo.contains(c)
		print("   %-20s %s" % [voce[1], "c'e'" if dentro else "MANCA"])
		if not dentro:
			errori += 1

	quit(1 if errori else 0)
