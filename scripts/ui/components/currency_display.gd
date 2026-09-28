class_name CurrencyDisplay
extends PanelFrame
## Compact resource plate: icon + animated counter. Gold binds to GameManager.

var _label: Label
var _shown := 0
var _tw: Tween


static func gold() -> CurrencyDisplay:
	var d := CurrencyDisplay.new()
	d.set_variant("inset", 10)
	d.custom_minimum_size = Vector2(300, 0)
	return d


func _ready() -> void:
	var h := UIKit.hbox(10)
	add_child(h)
	h.add_child(UIKit.icon("res://assets/icons/gold.png", 48))
	_label = UIKit.label("", 40, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 6)
	_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(_label)
	_shown = GameManager.gold()
	_label.text = UIKit.format_number(_shown)
	GameManager.gold_changed.connect(_on_gold)


func _exit_tree() -> void:
	if GameManager.gold_changed.is_connected(_on_gold):
		GameManager.gold_changed.disconnect(_on_gold)


func _on_gold(v: int) -> void:
	if _tw:
		_tw.kill()
	_tw = create_tween()
	_tw.tween_method(func(x): _label.text = UIKit.format_number(int(x)), float(_shown), float(v), 0.4)
	_shown = v
