class_name SummonCeremony
extends Control
## Embergate summon presentation, one hero at a time:
##   1 fragments fly into the gate   2 the gate flares   3 rarity light + stars
##   4 a silhouette steps out        5 reveal (name, element, NEW / Soul Shards)
## Tap to continue (or to hurry an animation). SKIP appears once the player has
## watched a summon before. Results are already saved when this plays.

signal finished

const RARITY_COLORS := {3: Color("#e0a060"), 4: Color("#d8e4f4"), 5: Color("#ffd84a")}

var _can_skip := false
var _skip := false
var _tapped := false
var _stage: Control
var _vortex: TextureRect
var _vframe := 0
var _center := Vector2.ZERO


func play(results: Array, can_skip: bool) -> void:
	_can_skip = can_skip
	_build()
	for i in results.size():
		if _skip or not is_inside_tree():
			break
		await _reveal(results[i], i, results.size())
	finished.emit()


func _build() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	z_index = 80
	gui_input.connect(_on_input)
	var bg := ColorRect.new()
	bg.color = Color(0.02, 0.01, 0.04, 0.97)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)
	var vp := get_viewport_rect().size
	_center = Vector2(vp.x / 2, vp.y * 0.44)
	_stage = Control.new()
	_stage.set_anchors_preset(Control.PRESET_FULL_RECT)
	_stage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_stage)
	var k := 8.0
	_vortex = TextureRect.new()
	_vortex.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_vortex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	var at := AtlasTexture.new()
	at.atlas = load("res://assets/ui/embergate_vortex.png")
	at.region = Rect2(0, 0, 64, 64)
	_vortex.texture = at
	_vortex.size = Vector2(56, 56) * k
	_vortex.position = _center - _vortex.size / 2 + Vector2(0, 20)
	_vortex.pivot_offset = _vortex.size / 2
	_vortex.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_vortex)
	var frame := UIKit.tex_rect(load("res://assets/ui/embergate_frame.png"), Vector2(96, 128) * k)
	frame.size = frame.custom_minimum_size
	frame.position = _center - Vector2(48, 60) * k
	add_child(frame)
	var t := Timer.new()
	t.wait_time = 0.1
	t.autostart = true
	t.timeout.connect(func():
		_vframe = (_vframe + 1) % 6
		(_vortex.texture as AtlasTexture).region = Rect2(_vframe * 64, 0, 64, 64))
	add_child(t)
	move_child(_stage, get_child_count() - 1)
	if _can_skip:
		var skip := FantasyButton.make("SKIP", "stone", Vector2(220, 96))
		skip.name = "SkipSummon"
		skip.position = Vector2(vp.x - 250, UIKit.safe_top() + 30)
		skip.z_index = 5
		skip.pressed.connect(func():
			_skip = true
			_tapped = true)
		add_child(skip)
	var hint := UIKit.label("TAP TO CONTINUE", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 5)
	hint.position = Vector2(0, vp.y - 120 - UIKit.safe_bottom())
	hint.size = Vector2(vp.x, 40)
	add_child(hint)


func _on_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		_tapped = true


func _wait(t: float) -> void:
	if _skip:
		return
	var left := t
	while left > 0.0 and not _skip:
		if not is_inside_tree():
			_skip = true
			return
		await get_tree().process_frame
		left -= get_process_delta_time() * (4.0 if _tapped else 1.0)


