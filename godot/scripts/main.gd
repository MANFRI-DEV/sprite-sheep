extends Control
## Schermata principale: barra di stato in alto, input a sinistra, azione a
## destra. Motore e modelli stanno in una finestra a parte: si toccano una volta
## sola, non meritano spazio nel flusso di ogni giorno.

@onready var _sfondo: ColorRect = %Sfondo
# HFlowContainer, non HBoxContainer: le spie vanno a capo quando la finestra
# e' stretta. Il tipo va tenuto largo, altrimenti l'assegnazione fallisce e
# porta giu' tutto `_ready` con se'.
@onready var _spie_riga: Container = %SpieRiga
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
@onready var _btn_cronologia: Button = %CronologiaButton
@onready var _cronologia: Window = %FinestraCronologia
@onready var _btn_copia_diag: Button = %CopiaDiagButton
@onready var _lingua: OptionButton = %LinguaOption   # scelta_lingua.gd
@onready var _riga_collegamenti: Container = %CollegamentiRiga

const Predefiniti := preload("res://scripts/predefiniti.gd")
const SCENA_SPLASH := preload("res://scenes/splash.tscn")

var _splash: CanvasLayer = null

var sprite_scelto := ""
var prompt_testo := ""
var prompt_valido := false
var modello_attivo := ""
var motore_pronto := false
var durata_s := 2.0

var _spie: Spie
var _diagnostica := ""


func _ready() -> void:
	theme = Tema.costruisci()
	_sfondo.color = Tema.FONDO
	# Si passano le chiavi, non le stringhe tradotte: qui il locale e' ancora
	# quello di partenza (`_lingua.prepara()` gira piu' sotto) e una tr() fatta
	# adesso resterebbe congelata nella lingua sbagliata per tutta la sessione.
	_spie = Spie.new(_spie_riga)
	_spie.crea("motore", "Motore")
	_spie.crea("comfy", "ComfyUI")
	_spie.crea("modello", "Modello")
	_spie.crea("edizione", "Edizione")

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
	_cronologia.imposta(_sidecar)
	_cronologia.rigenerata.connect(_pann_genera.segui)
	_btn_cronologia.pressed.connect(_cronologia.apri)
	_prepara_collegamenti()
	get_viewport().size_changed.connect(_adatta)
	_adatta()
	_finestra.close_requested.connect(func() -> void: _finestra.hide())
	_btn_copia_diag.pressed.connect(func() -> void:
		DisplayServer.clipboard_set(_diagnostica)
		_btn_copia_diag.text = tr("Copiato negli appunti"))

	_lingua.lingua_cambiata.connect(_su_lingua)
	_lingua.prepara()
	_mostra_splash()
	_spie.imposta("motore", Tema.AVVISO, tr("avvio..."))
	_sidecar.avvia()


## Lo splash sta sopra la schermata gia' costruita, non al suo posto: il
## sidecar parte subito e i venti secondi di avvio scorrono dietro la pecora.
func _mostra_splash() -> void:
	_splash = SCENA_SPLASH.instantiate()
	add_child(_splash)


## Lingua cambiata: il sidecar scrive i suoi messaggi gia' tradotti, quindi va
## avvisato, e va riletto tutto cio' che contiene testo suo.
func _su_lingua(codice: String) -> void:
	if _sidecar != null:
		_sidecar.post_json("/lingua", {"lingua": codice})
	_spie.ritraduci()
	_pann_modelli.aggiorna()
	_pann_comfy.aggiorna()
	_pann_genera.rivaluta()


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
		_spie.imposta("modello", Tema.ERRORE, tr("nessuno installato"))
	else:
		_spie.imposta("modello", Tema.ACCENTO, id_modello)
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
		_spie.imposta("edizione", Tema.ACCENTO, str(ed.get("nome", "")))
		return
	var restanti := int(ed.get("restanti", 0))
	var colore: Color = Tema.ACCENTO
	if restanti == 0:
		colore = Tema.ERRORE
	elif restanti <= 1:
		colore = Tema.AVVISO
	_spie.imposta("edizione", colore, tr("%s · %d/%d generazioni")
		% [ed.get("nome", ""), restanti, int(limite)])


func _su_setup(pronto: bool) -> void:
	motore_pronto = pronto
	_spie.imposta("comfy", Tema.ACCENTO if pronto else Tema.AVVISO,
		tr("pronta") if pronto else tr("da configurare"))
	_pann_genera.rivaluta()


