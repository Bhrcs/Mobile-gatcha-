class_name BattleUnitView
extends Node2D
## Visual representation of one Combatant on the battlefield: animated sprite,
## shadow, hit flash, overhead HP bar (smoothly draining), status icons,
## target cursor and movement helpers. Contains no combat rules.

const SHADER := preload("res://assets/shaders/unit.gdshader")
const BAR_W := 150.0

var combatant: Combatant
var home_pos := Vector2.ZERO
var unit_scale := 5.0
var frames: SpriteFrames
var sprite: AnimatedSprite2D
var shadow: Sprite2D
var cursor: Sprite2D
var target_ring: AnimatedSprite2D
var select_ring: Sprite2D
var guard_icon: Sprite2D
var overhead: Node2D
var hp_bar: ResourceBar
var name_label: Label
var status_row: HBoxContainer
var aura: CPUParticles2D
var frame_size := Vector2(48, 48)
var _flash_tween: Tween
var _dead_visual := false
var _cursor_time := 0.0

static var _shadow_tex: Texture2D
static var _ring_tex: Texture2D
static var _target_frames: SpriteFrames


func setup(c: Combatant, pos: Vector2, scale_mult := 1.0) -> void:
	combatant = c
	home_pos = pos
	position = pos
	var sprite_def: Dictionary = c.def.get("sprite", {})
	unit_scale = float(sprite_def.get("scale", 5)) * scale_mult
	frames = SpriteFactory.unit_frames(sprite_def)
	frame_size = SpriteFactory.frame_size(sprite_def)
	_build()
	c.hp_changed.connect(_on_hp_changed)
	c.statuses_changed.connect(_refresh_statuses)
	play_idle()


func _build() -> void:
	shadow = Sprite2D.new()
	shadow.texture = _get_shadow_tex()
	shadow.scale = Vector2(unit_scale, unit_scale) * (frame_size.x / 48.0)
	shadow.modulate = Color(0, 0, 0, 0.35)
	add_child(shadow)

	select_ring = Sprite2D.new()
	select_ring.texture = _get_ring_tex()
	select_ring.scale = shadow.scale
	select_ring.visible = false
	add_child(select_ring)

	# animated ember sigil on the ground under the current target
	target_ring = AnimatedSprite2D.new()
	target_ring.sprite_frames = _get_target_frames()
	var k := frame_size.x / 48.0
	target_ring.scale = Vector2(6.0, 2.4) * k
	target_ring.position = Vector2(0, 2)
	target_ring.visible = false
	add_child(target_ring)

	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = frames
	sprite.scale = Vector2(unit_scale, unit_scale)
	sprite.offset = Vector2(0, -(frame_size.y - 4 - frame_size.y / 2.0))
	sprite.flip_h = combatant.is_player    # heroes are drawn facing right; players face left
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	if combatant.def.has("tint"):
		var tint := Color(combatant.def["tint"])
		# elites keep most of their colours (gold sheen); tower guardians take the full tint
		mat.set_shader_parameter("tint", Color.WHITE.lerp(tint, 0.45) if combatant.is_elite else tint)
	sprite.material = mat
	sprite.animation_finished.connect(_on_anim_finished)
	add_child(sprite)

	overhead = Node2D.new()
	overhead.position = Vector2(0, -visual_height() - 34)
	add_child(overhead)
	if not combatant.is_player:
		# slim overhead bar; the enemy plates in the HUD carry the full details
		hp_bar = ResourceBar.make("boss" if is_boss() else "enemy", 24)
		hp_bar.position = Vector2(-BAR_W / 2, 0)
		hp_bar.size = Vector2(BAR_W, 24)
		overhead.add_child(hp_bar)
		hp_bar.ready.connect(func(): hp_bar.set_values(combatant.hp, combatant.max_hp, false))
	status_row = UIKit.hbox(2)
	status_row.position = Vector2(-BAR_W / 2, 28)
	overhead.add_child(status_row)

	guard_icon = Sprite2D.new()
	guard_icon.texture = load("res://assets/icons/shield.png")
	guard_icon.scale = Vector2(4, 4)
	guard_icon.position = Vector2(-60 if combatant.is_player else 60, -visual_height() * 0.55)
	guard_icon.visible = false
	add_child(guard_icon)

	cursor = Sprite2D.new()
	cursor.texture = load("res://assets/ui/v2_chevron.png")
	cursor.scale = Vector2(5, 5)
	cursor.position = Vector2(0, -visual_height() - 100)
	cursor.visible = false
	add_child(cursor)
	# names, HP and statuses live in the HUD plates / cards; keep the field clean
	overhead.visible = false
	if is_boss():
		_add_boss_aura()
	elif combatant.is_elite:
		_add_boss_aura(Color("#ffe07a"), Color("#ffb03a"), 8)


