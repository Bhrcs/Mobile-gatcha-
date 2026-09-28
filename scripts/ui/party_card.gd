class_name PartyCard
extends Control
## Battle card for one party member: element frame, large portrait, HP bar with
## healthy / injured / critical thresholds and a lost-section, Burst gauge with
## EMPTY / CHARGING / READY states, status icons, KO state and gesture feedback.
## Gestures (touch or mouse):  TAP = attack   SWIPE UP = Burst   SWIPE DOWN = Guard

signal action(c: Combatant, action: String)
signal pressed(c: Combatant)

const SWIPE_DIST := 60.0
const H := 210

var combatant: Combatant
var frame: PanelFrame
var content: Control
var hp_bar: ResourceBar
var hp_text: Label
var burst_bar: ResourceBar
var burst_label: Label
var burst_pct: Label
var status_row: HBoxContainer
var portrait: Control
var ko_stamp: Label
var gesture: Control
var gesture_icon: TextureRect
var gesture_label: Label
var _sparkle: CPUParticles2D
var _press_pos := Vector2.ZERO
var _pressing := false
var _glow_tween: Tween
var _enabled := true
var _ready_state := false
var _selected := false
var _el := "neutral"


func setup(c: Combatant) -> void:
	combatant = c
	name = "PartyCard_%d" % c.slot
	_el = c.element if c.element in ["fire", "water", "nature"] else "neutral"
	custom_minimum_size = Vector2(500, H)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	resized.connect(func(): pivot_offset = size / 2.0)

	frame = PanelFrame.make("card_" + _el, 14)
	frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(frame)
	var row := UIKit.hbox(12)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(row)
	content = row

	portrait = UIKit.portrait_art(c.def, Vector2(150, 176))
	row.add_child(portrait)
	ko_stamp = UIKit.label("KO", UIKit.T_TITLE, UIKit.DANGER, HORIZONTAL_ALIGNMENT_CENTER, 14)
	ko_stamp.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	ko_stamp.set_anchors_preset(Control.PRESET_FULL_RECT)
	ko_stamp.rotation = -0.2
	ko_stamp.pivot_offset = Vector2(75, 88)
	ko_stamp.visible = false
	portrait.add_child(ko_stamp)

	var col := UIKit.vbox(3)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(col)
	var top := UIKit.hbox(6)
	top.add_child(UIKit.orb(c.element, 32))
	var nm := UIKit.label(c.display_name.split(" ")[0], UIKit.T_BODY, Color.WHITE, HORIZONTAL_ALIGNMENT_LEFT, 7)
	nm.clip_text = true
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(nm)
	status_row = UIKit.hbox(2)
	top.add_child(status_row)
	col.add_child(top)
	var hp_row := UIKit.hbox(6)
	hp_row.add_child(UIKit.label("HP", UIKit.T_SMALL, UIKit.GOOD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	hp_text = UIKit.label("", UIKit.T_BODY, Color.WHITE, HORIZONTAL_ALIGNMENT_RIGHT, 6)
	hp_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hp_row.add_child(hp_text)
	col.add_child(hp_row)
	hp_bar = ResourceBar.make("hp", 28)
	col.add_child(hp_bar)
	var b_row := UIKit.hbox(6)
	burst_label = UIKit.label("BURST", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5)
	burst_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b_row.add_child(burst_label)
	burst_pct = UIKit.label("", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_RIGHT, 5)
	b_row.add_child(burst_pct)
	col.add_child(b_row)
	burst_bar = ResourceBar.make("burst", 24)
	col.add_child(burst_bar)
	burst_bar.filled.connect(_on_burst_filled)

	_build_gesture_overlay()

	c.hp_changed.connect(_on_hp)
	c.burst_changed.connect(_on_burst)
	c.statuses_changed.connect(_on_statuses)
	hp_bar.ready.connect(func(): hp_bar.set_values(c.hp, c.max_hp, false))
	burst_bar.ready.connect(func(): burst_bar.set_values(c.burst, c.burst_max, false))
	_on_hp(c.hp, c.max_hp)
	_on_burst(c.burst, c.burst_max)
	gui_input.connect(_on_gui_input)


func _build_gesture_overlay() -> void:
	gesture = Control.new()
	gesture.set_anchors_preset(Control.PRESET_FULL_RECT)
	gesture.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gesture.visible = false
	gesture.z_index = 5
	add_child(gesture)
	var shade := ColorRect.new()
	shade.color = Color(0.02, 0.01, 0.04, 0.55)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gesture.add_child(shade)
	var h := UIKit.hbox(12)
	h.set_anchors_preset(Control.PRESET_CENTER)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gesture.add_child(h)
	gesture_icon = UIKit.icon("res://assets/icons/gesture_up.png", 96)
	h.add_child(gesture_icon)
	gesture_label = UIKit.label("", UIKit.T_HEAD, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 10)
	h.add_child(gesture_label)
	h.resized.connect(func(): h.position = (size - h.size) / 2.0)


# ------------------------------------------------------------------ gestures
func _on_gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_pressing = true
			_press_pos = event.position
			pressed.emit(combatant)
			if _enabled and combatant.can_act():
				create_tween().tween_property(self, "scale", Vector2(1.03, 1.03), 0.06)
		elif _pressing:
			_pressing = false
			_release(event.position - _press_pos)
		accept_event()
	elif event is InputEventMouseMotion and _pressing:
		var dy: float = event.position.y - _press_pos.y
		content.position.y = clampf(dy, -40.0, 40.0) * 0.5
		_update_gesture(dy)
		accept_event()


## Direction indicator: up = Burst, down = Guard; brightens past the threshold.
func _update_gesture(dy: float) -> void:
	if not _enabled or not combatant.can_act() or abs(dy) < 16.0:
		gesture.visible = false
		return
	gesture.visible = true
	var up := dy < 0.0
	var k := clampf(abs(dy) / SWIPE_DIST, 0.0, 1.0)
	var armed := k >= 1.0
	gesture_icon.texture = load("res://assets/icons/gesture_up.png" if up else "res://assets/icons/gesture_down.png")
	if up and not combatant.burst_ready():
		gesture_label.text = "NOT READY"
		gesture_label.add_theme_color_override("font_color", UIKit.MUTED)
		gesture.modulate = Color(1, 1, 1, 0.4 + 0.4 * k)
		return
	gesture_label.text = ("BURST!" if up else "GUARD") if armed else ("BURST" if up else "GUARD")
	gesture_label.add_theme_color_override("font_color", UIKit.GOLD if up else Color("#a8d0ff"))
	gesture.modulate = Color(1.3, 1.2, 1.0) if armed else Color(1, 1, 1, 0.35 + 0.55 * k)
	gesture_icon.pivot_offset = gesture_icon.size / 2.0
	gesture_icon.scale = Vector2.ONE * (1.2 if armed else 0.8 + 0.2 * k)


func _release(delta: Vector2) -> void:
	gesture.visible = false
	var tw := create_tween().set_parallel(true)
	tw.tween_property(content, "position:y", 0.0, 0.1)
	tw.tween_property(self, "scale", Vector2.ONE, 0.08)
	if not _enabled:
		return
	if delta.y < -SWIPE_DIST and abs(delta.y) > abs(delta.x):
		action.emit(combatant, "burst")
	elif delta.y > SWIPE_DIST and abs(delta.y) > abs(delta.x):
		action.emit(combatant, "guard")
	elif delta.length() < SWIPE_DIST:
		action.emit(combatant, "attack")


## Used by tests / accessibility: perform the gesture for an action.
func simulate(action_name: String) -> void:
	match action_name:
		"burst":
			_release(Vector2(0, -120))
		"guard":
			_release(Vector2(0, 120))
		_:
			_release(Vector2.ZERO)


# ------------------------------------------------------------------ state
func set_enabled(on: bool) -> void:
	_enabled = on
	refresh_state()


func set_selected(on: bool) -> void:
	_selected = on
	refresh_state()


func refresh_state() -> void:
	var alive := combatant.is_alive()
	ko_stamp.visible = not alive
	if not alive:
		frame.set_variant("card_neutral", 14)
		modulate = Color(0.5, 0.42, 0.44)
		portrait.modulate = Color(0.55, 0.5, 0.55)
		_set_sparkle(false)
		return
	portrait.modulate = Color.WHITE
	var can := combatant.can_act() and _enabled
	frame.set_variant("card_%s%s" % [_el, "_lit" if (_ready_state or (can and _selected)) else ""], 14)
	if can:
		modulate = Color.WHITE
	elif not combatant.can_act():
		modulate = Color(0.6, 0.6, 0.68)     # already acted this turn
	else:
		modulate = Color(0.82, 0.82, 0.88)   # enemy phase / animating
	_set_sparkle(_ready_state and can)


func _on_hp(current: int, maximum: int) -> void:
	hp_text.text = "%d/%d" % [current, maximum]
	var r := float(current) / maxf(maximum, 1.0)
	hp_text.add_theme_color_override("font_color", Color.WHITE if r > 0.5 else (Color("#ffe06a") if r > 0.25 else Color("#ff7a6a")))
	if hp_bar.is_inside_tree():
		hp_bar.set_values(current, maximum)
	refresh_state()


func _on_burst(current: float, maximum: float) -> void:
	if burst_bar.is_inside_tree():
		burst_bar.set_values(current, maximum)
	var full := current >= maximum
	var pct := int(floor(current / max(maximum, 1.0) * 100.0))
	_ready_state = full
	if full:
		burst_label.text = "READY! SWIPE UP"
		burst_label.add_theme_color_override("font_color", UIKit.GOLD)
		burst_pct.text = ""
		if _glow_tween == null or not _glow_tween.is_valid():
			_glow_tween = create_tween().set_loops()
			_glow_tween.tween_property(frame, "self_modulate", Color(1.35, 1.2, 0.9), 0.35).set_trans(Tween.TRANS_SINE)
			_glow_tween.tween_property(frame, "self_modulate", Color.WHITE, 0.35).set_trans(Tween.TRANS_SINE)
	else:
		burst_label.text = "BURST" if current <= 0.0 else "CHARGING"
		burst_label.add_theme_color_override("font_color", UIKit.MUTED if current <= 0.0 else UIKit.SKY)
		burst_pct.text = "EMPTY" if current <= 0.0 else "%d%%" % pct
		if _glow_tween:
			_glow_tween.kill()
			_glow_tween = null
		frame.self_modulate = Color.WHITE
	refresh_state()


func _on_burst_filled() -> void:
	if not combatant.is_alive():
		return
	AudioManager.play_sfx("burst_ready", 0.02, -2.0)
	var tw := create_tween()
	tw.tween_property(self, "scale", Vector2(1.05, 1.05), 0.08)
	tw.tween_property(self, "scale", Vector2.ONE, 0.12)


func _set_sparkle(on: bool) -> void:
	if not bool(GameManager.settings.get("battle_effects", true)):
		on = false
	if on and _sparkle == null:
		_sparkle = UIKit.sparkle(self, Rect2(10, 10, max(size.x, 480) - 20, H - 20), Color("#ffe08a"), 10)
		_sparkle.z_index = 4
	elif not on and _sparkle:
		_sparkle.queue_free()
		_sparkle = null


func _on_statuses() -> void:
	for ch in status_row.get_children():
		ch.queue_free()
	for s in combatant.statuses:
		status_row.add_child(StatusIcon.make(s["id"], int(s.get("turns", 0)), float(s.get("value", 0.0)), 32))
