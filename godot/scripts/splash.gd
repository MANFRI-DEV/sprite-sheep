extends CanvasLayer
## Schermata di apertura: pecora, nome, edizione.
##
## Non e' solo decorazione. L'avvio del sidecar richiede una ventina di secondi
## (Python parte, importa, apre la porta) e senza niente davanti il programma
## sembra bloccato. Lo splash copre quell'attesa e si toglie da solo.

signal finito

## Quanto resta a schermo se il motore e' gia' pronto.
const DURATA_MIN := 1.6
## Limite oltre il quale ci si toglie comunque: se il motore non parte, il
## problema va mostrato nella schermata vera, non nascosto dietro una pecora.
const DURATA_MAX := 12.0

@onready var _pecora: TextureRect = %Pecora
@onready var _titolo: Label = %Titolo
@onready var _edizione: Label = %Edizione
@onready var _stato: Label = %Stato

var _pronto := false
var _trascorso := 0.0


func _ready() -> void:
	_titolo.text = "SPRITE SHEEP"
	_edizione.text = "PRE-ALPHA 0.0.4"
	_stato.text = tr("avvio del motore...")
	_pecora.modulate.a = 0.0
	_anima_entrata()


func _anima_entrata() -> void:
	var t := create_tween().set_parallel()
	t.tween_property(_pecora, "modulate:a", 1.0, 0.5)
	# La pecora scende di poco: un movimento breve legge come "arrivo",
	# uno lungo come attesa, e di attesa ce n'e' gia' abbastanza.
	_pecora.position.y -= 18
	t.tween_property(_pecora, "position:y", _pecora.position.y + 18, 0.6) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


func _process(delta: float) -> void:
	_trascorso += delta
	if (_pronto and _trascorso >= DURATA_MIN) or _trascorso >= DURATA_MAX:
		set_process(false)
		_esci()


## La chiama la schermata principale quando il sidecar risponde.
func motore_pronto() -> void:
	_pronto = true
	_stato.text = tr("pronto")


func motore_in_errore(messaggio: String) -> void:
	# Non si resta sullo splash a mostrare un errore: sotto c'e' la barra di
	# stato, che quell'errore lo sa raccontare per intero.
	_pronto = true
	_stato.text = messaggio


func _esci() -> void:
	var t := create_tween()
	t.tween_property(self, "offset:y", -get_viewport().get_visible_rect().size.y, 0.45) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	await t.finished
	finito.emit()
	queue_free()