func is_boss() -> bool:
	return bool(combatant.def.get("boss", false))


## Slow drifting spores and embers around an Ancient foe.
func _add_boss_aura(c0 := Color("#c8ff9a"), c1 := Color("#ffb04a"), amount := 16) -> void:
	aura = CPUParticles2D.new()
	aura.amount = amount
	aura.lifetime = 2.4
	aura.preprocess = 2.4
	aura.position = Vector2(0, -visual_height() * 0.5)
	aura.emission_shape = CPUParticles2D.EMISSION_SHAPE_SPHERE
	aura.emission_sphere_radius = visual_height() * 0.6
	aura.gravity = Vector2(0, -24)
	aura.initial_velocity_max = 10
	aura.scale_amount_min = 5
	aura.scale_amount_max = 9
	var g := Gradient.new()
	g.set_color(0, c0)
	g.add_point(0.5, c1)
	g.set_color(g.get_point_count() - 1, Color(0.4, 0.8, 0.3, 0))
	aura.color_ramp = g
	aura.z_index = 1
	add_child(aura)


func _process(delta: float) -> void:
	if cursor.visible:
		_cursor_time += delta
		cursor.position.y = -visual_height() - 100 + sin(_cursor_time * 6.0) * 8.0
	if guard_icon.visible:
		guard_icon.modulate.a = 0.7 + 0.3 * sin(Time.get_ticks_msec() * 0.008)


# ------------------------------------------------------------------ geometry
## Approximate on-screen height of the character (not the whole frame).
func visual_height() -> float:
	return frame_size.y * 0.62 * unit_scale


func impact_point() -> Vector2:
	return global_position + Vector2(0, -visual_height() * 0.5)


func hit_rect() -> Rect2:
	var w := frame_size.x * 0.6 * unit_scale
	var h := visual_height() + 20
	return Rect2(global_position.x - w / 2, global_position.y - h, w, h + 20)


## Where an attacker stands to strike this unit in melee.
func melee_anchor(attacker_is_player: bool) -> Vector2:
	var gap := frame_size.x * 0.5 * unit_scale * 0.62 + 70
	return position + Vector2(gap if attacker_is_player else -gap, 6)


# ------------------------------------------------------------------ animation
func play_idle() -> void:
	if _dead_visual:
		return
	_play("idle")


func play_anim(anim: String, speed: float = 1.0) -> float:
	if _dead_visual:
		return 0.0
	_play(anim, speed)
	return SpriteFactory.anim_length(frames, resolve_anim(anim)) / speed


## Animation actually used for `anim` on this sheet (special -> attack etc.).
func resolve_anim(anim: String) -> String:
	if frames.has_animation(anim):
		return anim
	var alt: String = {"special": "attack", "guard": "hit", "death": "ko", "ko": "death"}.get(anim, "idle")
	return alt if frames.has_animation(alt) else "idle"


func _play(anim: String, speed: float = 1.0) -> void:
	anim = resolve_anim(anim)
	sprite.speed_scale = speed
	sprite.play(anim)
	sprite.frame = 0


func _on_anim_finished() -> void:
	if _dead_visual:
		return
	if sprite.animation in ["attack", "hit", "burst", "special"]:
		play_idle()