func _reveal(e: Dictionary, index: int, total: int) -> void:
	for ch in _stage.get_children():
		ch.queue_free()
	_tapped = false
	var d := Database.get_character(e["char_id"])
	var rarity := int(e["rarity"])
	var rcol: Color = RARITY_COLORS.get(rarity, Color.WHITE)
	var vp := get_viewport_rect().size
	if total > 1:
		var cnt := UIKit.label("%d / %d" % [index + 1, total], UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 5)
		cnt.position = Vector2(40, UIKit.safe_top() + 40)
		_stage.add_child(cnt)
	# 1) fragments
	AudioManager.play_sfx("summon_charge", 0.03)
	var cols := [Color("#ff8a3a"), Color("#5ac8ff"), Color("#8ae05a")]
	for i in 18:
		var f := ColorRect.new()
		f.color = cols[i % 3].lightened(0.2)
		f.size = Vector2(16, 16)
		var a := TAU * i / 18.0
		f.position = _center + Vector2(cos(a), sin(a)) * 520
		f.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_stage.add_child(f)
		var tw := f.create_tween()
		tw.tween_property(f, "position", _center - Vector2(8, 8), 0.55).set_delay(i * 0.012).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		tw.tween_callback(f.queue_free)
	await _wait(0.65)
	# 2) the gate flares in the rarity colour
	var gtw := create_tween()
	gtw.tween_property(_vortex, "modulate", Color(2.2, 2.0, 1.8), 0.15)
	gtw.tween_property(_vortex, "modulate", rcol.lightened(0.3) * Color(1.6, 1.6, 1.6, 1), 0.3)
	gtw.parallel().tween_property(_vortex, "scale", Vector2(1.15, 1.15), 0.3)
	await _wait(0.45)
	# 3) rarity light + stars
	var glow := UIKit.tex_rect(load("res://assets/ui/rarity_glow_%d.png" % clampi(rarity, 3, 5)), Vector2(32, 32) * (14 + rarity * 2))
	glow.size = glow.custom_minimum_size
	glow.position = _center - glow.size / 2
	glow.pivot_offset = glow.size / 2
	glow.modulate.a = 0.0
	_stage.add_child(glow)
	var gl := glow.create_tween().set_parallel(true)
	gl.tween_property(glow, "modulate:a", 0.9, 0.25)
	gl.tween_property(glow, "rotation", 0.6, 2.5)
	if rarity >= 5:
		AudioManager.play_sfx("summon_rare")
		var fl := ColorRect.new()
		fl.color = Color(1.0, 0.9, 0.4, 0.8)
		fl.set_anchors_preset(Control.PRESET_FULL_RECT)
		fl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_stage.add_child(fl)
		fl.create_tween().tween_property(fl, "color:a", 0.0, 0.6)
		UIKit.sparkle(_stage, Rect2(_center.x - 400, _center.y - 500, 800, 900), Color("#ffe08a"), 40)
	elif rarity == 4:
		UIKit.sparkle(_stage, Rect2(_center.x - 300, _center.y - 400, 600, 700), Color("#e8f0ff"), 20)
	var stars := UIKit.hbox(6)
	stars.position = Vector2(vp.x / 2 - rarity * 38, _center.y - 520)
	_stage.add_child(stars)
	for i in rarity:
		if _skip:
			break
		var st := UIKit.icon("res://assets/icons/star.png", 72)
		stars.add_child(st)
		st.pivot_offset = Vector2(36, 36)
		st.scale = Vector2(2, 2)
		st.create_tween().tween_property(st, "scale", Vector2.ONE, 0.15).set_trans(Tween.TRANS_BACK)
		AudioManager.play_sfx("reward", 0.05, -8.0)
		await _wait(0.14)
	# 4) silhouette
	var sp := UnitSpriteDisplay.new()
	sp.setup(d.get("sprite", {}), 14.0, false)
	sp.size = sp.custom_minimum_size
	sp.position = Vector2(_center.x - sp.size.x / 2, _center.y + 330 - sp.size.y)
	sp.modulate = Color(0, 0, 0, 0)
	_stage.add_child(sp)
	var stw := sp.create_tween()
	stw.tween_property(sp, "modulate", Color(0, 0, 0, 1), 0.35)
	await _wait(0.6)
	# 5) reveal
	AudioManager.play_sfx("summon_reveal")
	var flash := ColorRect.new()
	flash.color = Color(1, 1, 1, 0.95)
	flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stage.add_child(flash)
	flash.create_tween().tween_property(flash, "color:a", 0.0, 0.4)
	sp.modulate = Color.WHITE
	sp.play("victory")
	var nm := UIKit.label(d.get("name", ""), UIKit.T_HEAD, rcol.lightened(0.2), HORIZONTAL_ALIGNMENT_CENTER, 12)
	nm.name = "RevealName"
	nm.position = Vector2(0, _center.y + 360)
	nm.size = Vector2(vp.x, 70)
	_stage.add_child(nm)
	var sub := UIKit.hbox(10)
	sub.alignment = BoxContainer.ALIGNMENT_CENTER
	sub.position = Vector2(0, _center.y + 440)
	sub.size = Vector2(vp.x, 60)
	sub.add_child(UIKit.orb(d.get("element", ""), 48))
	sub.add_child(UIKit.label("%s  %s" % [Database.element_name(d.get("element", "")), d.get("role", "")], UIKit.T_BODY, UIKit.TEXT,
			HORIZONTAL_ALIGNMENT_LEFT, 6))
	_stage.add_child(sub)
	if e["is_new"]:
		var nt := UIKit.label("NEW!", 90, Color("#ff5a4a"), HORIZONTAL_ALIGNMENT_CENTER, 14)
		nt.name = "NewStamp"
		nt.position = Vector2(vp.x / 2 + 120, _center.y - 380)
		nt.size = Vector2(300, 100)
		nt.rotation = 0.2
		nt.pivot_offset = Vector2(150, 50)
		nt.scale = Vector2(2.5, 2.5)
		_stage.add_child(nt)
		nt.create_tween().tween_property(nt, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_BACK)
	else:
		var dup := UIKit.label("Already owned  >  +%d Soul Shards" % int(e["shards"]), UIKit.T_BODY, Color("#d0a8ff"),
				HORIZONTAL_ALIGNMENT_CENTER, 6)
		dup.position = Vector2(0, _center.y + 510)
		dup.size = Vector2(vp.x, 50)
		_stage.add_child(dup)
	# wait for a tap (multi summons auto-advance)
	_tapped = false
	var waited := 0.0
	while not _tapped and not _skip:
		if not is_inside_tree():
			_skip = true
			return
		await get_tree().process_frame
		waited += get_process_delta_time()
		if total > 1 and waited > 1.6:
			break
	var rt := create_tween()
	rt.tween_property(_vortex, "modulate", Color.WHITE, 0.2)
	rt.parallel().tween_property(_vortex, "scale", Vector2.ONE, 0.2)
