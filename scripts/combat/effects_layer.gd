class_name EffectsLayer
extends Node2D
## Pooled battle effects: sprite effects, projectiles, elemental particle bursts,
## ring pulses / shield domes and damage numbers. Nodes are recycled instead of
## created/freed every hit, and live counts are capped so heavy combos never
## flood the scene. Battle Effects / Damage Numbers settings are respected here.

const MAX_PER_EFFECT := 10
const MAX_NUMBERS := 24
const MAX_BURSTS := 8
const EFFECT_SCALE := 6.0

## Number styles: font size, colour, icon, animation strength.
const NUMBER_STYLES := {
	"normal":    {"size": 50, "color": "#fff6e8", "icon": "",                                   "pop": 1.15},
	"player":    {"size": 50, "color": "#ff8a7a", "icon": "",                                   "pop": 1.15},
	"crit":      {"size": 70, "color": "#ffd35a", "icon": "res://assets/icons/star.png",        "pop": 1.5},
	"advantage": {"size": 60, "color": "#ff9a4a", "icon": "",                                   "pop": 1.3},
	"resist":    {"size": 40, "color": "#9ab4d0", "icon": "res://assets/icons/shield.png",      "pop": 1.0},
	"heal":      {"size": 50, "color": "#8ae05a", "icon": "res://assets/icons/herb.png",        "pop": 1.2},
	"dot":       {"size": 40, "color": "#ffa04a", "icon": "res://assets/icons/status_burn.png", "pop": 1.0},
	"finisher":  {"size": 80, "color": "#fff0a0", "icon": "res://assets/icons/burst.png",       "pop": 1.7},
}

const PARTICLE_STYLES := {
	"fire":    {"c0": "#fff0a0", "c1": "#ff5a1e", "gravity": Vector2(0, -260), "speed": 340.0},
	"water":   {"c0": "#dff6ff", "c1": "#3a8ad8", "gravity": Vector2(0, 700),  "speed": 380.0},
	"nature":  {"c0": "#c8ff9a", "c1": "#4a8a2a", "gravity": Vector2(0, 240),  "speed": 300.0},
	"neutral": {"c0": "#ffffff", "c1": "#a8a0b0", "gravity": Vector2(0, 300),  "speed": 300.0},
	"earth":   {"c0": "#c8a878", "c1": "#5a4026", "gravity": Vector2(0, 900),  "speed": 520.0},
	"heal":    {"c0": "#e0ffd0", "c1": "#5ae05a", "gravity": Vector2(0, -160), "speed": 120.0},
}

var _effect_pools: Dictionary = {}     # name -> Array[AnimatedSprite2D]
var _number_pool: Array[Node2D] = []
var _number_index := 0
var _bursts: Array[CPUParticles2D] = []
var _burst_index := 0


func fx_enabled() -> bool:
	return bool(GameManager.settings.get("battle_effects", true))


# ------------------------------------------------------------------ sprite effects
func spawn(effect_name: String, pos: Vector2, flip := false, scale_mult := 1.0, z := 20) -> AnimatedSprite2D:
	if effect_name.is_empty():
		return null
	var fx := _take_effect(effect_name)
	if fx == null:
		return null
	fx.global_position = pos
	fx.flip_h = flip
	fx.scale = Vector2.ONE * EFFECT_SCALE * scale_mult
	fx.z_index = z
	fx.modulate = Color.WHITE
	fx.visible = true
	fx.frame = 0
	fx.play("default")
	return fx


func _take_effect(effect_name: String) -> AnimatedSprite2D:
	var pool: Array = _effect_pools.get(effect_name, [])
	for fx in pool:
		if not fx.visible:
			return fx
	if pool.size() >= MAX_PER_EFFECT:
		return pool[0]   # recycle the oldest instead of growing
	var frames := SpriteFactory.effect_frames(effect_name)
	if frames.get_frame_count("default") == 0:
		return null
	var node := AnimatedSprite2D.new()
	node.sprite_frames = frames
	node.visible = false
	node.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	node.animation_finished.connect(func(): node.visible = false)
	add_child(node)
	pool.append(node)
	_effect_pools[effect_name] = pool
	return node


