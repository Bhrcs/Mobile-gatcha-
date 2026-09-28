extends ScreenBase
## Adventure map: a portrait route per world (Ashroot Wilds, Saltglass Reach...).
## Nodes show LOCKED / AVAILABLE / CLEARED / BOSS and earned stars. World tabs
## switch regions. The docked sheet shows energy, power, star objectives,
## possible drops and first-clear rewards; START opens the PREPARE check.

const MAP_SCALE := 4.0
const NODE_PX := 96
const BOSS_PX := 128
const SHEET_H := 700

var world: Dictionary = {}
var nodes: Dictionary = {}
var map_scroll: ScrollContainer
var map_view: Control
var path_layer: Control
var sheet: PanelFrame
var sheet_body: VBoxContainer
var selected_id := ""
var _marker: TextureRect
var _marker_tw: Tween
var _dash := 0.0


func _ready() -> void:
	if not require_profile():
		return
	var start: String = SceneRouter.params.get("highlight", GameManager.last_unlocked_stage)
	if start.is_empty() or not GameManager.is_stage_unlocked(start) or Database.is_tower_stage(start):
		start = _latest_unlocked()
	var wid: String = SceneRouter.params.get("world", Database.get_stage(start).get("world_id", ""))
	if not Database.worlds.has(wid):
		wid = Database.world_order[0]
	world = Database.worlds[wid]
	if Database.get_stage(start).get("world_id", "") != wid:
		start = _latest_unlocked_in(wid)
	back_fallback = "world_select"
	var area := build_frame("bg_camp", String(world.get("name", "Quest")).to_upper(), "world_select",
			Callable(), 0.6)

	# ---- world tabs
	var tabs := UIKit.hbox(10)
	tabs.name = "WorldTabs"
	tabs.set_anchors_preset(Control.PRESET_TOP_WIDE)
	tabs.offset_bottom = 96
	area.add_child(tabs)
	for w in Database.world_order:
		var wd: Dictionary = Database.worlds[w]
		var open := GameManager.world_unlocked(w)
		var b := FantasyButton.make("%d  %s" % [int(wd.get("number", 1)), String(wd.get("name", "")).to_upper()],
				"gold" if w == wid else "steel", Vector2(0, 92))
		b.name = "World_" + w
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", 28)
		if not open:
			b.modulate = Color(0.55, 0.53, 0.58)
			b.icon = load("res://assets/icons/lock.png")
			b.expand_icon = true
			b.add_theme_constant_override("icon_max_width", 40)
			var req: String = wd.get("requires", "")
			b.pressed.connect(func(): UIKit.toast(self, "Clear %s to reach %s." % [GameManager.stage_label(req), wd.get("name", "")],
					UIKit.MUTED))
		elif w != wid:
			var target := w
			b.pressed.connect(func(): SceneRouter.go("stage_select", {"world": target}))
		tabs.add_child(b)
		var total := 0
		for st in wd.get("stages", []):
			total += 3
		if open:
			b.tooltip_text = "Stars %d / %d" % [GameManager.total_stars(w), total]

	# ---- map (scrolls vertically)
	var frame := PanelFrame.make("inset", 6)
	frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	frame.offset_top = 104
	frame.offset_bottom = -SHEET_H - 10
	area.add_child(frame)
	map_scroll = ScrollContainer.new()
	map_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	map_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	frame.add_child(map_scroll)
	var center := CenterContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_scroll.add_child(center)
	map_view = Control.new()
	var tex: Texture2D = load(world.get("route_map", "res://assets/environments/bg_routemap.png"))
	map_view.custom_minimum_size = tex.get_size() * MAP_SCALE
	center.add_child(map_view)
	var map_tex := UIKit.tex_rect(tex, map_view.custom_minimum_size)
	map_tex.size = map_view.custom_minimum_size
	map_view.add_child(map_tex)
	_add_ambient()
	path_layer = Control.new()
	path_layer.size = map_view.custom_minimum_size
	path_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	path_layer.draw.connect(_draw_route)
	map_view.add_child(path_layer)
	_build_nodes()
	_enable_drag_scroll()

	# ---- docked stage sheet
	sheet = PanelFrame.make("panel", 26)
	sheet.name = "StageSheet"
	sheet.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	sheet.offset_top = -SHEET_H
	area.add_child(sheet)
	sheet_body = UIKit.vbox(12)
	sheet.add_child(sheet_body)

	_select(start, false)
	AudioManager.play_music(world.get("music", "world"))
	if SceneRouter.params.get("prepare", false) and GameManager.is_stage_unlocked(start):
		StageInfo.open_prepare(self, start)


