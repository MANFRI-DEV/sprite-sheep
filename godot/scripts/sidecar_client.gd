extends Node
## Avvia il sidecar Python e ci parla via HTTP.
##
## Godot non puo' eseguire l'inferenza (serve PyTorch + CUDA): tutto il lavoro
## pesante sta nel processo figlio, qui c'e' solo il ponte.

signal sidecar_pronto(info: Dictionary)
signal sidecar_errore(messaggio: String)

const PORTA := 8765
const HOST := "127.0.0.1"

## L'interprete Python non e' cablato: lo cerca TrovaPython, altrimenti su
## un'altra macchina il percorso non esisterebbe e l'app non partirebbe.

var _pid := -1
var _http: HTTPRequest

## Segreto condiviso col sidecar, nuovo a ogni avvio.
##
## Il sidecar ascolta su localhost, e localhost non e' "solo noi": qualunque
## pagina aperta nel browser puo' mandargli una POST. Senza questo, un sito
## poteva accettare una licenza a nome dell'utente e avviare un download da
## 40 GB. Il token passa nell'**ambiente** del processo figlio, non nella
## riga di comando: gli argomenti di un processo li legge chiunque sulla
## stessa macchina, l'ambiente no.
var _token := ""


func _ready() -> void:
	_http = HTTPRequest.new()
	add_child(_http)
	_token = Crypto.new().generate_random_bytes(24).hex_encode()


func _intestazioni(extra: Array = []) -> PackedStringArray:
	var h := PackedStringArray(["X-SpriteSheep-Token: " + _token])
	h.append_array(extra)
	return h


## Lancia il sidecar. Se risponde gia' qualcuno sulla porta, non ne avvia un altro.
func avvia() -> void:
	var script_path := _percorso_sidecar()
	if not FileAccess.file_exists(script_path):
		sidecar_errore.emit("server.py non trovato: %s" % script_path)
		return

	var python := TrovaPython.cerca()
	if python == "":
		sidecar_errore.emit(TrovaPython.spiegazione())
		return

	# Il figlio eredita l'ambiente del padre al momento della creazione:
	# impostarlo qui basta, e non lo vede nessun altro processo.
	OS.set_environment("SPRITESHEEP_TOKEN", _token)
	_pid = OS.create_process(python, [script_path, "--port", str(PORTA)], false)
	if _pid <= 0:
		sidecar_errore.emit("impossibile avviare il processo sidecar")
		return
	_attendi_pronto()


## Chiude il sidecar. Chiamato all'uscita dell'app.
func ferma() -> void:
	if _pid > 0:
		OS.kill(_pid)
		_pid = -1


## Dove sta `server.py`, in editor e nella build distribuita.
##
## In editor `res://` e' `godot/`, quindi il sidecar e' la cartella sorella.
## Nella build il .pck e' dentro l'eseguibile e `sidecar/` gli sta accanto:
## risalire di un livello finirebbe fuori dalla cartella d'installazione.
func _percorso_sidecar() -> String:
	var candidati: Array[String] = []
	if OS.has_feature("editor"):
		var res := ProjectSettings.globalize_path("res://")
		candidati.append(res.path_join("../sidecar/server.py").simplify_path())
	else:
		var exe := OS.get_executable_path().get_base_dir()
		candidati.append(exe.path_join("sidecar/server.py"))
		candidati.append(exe.path_join("../sidecar/server.py").simplify_path())

	for p in candidati:
		if FileAccess.file_exists(p):
			return p
	return candidati[0]      # il messaggio d'errore dira' dove l'abbiamo cercato


## Interroga /health finche' risponde, con un tetto di tentativi.
func _attendi_pronto(tentativi := 20) -> void:
	for i in tentativi:
		await get_tree().create_timer(0.5).timeout
		var info := await get_json("/health")
		if not info.is_empty() and info.get("ok", false):
			# Risponde, ma non e' il nostro: un sidecar rimasto appeso da una
			# sessione precedente tiene la porta, e il nostro non e' riuscito
			# a legarla. Parlargli darebbe 403 a ogni richiesta; meglio dire
			# subito cosa fare.
			if not info.get("token_ok", true):
				sidecar_errore.emit(TranslationServer.translate(
					"Un'altra istanza del motore occupa la porta %d. Chiudi le "
					+ "altre finestre di Sprite Sheep, oppure termina il processo "
					+ "python rimasto aperto, e riavvia.") % PORTA)
				return
			sidecar_pronto.emit(info)
			return
	sidecar_errore.emit("sidecar non risponde su %s:%d dopo %d tentativi" % [HOST, PORTA, tentativi])


## GET che restituisce il JSON, o un dizionario vuoto se fallisce.
## Nodo dedicato per chiamata, come per post_json: le richieste si sovrappongono.
func get_json(rotta: String) -> Dictionary:
	var req := HTTPRequest.new()
	add_child(req)
	var err := req.request("http://%s:%d%s" % [HOST, PORTA, rotta],
		_intestazioni())
	if err != OK:
		req.queue_free()
		return {}
	var r: Array = await req.request_completed
	req.queue_free()
	if int(r[1]) != 200:
		return {}
	var parsed: Variant = JSON.parse_string((r[3] as PackedByteArray).get_string_from_utf8())
	return parsed if parsed is Dictionary else {}


## POST JSON. Restituisce sempre un Dictionary: in caso di errore contiene
## `ok:false` e `errore`, cosi' i chiamanti hanno una forma sola da gestire.
## Usa un HTTPRequest dedicato: le chiamate possono sovrapporsi e un solo
## nodo condiviso andrebbe in "Another request is in progress".
func post_json(rotta: String, corpo: Dictionary) -> Dictionary:
	var req := HTTPRequest.new()
	add_child(req)
	var err := req.request(
		"http://%s:%d%s" % [HOST, PORTA, rotta],
		_intestazioni(["Content-Type: application/json"]),
		HTTPClient.METHOD_POST,
		JSON.stringify(corpo))
	if err != OK:
		req.queue_free()
		return {"ok": false, "errore": "richiesta non inviata (codice %d)" % err}

	var r: Array = await req.request_completed
	req.queue_free()

	var testo := (r[3] as PackedByteArray).get_string_from_utf8()
	var parsed: Variant = JSON.parse_string(testo)
	if parsed is Dictionary:
		return parsed
	return {"ok": false, "errore": "risposta non JSON (HTTP %d)" % int(r[1])}