func _su_durata(secondi: float) -> void:
	durata_s = secondi
	_pann_prompt.imposta_durata(secondi)


## Tutto il necessario per generare e' presente?
## Due colonne su una finestra larga, una sola su una stretta.
##
## Sotto i 1040 punti le due colonne diventano larghe circa 500 ciascuna, e a
## quel punto il pannello dell'immagine, la tendina del colore e la riga della
## tolleranza cominciano a tagliarsi. Impilarle e' meglio che schiacciarle: si
## scorre di piu', ma si legge tutto.
##
## Il nodo `Corpo` e' un **BoxContainer**, non un HBoxContainer: su un
## HBoxContainer la proprieta' `vertical` non si scrive — Godot la tiene
## inchiodata a falso e l'assegnazione viene ingoiata senza errore. La prima
## versione faceva proprio cosi' e non impilava niente, sembrando una soglia
## sbagliata invece che una riga senza effetto.
##
## Cosi' non serve spostare nodi: cambiare padre a runtime vorrebbe dire
## ricostruire i pannelli e perdere quello che c'e' dentro.
const LARGHEZZA_DUE_COLONNE := 1040


func _adatta() -> void:
	var corpo := $Margine/Colonna/Corpo as BoxContainer
	if corpo == null:
		return
	var stretta := get_viewport_rect().size.x < LARGHEZZA_DUE_COLONNE
	if corpo.vertical == stretta:
		return
	corpo.vertical = stretta
	# Girare il contenitore non basta: i due scorrevoli espandono **nella
	# direzione sbagliata**. Un ScrollContainer ha dimensione minima zero, e in
	# colonna senza l'espansione verticale si schiaccia a niente: i pannelli
	# c'erano ancora ma alti zero pixel, cioe' una finestra vuota.
	for c in corpo.get_children():
		var s := c as Control
		if s == null:
			continue
		s.size_flags_horizontal = (Control.SIZE_FILL if stretta
			else Control.SIZE_EXPAND_FILL)
		s.size_flags_vertical = (Control.SIZE_EXPAND_FILL if stretta
			else Control.SIZE_FILL)


## I collegamenti esterni della testata: aggiornamenti, Discord, Instagram,
## donazioni. Chi decide quali sono e in che ordine e' `collegamenti.gd`, che
## tiene anche il nome del pulsante: qui si passa solo la riga che li contiene.
func _prepara_collegamenti() -> void:
	Collegamenti.prepara(_riga_collegamenti)


## Il colore di sfondo scelto nel pannello 1, che il pannello 5 deve mandare
## al sidecar insieme al resto: e' un dato dell'immagine, non della generazione.
func colore_sfondo() -> String:
	return _pann_immagine.colore_sfondo()


func pronto_per_generare() -> bool:
	return motore_pronto and sprite_scelto != "" and prompt_valido and modello_attivo != ""


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_sidecar.ferma()


func _su_pronto(info: Dictionary) -> void:
	if _splash != null:
		_splash.motore_pronto()
	# La lingua va rimandata adesso. `_lingua.prepara()` gira in _ready, quando
	# il sidecar non e' ancora avviato: quel primo POST /lingua non arriva a
	# nessuno, e il processo Python resta sul suo default italiano. E' il motivo
	# per cui, con l'interfaccia in inglese, i messaggi del motore restavano in
	# italiano.
	_sidecar.post_json("/lingua", {"lingua": TranslationServer.get_locale()})
	_pann_modelli.aggiorna()
	_pann_comfy.aggiorna()
	var motore: Array = Diagnostica.spia_motore(info.get("capacita", {}))
	_spie.imposta("motore", motore[0], motore[1])
	_su_edizione(info.get("edizione", {}))
	var righe: Array = Diagnostica.righe(info)
	_dettagli.text = "\n".join(righe)
	_diagnostica = Diagnostica.senza_tag("\n".join(righe))
	_btn_copia_diag.text = tr("Copia diagnostica")
	_carica_esempio()


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
	_spie.imposta("motore", Tema.ERRORE, tr("non disponibile"))
	_dettagli.text = "[color=#e06060]%s[/color]" % messaggio
	_diagnostica = messaggio
	_btn_copia_diag.text = tr("Copia diagnostica")
