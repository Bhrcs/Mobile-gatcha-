class_name EnemyPlate
extends PanelFrame
## Enemy status plate in the battle HUD: element orb, name + level, HP bar with
## lost-section, HP %, status icons and the TARGET state. Bosses get the larger
## crimson frame, the heavy bar and an ANCIENT FOE tag. Tapping targets the enemy.

signal tapped(c: Combatant)

var combatant: Combatant
var is_boss := false
var bar: ResourceBar
var pct: Label
var status_row: HBoxContainer
var marker: TextureRect
var name_label: Label
var _targeted := false
var _last_hp := 0
var _pulse: Tween


var phase_tag: PanelContainer
var _danger: PanelContainer


static func create(c: Combatant) -> EnemyPlate:
	var p := EnemyPlate.new()
	p.combatant = c
	p.is_boss = bool(c.def.get("boss", false))
	p.name = "EnemyPlate_%d" % c.slot
	return p


func _ready() -> void:
	set_variant("boss" if is_boss else "enemy", 14 if is_boss else 10)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	custom_minimum_size = Vector2(200, 150 if is_boss else 120)
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	var row := UIKit.hbox(10)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(row)
	var left := Control.new()
	left.custom_minimum_size = Vector2(64 if is_boss else 48, 48)
	left.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(left)
	var orb := UIKit.orb(combatant.element, 64 if is_boss else 48)
	orb.position = Vector2(0, 8 if is_boss else 4)
	left.add_child(orb)
	marker = UIKit.icon("res://assets/ui/v2_chevron.png", 32)
	marker.position = Vector2(16 if is_boss else 8, -26)
	marker.visible = false
	left.add_child(marker)
	var col := UIKit.vbox(4)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(col)
	var top := UIKit.hbox(8)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	name_label = UIKit.label(combatant.display_name, UIKit.T_NAME if is_boss else UIKit.T_BODY,
			Database.element_color(combatant.element).lightened(0.5), HORIZONTAL_ALIGNMENT_LEFT, 7)
	name_label.clip_text = true
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(name_label)
	top.add_child(UIKit.label("Lv%d" % combatant.level, UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 5))
	col.add_child(top)
	bar = ResourceBar.make("boss" if is_boss else "enemy", 36 if is_boss else 26)
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_child(bar)
	var bottom := UIKit.hbox(6)
	bottom.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if is_boss:
		phase_tag = UIKit.tag(_phase_text(), Color("#7a1a14"))
		phase_tag.name = "PhaseTag"
		bottom.add_child(phase_tag)
		_add_phase_tick()
	elif combatant.is_elite:
		bottom.add_child(UIKit.tag("ELITE", Color("#8a6a10")))
	status_row = UIKit.hbox(4)
	status_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bottom.add_child(status_row)
	pct = UIKit.label("", UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_RIGHT, 5)
	bottom.add_child(pct)
	col.add_child(bottom)
	combatant.hp_changed.connect(_on_hp)
	combatant.statuses_changed.connect(_on_statuses)
	bar.ready.connect(func(): bar.set_values(combatant.hp, combatant.max_hp, false))
	_last_hp = combatant.hp
	_on_hp(combatant.hp, combatant.max_hp)
	gui_input.connect(func(e):
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and not e.pressed and combatant.is_alive():
			tapped.emit(combatant)
			accept_event())
	set_targeted(false)


func _on_hp(current: int, maximum: int) -> void:
	if bar.is_inside_tree():
		bar.set_values(current, maximum)
	pct.text = "%d%%" % int(ceil(float(current) / max(maximum, 1) * 100.0))
	if current <= 0:
		set_targeted(false)
		var tw := create_tween()
		tw.tween_interval(0.4)
		tw.tween_property(self, "modulate", Color(0.45, 0.4, 0.45, 0.55), 0.3)
		pct.text = "DOWN"
	elif current < _last_hp:
		# brief hit blink (layout-safe: containers own our position)
		var tw := create_tween()
		tw.tween_property(self, "self_modulate", Color(1.8, 1.5, 1.5), 0.04)
		tw.tween_property(self, "self_modulate", Color.WHITE, 0.12)
	_last_hp = current


func _on_statuses() -> void:
	for ch in status_row.get_children():
		ch.queue_free()
	var charging := false
	for s in combatant.statuses:
		status_row.add_child(StatusIcon.make(s["id"], int(s.get("turns", 0)), float(s.get("value", 0.0)), 32))
		if String(s["id"]) == "charging":
			charging = true
	_set_danger(charging)


## "PHASE 1 / 2" for bosses with a second phase, otherwise ANCIENT FOE.
func _phase_text() -> String:
	if combatant.def.get("ai", {}).get("phase2", {}).is_empty():
		return "ANCIENT FOE"
	return "PHASE %d / 2" % (2 if combatant.phase2 else 1)


## Small mark on the HP bar where phase 2 begins.
func _add_phase_tick() -> void:
	var p2: Dictionary = combatant.def.get("ai", {}).get("phase2", {})
	if p2.is_empty():
		return
	var tick := ColorRect.new()
	tick.name = "PhaseTick"
	tick.color = Color("#ffd35a")
	tick.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bar.add_child(tick)
	var ratio := float(p2.get("below", 0.5))
	bar.resized.connect(func():
		tick.size = Vector2(6, bar.size.y)
		tick.position = Vector2(6 + (bar.size.x - 12) * ratio - 3, 0))


func refresh_phase() -> void:
	if phase_tag:
		(phase_tag.get_child(0) as Label).text = _phase_text()
		phase_tag.add_theme_stylebox_override("panel", UIKit.flat(Color("#b8281e"), Color("#ffd35a"), 3))
		var tick := bar.get_node_or_null("PhaseTick")
		if tick:
			tick.visible = false


## DANGER: the foe is charging a big attack (guard!). Pulses until it fires.
func _set_danger(on: bool) -> void:
	if on and _danger == null:
		_danger = UIKit.tag("DANGER - GUARD!", Color("#c8281e"))
		_danger.name = "DangerTag"
		status_row.get_parent().add_child(_danger)
		status_row.get_parent().move_child(_danger, 0)
		var tw := _danger.create_tween().set_loops()
		tw.tween_property(_danger, "modulate", Color(1.6, 1.2, 1.2), 0.3)
		tw.tween_property(_danger, "modulate", Color.WHITE, 0.3)
	elif not on and _danger != null:
		_danger.queue_free()
		_danger = null


func set_targeted(on: bool) -> void:
	_targeted = on and combatant.is_alive()
	marker.visible = _targeted
	if _pulse:
		_pulse.kill()
		_pulse = null
	if not combatant.is_alive():
		return
	modulate = Color.WHITE if _targeted else Color(0.78, 0.76, 0.82)
	if _targeted:
		_pulse = create_tween().set_loops()
		_pulse.tween_property(marker, "modulate", Color(1.6, 1.3, 0.8), 0.35)
		_pulse.tween_property(marker, "modulate", Color.WHITE, 0.35)