func hit_react(knock: float = 14.0) -> void:
	if not combatant.is_alive() or _dead_visual:
		return
	_play("hit")
	flash(Color.WHITE, 0.12)
	# knockback away from the attacker, then settle
	var dir := 1.0 if combatant.is_player else -1.0
	var tw := create_tween()
	tw.tween_property(sprite, "position:x", dir * knock, 0.05).set_trans(Tween.TRANS_QUAD)
	tw.tween_property(sprite, "position:x", 0.0, 0.16).set_trans(Tween.TRANS_QUAD)


## Guard stance: shield pose, blue flash and a shield marker until next turn.
func play_guard() -> void:
	if _dead_visual:
		return
	if frames.has_animation("guard"):
		_play("guard")
	flash(Color("#a8d0ff"), 0.3)
	set_guarding(true)


## Solid dark silhouette (boss entrance). Uses the flash channel of the unit shader.
func set_silhouette(on: bool, time: float = 0.0) -> void:
	var mat := sprite.material as ShaderMaterial
	if _flash_tween:
		_flash_tween.kill()
	mat.set_shader_parameter("flash_color", Color(0.04, 0.02, 0.06))
	if time <= 0.0:
		mat.set_shader_parameter("flash_amount", 1.0 if on else 0.0)
		return
	_flash_tween = create_tween()
	_flash_tween.tween_method(func(v): mat.set_shader_parameter("flash_amount", v), 1.0 if not on else 0.0,
			1.0 if on else 0.0, time)


func set_guarding(on: bool) -> void:
	guard_icon.visible = on and not _dead_visual
	if not on and sprite.animation == "guard":
		play_idle()


## Wind-up before a special attack: glow in the element colour and a small crouch.
func anticipate(color: Color, time: float = 0.3) -> void:
	if _dead_visual:
		return
	flash(color, time)
	var tw := create_tween()
	tw.tween_property(sprite, "scale", Vector2(unit_scale * 1.08, unit_scale * 0.92), time * 0.6)
	tw.tween_property(sprite, "scale", Vector2(unit_scale, unit_scale), time * 0.4)


func flash(color: Color, time: float = 0.12) -> void:
	var mat := sprite.material as ShaderMaterial
	mat.set_shader_parameter("flash_color", color)
	if _flash_tween:
		_flash_tween.kill()
	mat.set_shader_parameter("flash_amount", 0.85)
	_flash_tween = create_tween()
	_flash_tween.tween_method(func(v): mat.set_shader_parameter("flash_amount", v), 0.85, 0.0, time)


## KO / death presentation. Enemies fade away; heroes stay down.
func play_defeat() -> void:
	if _dead_visual:
		return
	_dead_visual = true
	set_targeted(false)
	set_selected(false)
	guard_icon.visible = false
	if aura:
		aura.emitting = false
	var anim := "ko" if combatant.is_player else "death"
	sprite.speed_scale = 1.0
	sprite.play(anim)
	flash(Color("#ff5a4a"), 0.25)
	if combatant.is_player:
		var tw := create_tween()
		tw.tween_interval(0.4)
		tw.tween_property(sprite, "modulate", Color(0.6, 0.55, 0.6), 0.3)
	else:
		var tw := create_tween()
		tw.tween_interval(SpriteFactory.anim_length(frames, anim))
		tw.tween_property(self, "modulate:a", 0.0, 0.3)
		tw.tween_callback(func(): visible = false)


func play_victory() -> void:
	if combatant.is_alive():
		_play("victory")


func is_dead_visual() -> bool:
	return _dead_visual


# ------------------------------------------------------------------ movement
func move_to(target: Vector2, time: float) -> Tween:
	var tw := create_tween()
	tw.tween_property(self, "position", target, time).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# small hop so movement reads as a dash, not a slide
	var hop := create_tween()
	hop.tween_property(sprite, "position:y", -18.0, time * 0.5).set_ease(Tween.EASE_OUT)
	hop.tween_property(sprite, "position:y", 0.0, time * 0.5).set_ease(Tween.EASE_IN)
	return tw


func return_home(time: float) -> Tween:
	return move_to(home_pos, time)


# ------------------------------------------------------------------ overlays
func set_targeted(on: bool) -> void:
	var show := on and not _dead_visual
	cursor.visible = show
	target_ring.visible = show
	if show:
		target_ring.play("default")
	else:
		target_ring.stop()


