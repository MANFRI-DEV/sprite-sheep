extends Node
## Sprite e prompt caricati alla prima apertura, come esempio funzionante.
##
## Chi apre il programma per la prima volta trova gia' tutto compilato e puo'
## premere Genera: e' il modo piu' rapido per capire cosa fa. I campi restano
## modificabili, e chi ha gia' lavorato ritrova la propria roba (vedi
## `e_prima_apertura`).

const SPRITE_RES := "res://sprites/sprite_sheep.png"

## Copia dello sprite su disco vero. Il sidecar e' un processo Python separato:
## non sa cosa sia `res://`, e nella build il PNG sta dentro l'eseguibile.
const SPRITE_UTENTE := "user://sprite_sheep.png"

## Segna che i predefiniti sono gia' stati proposti una volta.
const SEGNO := "user://prima_apertura.cfg"

const CAMPI := {
	"soggetto":
		"A chubby cartoon sheep standing in profile facing the viewer's left, "
		+ "thick creamy-white curly wool covering its whole body, grey face and "
		+ "grey legs with dark hooves, small pink inner ears, round black eyes, "
		+ "pink cheek blushes, a small curled tail, waving hello with its "
		+ "front-left leg (the foreleg on the viewer's left, nearest the camera).",
	"stile":
		"Hand-drawn 2D cartoon sticker style with bold uniform black outlines, "
		+ "flat cel shading, light pencil hatching marks on the wool.",
	"sfondo":
		"Flat solid pure white background, one single uniform tone across the "
		+ "whole frame, unchanging for the entire shot.",
	"ciclico": true,
	"passi": [
		"the sheep stands still on all four legs, then shifts its weight onto its hind legs",
		"it lifts its front-left leg off the ground and raises it up beside its head",
		"it waves the raised front-left leg side to side twice in a friendly hello, "
			+ "smiling wider, the other three legs planted",
		"it lowers the front-left leg back down and settles onto all four legs in "
			+ "the starting pose",
	],
}


## Prima apertura assoluta? Solo allora si riempiono i campi da soli: dopo
## sarebbe una sovrascrittura del lavoro di chi usa il programma.
static func e_prima_apertura() -> bool:
	return not FileAccess.file_exists(SEGNO)


static func segna_aperto() -> void:
	var f := FileAccess.open(SEGNO, FileAccess.WRITE)
	if f != null:
		f.store_string("1")


## Estrae lo sprite di esempio su disco e ne restituisce il percorso assoluto.
## Stringa vuota se qualcosa va storto: l'esempio e' un di piu', non deve
## impedire l'avvio.
##
## Si passa dalla texture importata, non dal PNG sorgente: nella build il file
## originale non c'e': Godot mette nel pacchetto la sua versione importata, e
## un `FileAccess` sul percorso `.png` non trova niente. In editor funzionava,
## ed e' per questo che il difetto si e' visto solo alla prima apertura di una
## build.
static func estrai_sprite() -> String:
	var assoluto := ProjectSettings.globalize_path(SPRITE_UTENTE)
	if FileAccess.file_exists(SPRITE_UTENTE):
		return assoluto

	var tex: Texture2D = load(SPRITE_RES)
	if tex == null:
		push_warning("sprite di esempio non caricabile: %s" % SPRITE_RES)
		return ""
	var img := tex.get_image()
	if img == null:
		return ""
	# Una texture puo' arrivare compressa per la GPU: in quel caso i pixel non
	# si possono leggere finche' non la si riporta in chiaro.
	if img.is_compressed():
		img.decompress()
	if img.save_png(SPRITE_UTENTE) != OK:
		push_warning("sprite di esempio non scrivibile: %s" % SPRITE_UTENTE)
		return ""
	return assoluto
