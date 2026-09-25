extends SceneTree
## Prova delle scene senza sidecar: si caricano, si istanziano, i nodi che gli
## script cercano con % esistono. Esclusa dall'export (`test_*.gd`).
##
##     godot --headless --path godot --script res://test_scene.gd

var _errori: Array[String] = []


func _verifica(cond: bool, msg: String) -> void:
	if not cond:
		_errori.append(msg)


func _init() -> void:
	# main.tscn si carica ma non si istanzia: il suo _ready avvia il sidecar.
	for s in ["main", "pannello_immagine", "pannello_prompt", "pannello_modelli",
			"pannello_genera", "pannello_comfyui", "pannello_risultato", "splash"]:
		_verifica(load("res://scenes/%s.tscn" % s) != null, "scena %s non caricabile" % s)

	var genera: Node = load("res://scenes/pannello_genera.tscn").instantiate()
	var risultato: Node = load("res://scenes/pannello_risultato.tscn").instantiate()
	var cronologia: Window = load("res://scripts/finestra_cronologia.gd").new()
	for n in [genera, risultato, cronologia]:
		root.add_child(n)
	await process_frame

	var formato: OptionButton = genera.get_node("%FormatoOption")
	_verifica(formato.item_count == 6, "formati: %d" % formato.item_count)
	_verifica(genera.get_node("%MargineOption").item_count == 3, "margini")
	var lista = genera.get_node("%ListaAzioni")
	lista.aggiungi({"nome": "idle", "prompt": "p", "durata_s": 2.0, "n_frame": 16})
	_verifica(lista.azioni().size() == 1, "lista azioni")
	lista.svuota()
	_verifica(lista.azioni().is_empty(), "svuota")

	# Il risultato di un lotto: celle rettangolari, seme, log assente.
	var img := Image.create(192 * 2, 256 * 2, false, Image.FORMAT_RGBA8)
	var percorso := OS.get_user_data_dir().path_join("prova_sheet.png")
	img.save_png(percorso)
	risultato.mostra({"sheet": {"percorso": percorso, "colonne": 2, "righe": 2, "celle": 4},
		"gif": {"frame": 4, "fps_reale": 10.0, "durata_s": 0.4}, "seed": 7,
		"cartella": OS.get_user_data_dir(), "log": null})
	_verifica(risultato.get_node("%Contenuto").visible, "risultato non mostrato")
	DirAccess.remove_absolute(percorso)

	# Schermata principale con un sidecar finto: niente processo Python.
	var finto := GDScript.new()
	finto.source_code = """extends Node
signal sidecar_pronto(info)
signal sidecar_errore(messaggio)
func avvia() -> void: pass
func ferma() -> void: pass
func get_json(_r: String) -> Dictionary: return {}
func post_json(_r: String, _c: Dictionary) -> Dictionary: return {}
"""
	finto.reload()
	var main: Node = load("res://scenes/main.tscn").instantiate()
	main.get_node("Sidecar").set_script(finto)
	root.add_child(main)
	await process_frame
	var spie: Node = main.get_node("%SpieRiga")
	_verifica(spie.get_child_count() == 4, "spie: %d" % spie.get_child_count())
	_verifica(main.get_node("%LinguaOption").item_count == 2, "lingue")

	# Diagnostica: tre casi di GPU, niente markup negli appunti.
	var righe: Array = Diagnostica.righe({"app": "Sprite Sheep", "version": "x",
		"capacita": {"cuda": true, "gpu": "Radeon", "api": "rocm", "vram_mb": 8192}})
	var testo := "\n".join(righe)
	_verifica(testo.contains("Radeon - ROCm"), "GPU AMD: %s" % testo)
	_verifica(not Diagnostica.senza_tag(testo).contains("[b]"), "markup negli appunti")
	_verifica(Diagnostica.spia_motore({"comfyui_spenta": true})[0] == Tema.AVVISO, "ComfyUI spenta")
	_verifica(Diagnostica.spia_motore({})[0] == Tema.ERRORE, "nessuna GPU")

	# Riga di un modello in download: costruzione senza errori.
	var riga := RigaModello.costruisci({"id": "m", "nome": "M", "gb_totali": 1.0,
		"descrizione": "d", "file": [], "download": {"attivo": true, "percentuale": 40.0}},
		{"scarica": func(_i): pass, "licenza": func(_i): pass, "cartella": func(_i): pass})
	_verifica(riga.get_child_count() >= 4, "riga modello")
	riga.free()
	_verifica(TestiGenerazione.formatta(372.0) == "6:12", "formatta")
	_verifica(TestiGenerazione.in_corso({"percentuale": 0.5, "eta_s": 90}, 10.0).contains("1:30"), "eta")

	for e in _errori:
		printerr("ERRORE: ", e)
	print("tutto a posto" if _errori.is_empty() else "%d errori" % _errori.size())
	quit(0 if _errori.is_empty() else 1)
