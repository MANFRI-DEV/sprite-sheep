extends Control
## Schermata principale: barra di stato in alto, input a sinistra, azione a
## destra. Motore e modelli stanno in una finestra a parte: si toccano una volta
## sola, non meritano spazio nel flusso di ogni giorno.

@onready var _sfondo: ColorRect = %Sfondo
@onready var _spie_riga: HBoxContainer = %SpieRiga
@onready var _dettagli: RichTextLabel = %DettagliLabel
@onready var _sidecar: Node = %Sidecar
@onready var _pann_immagine: PanelContainer = %PannelloImmagine
@onready var _pann_prompt: PanelContainer = %PannelloPrompt
@onready var _pann_modelli: PanelContainer = %PannelloModelli
@onready var _pann_genera: PanelContainer = %PannelloGenera
@onready var _pann_risultato: PanelContainer = %PannelloRisultato
@onready var _pann_comfy: PanelContainer = %PannelloComfyUI
@onready var _finestra: Window = %FinestraImpostazioni
@onready var _btn_impostazioni: Button = %ImpostazioniButton
@onready var _btn_copia_diag: Button = %CopiaDiagButton
@onready var _lingua: OptionButton = %LinguaOption

const Predefiniti := preload("res://scripts/predefiniti.gd")
const SCENA_SPLASH := preload("res://scenes/splash.tscn")

var _splash: CanvasLayer = null

var sprite_scelto := ""
var prompt_testo := ""
var prompt_valido := false
var modello_attivo := ""
var motore_pronto := false
var durata_s := 2.0

var _spie := {}
var _diagnostica := ""


func _ready() -> void:
	theme = Tema.costruisci()
	_sfondo.color = Tema.FONDO
	# Si passano le chiavi, non le stringhe tradotte: qui il locale e' ancora
	# quello di partenza (`_prepara_lingue` gira piu' sotto) e una tr() fatta
	# adesso resterebbe congelata nella lingua sbagliata per tutta la sessione.
	_crea_spia("motore", "Motore")
	_crea_spia("comfy", "ComfyUI")
	_crea_spia("modello", "Modello")
	_crea_spia("edizione", "Edizione")

	_sidecar.sidecar_pronto.connect(_su_pronto)
	_sidecar.sidecar_errore.connect(_su_errore)
	_pann_immagine.imposta_sidecar(_sidecar)
	_pann_immagine.immagine_pronta.connect(_su_immagine)
	_pann_prompt.imposta_sidecar(_sidecar)
	_pann_prompt.imposta_durata(durata_s)
	_pann_prompt.prompt_cambiato.connect(_su_prompt)
	_pann_modelli.imposta_sidecar(_sidecar)
	_pann_modelli.modello_scelto.connect(_su_modello)
	_pann_genera.imposta(_sidecar, self)
	# la durata la comanda il pannello generazione, il prompt la subisce
	_pann_genera.durata_cambiata.connect(_su_durata)
	_pann_genera.tempi_clip.connect(_pann_prompt.imposta_tempi)
	_pann_genera.risultato_pronto.connect(_pann_risultato.mostra)
	_pann_genera.edizione_cambiata.connect(_su_edizione)
	_pann_genera.risultato_pulito.connect(_pann_risultato.pulisci)
	_pann_comfy.imposta_sidecar(_sidecar)
	_pann_comfy.setup_cambiato.connect(_su_setup)

	_btn_impostazioni.pressed.connect(_apri_impostazioni)
	_finestra.close_requested.connect(func() -> void: _finestra.hide())
	_btn_copia_diag.pressed.connect(func() -> void:
		DisplayServer.clipboard_set(_diagnostica)
		_btn_copia_diag.text = tr("Copiato negli appunti"))

	_prepara_lingue()
	_mostra_splash()
	_spia("motore", Tema.AVVISO, tr("avvio..."))
	_sidecar.avvia()


## Lo splash sta sopra la schermata gia' costruita, non al suo posto: il
## sidecar parte subito e i venti secondi di avvio scorrono dietro la pecora.
func _mostra_splash() -> void:
	_splash = SCENA_SPLASH.instantiate()
	add_child(_splash)


## Selettore di lingua. La scelta vale per l'interfaccia (TranslationServer) e
## per i messaggi del sidecar, che arrivano gia' scritti e quindi vanno
## tradotti alla fonte: per questo si avvisa anche il processo Python.
const LINGUE := [["it", "Italiano"], ["en", "Inglese"]]

func _prepara_lingue() -> void:
	var salvata := _lingua_salvata()
	for i in LINGUE.size():
		_lingua.add_item(tr(LINGUE[i][1]))
		_lingua.set_item_metadata(i, LINGUE[i][0])
		if LINGUE[i][0] == salvata:
			_lingua.selected = i
	_lingua.item_selected.connect(func(i: int) -> void:
		_applica_lingua(str(_lingua.get_item_metadata(i))))
	_applica_lingua(salvata)


