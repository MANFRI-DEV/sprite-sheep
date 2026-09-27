class_name TestiGenerazione
## I testi del pannello Generazione, ricavati dalle risposte del sidecar.
##
## Funzioni pure: entra un dizionario, esce BBCode. Il pannello decide quando
## mostrarli; cosa dicono si decide qui, e si puo' leggere in un posto solo.


static func _t(testo: String) -> String:
	return TranslationServer.translate(testo)


## Sotto il minuto i secondi bastano; sopra, "6:12" si legge a colpo d'occhio
## meglio di "372 s".
static func formatta(secondi: float) -> String:
	if secondi < 60.0:
		return "%.0fs" % secondi
	return "%d:%02d" % [int(secondi) / 60, int(secondi) % 60]


## Come il sidecar tradurra' i parametri, detto senza addolcirlo.
static func piano(p: Dictionary, durata_chiesta: float) -> String:
	var righe := [
		_t("Clip: [b]%d[/b] frame a %d fps → [b]%.2f s[/b]")
			% [int(p.get("lunghezza", 0)), int(p.get("fps", 0)), float(p.get("durata_effettiva_s", 0))],
		_t("Foglio: [b]%d x %d[/b], %d celle usate")
			% [int(p.get("colonne", 0)), int(p.get("righe", 0)), int(p.get("n_frame", 0))],
		_t("Riproduzione: [b]%.1f fps[/b]") % float(p.get("fps_riproduzione", 0)),
		_t("Formato: [b]%s[/b], generato a %d x %d px")
			% [str(p.get("formato", "1:1")), int(p.get("larghezza", 0)), int(p.get("altezza", 0))],
	]
	if int(p.get("celle_vuote", 0)) > 0:
		righe.append("[color=#e0a040]%s[/color]" % _t("%d celle resteranno vuote")
			% int(p["celle_vuote"]))
	if p.get("troncata", false):
		righe.append("[color=#e0a040]%s[/color]"
			% (_t("Durata ridotta a %.2f s: e' il massimo del modello.")
				% float(p.get("durata_effettiva_s", 0))))
	if abs(float(p.get("durata_effettiva_s", 0)) - durata_chiesta) > 0.15:
		righe.append("[color=#c6ccd8]%s[/color]" % _t(
			"La durata reale differisce da quella chiesta: il modello accetta solo certe lunghezze."))
	return "\n".join(righe)


## La riga mentre il lavoro gira. Due livelli: la fase della catena
## (inferenza, scontorno, gif) e, se c'e', cosa sta facendo ComfyUI dentro
## l'inferenza. La seconda arriva dal WebSocket e cambia ogni pochi decimi di
## secondo; senza, la riga diceva "inferenza..." per dieci minuti di fila.
static func in_corso(s: Dictionary, trascorso: float) -> String:
	var dettaglio := str(s.get("dettaglio", ""))
	var quanto := "%.0f%%" % (float(s.get("percentuale", 0)) * 100.0)
	# Quanto manca arriva dal sidecar solo dal primo passo di campionamento in
	# poi: prima il caricamento dei pesi va da secondi a minuti, e un numero
	# inventato sarebbe peggio di nessuno.
	var eta = s.get("eta_s", null)
	var resto := "" if eta == null or int(eta) <= 0 \
		else "  [color=#c6ccd8]%s[/color]" % (_t("~%s rimanenti") % formatta(float(eta)))
	if dettaglio != "":
		return "[color=#c6ccd8]%s[/color] [color=#ffffff]%s[/color] [color=#5ccf7e]%s[/color]%s" % [
			quanto, dettaglio, formatta(trascorso), resto]
	return "[color=#c6ccd8]%s %s...[/color] [color=#5ccf7e]%s[/color]%s" % [
		quanto, str(s.get("fase", "in corso")), formatta(trascorso), resto]


static func annullato(durata: float) -> String:
	return "[color=#c6ccd8]%s[/color] [color=#ffffff]%s[/color]" % [
		_t("Generazione annullata."), formatta(durata)]


## Esito di un lavoro riuscito: per un lotto, una cartella per azione.
static func fatto(s: Dictionary, durata: float) -> String:
	var sfondo := _t("Sfondo dei frame rimosso") if s.get("scontornato", true) \
		else _t("Sfondo dei frame conservato")
	var cartelle := str(s.get("cartella", ""))
	var risultati: Array = s.get("risultati", [])
	if risultati.size() > 1:
		sfondo += " · " + _t("%d azioni") % risultati.size()
		cartelle = "\n".join(risultati.map(func(x: Dictionary) -> String: return str(x.get("cartella", ""))))
	return "[color=#5ccf7e]%s[/color] [color=#ffffff]%s[/color] [color=#c6ccd8]· %s[/color]\n[color=#c6ccd8]%s[/color]" % [
		_t("Fatto."), formatta(durata), sfondo, cartelle]


## Tutto il contesto utile in un testo unico, incollabile dov'e' che serve:
## messaggio, traccia Python, parametri della richiesta.
static func rapporto_errore(s: Dictionary) -> String:
	var messaggio: String = str(s.get("errore", _t("errore sconosciuto")))
	var righe := [_t("Sprite Sheep — errore di generazione"),
		"quando: %s" % Time.get_datetime_string_from_system(),
		"", messaggio]
	var req: Dictionary = s.get("richiesta", {})
	if not req.is_empty():
		righe.append("")
		righe.append(_t("richiesta") + ":")
		for k in req:
			righe.append("  %s: %s" % [k, req[k]])
	var tb: String = str(s.get("traccia", ""))
	if tb != "":
		righe.append("")
		righe.append(tb)
	return "\n".join(righe)
