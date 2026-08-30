extends SceneTree
## Verifica una cosa sola: il pannello Modelli comunica il modello attivo
## anche senza che nessuno clicchi la tendina.

func _initialize() -> void:
	var sidecar := Node.new()
	sidecar.set_script(load("res://scripts/sidecar_client.gd"))
	root.add_child(sidecar)

	var pann := preload("res://scenes/pannello_modelli.tscn").instantiate()
	root.add_child(pann)
	pann.imposta_sidecar(sidecar)
	await process_frame   # i nodi devono entrare nell'albero prima di usarli

	var visti := []
	pann.modello_scelto.connect(func(id: String, inst: bool) -> void:
		visti.append([id, inst]))

	await pann.aggiorna()
	print("emessi al primo giro: ", visti)
	print("modello_attivo(): '", pann.modello_attivo(), "'")
	await pann.aggiorna()
	print("dopo un ridisegno:  ", visti)
	quit()
