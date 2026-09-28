class_name BattleStage
extends Node2D
## Layered portrait battle environment: far / mid / ground / foreground sprites
## with gentle parallax against the battle camera, plus ambient motion
## (leaves, dust, embers, water shimmer, spores, fog and light rays).
## Boss stages get denser ambience and a slow pulsing glow.

const PX := 6.0
const IMG_H := 270.0
const HORIZON := 150.0
const LAYERS := [["far", 0.45, -12], ["mid", 0.3, -11], ["ground", 0.0, -10], ["fore", -0.22, 30]]

var env := "forest"
var boss := false
var camera: Camera2D
var base_cam := Vector2.ZERO
var sprites: Array[Sprite2D] = []
var factors: Array[float] = []
var bottom_y := 0.0
var _fog: Sprite2D
var _sky: Polygon2D
var _t := 0.0


func setup(bg_name: String, is_boss: bool, cam: Camera2D) -> void:
	env = bg_name.trim_prefix("bg_")
	if not ResourceLoader.exists("res://assets/environments/battle/%s_ground.png" % env):
		env = "forest"
	boss = is_boss
	camera = cam
	# sky fill above the art so very tall screens never show a gap
	var far_img: Image = (load("res://assets/environments/battle/%s_far.png" % env) as Texture2D).get_image()
	_sky = Polygon2D.new()
	_sky.color = far_img.get_pixel(0, 0)
	_sky.polygon = PackedVector2Array([Vector2(-600, -4000), Vector2(1800, -4000), Vector2(1800, 40), Vector2(-600, 40)])
	_sky.z_index = -13
	add_child(_sky)
	for l in LAYERS:
		var s := Sprite2D.new()
		s.texture = load("res://assets/environments/battle/%s_%s.png" % [env, l[0]])
		s.centered = true
		s.scale = Vector2(PX, PX)
		s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		s.z_index = l[2]
		add_child(s)
		sprites.append(s)
		factors.append(l[1])
	_add_ambient()


## Places the stage so the image bottom sits just under the battlefield edge.
func fit(view_size: Vector2, field_bottom: float) -> void:
	bottom_y = field_bottom + 60.0
	base_cam = camera.position if camera else view_size / 2.0
	for s in sprites:
		s.position = Vector2(view_size.x / 2.0, bottom_y - IMG_H * PX / 2.0)
		s.set_meta("home", s.position)
	_sky.position = Vector2(0, bottom_y - IMG_H * PX)
	for c in get_children():
		if c is CPUParticles2D or c == _fog:
			c.set_meta("fit", true)
	_place_ambient(view_size)


func horizon_y() -> float:
	return bottom_y - (IMG_H - HORIZON) * PX


func _process(delta: float) -> void:
	_t += delta
	if camera:
		var d := camera.position - base_cam
		for i in sprites.size():
			var s := sprites[i]
			if s.has_meta("home"):
				s.position = s.get_meta("home") + d * factors[i]
	if _fog:
		_fog.modulate.a = 0.5 + 0.25 * sin(_t * 0.6)
		_fog.position.x = sin(_t * 0.15) * 60.0 + get_viewport_rect().size.x / 2.0
	if boss and sprites.size() > 0:
		var k := 0.92 + 0.08 * sin(_t * 1.6)
		sprites[0].modulate = Color(k, k * 1.02, k)


# ------------------------------------------------------------------ ambience
var _ambient: Array = []   # [particles, kind]


