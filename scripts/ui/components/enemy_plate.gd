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
		bottom.add_child(UIKit.tag("ANCIENT FOE", Color("#7a1a14")))
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
	for s in combatant.statuses:
		status_row.add_child(StatusIcon.make(s["id"], int(s.get("turns", 0)), float(s.get("value", 0.0)), 32))


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