func _lingua_salvata() -> String:
	if FileAccess.file_exists("user://lingua.cfg"):
		var f := FileAccess.open("user://lingua.cfg", FileAccess.READ)
		if f != null:
			var v: String = f.get_as_text().strip_edges()
			if v == "it" or v == "en":
				return v
	# prima apertura: si segue la lingua del sistema
	return "it" if OS.get_locale().begins_with("it") else "en"


func _applica_lingua(codice: String) -> void:
	TranslationServer.set_locale(codice)
	var f := FileAccess.open("user://lingua.cfg", FileAccess.WRITE)
	if f != null:
		f.store_string(codice)
	# le voci del selettore sono a loro volta tradotte
	for i in LINGUE.size():
		_lingua.set_item_text(i, tr(LINGUE[i][1]))
	if _sidecar != null:
		_sidecar.post_json("/lingua", {"lingua": codice})
	_ridisegna_tutto()


## Rilegge dal sidecar tutto cio' che contiene testo tradotto.
func _ridisegna_tutto() -> void:
	if not _spie.is_empty():
		_ritraduci_spie()
	_pann_modelli.aggiorna()
	_pann_comfy.aggiorna()
	_pann_genera.rivaluta()


## Pallino + etichetta nella barra in alto. Piu' compatto di un pannello e
## sempre visibile: il modello attivo, in particolare, prima non si vedeva.
func _crea_spia(chiave: String, titolo_chiave: String) -> void:
	var riga := HBoxContainer.new()
	riga.add_theme_constant_override("separation", 6)
	var punto := ColorRect.new()
	punto.custom_minimum_size = Vector2(8, 8)
	punto.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	punto.color = Tema.SPENTO
	riga.add_child(punto)
	var testo := Label.new()
	testo.text = tr(titolo_chiave)
	testo.add_theme_font_size_override("font_size", 12)
	testo.add_theme_color_override("font_color", Tema.TENUE)
	riga.add_child(testo)
	_spie_riga.add_child(riga)
	# Si conserva anche l'ultimo dettaglio: al cambio di lingua la spia va
	# riscritta per intero, e il dettaglio non sempre si puo' richiedere di nuovo.
	_spie[chiave] = {"punto": punto, "testo": testo,
		"titolo_chiave": titolo_chiave, "dettaglio": ""}


func _spia(chiave: String, colore: Color, dettaglio: String) -> void:
	var s: Dictionary = _spie[chiave]
	s["punto"].color = colore
	s["dettaglio"] = dettaglio
	s["testo"].text = "%s: %s" % [tr(s["titolo_chiave"]), dettaglio]


## Riscrive le spie nella lingua corrente, conservando stato e colore.
func _ritraduci_spie() -> void:
	for chiave in _spie:
		var s: Dictionary = _spie[chiave]
		s["testo"].text = "%s: %s" % [tr(s["titolo_chiave"]), s["dettaglio"]]


func _apri_impostazioni() -> void:
	_finestra.popup_centered(Vector2i(560, 720))
	_pann_modelli.aggiorna()
	_pann_comfy.aggiorna()


func _su_immagine(percorso: String, _info: Dictionary) -> void:
	sprite_scelto = percorso
	_pann_genera.rivaluta()


func _su_prompt(testo: String, valido: bool) -> void:
	prompt_testo = testo
	prompt_valido = valido
	_pann_genera.rivaluta()


func _su_modello(id_modello: String, _installato: bool) -> void:
	modello_attivo = id_modello
	_pann_prompt.imposta_modello(id_modello)
	if id_modello == "":
		_spia("modello", Tema.ERRORE, tr("nessuno installato"))
	else:
		_spia("modello", Tema.ACCENTO, id_modello)
	_pann_genera.rivaluta()


## Versione, e quota residua se un domani ne esistesse una. Oggi il sidecar
## risponde sempre `limite: null`, quindi si mostra solo il nome della versione;
## il ramo della quota resta perche' rimetterla sarebbe un cambio nel sidecar,
## non nell'interfaccia.
func _su_edizione(ed: Dictionary) -> void:
	if ed.is_empty():
		return
	var limite = ed.get("limite", null)
	if limite == null:
		_spia("edizione", Tema.ACCENTO, str(ed.get("nome", "")))
		return
	var restanti := int(ed.get("restanti", 0))
	var colore: Color = Tema.ACCENTO
	if restanti == 0:
		colore = Tema.ERRORE
	elif restanti <= 1:
		colore = Tema.AVVISO
	_spia("edizione", colore, tr("%s · %d/%d generazioni")
		% [ed.get("nome", ""), restanti, int(limite)])


func _su_setup(pronto: bool) -> void:
	motore_pronto = pronto
	_spia("comfy", Tema.ACCENTO if pronto else Tema.AVVISO,
		tr("pronta") if pronto else tr("da configurare"))
	_pann_genera.rivaluta()


