class_name SpriteFactory
extends RefCounted
## Builds SpriteFrames from the sprite sheets + JSON metadata written by
## tools/make_assets.py (one row per animation). Results are cached, so many
## units of the same species share one SpriteFrames resource.

static var _frames_cache: Dictionary = {}
static var _effect_cache: Dictionary = {}
static var _effect_meta: Dictionary = {}


## sprite_def: {"sheet": path, "meta": path}
static func unit_frames(sprite_def: Dictionary) -> SpriteFrames:
	var sheet_path: String = sprite_def.get("sheet", "")
	if _frames_cache.has(sheet_path):
		return _frames_cache[sheet_path]
	var frames := SpriteFrames.new()
	if frames.has_animation("default"):
		frames.remove_animation("default")
	var tex := Database.load_texture(sheet_path)
	var meta := Database.get_sprite_meta(sprite_def.get("meta", ""))
	if tex == null or meta.is_empty():
		push_error("Missing sprite sheet/meta: " + sheet_path)
		return _placeholder_frames()
	var fw := int(meta["frame_size"][0])
	var fh := int(meta["frame_size"][1])
	for anim_name in meta.get("animations", {}).keys():
		var a: Dictionary = meta["animations"][anim_name]
		frames.add_animation(anim_name)
		frames.set_animation_speed(anim_name, float(a.get("fps", 8)))
		frames.set_animation_loop(anim_name, bool(a.get("loop", false)))
		for i in int(a.get("frames", 1)):
			var at := AtlasTexture.new()
			at.atlas = tex
			at.region = Rect2(i * fw, int(a["row"]) * fh, fw, fh)
			frames.add_frame(anim_name, at)
	_frames_cache[sheet_path] = frames
	return frames


static func frame_size(sprite_def: Dictionary) -> Vector2:
	var meta := Database.get_sprite_meta(sprite_def.get("meta", ""))
	if meta.is_empty():
		return Vector2(48, 48)
	return Vector2(meta["frame_size"][0], meta["frame_size"][1])


## Seconds from animation start until `frame` is shown.
static func frame_time(frames: SpriteFrames, anim: String, frame: int) -> float:
	if not frames.has_animation(anim):
		return 0.0
	return float(frame) / max(frames.get_animation_speed(anim), 1.0)


static func anim_length(frames: SpriteFrames, anim: String) -> float:
	if not frames.has_animation(anim):
		return 0.0
	return float(frames.get_frame_count(anim)) / max(frames.get_animation_speed(anim), 1.0)


# ------------------------------------------------------------------ effects
static func effect_frames(effect_name: String) -> SpriteFrames:
	if _effect_cache.has(effect_name):
		return _effect_cache[effect_name]
	if _effect_meta.is_empty():
		_effect_meta = Database._read_json("res://assets/effects/effects.json")
	var meta: Dictionary = _effect_meta.get(effect_name, {})
	var tex := Database.load_texture("res://assets/effects/%s.png" % effect_name)
	var frames := SpriteFrames.new()
	if tex == null or meta.is_empty():
		_effect_cache[effect_name] = frames
		return frames
	var fw := int(meta["frame_size"][0])
	var fh := int(meta["frame_size"][1])
	frames.set_animation_speed("default", float(meta.get("fps", 12)))
	frames.set_animation_loop("default", false)
	for i in int(meta["frames"]):
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(i * fw, 0, fw, fh)
		frames.add_frame("default", at)
	_effect_cache[effect_name] = frames
	return frames


static func _placeholder_frames() -> SpriteFrames:
	var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
	img.fill(Color(1, 0, 1))
	var frames := SpriteFrames.new()
	var t := ImageTexture.create_from_image(img)
	for anim in ["idle", "attack", "hit", "victory", "ko", "burst", "death"]:
		if not frames.has_animation(anim):
			frames.add_animation(anim)
		frames.add_frame(anim, t)
	return frames