func _add_ambient() -> void:
	var dense := 1.6 if boss else 1.0
	match env:
		"forest":
			_ambient.append([_particles(int(14 * dense), Color("#8ac050"), Color("#4a7e30"), Vector2(20, 50), 7.0, 6, 9), "sky"])
			_add_rays(Color(1.0, 0.95, 0.7, 0.10))
		"ruins":
			_ambient.append([_particles(int(18 * dense), Color("#f0e8d0"), Color(0.9, 0.85, 0.7, 0), Vector2(8, -6), 6.0, 4, 6), "field"])
		"scorched":
			_ambient.append([_particles(int(30 * dense), Color("#ffd35a"), Color(1, 0.3, 0.1, 0), Vector2(6, -60), 4.0, 4, 8), "ground"])
			_add_fog(Color(0.35, 0.18, 0.14, 0.45))
		"flooded":
			_ambient.append([_particles(int(22 * dense), Color("#e0f8ff"), Color(0.6, 0.9, 1, 0), Vector2(0, 0), 1.6, 3, 6), "water"])
			_add_fog(Color(0.75, 0.85, 0.9, 0.35))
		"heart":
			_ambient.append([_particles(int(24 * dense), Color("#c8ff9a"), Color(0.4, 0.9, 0.3, 0), Vector2(4, -24), 5.0, 4, 8), "field"])
			_add_rays(Color(0.7, 1.0, 0.6, 0.12 if boss else 0.08))
			if boss:
				_add_fog(Color(0.2, 0.4, 0.2, 0.35))


func _particles(amount: int, c0: Color, c1: Color, gravity: Vector2, life: float, smin: float, smax: float) -> CPUParticles2D:
	if not bool(GameManager.settings.get("battle_effects", true)):
		amount = max(4, amount / 3)
	var p := CPUParticles2D.new()
	p.amount = amount
	p.lifetime = life
	p.preprocess = life
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.gravity = gravity
	p.initial_velocity_min = 5
	p.initial_velocity_max = 25
	p.direction = Vector2(0.3, 1)
	p.spread = 60
	p.scale_amount_min = smin
	p.scale_amount_max = smax
	var g := Gradient.new()
	g.set_color(0, c0)
	g.set_color(1, c1)
	p.color_ramp = g
	p.z_index = 25
	add_child(p)
	return p


func _add_rays(col: Color) -> void:
	for i in 3:
		var r := Polygon2D.new()
		var x := 260.0 + i * 260.0
		r.polygon = PackedVector2Array([Vector2(x - 40, 0), Vector2(x + 30, 0), Vector2(x + 260, 1400), Vector2(x + 90, 1400)])
		r.color = col
		var mat := CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		r.material = mat
		r.z_index = -9
		r.set_meta("ray", i)
		add_child(r)
		var tw := r.create_tween().set_loops()
		tw.tween_property(r, "modulate:a", 0.4, 2.0 + i * 0.7).set_trans(Tween.TRANS_SINE)
		tw.tween_property(r, "modulate:a", 1.0, 2.0 + i * 0.7).set_trans(Tween.TRANS_SINE)


func _add_fog(col: Color) -> void:
	var g := Gradient.new()
	g.set_color(0, Color(col.r, col.g, col.b, 0.0))
	g.add_point(0.5, col)
	g.set_color(g.get_point_count() - 1, Color(col.r, col.g, col.b, 0.0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill_from = Vector2(0.5, 0)
	gt.fill_to = Vector2(0.5, 1)
	gt.width = 8
	gt.height = 64
	_fog = Sprite2D.new()
	_fog.texture = gt
	_fog.scale = Vector2(190, 5)
	_fog.z_index = -9
	add_child(_fog)


func _place_ambient(view_size: Vector2) -> void:
	var hz := horizon_y()
	for a in _ambient:
		var p: CPUParticles2D = a[0]
		match a[1]:
			"sky":
				p.position = Vector2(view_size.x / 2, hz - 500)
				p.emission_rect_extents = Vector2(view_size.x / 2, 60)
			"ground":
				p.position = Vector2(view_size.x / 2, bottom_y - 200)
				p.emission_rect_extents = Vector2(view_size.x / 2, 180)
				p.direction = Vector2(0, -1)
			"water":
				p.position = Vector2(view_size.x / 2, (hz + bottom_y) / 2)
				p.emission_rect_extents = Vector2(view_size.x / 2, (bottom_y - hz) / 2)
				p.initial_velocity_max = 2
			_:
				p.position = Vector2(view_size.x / 2, (hz + bottom_y) / 2 - 150)
				p.emission_rect_extents = Vector2(view_size.x / 2, (bottom_y - hz) / 2 + 150)
	if _fog:
		_fog.position = Vector2(view_size.x / 2, hz + 40)
	for c in get_children():
		if c is Polygon2D and c.has_meta("ray"):
			c.position = Vector2(-200, hz - 1300)
