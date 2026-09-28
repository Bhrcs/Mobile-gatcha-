class_name UnitSpriteDisplay
extends Control
## Shows an animated battle sprite inside UI layouts (feet at the bottom centre).

var sprite: AnimatedSprite2D


func setup(sprite_def: Dictionary, pixel_scale: float = 4.0, face_left := false, anim := "idle") -> UnitSpriteDisplay:
	var fs := SpriteFactory.frame_size(sprite_def)
	custom_minimum_size = Vector2(fs.x * pixel_scale * 0.7, fs.y * pixel_scale * 0.8)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = SpriteFactory.unit_frames(sprite_def)
	sprite.scale = Vector2(pixel_scale, pixel_scale)
	sprite.centered = true
	sprite.offset = Vector2(0, -(fs.y - 4 - fs.y / 2.0))
	sprite.flip_h = face_left
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(sprite)
	sprite.play(anim)
	resized.connect(_place)
	_place()
	return self


func _ready() -> void:
	_place.call_deferred()


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_place()


## Feet at the bottom centre (falls back to the minimum size before layout).
func _place() -> void:
	if sprite:
		var s := Vector2(max(size.x, custom_minimum_size.x), max(size.y, custom_minimum_size.y))
		sprite.position = Vector2(s.x / 2.0, s.y)


func play(anim: String) -> void:
	if sprite and sprite.sprite_frames.has_animation(anim):
		sprite.play(anim)
