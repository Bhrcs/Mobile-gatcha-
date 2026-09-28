extends Node
## SceneRouter (autoload)
## Central scene switching with navigation history, consistent transitions and
## input blocking while a transition runs (rapid-click safety).
##
## Navigation modes (the `nav` argument of go()):
##   ""        auto: tab screens -> "tab", title/new-game screens -> "reset",
##             the same screen with new params -> "replace", everything else -> "push"
##   "push"    remember the current screen so Back returns to it (slide in from the right)
##   "tab"     bottom-nav destination: history becomes [home] (quick fade)
##   "replace" swap the current screen without remembering it
##   "reset"   clear history (title screen, new game)
## Battles are never remembered: leaving a battle returns along the history that
## led to it (Stage -> Squad -> Battle -> back to the stage map, not the squad).
## Screens call remember({...}) to store state (selected tab, scroll, open popup)
## that should come back when the player returns with Back.

signal scene_changed(path: String)

const SCENES := {
	"main_menu": "res://scenes/ui/main_menu.tscn",
	"starter_select": "res://scenes/ui/starter_select.tscn",
	"intro": "res://scenes/ui/intro.tscn",
	"home": "res://scenes/ui/home.tscn",
	"world_select": "res://scenes/ui/world_select.tscn",
	"stage_select": "res://scenes/ui/stage_select.tscn",
	"battle": "res://scenes/combat/battle.tscn",
	"units": "res://scenes/ui/units.tscn",
	"unit_detail": "res://scenes/ui/unit_detail.tscn",
	"train": "res://scenes/ui/train.tscn",
	"inventory": "res://scenes/ui/inventory.tscn",
	"squad": "res://scenes/ui/squad.tscn",
	"tower": "res://scenes/ui/tower.tscn",
	"summon": "res://scenes/ui/summon.tscn",
	"codex": "res://scenes/ui/codex.tscn",
	"missions": "res://scenes/ui/missions.tscn",
	"profile": "res://scenes/ui/profile.tscn",
	"evolve": "res://scenes/ui/evolve.tscn",
	"menu": "res://scenes/ui/menu.tscn",
	"settings": "res://scenes/ui/settings.tscn",
	"help": "res://scenes/ui/help.tscn",
}
## Bottom-navigation destinations.
const TABS := ["home", "world_select", "units", "summon", "menu"]
const RESETS := ["main_menu", "starter_select", "intro"]
const SLIDE_PX := 120.0
const LOADING_AFTER := 0.15   # seconds before a slow load shows the loading cover

var params: Dictionary = {}        # arguments for the current scene
var current := ""                  # current screen key (or path)
var history: Array = []            # [{scene, params}] - what Back returns to
var transitioning := false
var fade_time := 0.22              # each half of the battle transition
var reduce_motion := false         # settings: skip slides

var _layer: CanvasLayer
var _fade: ColorRect
var _ember: ColorRect


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_layer = CanvasLayer.new()
	_layer.layer = 100
	add_child(_layer)
	_fade = ColorRect.new()
	_fade.color = Color(0.05, 0.03, 0.06, 1.0)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.modulate.a = 0.0
	_layer.add_child(_fade)
	_ember = ColorRect.new()
	_ember.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ember.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = load("res://assets/shaders/ember_dissolve.gdshader")
	mat.set_shader_parameter("progress", 0.0)
	_ember.material = mat
	_ember.visible = false
	_layer.add_child(_ember)
	var cs := get_tree().current_scene
	if cs:
		current = _key_for(cs.scene_file_path)


## Switches to a named screen (see SCENES) or a raw scene path.
func go(scene: String, new_params: Dictionary = {}, nav := "") -> void:
	if transitioning:
		return
	var mode := _resolve_mode(scene, nav)
	match mode:
		"tab":
			history = [] if scene == "home" else [{"scene": "home", "params": {}}]
		"reset":
			history = []
		"push":
			if current != "battle" and not current.is_empty() and current != scene:
				history.append({"scene": current, "params": params.duplicate()})
			_trim_loop(scene)
		"replace":
			pass
	await _switch(scene, new_params, mode)


## Returns to the previous screen (or `fallback` when there is no history).
func back(fallback := "home", fallback_params: Dictionary = {}) -> void:
	if transitioning:
		return
	UIManager.sfx("back")
	if history.is_empty():
		if current == fallback:
			return
		await _switch(fallback, fallback_params, "back" if fallback != "home" else "tab")
		return
	var e: Dictionary = history.pop_back()
	var p: Dictionary = e.get("params", {}).duplicate()
	p["returning"] = true
	await _switch(String(e["scene"]), p, "back")


