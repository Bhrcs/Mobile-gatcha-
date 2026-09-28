class_name StageNode
extends TextureButton
## Map node: locked / open / cleared / boss. Available nodes pulse gently.

var stage_id := ""
var state := "locked"
var _tw: Tween


static func make(sid: String, st: String, px: int) -> StageNode:
	var n := StageNode.new()
	n.stage_id = sid
	n.state = st
	n.texture_normal = load("res://assets/ui/v2_node_%s.png" % st)
	n.ignore_texture_size = true
	n.stretch_mode = TextureButton.STRETCH_KEEP_ASPECT_CENTERED
	n.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	n.custom_minimum_size = Vector2(px, px)
	n.size = Vector2(px, px)
	n.pivot_offset = Vector2(px, px) / 2.0
	n.focus_mode = Control.FOCUS_NONE
	n.name = "Node_" + sid
	return n


func _ready() -> void:
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button_down.connect(func(): scale = Vector2(0.9, 0.9))
	button_up.connect(func(): scale = Vector2.ONE)
	if state == "open" or state == "boss":
		modulate = Color.WHITE
	elif state == "locked":
		modulate = Color(0.8, 0.8, 0.85)


func set_selected(on: bool) -> void:
	if _tw:
		_tw.kill()
	scale = Vector2.ONE
	if on:
		_tw = create_tween().set_loops()
		_tw.tween_property(self, "scale", Vector2(1.22, 1.22), 0.45).set_trans(Tween.TRANS_SINE)
		_tw.tween_property(self, "scale", Vector2.ONE, 0.45).set_trans(Tween.TRANS_SINE)
