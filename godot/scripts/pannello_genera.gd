extends PanelContainer
## Requisiti 5 e 6: parametri, avvio della generazione, salvataggio.
##
## Durata e numero di frame sono scelti dall'utente; la lunghezza reale della
## clip la decide il modello (H3 accetta solo 17k+5, i Wan 4n+1), quindi il
## piano viene ricalcolato dal sidecar a ogni modifica e mostrato com'e'.

signal durata_cambiata(secondi: float)
## Tempi reali della clip, noti solo dopo aver interrogato il piano
signal tempi_clip(effettiva: float, fine_utile: float)
## Lavoro finito bene: porta lo stato completo al pannello Risultato
signal risultato_pronto(stato: Dictionary)
## Nuova generazione avviata: il risultato precedente non vale piu'
signal risultato_pulito
## Quota dell'edizione aggiornata (consumata o rifiutata)
signal edizione_cambiata(stato: Dictionary)

@onready var _durata: HSlider = %DurataSlider
@onready var _durata_lbl: Label = %DurataLabel
@onready var _frame: SpinBox = %FrameSpin
@onready var _piano_lbl: RichTextLabel = %PianoLabel
@onready var _btn: Button = %GeneraButton
@onready var _barra: ProgressBar = %Barra
@onready var _esito: RichTextLabel = %EsitoLabel
@onready var _nome: LineEdit = %NomeEdit
@onready var _traccia: TextEdit = %TracciaEdit
@onready var _scontorna: CheckBox = %ScontornaCheck
@onready var _scontorna_nota: Label = %ScontornaNota
@onready var _riga_errore: HBoxContainer = %RigaErrore
@onready var _btn_copia: Button = %CopiaErroreButton
@onready var _btn_traccia: Button = %TracciaButton

var _sidecar: Node
var _principale: Control
var _job := ""
var _timer: Timer
## Testo completo dell'ultimo errore, quello che finisce negli appunti.
var _rapporto := ""

## Cronometro della generazione. Serve a due cose: sapere quanto manca mentre
## si aspetta, e sapere quanto e' costata dopo. Su questa macchina si va dai
## tre minuti e mezzo di WAN ai dieci di H3, e la differenza va vista.
var _inizio_ms := 0
var _durata_ultima := 0.0


func imposta(sidecar: Node, principale: Control) -> void:
	_sidecar = sidecar
	_principale = principale


func _ready() -> void:
	_durata.value_changed.connect(_su_durata)
	_frame.value_changed.connect(func(_v: float) -> void: _ricalcola())
	_btn.pressed.connect(_genera)
	Tema.accenta(_btn)
	_btn_copia.pressed.connect(_copia_errore)
	_btn_traccia.pressed.connect(func() -> void:
		_traccia.visible = not _traccia.visible
		_btn_traccia.text = tr("Nascondi traccia") if _traccia.visible else tr("Mostra traccia"))

	_scontorna.button_pressed = _scontorno_ricordato()
	_scontorna.toggled.connect(_su_scontorno)
	_su_scontorno(_scontorna.button_pressed)

	_timer = Timer.new()
	_timer.wait_time = 0.8
	_timer.timeout.connect(_controlla_job)
	add_child(_timer)
	_su_durata(_durata.value)


## La scelta si ricorda: chi lavora a sprite per un gioco vuole sempre lo
## sfondo via, chi guarda il video generato vuole sempre tenerlo. Riproporre
## ogni volta il default significa che uno dei due lo cambia a ogni avvio.
const MEMORIA_SCONTORNO := "user://scontorno.cfg"


func _scontorno_ricordato() -> bool:
	if not FileAccess.file_exists(MEMORIA_SCONTORNO):
		return true
	var f := FileAccess.open(MEMORIA_SCONTORNO, FileAccess.READ)
	return true if f == null else f.get_as_text().strip_edges() != "0"


func _su_scontorno(attivo: bool) -> void:
	var f := FileAccess.open(MEMORIA_SCONTORNO, FileAccess.WRITE)
	if f != null:
		f.store_string("1" if attivo else "0")
	_scontorna_nota.text = "" if attivo else tr(
		"Senza, lo sprite sheet esce con lo sfondo pieno del prompt.")


func _su_durata(v: float) -> void:
	_durata_lbl.text = "%.1f s" % v
	durata_cambiata.emit(v)
	_ricalcola()


## Chiede al sidecar come tradurra' i parametri, e lo mostra senza addolcirlo.
func _ricalcola() -> void:
	if _sidecar == null or _principale == null:
		return
	var modello: String = _principale.modello_attivo
	if modello == "":
		_piano_lbl.text = "[color=#8a93a3]%s[/color]" % tr("Scegli un modello installato.")
		_aggiorna_bottone()
		return

	var r: Dictionary = await _sidecar.post_json("/piano", {
		"modello": modello,
		"durata_s": _durata.value,
		"n_frame": int(_frame.value),
	})
	if not r.get("ok", false):
		_piano_lbl.text = "[color=#e06060]%s[/color]" % r.get("errore", "")
		return

	var p: Dictionary = r.get("piano", {})
	tempi_clip.emit(float(p.get("durata_effettiva_s", _durata.value)),
		float(p.get("fine_utile_s", _durata.value * 0.85)))
	var righe := [
		tr("Clip: [b]%d[/b] frame a %d fps → [b]%.2f s[/b]")
			% [int(p.get("lunghezza", 0)), int(p.get("fps", 0)), float(p.get("durata_effettiva_s", 0))],
		tr("Foglio: [b]%d x %d[/b], %d celle usate")
			% [int(p.get("colonne", 0)), int(p.get("righe", 0)), int(p.get("n_frame", 0))],
		tr("Riproduzione: [b]%.1f fps[/b]") % float(p.get("fps_riproduzione", 0)),
	]
	if int(p.get("celle_vuote", 0)) > 0:
		righe.append("[color=#e0a040]%s[/color]" % tr("%d celle resteranno vuote")
			% int(p["celle_vuote"]))
	if p.get("troncata", false):
		righe.append("[color=#e0a040]%s[/color]"
			% (tr("Durata ridotta a %.2f s: e' il massimo del modello.")
				% float(p.get("durata_effettiva_s", 0))))
	if abs(float(p.get("durata_effettiva_s", 0)) - _durata.value) > 0.15:
		righe.append("[color=#8a93a3]%s[/color]" % tr(
			"La durata reale differisce da quella chiesta: il modello accetta solo certe lunghezze."))

	_piano_lbl.text = "\n".join(righe)
	_aggiorna_bottone()


