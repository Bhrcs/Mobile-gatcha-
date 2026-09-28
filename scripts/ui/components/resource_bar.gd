class_name ResourceBar
extends Control
## Animated bar with a "lost section" that lingers briefly before catching up.
## kind: hp (auto green/yellow/red thresholds), burst, enemy, boss, xp, stat.
## Burst bars switch to the gold "ready" fill when full.

signal filled

@export var kind := "hp"
var max_value := 100.0
var value := 100.0
var _shown := 1.0
var _lag := 1.0
var frame_rect: NinePatchRect
var lag_rect: TextureRect
var fill_rect: TextureRect
var _tw: Tween
var _lag_tw: Tween


static func make(k := "hp", height := 30) -> ResourceBar:
	var b := ResourceBar.new()
	b.kind = k
	b.custom_minimum_size = Vector2(80, height)
	return b


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame_rect = NinePatchRect.new()
	frame_rect.texture = load("res://assets/ui/v2_bar_boss.png" if kind == "boss" else "res://assets/ui/v2_bar.png")
	frame_rect.patch_margin_left = 6
	frame_rect.patch_margin_right = 6
	frame_rect.patch_margin_top = 6
	frame_rect.patch_margin_bottom = 6
	frame_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	frame_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(frame_rect)
	lag_rect = _fill_rect("lag")
	fill_rect = _fill_rect(_fill_name())
	resized.connect(_layout)
	_layout()


func _fill_rect(fill_name: String) -> TextureRect:
	var r := TextureRect.new()
	r.texture = load("res://assets/ui/v2_fill_%s.png" % fill_name)
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_SCALE
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(r)
	return r


func _fill_name() -> String:
	match kind:
		"hp":
			if _shown > 0.5:
				return "hp_high"
			return "hp_mid" if _shown > 0.25 else "hp_low"
		"burst":
			return "burst_ready" if _shown >= 0.999 else "burst"
		_:
			return kind


func _layout() -> void:
	if fill_rect == null:
		return
	var inner := Rect2(Vector2(6, 6), size - Vector2(12, 12))
	fill_rect.position = inner.position
	fill_rect.size = Vector2(max(inner.size.x * _shown, 0.0), inner.size.y)
	lag_rect.position = inner.position
	lag_rect.size = Vector2(max(inner.size.x * max(_lag, _shown), 0.0), inner.size.y)
	fill_rect.visible = _shown > 0.001
	lag_rect.visible = _lag > _shown + 0.001


## Sets the bar. Decreases show the lost section briefly; increases grow smoothly.
func set_values(current: float, maximum: float, animate := true) -> void:
	var was_full := _shown >= 0.999
	max_value = max(maximum, 0.0001)
	value = clampf(current, 0.0, max_value)
	var target := value / max_value
	if not is_inside_tree() or not animate:
		_shown = target
		_lag = target
		_refresh()
		return
	if _tw:
		_tw.kill()
	if _lag_tw:
		_lag_tw.kill()
	if target < _shown:
		_lag = max(_lag, _shown)
		_shown = target
		_refresh()
		_lag_tw = create_tween()
		_lag_tw.tween_interval(0.25)
		_lag_tw.tween_method(func(v): _lag = v; _layout(), _lag, target, 0.3)
	else:
		_tw = create_tween()
		_tw.tween_method(func(v): _shown = v; _lag = v; _refresh(), _shown, target, 0.25)
	if kind == "burst" and target >= 0.999 and not was_full:
		filled.emit()


func _refresh() -> void:
	if fill_rect:
		fill_rect.texture = load("res://assets/ui/v2_fill_%s.png" % _fill_name())
	_layout()


func ratio() -> float:
	return value / max_value