## Moves a looping projectile from a to b. Await the returned tween.
func projectile(effect_name: String, from: Vector2, to: Vector2, time: float, flip := false) -> Tween:
	var fx := spawn(effect_name, from, flip, 1.0, 25)
	var tw := create_tween()
	if fx == null:
		tw.tween_interval(time)
		return tw
	fx.sprite_frames.set_animation_loop("default", true)
	fx.play("default")
	tw.tween_property(fx, "global_position", to, time).set_trans(Tween.TRANS_SINE)
	tw.tween_callback(func():
		fx.visible = false
		fx.stop())
	return tw


# ------------------------------------------------------------------ particles
## One-shot elemental particle burst (pooled CPUParticles2D).
func particles(kind: String, pos: Vector2, amount: int = 14, spread_deg: float = 180.0) -> void:
	if not fx_enabled():
		amount = max(3, amount / 3)
	var st: Dictionary = PARTICLE_STYLES.get(kind, PARTICLE_STYLES["neutral"])
	var p := _take_burst()
	p.global_position = pos
	p.amount = clampi(amount, 2, 40)
	p.spread = spread_deg
	p.gravity = st["gravity"]
	p.initial_velocity_min = float(st["speed"]) * 0.4
	p.initial_velocity_max = float(st["speed"])
	var g := Gradient.new()
	g.set_color(0, Color(st["c0"]))
	g.set_color(1, Color(Color(st["c1"]), 0.0))
	p.color_ramp = g
	p.restart()
	p.emitting = true


func _take_burst() -> CPUParticles2D:
	if _bursts.size() < MAX_BURSTS:
		var p := CPUParticles2D.new()
		p.one_shot = true
		p.explosiveness = 0.9
		p.lifetime = 0.7
		p.direction = Vector2(0, -1)
		p.scale_amount_min = 5
		p.scale_amount_max = 10
		p.damping_min = 80
		p.damping_max = 160
		p.z_index = 30
		p.emitting = false
		add_child(p)
		_bursts.append(p)
		return p
	var reuse := _bursts[_burst_index]
	_burst_index = (_burst_index + 1) % _bursts.size()
	return reuse


## Expanding pixel ring (heal pulse, shockwave, root pulse).
func ring(pos: Vector2, color: Color, radius: float = 180.0, time: float = 0.45, thickness: float = 10.0,
		squash: float = 0.45) -> void:
	var r := PulseRing.new()
	r.color = color
	r.thickness = thickness
	r.squash = squash
	r.global_position = pos
	r.z_index = 22
	add_child(r)
	var tw := r.create_tween().set_parallel(true)
	tw.tween_property(r, "radius", radius, time).from(radius * 0.15).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(r, "modulate:a", 0.0, time).from(1.0).set_ease(Tween.EASE_IN)
	tw.chain().tween_callback(r.queue_free)


## Translucent shield dome over a unit that pulses in, holds and fades.
func shield_dome(pos: Vector2, color: Color, radius: float = 130.0, hold: float = 0.6) -> void:
	var d := ShieldDome.new()
	d.color = color
	d.radius = radius
	d.global_position = pos
	d.z_index = 21
	d.scale = Vector2(0.2, 0.2)
	add_child(d)
	var tw := d.create_tween()
	tw.tween_property(d, "scale", Vector2(1.1, 1.1), 0.18).set_trans(Tween.TRANS_BACK)
	tw.tween_property(d, "scale", Vector2.ONE, 0.08)
	tw.tween_interval(hold)
	tw.tween_property(d, "modulate:a", 0.0, 0.3)
	tw.tween_callback(d.queue_free)


