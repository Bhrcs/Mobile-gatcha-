class_name FantasyButton
extends Button
## Raised metal-and-stone button used everywhere in Cinderbound.
## Styles: "ember" (primary), "steel" (secondary), "gold" (special), "stone" (quiet).
## Gives clear feedback on every press: pressed art (face drops, shadow vanishes),
## a quick squash animation and a click sound. Hover brightens on PC.

var style_name := "steel"
## Minimum time between two accepted presses (rapid-tap / double-tap safety).
## Set to 0 for buttons meant to be tapped quickly (+1 / -1 steppers).
var press_cooldown := 0.25
var selected := false
var _tween: Tween
var _last_press_ms := -100000


static func make(text_value: String, style := "steel", min_size := Vector2(320, 110), icon_path := "") -> FantasyButton:
	var b := FantasyButton.new()
	b.text = text_value
	b.style_name = style
	b.custom_minimum_size = min_size
	if not icon_path.is_empty():
		b.icon = load(icon_path)
		b.expand_icon = true
		b.add_theme_constant_override("icon_max_width", 48)
	return b


func _ready() -> void:
	focus_mode = Control.FOCUS_NONE
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	apply_style(style_name)
	add_theme_font_size_override("font_size", get_theme_font_size("font_size") if has_theme_font_size_override("font_size") else 40)
	button_down.connect(_on_down)
	button_up.connect(_on_up)
	mouse_entered.connect(func():
		if not disabled:
			AudioManager.play_sfx("hover", 0.02, -12.0))
	pressed.connect(func():
		_last_press_ms = Time.get_ticks_msec()
		AudioManager.play_sfx("click", 0.03))
	resized.connect(func(): pivot_offset = size / 2.0)
	pivot_offset = size / 2.0


## Swallows presses that arrive faster than press_cooldown (before Button sees them).
func _gui_input(event: InputEvent) -> void:
	if press_cooldown <= 0.0:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		if Time.get_ticks_msec() - _last_press_ms < int(press_cooldown * 1000.0):
			accept_event()


## Selected state (tabs, chosen options): lit face and gold text.
func set_selected(on: bool) -> void:
	selected = on
	apply_style(style_name)
	if on:
		add_theme_stylebox_override("normal", get_theme_stylebox("hover"))
		add_theme_color_override("font_color", UIKit.GOLD)
	else:
		remove_theme_color_override("font_color")


func apply_style(style: String) -> void:
	style_name = style
	var normal := _sb("v2_btn_%s.png" % style, 24, 13)
	var pressed_sb := _sb("v2_btn_%s_p.png" % style, 30, 7)
	var hover := normal.duplicate()
	hover.modulate_color = Color(1.18, 1.12, 1.06)
	var off := _sb("v2_btn_off.png", 24, 13)
	add_theme_stylebox_override("normal", normal)
	add_theme_stylebox_override("hover", hover)
	add_theme_stylebox_override("pressed", pressed_sb)
	add_theme_stylebox_override("hover_pressed", pressed_sb)
	add_theme_stylebox_override("disabled", off)
	add_theme_stylebox_override("focus", StyleBoxEmpty.new())


func _sb(file: String, top: int, bottom: int) -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = load("res://assets/ui/" + file)
	sb.texture_margin_left = 12
	sb.texture_margin_right = 12
	sb.texture_margin_top = 12
	sb.texture_margin_bottom = 18
	sb.content_margin_left = 30
	sb.content_margin_right = 30
	sb.content_margin_top = top
	sb.content_margin_bottom = bottom
	return sb


func _on_down() -> void:
	if disabled:
		return
	if _tween:
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(self, "scale", Vector2(0.96, 0.94), 0.05)


func _on_up() -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(self, "scale", Vector2(1.03, 1.03), 0.06)
	_tween.tween_property(self, "scale", Vector2.ONE, 0.08)


## Periodic light sweep across the face (used on the main call-to-action buttons).
func add_shine(period: float = 2.8) -> void:
	clip_contents = true
	var band := Polygon2D.new()
	band.color = Color(1, 0.95, 0.8, 0.28)
	band.polygon = PackedVector2Array([Vector2(0, 0), Vector2(36, 0), Vector2(-24, 400), Vector2(-60, 400)])
	band.position = Vector2(-120, -40)
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	band.material = mat
	add_child(band)
	var tw := band.create_tween().set_loops()
	tw.tween_interval(period)
	tw.tween_callback(func(): band.position.x = -120.0)
	tw.tween_property(band, "position:x", 1400.0, 0.7).set_trans(Tween.TRANS_SINE)
