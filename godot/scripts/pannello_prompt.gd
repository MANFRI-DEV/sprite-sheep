extends PanelContainer
## Il prompt: un pulsante che apre la creazione guidata, e il testo che ne esce.
##
## Fino alla 0.0.4 c'era un grafo a blocchi collegabili. Mostrava bene **quali**
## parti compongono un prompt, ma chiedeva di capirle tutte insieme prima di
## scriverne una: sei nodi, i fili, nessun ordine suggerito. Il wizard fa le
## stesse domande una per volta, nell'ordine in cui conviene pensarle.
##
## Quello che il sidecar riceve non e' cambiato: `WizardPrompt.campi()`
## restituisce le stesse chiavi del grafo, e `/prompt` non e' stato toccato.
##
## Il testo composto resta modificabile a mano. Da quel momento comanda
## l'utente: `_modificato_a_mano` blocca la ricomposizione automatica, perche'
## sovrascrivere un prompt scritto a mano e' il modo piu' rapido di far
## perdere lavoro a qualcuno.

signal prompt_cambiato(testo: String, valido: bool)

@onready var _testo: TextEdit = %TestoEdit
@onready var _spia: ColorRect = %Spia
@onready var _esito: RichTextLabel = %EsitoLabel
@onready var _btn_wizard: Button = %WizardButton
@onready var _nota_modello: Label = %NotaModello

const COLORI := {
	"verde": Color(0.28, 0.75, 0.4),
	"giallo": Color(0.9, 0.7, 0.25),
	"rosso": Color(0.85, 0.3, 0.3),
}

var _sidecar: Node
var _wizard: WizardPrompt
var _durata_s := 2.0
## Durata reale della clip: il modello accetta solo certe lunghezze, quindi
## e' quasi sempre maggiore di quella chiesta.
var _durata_effettiva := 2.0
## Istante oltre il quale i frame vengono scartati: i passi devono chiudere qui.
var _fine_utile := 1.7
var _modello := ""
var _modificato_a_mano := false
var _in_validazione := false


func _ready() -> void:
	_wizard = WizardPrompt.new()
	add_child(_wizard)
	_wizard.hide()
	_wizard.completato.connect(_su_wizard)

	_btn_wizard.pressed.connect(_apri_wizard)
	Tema.accenta(_btn_wizard)
	_testo.text_changed.connect(func() -> void:
		_modificato_a_mano = true
		_valida())
	_imposta_spia("rosso", tr("Apri il wizard e componi il prompt."))


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo
	_aggiorna_wizard()


func imposta_durata(secondi: float) -> void:
	_durata_s = secondi
	_durata_effettiva = max(_durata_effettiva, secondi)
	_fine_utile = min(_fine_utile, _durata_effettiva * 0.85)
	_aggiorna_wizard()
	_valida()


## La chiama il pannello Generazione quando conosce la lunghezza reale.
func imposta_tempi(effettiva: float, fine_utile: float) -> void:
	_durata_effettiva = effettiva
	_fine_utile = fine_utile
	_aggiorna_wizard()
	_valida()


## La chiama la schermata quando cambia il modello attivo.
func imposta_modello(id_modello: String) -> void:
	if id_modello == _modello:
		return
	_modello = id_modello
	_aggiorna_wizard()
	_aggiorna_nota_dialetto()
	# Il testo composto e' nel dialetto del modello precedente: va rifatto, a
	# meno che l'utente l'abbia scritto lui.
	if not _modificato_a_mano and _testo.text.strip_edges() != "":
		_ricomponi()
	else:
		_valida()


func _aggiorna_wizard() -> void:
	if _wizard != null:
		_wizard.imposta(_sidecar, _modello, _durata_s, _fine_utile)


func _aggiorna_nota_dialetto() -> void:
	if _modello.begins_with("wan"):
		_nota_modello.text = tr("WAN: prosa unica, la sequenza va a parole (first, then, finally).")
	elif _modello == "":
		_nota_modello.text = ""
	else:
		_nota_modello.text = tr("MiniMax H3: blocchi con intestazioni e marcatori [0s-1s].")


func _apri_wizard() -> void:
	_aggiorna_wizard()
	_wizard.apri()


func _su_wizard(_campi: Dictionary) -> void:
	_modificato_a_mano = false
	_ricomponi()


## Riempie il wizard con l'esempio e compone subito il testo.
##
## Si compone invece di incollare un prompt pronto perche' il dialetto dipende
## dal modello attivo: lo stesso esempio va scritto in un modo per H3 e in un
## altro per WAN, e a saperlo e' il sidecar.
func precompila(d: Dictionary) -> void:
	if _wizard == null or not _wizard.vuoto():
		return
	_wizard.precompila(d)
	_ricomponi()


func _ricomponi() -> void:
	if _sidecar == null or _wizard == null:
		return
	var r: Dictionary = await _sidecar.post_json("/prompt", {
		"campi": _wizard.campi(), "durata_s": _durata_effettiva,
		"modello": _modello})
	if not r.get("ok", false):
		_imposta_spia("rosso", r.get("errore", tr("composizione fallita")))
		return
	_modificato_a_mano = false
	_testo.text = str(r.get("testo", ""))
	_mostra(r.get("validazione", {}))


func _valida() -> void:
	if _sidecar == null or _in_validazione or _wizard == null:
		return
	_in_validazione = true
	var corpo := {"durata_s": _durata_effettiva, "modello": _modello}
	if _modificato_a_mano:
		corpo["testo"] = _testo.text
	else:
		corpo["campi"] = _wizard.campi()
	var r: Dictionary = await _sidecar.post_json("/prompt", corpo)
	_in_validazione = false
	if r.get("ok", false):
		_mostra(r.get("validazione", {}))


func _mostra(v: Dictionary) -> void:
	var righe := []
	for p in v.get("problemi", []):
		righe.append("[color=#e06060]• %s[/color]" % p)
	for a in v.get("avvisi", []):
		righe.append("[color=#e0a040]• %s[/color]" % a)
	if righe.is_empty():
		righe.append("[color=#5cc76e]Prompt valido: %d passi, chiude a %.1fs.[/color]"
			% [int(v.get("n_beat", 0)), float(v.get("fine_beat_s", 0))])
	_imposta_spia(str(v.get("semaforo", "rosso")), "\n".join(righe))
	prompt_cambiato.emit(_testo.text, bool(v.get("generabile", false)))


func _imposta_spia(semaforo: String, messaggio: String) -> void:
	_spia.color = COLORI.get(semaforo, COLORI["rosso"])
	_esito.text = messaggio


func testo_prompt() -> String:
	return _testo.text