func _su_durata(secondi: float) -> void:
	durata_s = secondi
	_pann_prompt.imposta_durata(secondi)


## Tutto il necessario per generare e' presente?
func pronto_per_generare() -> bool:
	return motore_pronto and sprite_scelto != "" and prompt_valido and modello_attivo != ""


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_sidecar.ferma()


func _su_pronto(info: Dictionary) -> void:
	if _splash != null:
		_splash.motore_pronto()
	# La lingua va rimandata adesso. `_prepara_lingue()` gira in _ready, quando
	# il sidecar non e' ancora avviato: quel primo POST /lingua non arriva a
	# nessuno, e il processo Python resta sul suo default italiano. E' il motivo
	# per cui, con l'interfaccia in inglese, i messaggi del motore restavano in
	# italiano.
	_sidecar.post_json("/lingua", {"lingua": TranslationServer.get_locale()})
	_pann_modelli.aggiorna()
	_pann_comfy.aggiorna()
	var cap: Dictionary = info.get("capacita", {})
	_aggiorna_spia_motore(cap)

	var righe := [
		"[b]%s[/b] v%s" % [info.get("app", "?"), info.get("version", "?")],
		"Python %s" % info.get("python", "?"),
	]
	# torch nel sidecar non c'e' e non serve: dirlo evita che "torch assente"
	# venga letto come un pezzo mancante.
	if cap.get("torch", null) == null:
		righe.append(tr("Calcolo su GPU: a carico di ComfyUI"))
	else:
		righe.append("torch %s" % str(cap.get("torch")))

	if cap.get("cuda", false):
		righe.append(tr("GPU: %s ([b]%d MB[/b])")
			% [cap.get("gpu", "?"), int(cap.get("vram_mb", 0))])
	elif cap.get("comfyui_spenta", false):
		righe.append("[color=#e0a840]%s[/color]"
			% tr("GPU non ancora nota: avvia ComfyUI"))
	else:
		righe.append("[color=#e0a840]%s[/color]" % tr("Nessuna GPU CUDA"))

	_su_edizione(info.get("edizione", {}))
	righe.append("%s %s" % [tr("Modelli:"), info.get("models_dir", "?")])
	var ed: Dictionary = info.get("edizione", {})
	righe.append("%s %s" % [tr("Edizione:"), ed.get("nome", "?")])
	_dettagli.text = "\n".join(righe)
	_diagnostica = _senza_tag("\n".join(righe))
	_btn_copia_diag.text = tr("Copia diagnostica")
	_carica_esempio()


## Tre casi distinti, e nessuno dei tre e' un guasto da solo: GPU nota, GPU
## ancora ignota perche' ComfyUI e' spenta, oppure nessuna GPU. Confonderli
## faceva apparire "nessuna GPU CUDA" a chi ne aveva una che lavorava.
func _aggiorna_spia_motore(cap: Dictionary) -> void:
	if cap.get("cuda", false):
		var nome: String = str(cap.get("gpu", "pronto"))
		var mb := int(cap.get("vram_mb", 0))
		_spia("motore", Tema.ACCENTO,
			"%s (%d MB)" % [nome, mb] if mb > 0 else nome)
	elif cap.get("comfyui_spenta", false):
		_spia("motore", Tema.AVVISO, tr("GPU ignota: ComfyUI spenta"))
	else:
		# Qui la GPU manca davvero: su CPU una generazione video e' di fatto
		# impraticabile, e va detto subito.
		_spia("motore", Tema.ERRORE, tr("Nessuna GPU CUDA"))


## Il testo per gli appunti non deve portarsi dietro il markup: prima toglieva
## solo [b] e [/b], e negli appunti finivano [color=#e0a840] e simili.
func _senza_tag(testo: String) -> String:
	var rx := RegEx.new()
	rx.compile("\\[/?[a-zA-Z]+[^\\]]*\\]")
	return rx.sub(testo, "", true)


## Sprite e prompt di esempio, una volta sola. Serve il sidecar vivo: il prompt
## lo compone lui, e l'immagine la analizza lui.
func _carica_esempio() -> void:
	if not Predefiniti.e_prima_apertura():
		return
	Predefiniti.segna_aperto()
	var sprite := Predefiniti.estrai_sprite()
	if sprite != "":
		_pann_immagine.carica_predefinito(sprite)
	_pann_prompt.precompila(Predefiniti.CAMPI)


func _su_errore(messaggio: String) -> void:
	if _splash != null:
		_splash.motore_in_errore(messaggio)
	_spia("motore", Tema.ERRORE, tr("non disponibile"))
	_dettagli.text = "[color=#e06060]%s[/color]" % messaggio
	_diagnostica = messaggio
	_btn_copia_diag.text = tr("Copia diagnostica")
