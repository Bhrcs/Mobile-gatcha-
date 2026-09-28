extends ScreenBase
## Elemental Towers: three climbs (Ember / Tide / Verdant) of ten floors each.
## Floors unlock one by one; floors 5 and 10 hold a guardian boss. Each tower is
## the main source of its element's evolution materials. The docked sheet shows
## the selected floor (energy, power, stars, possible drops) and START -> PREPARE.

const SHEET_H := 660
const COLORS := {"fire": Color("#ff8a4a"), "water": Color("#5ac8ff"), "nature": Color("#8ae05a")}

var tower_id := ""
var tower: Dictionary = {}
var list: VBoxContainer
var scroll: ScrollContainer
var sheet_body: VBoxContainer
var sheet: PanelFrame
var selected_id := ""
var rows: Dictionary = {}


func _ready() -> void:
	if not require_profile():
		return
	var hl: String = SceneRouter.params.get("highlight", "")
	tower_id = SceneRouter.params.get("tower", Database.get_stage(hl).get("world_id", "") if not hl.is_empty() else "")
	if not Database.towers.has(tower_id):
		tower_id = Database.tower_order[0]
	tower = Database.towers[tower_id]
	var area := build_frame("bg_tower", "ELEMENTAL TOWERS", "tower", Callable(), 0.45, true, {"help": "tower"})
	if not GameManager.feature_unlocked("tower"):
		var lock := UIKit.wrap_label("The Towers open after clearing %s." % GameManager.feature_unlock_label("tower"), UIKit.T_NAME, UIKit.MUTED)
		lock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lock.set_anchors_preset(Control.PRESET_CENTER)
		area.add_child(lock)
		return
	var col := UIKit.vbox(10)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	col.offset_bottom = -SHEET_H - 10
	area.add_child(col)

	var tabs := UIKit.hbox(10)
	tabs.name = "TowerTabs"
	for tid in Database.tower_order:
		var td: Dictionary = Database.towers[tid]
		var el: String = td.get("element", "fire")
		var b := FantasyButton.make(String(td.get("name", "")).get_slice(" ", 0).to_upper(), "gold" if tid == tower_id else "steel",
				Vector2(0, 100), "res://assets/icons/orb_%s.png" % el)
		b.name = "Tower_" + tid
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", 32)
		if tid != tower_id:
			var t := tid
			b.pressed.connect(func(): SceneRouter.go("tower", {"tower": t}))
		tabs.add_child(b)
	col.add_child(tabs)

	var head := PanelFrame.make("plank", 12)
	var hv := UIKit.vbox(4)
	head.add_child(hv)
	var el: String = tower.get("element", "fire")
	var r1 := UIKit.hbox(12)
	r1.add_child(UIKit.orb(el, 56))
	var nm := UIKit.label(String(tower.get("name", "")).to_upper(), UIKit.T_NAME, COLORS.get(el, UIKit.TEXT), HORIZONTAL_ALIGNMENT_LEFT, 8)
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	r1.add_child(nm)
	r1.add_child(UIKit.label("BEST FLOOR %d / %d" % [GameManager.tower_highest_floor(tower_id), tower.get("stages", []).size()],
			UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 6))
	hv.add_child(r1)
	var r2 := UIKit.hbox(10)
	var counter: String = tower.get("counter_element", "")
	r2.add_child(UIKit.label("Bring", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 5))
	r2.add_child(UIKit.orb(counter, 32))
	r2.add_child(UIKit.label("%s heroes.  Materials:" % Database.element_name(counter), UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 5))
	for m in tower.get("materials", []):
		r2.add_child(UIKit.icon(Database.get_item(m).get("icon", ""), 40))
	hv.add_child(r2)
	col.add_child(head)

	scroll = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	list = UIKit.vbox(0)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	var floors: Array = tower.get("stages", []).duplicate()
	floors.reverse()            # climb upwards: top floor first
	for i in floors.size():
		var fl: Dictionary = floors[i]
		if i > 0:
			# the stair between this floor and the one above, lit once that floor is open
			list.add_child(_connector(GameManager.is_stage_unlocked(floors[i - 1]["id"])))
		var row := _floor_row(fl)
		list.add_child(row)
		rows[fl["id"]] = row

	sheet = PanelFrame.make("panel", 24)
	sheet.name = "FloorSheet"
	sheet.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	sheet.offset_top = -SHEET_H
	area.add_child(sheet)
	sheet_body = UIKit.vbox(10)
	sheet.add_child(sheet_body)
	var start := hl
	if start.is_empty() or Database.get_stage(start).get("world_id", "") != tower_id:
		start = _next_floor()
	_select(start)
	AudioManager.play_music(tower.get("music", "tower"))
	if SceneRouter.params.get("prepare", false) and GameManager.is_stage_unlocked(start):
		StageInfo.open_prepare(self, start, "tower")


func _next_floor() -> String:
	var best: String = tower["stages"][0]["id"]
	for fl in tower.get("stages", []):
		if GameManager.is_stage_unlocked(fl["id"]):
			best = fl["id"]
	return best


