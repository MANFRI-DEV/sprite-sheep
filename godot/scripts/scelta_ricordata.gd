extends OptionButton
## Tendina che ricorda l'ultima scelta fra un avvio e l'altro.
##
## Serve al formato della clip e al margine intorno alla figura: chi fa sprite
## per un gioco usa sempre le stesse impostazioni, e riproporre il default a
## ogni avvio lo costringerebbe a ricambiarle ogni volta.
##
## Le chiavi sono quelle che il sidecar accetta (`parametri.FORMATI`,
## `inquadra.MARGINI`); le etichette sono testo da tradurre, e la tendina lo
## traduce da se', anche a lingua cambiata.

@export var chiavi: PackedStringArray = []
@export var etichette: PackedStringArray = []
@export var predefinita := ""
@export var memoria := ""


func _ready() -> void:
	for i in chiavi.size():
		add_item(etichette[i] if i < etichette.size() else chiavi[i])
	select(maxi(0, chiavi.find(_ricordata())))
	item_selected.connect(func(_i: int) -> void: _ricorda())


func valore() -> String:
	return chiavi[maxi(0, selected)] if chiavi.size() > 0 else predefinita


func _ricordata() -> String:
	return Memoria.leggi(memoria, predefinita)


func _ricorda() -> void:
	Memoria.scrivi(memoria, valore())