func _aggiorna_bottone() -> void:
	if _principale == null:
		return
	var pronto: bool = _principale.pronto_per_generare() and _job == ""
	_btn.disabled = not pronto
	if _job != "":
		_btn.text = tr("Generazione in corso...")
	elif pronto:
		_btn.text = tr("Genera sprite sheet e GIF")
	else:
		_btn.text = tr("Servono sprite, prompt valido e modello")


func _genera() -> void:
	if _sidecar == null or _principale == null:
		return
	_esito.text = ""
	_barra.value = 0
	_nascondi_errore()
	risultato_pulito.emit()
	var r: Dictionary = await _sidecar.post_json("/genera", {
		"modello": _principale.modello_attivo,
		"sprite": _principale.sprite_scelto,
		"prompt": _principale.prompt_testo,
		"nome": _nome.text.strip_edges() if _nome.text.strip_edges() != "" else "animazione",
		"durata_s": _durata.value,
		"n_frame": int(_frame.value),
		"scontorna": _scontorna.button_pressed,
	})
	if r.has("edizione"):
		edizione_cambiata.emit(r["edizione"])
	if not r.get("ok", false):
		_mostra_errore({"errore": r.get("errore", tr("avvio fallito"))})
		return
	_job = str(r.get("job", ""))
	_inizio_ms = Time.get_ticks_msec()
	_aggiorna_bottone()
	_timer.start()


func _controlla_job() -> void:
	if _job == "" or _sidecar == null:
		return
	var r: Dictionary = await _sidecar.get_json("/genera?job=%s" % _job)
	var s: Dictionary = r.get("stato", {})
	_barra.value = float(s.get("percentuale", 0)) * 100.0

	if s.get("attivo", true):
		_esito.text = "[color=#8a93a3]%s...[/color] [color=#5ccf7e]%s[/color]" % [
			str(s.get("fase", "in corso")), _cronometro()]
		return

	_timer.stop()
	_durata_ultima = _trascorso_s()
	_job = ""
	_aggiorna_bottone()

	if s.get("errore", null) != null:
		_mostra_errore(s)
		return

	var sfondo := tr("Sfondo dei frame rimosso") if s.get("scontornato", true) \
		else tr("Sfondo dei frame conservato")
	_esito.text = "[color=#5ccf7e]%s[/color] [color=#e2e6ee]%s[/color] [color=#8a93a3]· %s[/color]\n[color=#7f8798]%s[/color]" % [
		tr("Fatto."), _formatta(_durata_ultima), sfondo, str(s.get("cartella", ""))]
	if s.has("edizione"):
		edizione_cambiata.emit(s["edizione"])
	risultato_pronto.emit(s)


func _trascorso_s() -> float:
	return 0.0 if _inizio_ms == 0 else (Time.get_ticks_msec() - _inizio_ms) / 1000.0


func _cronometro() -> String:
	return _formatta(_trascorso_s())


## Sotto il minuto i secondi bastano; sopra, "6:12" si legge a colpo d'occhio
## meglio di "372 s".
func _formatta(secondi: float) -> String:
	if secondi < 60.0:
		return "%.0fs" % secondi
	return "%d:%02d" % [int(secondi) / 60, int(secondi) % 60]


## Quanto e' durata l'ultima generazione, per chi la vuole altrove.
func durata_ultima_s() -> float:
	return _durata_ultima


## Raccoglie tutto il contesto utile in un testo unico, incollabile dov'e' che
## serve: messaggio, traccia Python, parametri della richiesta, versione.
func _mostra_errore(s: Dictionary) -> void:
	var messaggio: String = str(s.get("errore", tr("errore sconosciuto")))
	_esito.text = "[color=#e06060]%s[/color]" % messaggio

	var righe := [tr("Sprite Sheep — errore di generazione"),
		"quando: %s" % Time.get_datetime_string_from_system(),
		"", messaggio]
	var req: Dictionary = s.get("richiesta", {})
	if not req.is_empty():
		righe.append("")
		righe.append(tr("richiesta") + ":")
		for k in req:
			righe.append("  %s: %s" % [k, req[k]])
	var tb: String = str(s.get("traccia", ""))
	if tb != "":
		righe.append("")
		righe.append(tb)
	_rapporto = "\n".join(righe)

	_traccia.text = _rapporto
	_traccia.visible = false
	_btn_traccia.text = tr("Mostra traccia")
	_btn_traccia.visible = tb != ""
	_riga_errore.visible = true
	_btn_copia.text = tr("Copia errore")


func _nascondi_errore() -> void:
	_riga_errore.visible = false
	_traccia.visible = false
	_rapporto = ""


func _copia_errore() -> void:
	if _rapporto == "":
		return
	DisplayServer.clipboard_set(_rapporto)
	_btn_copia.text = tr("Copiato negli appunti")


## Chiamato dalla schermata quando cambia qualcosa altrove (sprite, prompt, modello)
func rivaluta() -> void:
	_ricalcola()
