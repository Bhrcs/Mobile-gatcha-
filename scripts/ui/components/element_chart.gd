class_name ElementChart
extends Control
## Element triangle: each arrow points from the stronger element to the one it
## beats. Elements are shown by symbol (flame / drop / leaf) and name, not by
## colour alone. Used by Help, the battle pause menu and the squad screen.

const ORDER := ["fire", "nature", "water"]    # fire beats nature beats water beats fire
const SIZE := Vector2(620, 520)

var _pos := {}


static func make() -> ElementChart:
	var c := ElementChart.new()
	c.name = "ElementChart"
	c.custom_minimum_size = SIZE
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


## Popup with the chart and a two-line explanation.
static func popup(parent: Node) -> FantasyPopup:
	var p := FantasyPopup.open(parent, "ELEMENTS", 900)
	p.name = "ElementPopup"
	var chart := ElementChart.make()
	chart.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(chart)
	for line in explanation():
		var l := UIKit.wrap_label(line, UIKit.T_BODY)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.custom_minimum_size.x = 820
		p.content.add_child(l)
	var ok := UIKit.btn("OK", "primary", Vector2(300, 110))
	ok.name = "ElementOK"
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	ok.pressed.connect(p.close)
	p.content.add_child(ok)
	p.default_action = p.close
	p.tap_outside_closes = true
	return p


static func explanation() -> Array:
	var strong := int(round((float(Database.element_config.get("strong_multiplier", 1.25)) - 1.0) * 100.0))
	var weak := int(round((1.0 - float(Database.element_config.get("weak_multiplier", 0.75))) * 100.0))
	return ["Attacking the element you beat deals +%d%% damage." % strong,
			"Attacking the element that beats you deals -%d%% damage." % weak]


func _ready() -> void:
	var c := SIZE / 2.0 + Vector2(0, 20)
	var r := 190.0
	_pos = {
		"fire": c + Vector2(0, -r),
		"nature": c + Vector2(r * 0.87, r * 0.5),
		"water": c + Vector2(-r * 0.87, r * 0.5),
	}
	for el in ORDER:
		var box := UIKit.vbox(2)
		box.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var o := UIKit.orb(el, 96)
		o.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		box.add_child(o)
		box.add_child(UIKit.label(Database.element_name(el).to_upper(), UIKit.T_BODY, Database.element_color(el).lightened(0.3),
				HORIZONTAL_ALIGNMENT_CENTER, 6))
		add_child(box)
		box.size = box.get_combined_minimum_size()
		box.position = _pos[el] - Vector2(box.size.x / 2.0, 52)
	var mid := UIKit.label("BEATS", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 5)
	add_child(mid)
	mid.size = mid.get_combined_minimum_size()
	mid.position = c - mid.size / 2.0 + Vector2(0, 10)
	queue_redraw()


func _draw() -> void:
	if _pos.is_empty():
		return
	for i in ORDER.size():
		var a: Vector2 = _pos[ORDER[i]]
		var b: Vector2 = _pos[ORDER[(i + 1) % ORDER.size()]]
		var dir := (b - a).normalized()
		var s := a + dir * 92.0
		var e := b - dir * 92.0
		var col := Database.element_color(ORDER[i]).lightened(0.2)
		draw_line(s, e, Color(0, 0, 0, 0.6), 14.0)
		draw_line(s, e, col, 8.0)
		var n := Vector2(-dir.y, dir.x)
		var head := PackedVector2Array([e + dir * 18.0, e - dir * 22.0 + n * 20.0, e - dir * 22.0 - n * 20.0])
		draw_colored_polygon(head, col)
