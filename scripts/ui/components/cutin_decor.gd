class_name CutinDecor
extends RefCounted
## Element-themed motion inside the Burst cut-in band.
##   fire   : racing ember streaks + rising sparks        (Kael)
##   water  : flowing twin water ribbon + bubbles          (Mira)
##   nature : roots creeping in from the edges + earth bits (Thorne)


static func add(band: Control, element: String) -> void:
	var fx_on := bool(GameManager.settings.get("battle_effects", true))
	match element:
		"fire":
			_streaks(band, fx_on)
			_particles(band, Color("#ffd35a"), Color(1, 0.3, 0.1, 0), Vector2(0, -80), 30 if fx_on else 10, 4, 10)
		"water":
			var r := Ribbon.new()
			r.size = band.size
			r.mouse_filter = Control.MOUSE_FILTER_IGNORE
			band.add_child(r)
			_particles(band, Color("#dff6ff"), Color(0.5, 0.8, 1, 0), Vector2(0, -120), 24 if fx_on else 8, 6, 12)
		"nature":
			var roots := Roots.new()
			roots.size = band.size
			roots.mouse_filter = Control.MOUSE_FILTER_IGNORE
			band.add_child(roots)
			_particles(band, Color("#b08a5a"), Color(0.3, 0.2, 0.1, 0), Vector2(0, 260), 22 if fx_on else 8, 6, 12, true)
		_:
			pass


static func _streaks(band: Control, fx_on: bool) -> void:
	var n := 14 if fx_on else 6
	for i in n:
		var s := ColorRect.new()
		s.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var h := 4 + (i % 3) * 4
		s.size = Vector2(160 + (i * 53) % 260, h)
		s.color = [Color("#ffb03a"), Color("#ff6a1e"), Color("#fff0a0")][i % 3]
		s.position = Vector2(band.size.x + (i * 97) % 600, 20 + (i * 71) % int(band.size.y - 40))
		band.add_child(s)
		var tw := s.create_tween().set_loops()
		var t := 0.35 + (i % 4) * 0.08
		tw.tween_property(s, "position:x", -s.size.x - 20, t).from(band.size.x + 20)


static func _particles(band: Control, c0: Color, c1: Color, gravity: Vector2, amount: int, smin: float, smax: float,
		burst := false) -> void:
	var p := CPUParticles2D.new()
	p.amount = amount
	p.lifetime = 1.0
	p.preprocess = 0.3
	p.explosiveness = 0.6 if burst else 0.0
	p.position = Vector2(band.size.x * 0.5, band.size.y * (0.95 if gravity.y < 0 else 0.6))
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(band.size.x * 0.5, 20)
	p.direction = Vector2(0, -1)
	p.spread = 30
	p.gravity = gravity
	p.initial_velocity_min = 60 if not burst else 200
	p.initial_velocity_max = 160 if not burst else 420
	p.scale_amount_min = smin
	p.scale_amount_max = smax
	var g := Gradient.new()
	g.set_color(0, c0)
	g.set_color(1, c1)
	p.color_ramp = g
	band.add_child(p)


## Two flowing sine ribbons drawn with chunky pixel steps.
class Ribbon extends Control:
	var t := 0.0

	func _process(delta: float) -> void:
		t += delta
		queue_redraw()

	func _draw() -> void:
		for k in 2:
			var amp := 40.0 - k * 12.0
			var yb := size.y * (0.45 + k * 0.2)
			var col := Color("#5ac8ff") if k == 0 else Color("#bff0ff")
			var x := 0.0
			while x < size.x:
				var y := yb + sin(x * 0.012 + t * (6.0 + k * 2.0)) * amp
				draw_rect(Rect2(x, y, 12, 12 - k * 4), col)
				draw_rect(Rect2(x, y + 12, 12, 6), Color(0.2, 0.5, 0.8, 0.6))
				x += 12.0


## Roots that grow inward from both bottom corners and the band edges.
class Roots extends Control:
	var t := 0.0
	var branches: Array = []

	func _ready() -> void:
		var rng := RandomNumberGenerator.new()
		rng.seed = 7
		for i in 7:
			var from_left := i % 2 == 0
			var start := Vector2(0 if from_left else size.x, size.y - rng.randf_range(0, size.y * 0.8))
			var pts: Array = [start]
			var p := start
			for s in 14:
				p += Vector2((1 if from_left else -1) * rng.randf_range(24, 44), rng.randf_range(-22, 22))
				pts.append(p)
			branches.append(pts)

	func _process(delta: float) -> void:
		t = min(t + delta * 1.6, 1.0)
		queue_redraw()

	func _draw() -> void:
		for pts in branches:
			var n := int(floor((pts.size() - 1) * t))
			for i in n:
				var a: Vector2 = pts[i]
				var b: Vector2 = pts[i + 1]
				var w := 14.0 - i * 0.8
				draw_line(a, b, Color("#3a2616"), max(w + 4, 4))
				draw_line(a, b, Color("#6a8a3a") if i % 3 == 0 else Color("#5a4026"), max(w, 2))
