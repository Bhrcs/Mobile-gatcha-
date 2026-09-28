class_name StatusIcon
extends Control
## Status effect badge: 16px icon scaled x2/x3 with remaining turns.
## Hover (PC) or tap/hold (touch) shows name, effect and duration.

var status_id := ""
var turns := 0
var value := 0.0
var _tip: Control


static func make(sid: String, t: int, v: float = 0.0, px := 32) -> StatusIcon:
	var s := StatusIcon.new()
	s.status_id = sid
	s.turns = t
	s.value = v
	s.custom_minimum_size = Vector2(px, px)
	return s


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	var sdef := Database.get_status(status_id)
	var ic := UIKit.icon(sdef.get("icon", ""), int(custom_minimum_size.x))
	add_child(ic)
	if turns > 0 and status_id != "charging":
		var l := UIKit.label(str(turns), 20, Color.WHITE, HORIZONTAL_ALIGNMENT_RIGHT, 6)
		l.position = Vector2(custom_minimum_size.x - 22, custom_minimum_size.y - 26)
		l.size = Vector2(24, 26)
		add_child(l)
	tooltip_text = describe()
	gui_input.connect(_on_input)


## "Burn - loses 5% max HP each turn (2 turns left)"
func describe() -> String:
	var sdef := Database.get_status(status_id)
	var effect := ""
	match sdef.get("kind", ""):
		"dot":
			effect = "loses %d%% max HP each turn" % int(float(sdef.get("dot_percent_max_hp", 0.05)) * 100)
		"stat_mod":
			effect = "%s %s%d%%" % [String(sdef.get("stat", "")).to_upper(), "-" if int(sdef.get("sign", 1)) < 0 else "+",
					int(round(value * 100))]
		"hot":
			effect = "recovers %d%% max HP each turn" % int(round(value * 100))
		"shield":
			effect = "absorbs %d more damage" % int(value)
		"charge":
			effect = "unleashes a powerful attack on its next action - Guard!"
		"damage_reduction":
			effect = "takes %d%% less damage" % int(round(value * 100))
		"taunt":
			effect = "draws enemy attacks"
	if turns <= 0 or status_id == "charging":
		return "%s - %s" % [sdef.get("name", status_id), effect]
	return "%s - %s (%d turn%s left)" % [sdef.get("name", status_id), effect, turns, "" if turns == 1 else "s"]


func _on_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
		if e.pressed:
			_show_tip()
		else:
			_hide_tip()
		accept_event()


func _show_tip() -> void:
	_hide_tip()
	var root := get_tree().current_scene
	if root == null:
		return
	var p := PanelFrame.make("inset", 14)
	p.add_child(UIKit.label(describe(), 20, UIKit.TEXT))
	p.z_index = 90
	p.top_level = true
	add_child(p)
	await get_tree().process_frame
	if is_instance_valid(p):
		var gp := get_global_rect()
		var vw := get_viewport_rect().size.x
		p.global_position = Vector2(clampf(gp.position.x - p.size.x / 2, 8, vw - p.size.x - 8), gp.position.y - p.size.y - 8)
	_tip = p


func _hide_tip() -> void:
	if _tip and is_instance_valid(_tip):
		_tip.queue_free()
	_tip = null