## Fast speed-line streaks through a point (Kael's rapid slash trails).
func streaks(pos: Vector2, color: Color, count: int = 5, length: float = 260.0) -> void:
	if not fx_enabled():
		count = 2
	for i in count:
		var s := Streak.new()
		s.color = color if i % 2 == 0 else color.lightened(0.4)
		s.length = length * randf_range(0.6, 1.1)
		s.global_position = pos + Vector2(randf_range(-60, 60), randf_range(-60, 60))
		s.rotation = randf_range(-0.9, -0.5) if i % 2 == 0 else randf_range(0.5, 0.9)
		s.z_index = 24
		add_child(s)
		var tw := s.create_tween().set_parallel(true)
		tw.tween_property(s, "progress", 1.0, 0.16).from(0.0)
		tw.tween_property(s, "modulate:a", 0.0, 0.12).set_delay(0.12)
		tw.chain().tween_callback(s.queue_free)


# ------------------------------------------------------------------ numbers
var _recent: Array = []     # [position, msec] of numbers launched just now


## kind: normal | player | crit | advantage | resist | heal | dot | finisher
## tag : "", "WEAK" (shown as ADVANTAGE), "RESIST"
func damage_number(pos: Vector2, value: int, kind: String = "normal", tag: String = "", icon_path: String = "") -> void:
	if not bool(GameManager.settings.get("damage_numbers", true)) and kind != "heal":
		return
	var st: Dictionary = NUMBER_STYLES.get(kind, NUMBER_STYLES["normal"])
	var n := _take_number()
	var row: HBoxContainer = n.get_child(0)
	var ic: TextureRect = row.get_child(0)
	var main: Label = row.get_child(1)
	var sub: Label = n.get_child(1)
	main.text = ("+" if kind == "heal" else "") + str(value)
	main.add_theme_font_size_override("font_size", int(st["size"]))
	main.add_theme_color_override("font_color", Color(st["color"]))
	main.add_theme_constant_override("outline_size", int(st["size"]) / 5)
	var ipath: String = icon_path if not icon_path.is_empty() else st["icon"]
	ic.visible = not ipath.is_empty()
	if ic.visible:
		ic.texture = load(ipath)
		var isz := 48 if int(st["size"]) >= 60 else 32
		ic.custom_minimum_size = Vector2(isz, isz)
	var tags: Array = []
	match kind:
		"crit":
			tags.append("CRITICAL")
		"finisher":
			tags.append("FINISH")
	if tag == "WEAK":
		tags.append("ADVANTAGE")
	elif tag == "RESIST":
		tags.append("RESIST")
	elif not tag.is_empty() and tag not in tags:
		tags.append(tag)
	sub.text = "  ".join(tags)
	sub.visible = not tags.is_empty()
	var tag_color := Color("#ffd35a")
	if tag == "WEAK":
		tag_color = Color("#ff7a3a")
	elif tag == "RESIST":
		tag_color = Color("#9ab4d0")
	sub.add_theme_color_override("font_color", tag_color)
	row.reset_size()
	row.position = Vector2(-row.size.x / 2.0, -row.size.y / 2.0)
	_launch(n, pos, float(st["pop"]), kind == "resist" or kind == "dot")


func floating_text(pos: Vector2, text: String, color: Color, size: int = 40) -> void:
	var n := _take_number()
	var row: HBoxContainer = n.get_child(0)
	var ic: TextureRect = row.get_child(0)
	var main: Label = row.get_child(1)
	var sub: Label = n.get_child(1)
	ic.visible = false
	main.text = text
	main.add_theme_font_size_override("font_size", UIKit.snap_text(size))
	main.add_theme_color_override("font_color", color)
	main.add_theme_constant_override("outline_size", 8)
	sub.visible = false
	row.reset_size()
	row.position = Vector2(-row.size.x / 2.0, -row.size.y / 2.0)
	_launch(n, pos, 1.1, true)


