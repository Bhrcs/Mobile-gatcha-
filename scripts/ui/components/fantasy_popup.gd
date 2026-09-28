class_name FantasyPopup
extends Control
## Modal popup (Cinder popup rules): dims the screen, the framed panel fades in
## with a slight scale (no bounce), closes with a short fade.
## `content` is a VBoxContainer to fill.
## Registers with UIManager so Esc closes the top popup and Enter triggers
## `default_action` (when a popup sets one).

signal closed

var content: VBoxContainer
var panel: PanelFrame
var _closing := false
## Called by Esc / the dim backdrop. Defaults to close().
var cancel_action: Callable
## Called by Enter. Unset = Enter does nothing.
var default_action: Callable
## Tapping the dim area outside the panel closes (via cancel()).
var tap_outside_closes := false


static func open(parent: Node, title := "", width := 940, variant := "panel") -> FantasyPopup:
	var p := FantasyPopup.new()
	p.name = "Popup"
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	p.mouse_filter = Control.MOUSE_FILTER_STOP
	p.z_index = 50
	var dim := ColorRect.new()
	dim.name = "Dim"
	dim.color = Color(0.02, 0.01, 0.04, 0.78)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.gui_input.connect(p._on_dim_input)
	p.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_PASS
	p.add_child(center)
	p.panel = PanelFrame.make(variant)
	p.panel.custom_minimum_size.x = width
	center.add_child(p.panel)
	p.content = UIKit.vbox(24)
	p.panel.add_child(p.content)
	if not title.is_empty():
		p.content.add_child(UIKit.title_plate(title))
	parent.add_child(p)
	UIManager.register_popup(p)
	AudioManager.play_sfx("menu_open", 0.02, -3.0)
	p.panel.pivot_offset = Vector2(width / 2.0, 200)
	p.panel.scale = Vector2(0.94, 0.94)
	p.panel.modulate.a = 0.0
	dim.modulate.a = 0.0
	var tw := p.create_tween().set_parallel(true)
	tw.tween_property(p.panel, "scale", Vector2.ONE, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(p.panel, "modulate:a", 1.0, 0.12)
	tw.tween_property(dim, "modulate:a", 1.0, 0.12)
	# keep the pivot centred once the real height is known
	p.panel.resized.connect(func(): p.panel.pivot_offset = p.panel.size / 2.0)
	return p


func _on_dim_input(e: InputEvent) -> void:
	if tap_outside_closes and e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		cancel()


## Esc / back behaviour.
func cancel() -> void:
	if _closing:
		return
	if cancel_action.is_valid():
		cancel_action.call()
	else:
		close()


## Enter behaviour.
func confirm_default() -> void:
	if _closing:
		return
	if default_action.is_valid():
		default_action.call()


func close() -> void:
	if _closing:
		return
	_closing = true
	mouse_filter = Control.MOUSE_FILTER_STOP
	AudioManager.play_sfx("menu_close", 0.02, -6.0)
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.0, 0.1)
	tw.tween_callback(func():
		closed.emit()
		queue_free())
