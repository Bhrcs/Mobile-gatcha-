class_name Toast
extends PanelFrame
## Short floating notice near the top of the screen.


static func show_text(parent: Node, text: String, color: Color = UIKit.TEXT) -> void:
	var t := Toast.new()
	t.set_variant("inset", 16)
	t.add_child(UIKit.label(text, 30, color, HORIZONTAL_ALIGNMENT_CENTER))
	t.z_index = 60
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(t)
	t._run()


func _run() -> void:
	await get_tree().process_frame
	if not is_inside_tree():
		return
	position = Vector2((get_viewport_rect().size.x - size.x) / 2.0, 260 + UIKit.safe_top())
	modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 1.0, 0.12)
	tw.tween_interval(1.4)
	tw.tween_property(self, "modulate:a", 0.0, 0.3)
	tw.tween_callback(queue_free)
