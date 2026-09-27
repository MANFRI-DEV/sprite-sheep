extends CanvasLayer
## Schermata di apertura: logo, nome, edizione, collegamenti e il tasto Avvia.
##
## Non e' solo decorazione. L'avvio del sidecar richiede una ventina di secondi
## (Python parte, importa, apre la porta) e senza niente davanti il programma
## sembra bloccato. Lo splash copre quell'attesa.
##
## **Da 0.0.4 non si toglie da solo.** Prima spariva appena il motore
## rispondeva, e un utente che si era alzato a prendere un caffe' tornava
## trovando una schermata che non aveva visto partire. Ora c'e' un tasto, e la
## sala d'attesa la si lascia quando si vuole. E' anche l'unico posto in cui i
## collegamenti si leggono con calma: nella schermata vera stanno in un angolo
## della testata, qui sono davanti.
##
## Il tasto resta spento finche' il motore non e' pronto. Accenderlo subito
## vorrebbe dire far entrare qualcuno in un programma che non puo' ancora
## generare niente, e la prima cosa che vedrebbe e' un pulsante Genera grigio
## senza sapere perche'.
##
## Se il motore **non** parte, il tasto si accende lo stesso dopo `DURATA_MAX`,
## con un'altra scritta: restare bloccati qui sarebbe peggio: sotto c'e' la
## barra di stato, che l'errore lo racconta per intero e permette di copiarlo.

signal finito

## Oltre questo tempo si entra comunque, anche se il motore tace.
const DURATA_MAX := 25.0

@onready var _pecora: TextureRect = %Pecora
@onready var _titolo: Label = %Titolo
@onready var _edizione: Label = %Edizione
@onready var _stato: Label = %Stato
@onready var _avvia: Button = %AvviaButton
@onready var _riga_collegamenti: Container = %CollegamentiRiga

var _pronto := false
var _trascorso := 0.0
var _uscendo := false


func _ready() -> void:
	_titolo.text = "SPRITE SHEEP"
	# Dalle impostazioni del progetto, non scritta qui: era una stringa a mano
	# e a ogni versione restava indietro, annunciando quella precedente.
	# La schermata d'avvio e' proprio il posto in cui una versione sbagliata
	# non si nota, perche' dura due secondi e nessuno la rilegge.
	_edizione.text = str(ProjectSettings.get_setting(
		"application/config/version", "")).to_upper()
	_stato.text = tr("avvio del motore...")
	_pecora.modulate.a = 0.0

	_avvia.text = tr("Attendi, avvio del motore...")
	_avvia.disabled = true
	_avvia.pressed.connect(_esci)
	Tema.accenta(_avvia)
	_prepara_collegamenti()
	_anima_entrata()


## Gli stessi della testata, dalla stessa tabella: qui sono piu' grandi e si
## leggono con calma, mentre nella schermata vera stanno in un angolo.
func _prepara_collegamenti() -> void:
	Collegamenti.prepara(_riga_collegamenti)


func _anima_entrata() -> void:
	var t := create_tween().set_parallel()
	t.tween_property(_pecora, "modulate:a", 1.0, 0.5)
	# La pecora scende di poco: un movimento breve legge come "arrivo",
	# uno lungo come attesa, e di attesa ce n'e' gia' abbastanza.
	_pecora.position.y -= 18
	t.tween_property(_pecora, "position:y", _pecora.position.y + 18, 0.6) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


func _process(delta: float) -> void:
	if _pronto:
		set_process(false)
		return
	_trascorso += delta
	if _trascorso >= DURATA_MAX:
		set_process(false)
		_sblocca(tr("Entra comunque"))
		_stato.text = tr("il motore non risponde: entra e guarda la barra di stato")


## Invio e spazio fanno partire: chi arriva da tastiera non deve cercare il
## mouse per superare una schermata che ha un solo bottone.
func _unhandled_input(evento: InputEvent) -> void:
	if _avvia != null and not _avvia.disabled and evento.is_action_pressed("ui_accept"):
		_esci()


## La chiama la schermata principale quando il sidecar risponde.
func motore_pronto() -> void:
	_pronto = true
	_stato.text = tr("motore pronto")
	_sblocca(tr("Avvia"))


func motore_in_errore(messaggio: String) -> void:
	_pronto = true
	_stato.text = messaggio
	_sblocca(tr("Entra comunque"))


func _sblocca(etichetta: String) -> void:
	if _avvia == null:
		return
	_avvia.text = etichetta
	_avvia.disabled = false
	_avvia.grab_focus()


func _esci() -> void:
	# Il tasto puo' essere premuto due volte, o premuto mentre Invio fa la
	# stessa cosa: senza questa guardia partirebbero due animazioni e due
	# `queue_free`, e la seconda lavorerebbe su un nodo gia' liberato.
	if _uscendo:
		return
	_uscendo = true
	var t := create_tween()
	t.tween_property(self, "offset:y", -get_viewport().get_visible_rect().size.y, 0.45) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	await t.finished
	finito.emit()
	queue_free()