## Vertical stair segment in the tower's own path style (ember / tide / verdant).
func _connector(lit: bool) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0, 34)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var path := TextureRect.new()
	var tname: String = {"fire": "ember", "water": "tide", "nature": "verdant"}.get(String(tower.get("element", "fire")), "ember")
	path.texture = load("res://assets/ui/p5_path_%s.png" % tname)
	path.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	path.stretch_mode = TextureRect.STRETCH_TILE
	path.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	path.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	path.size = Vector2(12, 16)
	path.scale = Vector2(3, 3)           # 1x pixel art shown at 3x
	path.position = Vector2(40, -7)
	path.modulate = Color.WHITE if lit else Color(0.35, 0.33, 0.4)
	path.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.add_child(path)
	return c


func _floor_row(fl: Dictionary) -> Control:
	var sid: String = fl["id"]
	var unlocked := GameManager.is_stage_unlocked(sid)
	var cleared := GameManager.is_stage_cleared(sid)
	var boss: bool = fl.get("boss", false)
	var p := PanelFrame.make("boss" if boss and unlocked else ("plank" if unlocked else "inset"), 10)
	p.name = "Floor_%d" % int(fl.get("number", 0))
	var h := UIKit.hbox(14)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(h)
	var badge := PanelFrame.make("slot", 4)
	if unlocked:
		badge.self_modulate = COLORS.get(tower.get("element", "fire"), Color.WHITE).lightened(0.3)
	badge.custom_minimum_size = Vector2(96, 76)
	badge.add_child(UIKit.label(str(int(fl.get("number", 0))), UIKit.T_NAME, UIKit.GOLD if unlocked else UIKit.MUTED,
			HORIZONTAL_ALIGNMENT_CENTER, 8))
	h.add_child(badge)
	var v := UIKit.vbox(0)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var title := "%s" % fl.get("name", "")
	v.add_child(UIKit.label(title, UIKit.T_BODY, Color("#fff0c0") if unlocked else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var sub := UIKit.hbox(10)
	sub.add_child(UIKit.icon("res://assets/icons/energy.png", 28))
	sub.add_child(UIKit.label(str(int(fl.get("energy", 0))), UIKit.T_SMALL, Color("#ffe07a"), HORIZONTAL_ALIGNMENT_LEFT, 5))
	sub.add_child(UIKit.label("POWER %s" % UIKit.format_number(int(fl.get("recommended_power", 0))), UIKit.T_SMALL, UIKit.MUTED,
			HORIZONTAL_ALIGNMENT_LEFT, 5))
	if boss:
		sub.add_child(UIKit.tag("GUARDIAN", Color("#7a1a14")))
	v.add_child(sub)
	h.add_child(v)
	if cleared:
		var got: Array = GameManager.stage_stars(sid)
		for i in 3:
			h.add_child(UIKit.icon("res://assets/icons/star.png" if bool(got[i]) else "res://assets/icons/star_empty.png", 32))
	elif not unlocked:
		h.add_child(UIKit.icon("res://assets/icons/lock.png", 48))
	else:
		h.add_child(UIKit.tag("NEXT", Color("#b8401e")))
	UIKit.on_tap(p, func(): _select(sid))
	return p


func _select(sid: String) -> void:
	selected_id = sid
	for id in rows.keys():
		rows[id].modulate = Color(1.15, 1.1, 0.95) if id == sid else Color.WHITE
	AudioManager.play_sfx("stage_select", 0.03, -4.0)
	_scroll_to(rows.get(sid))
	for ch in sheet_body.get_children():
		ch.queue_free()
	var st := Database.get_stage(sid)
	var unlocked := GameManager.is_stage_unlocked(sid)
	sheet.set_variant("boss" if st.get("boss", false) else "panel", 24)
	var head := UIKit.hbox(12)
	var fname: String = st.get("name", "")
	var title := GameManager.stage_label(sid) if fname.begins_with("Floor") else "%s  -  %s" % [GameManager.stage_label(sid), fname]
	var t := UIKit.label(title, UIKit.T_NAME, Color("#fff0c0"),
			HORIZONTAL_ALIGNMENT_LEFT, 8)
	t.name = "FloorTitle"
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t.clip_text = true
	head.add_child(t)
	sheet_body.add_child(head)
	if not unlocked:
		var l := UIKit.label("Clear the floor below to climb higher.", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
		l.size_flags_vertical = Control.SIZE_EXPAND_FILL
		sheet_body.add_child(l)
	else:
		sheet_body.add_child(StageInfo.info_row(st))
		sheet_body.add_child(StageInfo.stars_row(st))
		sheet_body.add_child(StageInfo.rewards_row(st))
	sheet_body.add_child(UIKit.spacer(false, true))
	var go := FantasyButton.make("START", "ember", Vector2(600, 116))
	go.name = "StartButton"
	go.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	go.add_theme_font_size_override("font_size", UIKit.T_HEAD)
	go.disabled = not unlocked
	go.pressed.connect(func(): StageInfo.open_prepare(self, sid, "tower"))
	sheet_body.add_child(go)


func _scroll_to(n: Control) -> void:
	if n == null:
		return
	await get_tree().process_frame
	await get_tree().process_frame
	if is_instance_valid(scroll) and is_instance_valid(n):
		scroll.scroll_vertical = int(n.position.y - scroll.size.y / 2 + n.size.y / 2)
