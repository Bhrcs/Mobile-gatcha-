class_name CinderTabs
extends HBoxContainer
## Reusable tab row (CinderTabs). Tabs are named "Tab_<LABEL>" and can carry a
## red badge. The selected tab uses the lit tab plate and gold text.
## Changing tab plays the select sound and calls on_change(index).

signal tab_changed(index: int)

var labels: Array = []
var selected := 0
var tabs: Array = []
var _cb: Callable


static func make(tab_labels: Array, current := 0, on_change: Callable = Callable(), height := 96) -> CinderTabs:
	var t := CinderTabs.new()
	t.name = "Tabs"
	t.labels = tab_labels
	t.selected = current
	t._cb = on_change
	t.add_theme_constant_override("separation", UIKit.SP_S)
	for i in tab_labels.size():
		var b := Button.new()
		b.name = "Tab_" + String(tab_labels[i]).to_upper().replace(" ", "_")
		b.text = String(tab_labels[i])
		b.custom_minimum_size = Vector2(0, height)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.focus_mode = Control.FOCUS_NONE
		b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		b.clip_text = true
		b.add_theme_font_size_override("font_size", UIKit.T_BODY if height >= 80 else UIKit.T_SMALL)
		b.add_theme_constant_override("outline_size", 8)
		UIKit.hook_sounds(b)
		var idx := i
		b.pressed.connect(func(): t.select(idx))
		t.add_child(b)
		t.tabs.append(b)
	t._style()
	return t


func select(i: int, emit := true) -> void:
	if i == selected and emit:
		return
	selected = i
	_style()
	var b: Button = tabs[i]
	b.pivot_offset = b.size / 2.0
	b.scale = Vector2(0.95, 0.95)
	create_tween().tween_property(b, "scale", Vector2.ONE, 0.12).set_trans(Tween.TRANS_QUAD)
	if emit:
		tab_changed.emit(i)
		if _cb.is_valid():
			_cb.call(i)


func set_badge(i: int, text := "!") -> void:
	var b: Button = tabs[i]
	var old := b.get_node_or_null("Badge")
	if old:
		old.queue_free()
	if not text.is_empty():
		UIKit.badge(b, text).name = "Badge"


func _style() -> void:
	for i in tabs.size():
		var b: Button = tabs[i]
		var on := i == selected
		var sb := UIKit.tex_style("p5_tab_on.png" if on else "p5_tab.png", 12, 10, false)
		sb.content_margin_top = 6 if on else 12
		var hover := sb.duplicate()
		hover.modulate_color = Color(1.15, 1.1, 1.05)
		for st in ["normal", "pressed", "hover_pressed", "disabled"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_stylebox_override("hover", hover)
		b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
		b.add_theme_color_override("font_color", UIKit.GOLD if on else UIKit.MUTED)
		b.add_theme_color_override("font_hover_color", UIKit.GOLD if on else Color.WHITE)
		b.add_theme_color_override("font_pressed_color", UIKit.GOLD)