## Pop (scale overshoot) -> rise -> fade. Softer drift for small numbers.
func _launch(n: Node2D, pos: Vector2, pop: float, soft: bool) -> void:
	# numbers landing on the same spot at the same time stack upwards instead of overlapping
	var now := Time.get_ticks_msec()
	var stack := 0
	for r in _recent:
		if now - int(r[1]) < 450 and (r[0] as Vector2).distance_to(pos) < 90.0:
			stack += 1
	_recent = _recent.filter(func(r): return now - int(r[1]) < 450)
	_recent.append([pos, now])
	n.global_position = pos + Vector2(randf_range(-10, 10) + (stack % 2) * 30 - 15 * mini(stack, 1), -52.0 * mini(stack, 4))
	n.visible = true
	n.modulate.a = 1.0
	n.scale = Vector2.ONE * pop
	var rise := 60.0 if soft else 100.0
	var tw := n.create_tween()
	tw.set_parallel(true)
	tw.tween_property(n, "scale", Vector2.ONE, 0.14).set_trans(Tween.TRANS_BACK)
	tw.tween_property(n, "position:y", n.position.y - rise, 0.85).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	if pop >= 1.5:
		tw.tween_property(n, "rotation", 0.0, 0.2).from(randf_range(-0.12, 0.12))
	tw.chain().tween_property(n, "modulate:a", 0.0, 0.25)
	tw.chain().tween_callback(func(): n.visible = false)
	n.set_meta("tween", tw)


func _take_number() -> Node2D:
	if _number_pool.size() < MAX_NUMBERS:
		var n := Node2D.new()
		n.z_index = 40
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var ic := TextureRect.new()
		ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ic.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		ic.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_child(ic)
		var main := UIKit.label("", 50, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 10)
		main.add_theme_constant_override("shadow_offset_x", 5)
		main.add_theme_constant_override("shadow_offset_y", 5)
		row.add_child(main)
		var sub := UIKit.label("", 30, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 7)
		sub.size = Vector2(400, 40)
		sub.position = Vector2(-200, -84)
		n.add_child(row)
		n.add_child(sub)
		add_child(n)
		_number_pool.append(n)
		return n
	# recycle round-robin
	var reuse := _number_pool[_number_index]
	_number_index = (_number_index + 1) % _number_pool.size()
	if reuse.has_meta("tween"):
		var old: Tween = reuse.get_meta("tween")
		if old and old.is_valid():
			old.kill()
	reuse.rotation = 0.0
	return reuse


# ------------------------------------------------------------------ drawn helpers
class PulseRing extends Node2D:
	var color := Color.WHITE
	var radius := 10.0:
		set(v):
			radius = v
			queue_redraw()
	var thickness := 10.0
	var squash := 0.45

	func _draw() -> void:
		# chunky pixel ring: small squares around an ellipse
		var steps := int(clampf(radius * 0.35, 16, 96))
		for i in steps:
			var a := TAU * i / steps
			var p := Vector2(cos(a) * radius, sin(a) * radius * squash)
			p = (p / 4.0).floor() * 4.0
			draw_rect(Rect2(p - Vector2(thickness, thickness) / 2.0, Vector2(thickness, thickness)), color)


class ShieldDome extends Node2D:
	var color := Color(0.6, 1.0, 0.5)
	var radius := 130.0

	func _draw() -> void:
		var fill := Color(color.r, color.g, color.b, 0.18)
		draw_circle(Vector2(0, -radius * 0.55), radius, fill)
		var steps := 40
		for i in steps + 1:
			var a := PI + PI * i / steps
			var p := Vector2(cos(a) * radius, -radius * 0.55 + sin(a) * radius)
			p = (p / 6.0).floor() * 6.0
			draw_rect(Rect2(p - Vector2(5, 5), Vector2(10, 10)), Color(color.r, color.g, color.b, 0.85))
		# hex facets
		for k in 3:
			var y := -radius * 0.55 - radius * 0.3 * k
			draw_line(Vector2(-radius * 0.6 + k * 20, y), Vector2(radius * 0.6 - k * 20, y), Color(1, 1, 1, 0.25), 4)


class Streak extends Node2D:
	var color := Color.WHITE
	var length := 200.0
	var progress := 0.0:
		set(v):
			progress = v
			queue_redraw()

	func _draw() -> void:
		var a := Vector2(-length / 2.0, 0)
		var b := Vector2(length / 2.0, 0)
		var head := a.lerp(b, progress)
		var tail := a.lerp(b, max(progress - 0.5, 0.0))
		draw_line(tail, head, color, 8)
		draw_line(tail.lerp(head, 0.5), head, Color(1, 1, 1, 0.9), 4)
