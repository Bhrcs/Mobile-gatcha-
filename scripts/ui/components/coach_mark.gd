class_name CoachMark
extends Control
## Visual tutorial step: dims everything except one control, frames it with a
## pulsing ember border, shows a short instruction and an animated hand or
## swipe arrow, and lets input through only to the highlighted control.
## The caller finishes the step (e.g. when the player performed the action).

signal finished

var target: Control
var text := ""
var gesture := "tap"          # tap | up | down
var blocking := true          # false: a hint only - the rest of the screen stays usable
var _dims: Array[ColorRect] = []
var _border: Panel
var _hand: TextureRect
var _plate: PanelFrame
var _t := 0.0
var _done := false


static func show_on(parent: Control, target_control: Control, message: String, gesture_kind := "tap",
		block := true) -> CoachMark:
	var c := CoachMark.new()
	c.blocking = block
	c.target = target_control
	c.text = message
	c.gesture = gesture_kind
	c.name = "CoachMark"
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.z_index = 60
	parent.add_child(c)
	return c


func _ready() -> void:
	for i in 4:
		var d := ColorRect.new()
		d.color = Color(0.02, 0.01, 0.04, 0.72)
		d.mouse_filter = Control.MOUSE_FILTER_STOP if blocking else Control.MOUSE_FILTER_IGNORE
		if not blocking:
			d.color.a = 0.45
		add_child(d)
		_dims.append(d)
	_border = Panel.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0, 0, 0, 0)
	sb.border_color = UIKit.GOLD
	sb.set_border_width_all(6)
	sb.anti_aliasing = false
	_border.add_theme_stylebox_override("panel", sb)
	_border.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_border)
	_hand = UIKit.icon("res://assets/icons/%s.png" % {"tap": "hand", "up": "gesture_up", "down": "gesture_down"}.get(gesture, "hand"), 96)
	add_child(_hand)
	_plate = PanelFrame.make("plank", 16)
	_plate.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var l := UIKit.label(text, UIKit.T_NAME, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_CENTER, 8)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = 820
	_plate.add_child(l)
	add_child(_plate)
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 0.2)
	AudioManager.play_sfx("menu_open", 0.0, -6.0)


func _process(delta: float) -> void:
	if not is_instance_valid(target) or not target.is_visible_in_tree():
		finish()
		return
	_t += delta
	var r := target.get_global_rect().grow(8)
	var vp := get_viewport_rect().size
	_dims[0].position = Vector2.ZERO
	_dims[0].size = Vector2(vp.x, max(r.position.y, 0))
	_dims[1].position = Vector2(0, r.end.y)
	_dims[1].size = Vector2(vp.x, max(vp.y - r.end.y, 0))
	_dims[2].position = Vector2(0, r.position.y)
	_dims[2].size = Vector2(max(r.position.x, 0), r.size.y)
	_dims[3].position = Vector2(r.end.x, r.position.y)
	_dims[3].size = Vector2(max(vp.x - r.end.x, 0), r.size.y)
	_border.position = r.position
	_border.size = r.size
	_border.modulate = Color(1, 1, 1, 0.6 + 0.4 * sin(_t * 6.0))
	# instruction sits above the highlight (or below when there is no room)
	var above := r.position.y - _plate.size.y - 40 > 260.0
	_plate.position = Vector2((vp.x - _plate.size.x) / 2.0, r.position.y - _plate.size.y - 30 if above else r.end.y + 30)
	var c := r.get_center()
	match gesture:
		"up":
			var k := fmod(_t, 1.0)
			_hand.position = c + Vector2(-48, 40 - k * 140)
			_hand.modulate.a = 1.0 - k * 0.7
		"down":
			var k2 := fmod(_t, 1.0)
			_hand.position = c + Vector2(-48, -120 + k2 * 140)
			_hand.modulate.a = 1.0 - k2 * 0.7
		_:
			_hand.position = c + Vector2(10, 10 + abs(sin(_t * 5.0)) * -24)


func finish() -> void:
	if _done:
		return
	_done = true
	set_process(false)
	for d in _dims:
		d.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.0, 0.15)
	tw.tween_callback(func():
		finished.emit()
		queue_free())
