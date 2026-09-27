class_name Diagnostica
## Cosa dire dell'ambiente quando il sidecar risponde: testo per le
## Impostazioni, testo per gli appunti, stato della spia del motore.


## Il nome della scheda con accanto l'API che la muove.
##
## "CUDA" non si scrive piu' a meno che non sia vero: le build ROCm di PyTorch
## espongono l'API CUDA e il sidecar le vedeva come NVIDIA, cosi' chi generava
## con una Radeon si leggeva in faccia "nessuna GPU CUDA" mentre la GPU
## lavorava. Ora l'etichetta arriva dal sidecar e dice ROCm, DirectML o quel
## che e'.
const API_LEGGIBILE := {
	"cuda": "CUDA", "rocm": "ROCm", "directml": "DirectML",
	"mps": "Metal", "xpu": "oneAPI",
}


static func nome_gpu(cap: Dictionary) -> String:
	var nome: String = str(cap.get("gpu", "?"))
	var api: String = str(cap.get("api", ""))
	if api != "" and API_LEGGIBILE.has(api):
		return "%s - %s" % [nome, API_LEGGIBILE[api]]
	return nome


## Tre casi distinti, e nessuno dei tre e' un guasto da solo: GPU nota, GPU
## ancora ignota perche' ComfyUI e' spenta, oppure nessuna GPU. Confonderli
## faceva apparire "nessuna GPU" a chi ne aveva una che lavorava.
## Restituisce [colore, dettaglio] per la spia "motore".
static func spia_motore(cap: Dictionary) -> Array:
	if cap.get("cuda", false):
		var nome := nome_gpu(cap)
		var mb := int(cap.get("vram_mb", 0))
		return [Tema.ACCENTO, "%s (%d MB)" % [nome, mb] if mb > 0 else nome]
	if cap.get("comfyui_spenta", false):
		return [Tema.AVVISO, TranslationServer.translate("GPU ignota: ComfyUI spenta")]
	# Qui la GPU manca davvero: su CPU una generazione video e' di fatto
	# impraticabile, e va detto subito.
	return [Tema.ERRORE, TranslationServer.translate("Nessuna GPU compatibile")]


## Le righe del riquadro Diagnostica, con markup BBCode.
static func righe(info: Dictionary) -> Array:
	var cap: Dictionary = info.get("capacita", {})
	var fuori := [
		"[b]%s[/b] v%s" % [info.get("app", "?"), info.get("version", "?")],
		"Python %s" % info.get("python", "?"),
	]
	# torch nel sidecar non c'e' e non serve: dirlo evita che "torch assente"
	# venga letto come un pezzo mancante.
	if cap.get("torch", null) == null:
		fuori.append(_t("Calcolo su GPU: a carico di ComfyUI"))
	else:
		fuori.append("torch %s" % str(cap.get("torch")))

	if cap.get("cuda", false):
		fuori.append(_t("GPU: %s ([b]%d MB[/b])")
			% [nome_gpu(cap), int(cap.get("vram_mb", 0))])
	elif cap.get("comfyui_spenta", false):
		fuori.append("[color=#e0a840]%s[/color]"
			% _t("GPU non ancora nota: avvia ComfyUI"))
	else:
		fuori.append("[color=#e0a840]%s[/color]" % _t("Nessuna GPU compatibile"))

	fuori.append("%s %s" % [_t("Modelli:"), info.get("models_dir", "?")])
	var ed: Dictionary = info.get("edizione", {})
	fuori.append("%s %s" % [_t("Edizione:"), ed.get("nome", "?")])
	return fuori


static func _t(testo: String) -> String:
	return TranslationServer.translate(testo)


## Il testo per gli appunti non deve portarsi dietro il markup: prima toglieva
## solo [b] e [/b], e negli appunti finivano [color=#e0a840] e simili.
static func senza_tag(testo: String) -> String:
	var rx := RegEx.new()
	rx.compile("\\[/?[a-zA-Z]+[^\\]]*\\]")
	return rx.sub(testo, "", true)