## Leaves a battle for the screen that led into it (stage map / tower).
## The battle replaced that screen, so the history below it is intact.
func leave_battle(map_scene: String, extra: Dictionary = {}) -> void:
	await go(map_scene, extra, "replace")


## Adds a screen to the history without visiting it (e.g. defeat -> EDIT SQUAD
## should come Back to the stage's preparation, not to the finished battle).
func push_entry(scene: String, entry_params: Dictionary = {}) -> void:
	history.append({"scene": scene, "params": entry_params})


## Stores state for the current screen so Back can restore it.
func remember(values: Dictionary) -> void:
	params.merge(values, true)


func has_history() -> bool:
	return not history.is_empty()


func previous_scene() -> String:
	return "" if history.is_empty() else String(history.back()["scene"])


func _resolve_mode(scene: String, nav: String) -> String:
	if not nav.is_empty():
		return nav
	if scene in RESETS:
		return "reset"
	if scene in TABS:
		return "tab"
	if scene == current:
		return "replace"
	if scene == "battle":
		return "replace"
	return "push"


## Avoid Units > Detail > Units > Detail ... chains: if the destination is
## already in the history, cut the history back to just before it.
func _trim_loop(scene: String) -> void:
	for i in range(history.size() - 1, -1, -1):
		if String(history[i]["scene"]) == scene:
			history.resize(i)
			return


func _key_for(path: String) -> String:
	for k in SCENES:
		if SCENES[k] == path:
			return k
	return path


func _switch(scene: String, new_params: Dictionary, mode: String) -> void:
	var path: String = SCENES.get(scene, scene)
	transitioning = true
	UIManager.hide_tooltip()
	var cur := get_tree().current_scene
	var ember := scene == "battle" or (cur != null and cur is BattleController)
	_fade.mouse_filter = Control.MOUSE_FILTER_STOP
	# start loading in the background while the old screen fades
	var threaded := ResourceLoader.load_threaded_request(path) == OK
	if ember:
		await _cover(true, true)
	else:
		await _fade_to(1.0 if mode in ["tab", "replace", "reset"] else 0.55, 0.12)
	var packed := await _finish_load(path, threaded)
	params = new_params
	current = scene if SCENES.has(scene) else _key_for(scene)
	var err := ERR_CANT_OPEN
	if packed:
		err = get_tree().change_scene_to_packed(packed)
	if err != OK:
		push_error("Failed to change scene to " + path)
		err = get_tree().change_scene_to_file(path)
	await get_tree().process_frame
	await get_tree().process_frame
	var root := get_tree().current_scene as Control
	if ember:
		await _cover(false, true)
	elif mode in ["push", "back"] and root and not reduce_motion:
		var dir := 1.0 if mode == "push" else -1.0
		var base := root.position
		root.position = base + Vector2(SLIDE_PX * dir, 0)
		root.modulate.a = 0.0
		var tw := create_tween().set_parallel(true)
		tw.tween_property(root, "position", base, 0.18).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tw.tween_property(root, "modulate:a", 1.0, 0.14)
		tw.tween_property(_fade, "modulate:a", 0.0, 0.14)
		await tw.finished
	else:
		await _fade_to(0.0, 0.14)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	transitioning = false
	scene_changed.emit(path)


func _finish_load(path: String, threaded: bool) -> PackedScene:
	if not threaded:
		return load(path) as PackedScene
	var start := Time.get_ticks_msec()
	var shown := false
	while ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
		if not shown and (Time.get_ticks_msec() - start) / 1000.0 > LOADING_AFTER:
			shown = true
			UIManager.show_loading()
		await get_tree().process_frame
	if shown:
		UIManager.hide_loading()
	return ResourceLoader.load_threaded_get(path) as PackedScene


func _fade_to(a: float, t: float) -> void:
	var tw := create_tween()
	tw.tween_property(_fade, "modulate:a", a, t)
	await tw.finished


func _cover(on: bool, ember: bool) -> void:
	var tw := create_tween()
	if ember:
		_ember.visible = true
		var mat := _ember.material as ShaderMaterial
		tw.tween_method(func(v: float): mat.set_shader_parameter("progress", v), 0.0 if on else 1.0, 1.0 if on else 0.0,
				fade_time + 0.08)
		await tw.finished
		if not on:
			_ember.visible = false
	else:
		tw.tween_property(_fade, "modulate:a", 1.0 if on else 0.0, fade_time)
		await tw.finished
