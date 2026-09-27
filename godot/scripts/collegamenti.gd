extends Node
class_name Collegamenti
## Gli indirizzi esterni del programma, tutti in un posto solo.
##
## Cambiano raramente, ma cambiano **insieme** — quando si sposta la pagina
## itch si sposta anche il resto — e cercarli sparsi fra i pannelli e' il modo
## in cui uno resta indietro.
##
## Quelli ancora vuoti non aprono niente e il loro pulsante resta spento, con
## scritto perche'. L'alternativa sarebbe un pulsante che porta alla pagina
## sbagliata o a un 404: per chi lo preme e' un programma rotto, e non ha modo
## di sapere che era solo un segnaposto.

const ITCH := "https://shaddafare.itch.io/sprite-sheep"
const DISCORD := "https://discord.gg/4bbsrj8YH"
const INSTAGRAM := "https://www.instagram.com/sprite_sheep/"

## Ko-fi da' un frammento di HTML, non un indirizzo: dentro c'e' solo il codice
## della pagina, che e' l'ultimo argomento di `kofiwidget2.init`. Il widget
## serve a incollare un pulsante in un sito web e qui non c'entra — un
## programma Godot apre il browser di sistema, non incorpora JavaScript.
const KOFI := "https://ko-fi.com/V3V027D3II"

## I segni dei servizi, ciascuno il marchio ufficiale senza ritocchi se non il
## bianco, perche' i pulsanti sono scuri.
##
## Sono indicizzati per **nome**, non per indirizzo, ed e' una correzione: con
## l'indirizzo come chiave il pulsante di itch restava senza segno finche'
## l'indirizzo non arrivava, cioe' proprio nel caso in cui e' spento e ha piu'
## bisogno di dire di cosa parla.
const ICONE := {
	"itch": preload("res://icone/itch.svg"),
	"discord": preload("res://icone/discord.svg"),
	"instagram": preload("res://icone/instagram.svg"),
	"kofi": preload("res://icone/kofi.svg"),
}

## Nome, nodo, indirizzo — nell'ordine in cui i pulsanti stanno sullo schermo.
##
## Il nome del nodo sta qui dentro, e non e' un dettaglio: prima testata e
## splash tenevano ciascuno un proprio elenco di pulsanti allineato a questa
## tabella **per posizione**. Aggiungere Instagram voleva dire ricordarsi di
## infilarlo al terzo posto in tre punti diversi, e sbagliarne uno avrebbe
## dato un pulsante Instagram che apre Ko-fi: acceso, con l'icona giusta, e
## sbagliato. Ora la corrispondenza e' scritta una volta sola.
const VOCI := [
	["itch", "AggiornamentiButton", ITCH],
	["discord", "DiscordButton", DISCORD],
	["instagram", "InstagramButton", INSTAGRAM],
	["kofi", "KofiButton", KOFI],
]


static func icona(nome: String) -> Texture2D:
	return ICONE.get(nome, null)


static func attivo(url: String) -> bool:
	return url.begins_with("https://")


## Apre il collegamento nel browser di sistema. Torna falso se non c'e'.
static func apri(url: String) -> bool:
	if not attivo(url):
		return false
	OS.shell_open(url)
	return true


## Accende i pulsanti dentro `riga`, uno per voce.
##
## La stessa procedura per la testata e per lo splash: erano due copie della
## stessa dozzina di righe, e la seconda si e' gia' presa una correzione che
## la prima non aveva. Torna quanti pulsanti ha trovato, cosi' chi chiama puo'
## accorgersi di una scena rimasta indietro invece di ritrovarsi un pulsante
## morto.
static func prepara(riga: Node) -> int:
	var trovati := 0
	for voce in VOCI:
		var b := riga.get_node_or_null(NodePath(voce[1])) as Button
		if b == null:
			push_warning("collegamenti: manca %s in %s" % [voce[1], riga.name])
			continue
		trovati += 1
		var url: String = voce[2]
		b.icon = icona(voce[0])
		b.disabled = not attivo(url)
		if b.disabled:
			b.tooltip_text = TranslationServer.translate(
				"Indirizzo non ancora configurato.")
		else:
			b.tooltip_text = url
			b.pressed.connect(func() -> void: apri(url))
	return trovati
