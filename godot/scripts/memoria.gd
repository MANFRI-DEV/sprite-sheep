class_name Memoria
## Le scelte che l'interfaccia ricorda fra un avvio e l'altro: lingua, modello,
## formato, margine, scontorno. Un file di testo per scelta in `user://`.
##
## Stava copiato in quattro script, ognuno con la sua variante del controllo
## sul file mancante: una sola versione vuol dire un solo modo di sbagliare.


## Il valore salvato, o `predefinito` se non c'e' o non si legge.
static func leggi(percorso: String, predefinito: String) -> String:
	if percorso == "" or not FileAccess.file_exists(percorso):
		return predefinito
	var f := FileAccess.open(percorso, FileAccess.READ)
	if f == null:
		return predefinito
	var v := f.get_as_text().strip_edges()
	return predefinito if v == "" else v


static func scrivi(percorso: String, valore: String) -> void:
	if percorso == "":
		return
	var f := FileAccess.open(percorso, FileAccess.WRITE)
	if f != null:
		f.store_string(valore)
