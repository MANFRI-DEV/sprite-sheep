extends Control
## Scena di prova per vedere l'elenco file nei suoi quattro stati.
##
## Serve perche' il pannello Modelli sta in una finestra che si apre solo col
## mouse, e il clic sintetico su Godot non funziona: senza questa scena l'unico
## modo di guardare l'interfaccia sarebbe chiedere a una persona.
##
## Si lancia con:  Godot --path . prova_elenco.tscn
## Non fa parte dell'applicazione: `export_presets.cfg` esclude `prova_*`.

const ElencoFileC := preload("res://scripts/elenco_file.gd")

const CARTELLA := "E:/AI_Video/SpriteSheep/models/minimax_h3_fl2va"


func _ready() -> void:
	theme = Tema.costruisci()
	var sfondo := ColorRect.new()
	sfondo.color = Tema.FONDO
	sfondo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(sfondo)

	var margine := MarginContainer.new()
	margine.set_anchors_preset(Control.PRESET_FULL_RECT)
	for lato in ["left", "top", "right", "bottom"]:
		margine.add_theme_constant_override("margin_" + lato, 18)
	add_child(margine)

	var colonna := VBoxContainer.new()
	colonna.add_theme_constant_override("separation", 16)
	margine.add_child(colonna)

	colonna.add_child(_caso("Tutto presente — elenco chiuso di default",
		_modello([["presente", ""], ["presente", ""], ["presente", ""],
				  ["presente", ""]])))
	colonna.add_child(_caso("Download in corso",
		_modello([["presente", ""], ["in_corso", ""], ["mancante", ""],
				  ["mancante", ""]])))
	colonna.add_child(_caso("Un file fallito — il bug dei tester",
		_modello([["presente", ""],
				  ["errore", "ConnectionError: repo momentaneamente irraggiungibile"],
				  ["presente", ""], ["presente", ""]])))
	colonna.add_child(_caso("Niente scaricato",
		_modello([["mancante", ""], ["mancante", ""], ["mancante", ""],
				  ["mancante", ""]])))


func _caso(titolo: String, m: Dictionary) -> Control:
	var carta := PanelContainer.new()
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	var t := Label.new()
	t.text = titolo
	t.add_theme_font_size_override("font_size", 13)
	t.add_theme_color_override("font_color", Tema.ACCENTO)
	box.add_child(t)
	box.add_child(ElencoFileC.costruisci(m))
	carta.add_child(box)
	return carta


## Un modello finto con i quattro file di H3 negli stati richiesti.
func _modello(stati: Array) -> Dictionary:
	var nomi := [
		["minimax_h3_fl2va_pruned_fp8_scaled.safetensors", 19.5, "diffusion"],
		["qwen3vl_32b_minimax_h3_int4_convrot.safetensors", 13.9, "text_encoder"],
		["minimax_h3_video_vae_fp16.safetensors", 4.9, "vae"],
		["minimax_h3_audio_vae_fp32.safetensors", 0.6, "vae_audio"],
	]
	var file := []
	for i in nomi.size():
		var stato: String = stati[i][0]
		file.append({
			"nome": nomi[i][0], "gb": nomi[i][1], "ruolo": nomi[i][2],
			"repo": "Comfy-Org/MiniMax-H3",
			"locale": CARTELLA + "/" + nomi[i][0],
			"presente": stato == "presente",
			"stato": stato, "errore": stati[i][1],
		})
	return {"nome": "MiniMax H3", "gb_totali": 38.9, "file": file}