func _process(delta: float) -> void:
	_dash = fmod(_dash + delta * 18.0, 24.0)
	if path_layer:
		path_layer.queue_redraw()


func _latest_unlocked() -> String:
	var last := Database.stage_order[0]
	for sid in Database.stage_order:
		if GameManager.is_stage_unlocked(sid):
			last = sid
	return last


func _latest_unlocked_in(wid: String) -> String:
	var stages: Array = Database.worlds[wid].get("stages", [])
	var last: String = stages[0]["id"]
	for st in stages:
		if GameManager.is_stage_unlocked(st["id"]):
			last = st["id"]
	return last


func _node_state(stage: Dictionary) -> String:
	var sid: String = stage["id"]
	if not GameManager.is_stage_unlocked(sid):
		return "locked"
	if GameManager.is_stage_cleared(sid) and not stage.get("boss", false):
		return "cleared"
	return "boss" if stage.get("boss", false) else "open"


func _route_point(stage: Dictionary) -> Vector2:
	var p: Array = stage.get("route_pos", [128, 224])
	return Vector2(p[0], p[1]) * MAP_SCALE


func _build_nodes() -> void:
	for stage in world.get("stages", []):
		var sid: String = stage["id"]
		var st := _node_state(stage)
		var boss: bool = stage.get("boss", false)
		var px := BOSS_PX if boss else NODE_PX
		var n := StageNode.make(sid, "boss" if boss else st, px)
		n.position = _route_point(stage) - Vector2(px, px) / 2.0 - Vector2(0, 16)
		if boss and st == "locked":
			n.modulate = Color(0.45, 0.4, 0.5)
		n.pressed.connect(func(): _select(sid))
		map_view.add_child(n)
		nodes[sid] = n
		var num := UIKit.label(str(stage["number"]), UIKit.T_BODY, UIKit.TEXT if st != "locked" else UIKit.MUTED,
				HORIZONTAL_ALIGNMENT_CENTER, 8)
		num.position = n.position + Vector2(0, px - 4)
		num.size = Vector2(px, 34)
		map_view.add_child(num)
		if GameManager.is_stage_cleared(sid):
			var srow := UIKit.hbox(0)
			srow.name = "Stars_" + sid
			var got: Array = GameManager.stage_stars(sid)
			for i in 3:
				srow.add_child(UIKit.icon("res://assets/icons/star.png" if bool(got[i]) else "res://assets/icons/star_empty.png", 24))
			srow.position = n.position + Vector2(px / 2.0 - 36, px + 26)
			map_view.add_child(srow)
		if boss:
			var tag := UIKit.tag("ANCIENT FOE", Color("#7a1a14"))
			tag.position = n.position + Vector2(px / 2.0 - 110, -44)
			map_view.add_child(tag)
	_marker = TextureRect.new()
	_marker.texture = load("res://assets/ui/v2_chevron.png")
	_marker.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_marker.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_marker.size = Vector2(64, 64)
	_marker.mouse_filter = Control.MOUSE_FILTER_IGNORE
	map_view.add_child(_marker)