func set_selected(on: bool) -> void:
	select_ring.visible = on and not _dead_visual


func _on_hp_changed(current: int, maximum: int) -> void:
	if hp_bar and hp_bar.is_inside_tree():
		hp_bar.set_values(current, maximum)


var _charge_fx: CPUParticles2D
var _charge_tw: Tween


## Pulsing glow + rising sparks while an enemy charges a telegraphed attack.
func set_charging(on: bool) -> void:
	if on == (_charge_fx != null):
		return
	var mat: ShaderMaterial = sprite.material
	if on:
		_charge_fx = CPUParticles2D.new()
		_charge_fx.amount = 24
		_charge_fx.lifetime = 0.9
		_charge_fx.position = Vector2(0, -visual_height() * 0.4)
		_charge_fx.emission_shape = CPUParticles2D.EMISSION_SHAPE_SPHERE
		_charge_fx.emission_sphere_radius = visual_height() * 0.5
		_charge_fx.gravity = Vector2(0, -160)
		_charge_fx.scale_amount_min = 5
		_charge_fx.scale_amount_max = 10
		var g := Gradient.new()
		g.set_color(0, Color("#fff4a0"))
		g.set_color(g.get_point_count() - 1, Color(1.0, 0.3, 0.1, 0.0))
		_charge_fx.color_ramp = g
		_charge_fx.z_index = 2
		add_child(_charge_fx)
		mat.set_shader_parameter("flash_color", Color("#ffcf4a"))
		_charge_tw = create_tween().set_loops()
		_charge_tw.tween_method(func(v): mat.set_shader_parameter("flash_amount", v), 0.0, 0.45, 0.35)
		_charge_tw.tween_method(func(v): mat.set_shader_parameter("flash_amount", v), 0.45, 0.0, 0.35)
	else:
		_charge_fx.emitting = false
		var fx := _charge_fx
		get_tree().create_timer(1.0).timeout.connect(fx.queue_free)
		_charge_fx = null
		if _charge_tw:
			_charge_tw.kill()
			_charge_tw = null
		mat.set_shader_parameter("flash_amount", 0.0)


func _refresh_statuses() -> void:
	if not combatant.is_player and is_inside_tree():
		set_charging(combatant.has_status("charging") and combatant.is_alive())
	for c in status_row.get_children():
		c.queue_free()
	for s in combatant.statuses:
		status_row.add_child(StatusIcon.make(s["id"], int(s.get("turns", 0)), float(s.get("value", 0.0)), 32))


# ------------------------------------------------------------------ textures
static func _get_shadow_tex() -> Texture2D:
	if _shadow_tex == null:
		var img := Image.create(28, 8, false, Image.FORMAT_RGBA8)
		for y in 8:
			for x in 28:
				var dx := (x - 13.5) / 13.5
				var dy := (y - 3.5) / 3.5
				if dx * dx + dy * dy <= 1.0:
					img.set_pixel(x, y, Color.WHITE)
		_shadow_tex = ImageTexture.create_from_image(img)
	return _shadow_tex


static func _get_target_frames() -> SpriteFrames:
	if _target_frames == null:
		_target_frames = SpriteFrames.new()
		_target_frames.set_animation_speed("default", 12)
		_target_frames.set_animation_loop("default", true)
		for i in 8:
			var path := "res://assets/ui/v2_target_%d.png" % i
			if ResourceLoader.exists(path):
				_target_frames.add_frame("default", load(path))
	return _target_frames


static func clear_cache() -> void:
	_shadow_tex = null
	_ring_tex = null
	_target_frames = null


static func _get_ring_tex() -> Texture2D:
	if _ring_tex == null:
		var img := Image.create(30, 10, false, Image.FORMAT_RGBA8)
		for y in 10:
			for x in 30:
				var dx := (x - 14.5) / 14.5
				var dy := (y - 4.5) / 4.5
				var d := dx * dx + dy * dy
				if d <= 1.0 and d >= 0.55:
					img.set_pixel(x, y, Color("#ffc14a"))
		_ring_tex = ImageTexture.create_from_image(img)
	return _ring_tex
