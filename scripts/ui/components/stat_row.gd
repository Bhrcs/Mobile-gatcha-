class_name StatRow
extends HBoxContainer
## "HP  [=========     ]  934" with the bar scaled against a reference maximum.

static func make(stat_name: String, value: int, ref_max: int, color := UIKit.SKY) -> StatRow:
	var r := StatRow.new()
	r.add_theme_constant_override("separation", 14)
	var n := UIKit.label(stat_name, 30, color, HORIZONTAL_ALIGNMENT_LEFT, 6)
	n.custom_minimum_size.x = 90
	r.add_child(n)
	var bar := ResourceBar.make("stat", 30)
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	r.add_child(bar)
	bar.ready.connect(func(): bar.set_values(value, max(ref_max, 1), false))
	var v := UIKit.label(str(value), 40, UIKit.TEXT, HORIZONTAL_ALIGNMENT_RIGHT, 6)
	v.custom_minimum_size.x = 120
	r.add_child(v)
	return r
