extends PanelContainer
## Prompt a blocchi collegabili, con semaforo di validazione.
##
## Fino alla 0.9 era una colonna di campi impilati. Il testo che ne usciva era
## lo stesso, ma la struttura del prompt — che e' fatto di parti distinte, e in
## cui **quali** parti includere conta quanto cosa ci si scrive — non si vedeva.
## Ora ogni parte e' un blocco e i fili dicono cosa entra nel prompt.
##
## Quello che il sidecar riceve non e' cambiato: `GrafoPrompt.campi()`
## restituisce le stesse chiavi di prima. Cambiare interfaccia e servizio
## insieme avrebbe reso impossibile capire quale dei due ha rotto il prompt.

signal prompt_cambiato(testo: String, valido: bool)

@onready var _grafo: GrafoPrompt = %Grafo
@onready var _testo: TextEdit = %TestoEdit
@onready var _spia: ColorRect = %Spia
@onready var _esito: RichTextLabel = %EsitoLabel
@onready var _btn_componi: Button = %ComponiButton
@onready var _nota_modello: Label = %NotaModello

const COLORI := {
	"verde": Color(0.28, 0.75, 0.4),
	"giallo": Color(0.9, 0.7, 0.25),
	"rosso": Color(0.85, 0.3, 0.3),
}

var _sidecar: Node
var _durata_s := 2.0
## Durata reale della clip: il modello accetta solo certe lunghezze, quindi
## e' quasi sempre maggiore di quella chiesta.
var _durata_effettiva := 2.0
## Istante oltre il quale i frame vengono scartati: i beat devono chiudere qui.
var _fine_utile := 1.7
var _modello := ""
var _modificato_a_mano := false
var _in_validazione := false


func _ready() -> void:
	_grafo.modificato.connect(_valida)
	_btn_componi.pressed.connect(_componi)
	# Se l'utente tocca il testo composto, da li' in poi comanda lui.
	_testo.text_changed.connect(func() -> void:
		_modificato_a_mano = true
		_valida())
	_grafo.imposta_tempi(_durata_s, _fine_utile)
	_imposta_spia("rosso", tr("Compila i blocchi e premi Componi."))


func imposta_sidecar(nodo: Node) -> void:
	_sidecar = nodo


func imposta_durata(secondi: float) -> void:
	_durata_s = secondi
	_durata_effettiva = max(_durata_effettiva, secondi)
	_fine_utile = min(_fine_utile, _durata_effettiva * 0.85)
	_grafo.imposta_tempi(_durata_s, _fine_utile)
	_valida()


## La chiama il pannello Generazione quando conosce la lunghezza reale.
func imposta_tempi(effettiva: float, fine_utile: float) -> void:
	_durata_effettiva = effettiva
	_fine_utile = fine_utile
	_grafo.imposta_tempi(_durata_s, _fine_utile)
	_valida()


## La chiama la schermata quando cambia il modello attivo.
func imposta_modello(id_modello: String) -> void:
	if id_modello == _modello:
		return
	_modello = id_modello
	_aggiorna_nota_dialetto()
	# Il testo composto e' nel dialetto del modello precedente: va rifatto, a
	# meno che l'utente l'abbia scritto lui.
	if not _modificato_a_mano and _testo.text.strip_edges() != "":
		_componi()
	else:
		_valida()


func _aggiorna_nota_dialetto() -> void:
	if _modello.begins_with("wan"):
		_nota_modello.text = tr("WAN: prosa unica, la sequenza va a parole (first, then, finally).")
	elif _modello == "":
		_nota_modello.text = ""
	else:
		_nota_modello.text = tr("MiniMax H3: blocchi con intestazioni e marcatori [0s-1s].")


## Riempie i blocchi con l'esempio e compone subito il testo.
##
## Si compone invece di incollare un prompt pronto perche' il dialetto dipende
## dal modello attivo: lo stesso esempio va scritto in un modo per H3 e in un
## altro per WAN, e a saperlo e' il sidecar.
func precompila(d: Dictionary) -> void:
	if not _grafo.vuoto():
		return
	_grafo.precompila(d)
	_componi()


func _componi() -> void:
	if _sidecar == null:
		return
	var r: Dictionary = await _sidecar.post_json("/prompt", {
		"campi": _grafo.campi(), "durata_s": _durata_effettiva,
		"modello": _modello})
	if not r.get("ok", false):
		_imposta_spia("rosso", r.get("errore", tr("composizione fallita")))
		return
	_modificato_a_mano = false
	_testo.text = str(r.get("testo", ""))
	_mostra(r.get("validazione", {}))


func _valida() -> void:
	if _sidecar == null or _in_validazione:
		return
	_in_validazione = true
	var corpo := {"durata_s": _durata_effettiva, "modello": _modello}
	if _modificato_a_mano:
		corpo["testo"] = _testo.text
	else:
		corpo["campi"] = _grafo.campi()
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
		righe.append("[color=#5cc76e]Prompt valido: %d beat, chiude a %.1fs.[/color]"
			% [int(v.get("n_beat", 0)), float(v.get("fine_beat_s", 0))])
	_imposta_spia(str(v.get("semaforo", "rosso")), "\n".join(righe))
	prompt_cambiato.emit(_testo.text, bool(v.get("generabile", false)))


func _imposta_spia(semaforo: String, messaggio: String) -> void:
	_spia.color = COLORI.get(semaforo, COLORI["rosso"])
	_esito.text = messaggio


func testo_prompt() -> String:
	return _testo.text
