class_name CinderSwitch
extends Button
## ON / OFF switch (CinderToggle). Shows the pixel switch plus an ON/OFF word so
## the state never depends on colour alone. Named "Toggle_<key>" by the caller.

signal toggled_to(on: bool)

var on := false
static var _tex := {}


static func make(start_on: bool, on_toggle: Callable = Callable()) -> CinderSwitch:
	var s := CinderSwitch.new()
	s.on = start_on
	s.custom_minimum_size = Vector2(250, UIKit.TOUCH_MIN)
	s.focus_mode = Control.FOCUS_NONE
	s.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	s.expand_icon = false
	s.icon_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	s.alignment = HORIZONTAL_ALIGNMENT_LEFT
	s.add_theme_font_size_override("font_size", UIKit.T_BODY)
	s.add_theme_constant_override("outline_size", 8)
	s.add_theme_constant_override("h_separation", UIKit.SP_M)
	for st in ["normal", "hover", "pressed", "hover_pressed", "focus", "disabled"]:
		s.add_theme_stylebox_override(st, StyleBoxEmpty.new())
	if on_toggle.is_valid():
		s.toggled_to.connect(on_toggle)
	s.pressed.connect(func():
		s.set_on(not s.on)
		UIManager.sfx("toggle", -4.0)
		s.toggled_to.emit(s.on))
	s._refresh()
	return s


func set_on(v: bool) -> void:
	on = v
	_refresh()


func _refresh() -> void:
	icon = _art(on)
	text = "ON" if on else "OFF"
	add_theme_color_override("font_color", UIKit.GOOD if on else UIKit.MUTED)
	add_theme_color_override("font_hover_color", UIKit.GOOD if on else UIKit.TEXT)
	add_theme_color_override("font_pressed_color", UIKit.GOOD if on else UIKit.MUTED)


## The switch art at 2x (nearest-neighbour), built once.
static func _art(state: bool) -> Texture2D:
	if not _tex.has(state):
		var tex: Texture2D = load("res://assets/ui/p5_switch_on.png" if state else "res://assets/ui/p5_switch_off.png")
		var img := tex.get_image()
		img.resize(tex.get_width() * 2, tex.get_height() * 2, Image.INTERPOLATE_NEAREST)
		_tex[state] = ImageTexture.create_from_image(img)
	return _tex[state]
