extends SceneTree
## Il wizard produce gli stessi campi che produceva il grafo?
##
## E' l'unica cosa che il sidecar vede, e l'unica che puo' rompersi in silenzio:
## se `campi()` cambia forma, `prompt.componi()` compone un prompt monco senza
## dire niente a nessuno.
##
##     Godot --headless --path godot --script test_wizard.gd

const CHIAVI_ATTESE := ["soggetto", "stile", "sfondo", "camera", "beat", "ciclico"]

var _w: WizardPrompt


## Il controllo non si puo' fare in `_initialize`: il `_ready` di una Window
## non viene eseguito quando la si aggiunge all'albero, ma al primo frame.
## Provandoci si legge un wizard ancora vuoto — zero pagine, zero campi — e il
## test passa o fallisce per il motivo sbagliato.
func _initialize() -> void:
	_w = WizardPrompt.new()
	root.add_child(_w)


func _process(_delta: float) -> bool:
	var w := _w
	w.imposta(null, "minimax_h3_fl2va", 2.0, 1.98)

	var esito := 0
	if w.numero_pagine() != 6:
		printerr("attese 6 pagine, trovate ", w.numero_pagine())
		esito = 1
	var c: Dictionary = w.campi()

	for k in CHIAVI_ATTESE:
		if not c.has(k):
			printerr("manca la chiave: ", k)
			esito = 1
	for k in c:
		if not (k in CHIAVI_ATTESE):
			printerr("chiave di troppo: ", k)
			esito = 1

	if not (c["beat"] is Array):
		printerr("beat non e' un Array: ", typeof(c["beat"]))
		esito = 1
	if not (c["ciclico"] is bool):
		printerr("ciclico non e' un bool")
		esito = 1
	if str(c["camera"]).find("locked off") < 0:
		printerr("camera: atteso il testo della camera bloccata, trovato: ", c["camera"])
		esito = 1

	# Precompilazione: e' la via da cui passa l'esempio alla prima apertura.
	w.precompila({
		"soggetto": "a cartoon sheep",
		"stile": "flat 2D",
		"sfondo": "solid white",
		"passi": ["stands still", "bends knees", "jumps", "lands"],
		"ciclico": true,
	})
	c = w.campi()
	if c["soggetto"] != "a cartoon sheep":
		printerr("precompila non ha riempito il soggetto")
		esito = 1
	var beat: Array = c["beat"]
	if beat.size() != 4:
		printerr("attesi 4 passi, trovati ", beat.size())
		esito = 1
	else:
		# I passi devono coprire la finestra utile senza buchi ne' sormonti, e
		# chiudere esattamente su di essa: e' il vincolo che la validazione del
		# sidecar controlla, e sbagliarlo qui da' sempre giallo.
		if abs(float(beat[0]["da"])) > 0.001:
			printerr("il primo passo non parte da 0: ", beat[0]["da"])
			esito = 1
		if abs(float(beat[3]["a"]) - 1.98) > 0.02:
			printerr("l'ultimo passo non chiude sulla finestra utile: ", beat[3]["a"])
			esito = 1
		for i in range(1, beat.size()):
			if abs(float(beat[i]["da"]) - float(beat[i - 1]["a"])) > 0.001:
				printerr("buco fra il passo ", i - 1, " e il ", i)
				esito = 1

	if w.vuoto():
		printerr("vuoto() vero dopo la precompilazione")
		esito = 1

	print("campi: ", c.keys())
	print("beat[0]: ", beat[0] if beat.size() > 0 else "-")
	print("beat[3]: ", beat[3] if beat.size() > 3 else "-")
	print("ESITO: ", "ok" if esito == 0 else "FALLITO")
	quit(esito)
	return true