## Trail dots: lit and marching up to the furthest unlocked stage, dark beyond it.
func _draw_route() -> void:
	var stages: Array = world.get("stages", [])
	for i in range(stages.size() - 1):
		var a := _route_point(stages[i])
		var b := _route_point(stages[i + 1])
		var reached := GameManager.is_stage_unlocked(stages[i + 1]["id"])
		var dist := a.distance_to(b)
		var d := 60.0 + (_dash if reached else 0.0)
		while d < dist - 50.0:
			var p := a.lerp(b, d / dist)
			path_layer.draw_rect(Rect2(p - Vector2(8, 8), Vector2(16, 16)), Color(0.06, 0.04, 0.03, 0.85))
			path_layer.draw_rect(Rect2(p - Vector2(4, 4), Vector2(8, 8)),
					Color("#ffd88a") if reached else Color(0.22, 0.18, 0.14))
			d += 24.0


## Drifting light motes and falling leaves over the map.
func _add_ambient() -> void:
	var size := map_view.custom_minimum_size
	var leaves := CPUParticles2D.new()
	leaves.amount = 18
	leaves.lifetime = 7.0
	leaves.preprocess = 7.0
	leaves.position = Vector2(size.x / 2, -20)
	leaves.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	leaves.emission_rect_extents = Vector2(size.x / 2, 10)
	leaves.direction = Vector2(0.3, 1)
	leaves.gravity = Vector2(10, 40)
	leaves.initial_velocity_min = 40
	leaves.initial_velocity_max = 90
	leaves.scale_amount_min = 6
	leaves.scale_amount_max = 8
	leaves.color = Color("#8ac04a") if world.get("id", "") == "ashroot_wilds" else Color("#bff4ff")
	leaves.lifetime_randomness = 0.4
	map_view.add_child(leaves)
	var glow := CPUParticles2D.new()
	glow.amount = 14
	glow.lifetime = 3.0
	glow.preprocess = 3.0
	var heart := _route_point(world.get("stages", [{}])[-1]) if not world.get("stages", []).is_empty() else Vector2(512, 200)
	glow.position = heart + Vector2(0, -80)
	glow.emission_shape = CPUParticles2D.EMISSION_SHAPE_SPHERE
	glow.emission_sphere_radius = 90
	glow.gravity = Vector2(0, -12)
	glow.initial_velocity_max = 8
	glow.scale_amount_min = 4
	glow.scale_amount_max = 8
	var g := Gradient.new()
	g.set_color(0, Color("#c8ff9a"))
	g.set_color(1, Color(0.5, 1.0, 0.4, 0.0))
	glow.color_ramp = g
	map_view.add_child(glow)
	var embers := CPUParticles2D.new()   # scorched band
	embers.amount = 12
	embers.lifetime = 2.5
	embers.preprocess = 2.5
	embers.position = Vector2(size.x / 2, 200 * MAP_SCALE)
	embers.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	embers.emission_rect_extents = Vector2(size.x / 2, 20 * MAP_SCALE)
	embers.gravity = Vector2(0, -30)
	embers.initial_velocity_max = 12
	embers.scale_amount_min = 4
	embers.scale_amount_max = 6
	var ge := Gradient.new()
	ge.set_color(0, Color("#ffb04a"))
	ge.set_color(1, Color(1, 0.3, 0.1, 0))
	embers.color_ramp = ge
	map_view.add_child(embers)


## Touch-drag the map (scroll bars are hidden).
func _enable_drag_scroll() -> void:
	map_view.mouse_filter = Control.MOUSE_FILTER_PASS
	map_scroll.gui_input.connect(func(e):
		if e is InputEventMouseMotion and (e.button_mask & MOUSE_BUTTON_MASK_LEFT):
			map_scroll.scroll_vertical -= int(e.relative.y))


func _select(sid: String, with_sound := true) -> void:
	selected_id = sid
	for id in nodes.keys():
		nodes[id].set_selected(id == sid)
	if with_sound:
		AudioManager.play_sfx("stage_select", 0.03, -2.0)
	var n: StageNode = nodes.get(sid)
	if n:
		_marker.position = n.position + Vector2(n.size.x / 2 - 32, -76)
		if _marker_tw:
			_marker_tw.kill()
		_marker_tw = create_tween().set_loops()
		_marker_tw.tween_property(_marker, "position:y", _marker.position.y - 14, 0.4).set_trans(Tween.TRANS_SINE)
		_marker_tw.tween_property(_marker, "position:y", _marker.position.y, 0.4).set_trans(Tween.TRANS_SINE)
		_scroll_to(n)
	_build_sheet(sid)


