extends RefCounted
class_name TrovaPython
## Individua l'interprete Python da usare per il sidecar.
##
## Niente percorsi assoluti cablati: su un'altra macchina non esisterebbero e
## l'applicazione non partirebbe. Si cerca in ordine di preferenza, e la scelta
## viene memorizzata in `user://` cosi' i tentativi si fanno una volta sola.

const MEMORIA := "user://python.cfg"

## Sottocartelle in cui puo' stare un runtime distribuito con l'applicazione.
## Le voci con .exe valgono su Windows, le altre su Linux e macOS: si provano
## tutte, tanto quelle del sistema sbagliato semplicemente non esistono.
const RELATIVI := [
	"python/python.exe",
	"python_embeded/python.exe",
	"runtime/python.exe",
	"python/bin/python3",
	"runtime/bin/python3",
]

## Interpreti di installazioni note, provati solo come ultima spiaggia
const NOTI := [
	"ComfyUI/venv/Scripts/python.exe",
	"ComfyUI_windows_portable/python_embeded/python.exe",
	"ComfyUI/venv/bin/python3",
	"ComfyUI/.venv/bin/python3",
]


static func _valido(percorso: String) -> bool:
	return percorso != "" and FileAccess.file_exists(percorso)


static func _memorizzato() -> String:
	if not FileAccess.file_exists(MEMORIA):
		return ""
	var f := FileAccess.open(MEMORIA, FileAccess.READ)
	if f == null:
		return ""
	var p: String = f.get_as_text().strip_edges()
	return p if _valido(p) else ""


static func ricorda(percorso: String) -> void:
	var f := FileAccess.open(MEMORIA, FileAccess.WRITE)
	if f != null:
		f.store_string(percorso)


## Cartella dell'eseguibile (esportato) o del progetto (in editor)
static func _radice() -> String:
	if OS.has_feature("editor"):
		return ProjectSettings.globalize_path("res://").path_join("..").simplify_path()
	return OS.get_executable_path().get_base_dir()


## Chiede al sistema dove sta python, senza indovinare percorsi.
## Su Windows lo strumento e' `where`, altrove `which`: cambia il comando, non
## l'idea. Si prova piu' di un nome perche' su Linux "python" spesso non esiste.
static func _da_path() -> String:
	var windows := OS.get_name() == "Windows"
	var comando := "where" if windows else "which"
	var nomi := ["python.exe"] if windows else ["python3", "python"]
	for nome in nomi:
		var uscita := []
		var codice: int = OS.execute(comando, [nome], uscita, true)
		if codice != 0 or uscita.is_empty():
			continue
		for riga in str(uscita[0]).split("\n"):
			var p: String = riga.strip_edges()
			if _valido(p):
				return p
	return ""


## Moduli che il sidecar importa appena parte. Senza uno solo di questi il
## processo muore all'avvio, quindi un interprete che non li ha non e' un
## candidato: e' un guasto rimandato.
const MODULI := ["PIL", "numpy", "scipy", "huggingface_hub"]


## L'interprete regge il sidecar? Costa qualche decimo di secondo, e si paga
## una volta sola: subito dopo la scelta viene memorizzata.
static func _adeguato(percorso: String) -> bool:
	var uscita := []
	var codice: int = OS.execute(percorso, ["-c",
		"import importlib.util as u,sys;"
		+ "sys.exit(0 if all(u.find_spec(m) for m in %s) else 1)" % [MODULI]],
		uscita, true)
	return codice == 0


## Percorso dell'interprete, oppure "" se non se ne trova nessuno.
##
## L'ordine conta due volte: si preferisce il runtime che viaggia con il
## programma, e si scarta chi non ha le librerie. Un interprete trovato ma
## inadatto e' peggio di nessun interprete: il sidecar parte e muore, e il
## motivo lo si scopre solo leggendo i log.
static func cerca() -> String:
	var radice: String = _radice()

	# 1. runtime distribuito insieme al programma. Viene prima della scelta
	#    memorizzata: se l'applicazione si porta dietro il proprio Python,
	#    quello e' l'interprete giusto, e una preferenza salvata da
	#    un'installazione diversa non deve scavalcarlo.
	for rel in RELATIVI:
		var p: String = radice.path_join(rel)
		if _valido(p):
			ricorda(p)
			return p

	var memoria: String = _memorizzato()
	if memoria != "" and _adeguato(memoria):
		return memoria

	# 2. installazioni note vicine alla cartella dell'applicazione
	var ripiego := ""
	for rel in NOTI:
		for base in [radice, radice.path_join(".."), radice.path_join("../..")]:
			var p: String = base.path_join(rel).simplify_path()
			if _valido(p):
				if _adeguato(p):
					ricorda(p)
					return p
				elif ripiego == "":
					ripiego = p

	# 3. python di sistema
	var sistema: String = _da_path()
	if sistema != "":
		if _adeguato(sistema):
			ricorda(sistema)
			return sistema
		elif ripiego == "":
			ripiego = sistema

	# Nessuno completo. Si restituisce comunque il migliore trovato: il sidecar
	# fallira', ma con un errore che nomina il modulo mancante, che e' piu' utile
	# di "Python non trovato" detto a chi Python ce l'ha.
	if ripiego != "":
		ricorda(ripiego)
	return ripiego


## `tr()` e' un metodo di Node e da qui non si puo' chiamare: questa classe non
## sta nell'albero della scena. `TranslationServer.translate()` fa la stessa
## cosa senza pretendere un nodo.
static func spiegazione() -> String:
	return TranslationServer.translate(
		"Python non trovato. Sprite Sheep ne ha bisogno per il motore. "
		+ "Mettilo in una cartella 'python' accanto all'applicazione, "
		+ "oppure installalo e assicurati che sia nel PATH di sistema.")
