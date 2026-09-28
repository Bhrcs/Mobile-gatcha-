class_name BattleCamera
extends Camera2D
## Restrained combat camera: small attack zoom, burst zoom, character focus
## and short screen shake. Movements are capped so the fight stays readable.

const MAX_ZOOM := 1.22
const MAX_OFFSET := 220.0

var base_position := Vector2(540, 960)
var _shake_strength := 0.0
var _shake_time := 0.0
var _shake_duration := 0.0
var _move_tween: Tween


func _ready() -> void:
	position = base_position
	zoom = Vector2.ONE


func _process(delta: float) -> void:
	if _shake_time > 0.0:
		_shake_time -= delta
		var k: float = _shake_time / max(_shake_duration, 0.001)
		offset = Vector2(randf_range(-1, 1), randf_range(-1, 1)) * _shake_strength * k
		if _shake_time <= 0.0:
			offset = Vector2.ZERO


## strength in pixels (kept small); respects the Screen Shake setting.
func shake(strength: float = 10.0, duration: float = 0.18) -> void:
	if not bool(GameManager.settings.get("screen_shake", true)):
		return
	_shake_strength = min(strength, 24.0)
	_shake_duration = duration
	_shake_time = duration


## Zoom slightly toward a world point (clamped so the whole arena stays in view).
func focus(point: Vector2, zoom_amount: float, time: float = 0.25) -> Tween:
	var z := clampf(zoom_amount, 1.0, MAX_ZOOM)
	var target := base_position + (point - base_position).limit_length(MAX_OFFSET) * (z - 1.0) * 2.5
	if _move_tween:
		_move_tween.kill()
	_move_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_move_tween.tween_property(self, "zoom", Vector2(z, z), time)
	_move_tween.tween_property(self, "position", target, time)
	return _move_tween


func reset(time: float = 0.3) -> Tween:
	if _move_tween:
		_move_tween.kill()
	_move_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_move_tween.tween_property(self, "zoom", Vector2.ONE, time)
	_move_tween.tween_property(self, "position", base_position, time)
	return _move_tween
