extends SceneTree
## Verifica il pannello Risultato con un output vero gia' su disco, e il
## rapporto d'errore copiabile del pannello Generazione.

func _initialize() -> void:
	var ris := preload("res://scenes/pannello_risultato.tscn").instantiate()
	root.add_child(ris)
	await process_frame

	var cartella := "E:/AI_Video/SpriteSheep/output/idle"
	ris.mostra({
		"cartella": cartella,
		"sheet": {"percorso": cartella + "/idle_sheet.png",
			"larghezza": 1280, "altezza": 1280, "colonne": 5, "righe": 5, "celle": 25},
		"gif": {"frame": 25, "fps_reale": 11.1, "durata_s": 2.25},
	})
	print("contenuto visibile: ", ris.get_node("%Contenuto").visible)
	print("celle ritagliate:   ", ris._celle.size())
	print("dati: ", ris.get_node("%DatiLabel").text.replace("\n", " | "))

	# foglio inesistente: deve dirlo, non lasciare un riquadro vuoto
	ris.mostra({"cartella": "x", "sheet": {"percorso": "E:/non/esiste.png"}, "gif": {}})
	print("mancante -> ", ris.get_node("%Vuoto").text)

	var gen := preload("res://scenes/pannello_genera.tscn").instantiate()
	root.add_child(gen)
	await process_frame
	gen._mostra_errore({
		"errore": "RuntimeError: ComfyUI ha fallito",
		"traccia": "Traceback (most recent call last):\n  File \"genera.py\", line 70\n",
		"richiesta": {"modello": "minimax_h3_fl2va", "nome": "idle", "n_frame": 25},
	})
	print("riga errore visibile: ", gen.get_node("%RigaErrore").visible)
	print("--- rapporto negli appunti ---")
	print(gen._rapporto)
	quit()