func _scroll_to(n: Control) -> void:
	await get_tree().process_frame
	if not is_instance_valid(map_scroll):
		return
	var target := int(n.position.y + n.size.y / 2 - map_scroll.size.y / 2)
	var tw := create_tween()
	tw.tween_property(map_scroll, "scroll_vertical", clampi(target, 0, int(map_view.custom_minimum_size.y)), 0.25)


func _build_sheet(sid: String) -> void:
	for ch in sheet_body.get_children():
		ch.queue_free()
	var stage := Database.get_stage(sid)
	var unlocked := GameManager.is_stage_unlocked(sid)
	var cleared := GameManager.is_stage_cleared(sid)
	var boss: bool = stage.get("boss", false)
	sheet.set_variant("boss" if boss else "panel", 26)

	var head := UIKit.hbox(16)
	var badge := PanelFrame.make("slot", 8)
	badge.custom_minimum_size = Vector2(110, 90)
	badge.add_child(UIKit.label(str(stage.get("number", 0)), UIKit.T_HEAD, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	head.add_child(badge)
	var tv := UIKit.vbox(2)
	tv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var title := UIKit.label(stage.get("name", "") if unlocked else "? ? ?", UIKit.T_HEAD, Color("#fff0c0") if unlocked else UIKit.MUTED,
			HORIZONTAL_ALIGNMENT_LEFT, 10)
	title.name = "StageTitle"
	tv.add_child(title)
	var sub := "ANCIENT FOE AWAITS" if boss else ("CLEARED" if cleared else ("NEW" if unlocked else "LOCKED"))
	tv.add_child(UIKit.label(sub, UIKit.T_BODY, Color("#ff7a5a") if boss else (UIKit.GOOD if cleared else (UIKit.EMBER if unlocked else UIKit.MUTED)),
			HORIZONTAL_ALIGNMENT_LEFT, 6))
	head.add_child(tv)
	sheet_body.add_child(head)

	if not unlocked:
		var prev := ""
		for st2 in Database.stages.values():
			if st2.get("unlocks", []).has(sid):
				prev = GameManager.stage_label(st2["id"])
		var lock := UIKit.hbox(14)
		lock.alignment = BoxContainer.ALIGNMENT_CENTER
		lock.add_child(UIKit.icon("res://assets/icons/lock.png", 64))
		lock.add_child(UIKit.label("Clear %s to unlock this path." % prev, UIKit.T_BODY, UIKit.MUTED))
		lock.size_flags_vertical = Control.SIZE_EXPAND_FILL
		sheet_body.add_child(lock)
	else:
		sheet_body.add_child(StageInfo.info_row(stage))
		var summary := UIKit.wrap_label(stage.get("summary", ""), UIKit.T_SMALL, Color("#e0d6c6"))
		summary.custom_minimum_size.x = 980
		sheet_body.add_child(summary)
		sheet_body.add_child(StageInfo.stars_row(stage))
		sheet_body.add_child(StageInfo.rewards_row(stage))
	sheet_body.add_child(UIKit.spacer(false, true))
	var go := FantasyButton.make("START", "ember", Vector2(640, 120))
	go.name = "StartButton"
	go.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	go.add_theme_font_size_override("font_size", UIKit.T_HEAD)
	go.disabled = not unlocked
	go.pressed.connect(func(): _start(sid))
	go.add_shine()
	sheet_body.add_child(go)
	if unlocked:
		var tw := go.create_tween().set_loops()
		tw.tween_property(go, "modulate", Color(1.18, 1.1, 1.0), 0.6).set_trans(Tween.TRANS_SINE)
		tw.tween_property(go, "modulate", Color.WHITE, 0.6).set_trans(Tween.TRANS_SINE)


func _start(sid: String) -> void:
	if not GameManager.is_stage_unlocked(sid):
		return
	StageInfo.open_prepare(self, sid)
