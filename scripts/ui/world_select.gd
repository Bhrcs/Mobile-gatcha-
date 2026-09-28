extends ScreenBase
## QUEST hub (World Select): one card per story world with its scenery, completion,
## stars and boss state, plus the Elemental Towers. Locked worlds say exactly what
## opens them. Tapping a world opens its stage map.

const ART_SCALE := 5
const CARD_H := 330

var list: VBoxContainer


func _ready() -> void:
	if not require_profile():
		return
	var area := build_frame("bg_camp", "QUEST", "world_select", Callable(), 0.6, true, {"help": "progress"})
	var scroll := ScrollContainer.new()
	scroll.name = "WorldScroll"
	scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	area.add_child(scroll)
	list = UIKit.vbox(UIKit.SP_L)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	for wid in Database.world_order:
		list.add_child(_world_card(wid))
	list.add_child(_tower_card())
	AudioManager.play_music("world")


func _world_card(wid: String) -> Control:
	var w: Dictionary = Database.worlds[wid]
	var open := GameManager.world_unlocked(wid)
	var stages: Array = w.get("stages", [])
	var cleared := 0
	var boss_id := ""
	for st in stages:
		if GameManager.is_stage_cleared(st["id"]):
			cleared += 1
		if st.get("boss", false):
			boss_id = st["id"]
	var stars := GameManager.total_stars(wid)
	var bg_name: String = String(stages[0].get("background", "bg_forest")).trim_prefix("bg_") if not stages.is_empty() else "forest"
	var card := _card("World_" + wid, bg_name, open)
	var v: VBoxContainer = card.get_meta("body")
	var top := UIKit.hbox(UIKit.SP_M)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var num := UIKit.label("WORLD %d" % int(w.get("number", 1)), UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 6)
	top.add_child(num)
	top.add_child(UIKit.spacer())
	if open:
		top.add_child(UIKit.icon("res://assets/icons/star.png", 32))
		top.add_child(UIKit.label("%d / %d" % [stars, stages.size() * 3], UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	v.add_child(top)
	var name_l := UIKit.label(String(w.get("name", wid)).to_upper(), UIKit.T_TITLE if open else UIKit.T_HEAD,
			Color("#fff0c0") if open else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 12)
	v.add_child(name_l)
	var sub := UIKit.label(String(w.get("subtitle", "")), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6)
	sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(sub)
	v.add_child(UIKit.spacer(false, true))
	var bottom := UIKit.hbox(UIKit.SP_M)
	bottom.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if open:
		var pct := int(round(100.0 * cleared / max(1, stages.size())))
		var bar := ResourceBar.make("xp", 28)
		bar.custom_minimum_size.x = 360
		bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		bar.ready.connect(func(): bar.set_values(cleared, stages.size(), false))
		bottom.add_child(bar)
		var pl := UIKit.label("%d%% CLEARED" % pct, UIKit.T_BODY, UIKit.GOOD if pct >= 100 else UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6)
		pl.name = "Completion"
		bottom.add_child(pl)
		bottom.add_child(UIKit.spacer())
		var boss_done := not boss_id.is_empty() and GameManager.is_stage_cleared(boss_id)
		bottom.add_child(UIKit.tag("BOSS DEFEATED" if boss_done else "BOSS AWAITS", Color("#2a5a1a") if boss_done else Color("#7a1a14")))
	else:
		bottom.add_child(UIKit.icon("res://assets/icons/lock.png", 40))
		var req: String = w.get("requires", "")
		var why := UIKit.label("Clear %s to open" % GameManager.stage_label(req), UIKit.T_BODY, UIKit.EMBER, HORIZONTAL_ALIGNMENT_LEFT, 6)
		why.name = "LockReason"
		bottom.add_child(why)
	v.add_child(bottom)
	if open:
		UIKit.on_tap(card, func(): SceneRouter.go("stage_select", {"world": wid}))
	else:
		var req2: String = w.get("requires", "")
		UIKit.on_tap(card, func(): UIManager.toast("Clear %s to reach %s." % [GameManager.stage_label(req2), w.get("name", "")], "info"))
	return card


func _tower_card() -> Control:
	var open := GameManager.feature_unlocked("tower")
	var card := _card("World_towers", "", open)
	var v: VBoxContainer = card.get_meta("body")
	v.add_child(UIKit.label("CHALLENGE", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 6))
	v.add_child(UIKit.label("ELEMENTAL TOWERS", UIKit.T_HEAD, Color("#fff0c0") if open else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 12))
	v.add_child(UIKit.spacer(false, true))
	var row := UIKit.hbox(UIKit.SP_L)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if open:
		for t in Database.tower_order:
			var td: Dictionary = Database.towers[t]
			var h := UIKit.hbox(UIKit.SP_S)
			h.mouse_filter = Control.MOUSE_FILTER_IGNORE
			h.add_child(UIKit.orb(String(td.get("element", "fire")), 40))
			h.add_child(UIKit.label("%d/%d" % [GameManager.tower_highest_floor(t), td.get("stages", []).size()], UIKit.T_BODY,
					UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6))
			row.add_child(h)
		row.add_child(UIKit.spacer())
		row.add_child(UIKit.label("Evolution materials", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_RIGHT, 5))
		UIKit.on_tap(card, func(): SceneRouter.go("tower"))
	else:
		row.add_child(UIKit.icon("res://assets/icons/lock.png", 40))
		row.add_child(UIKit.label("Clear %s to open" % GameManager.feature_unlock_label("tower"), UIKit.T_BODY, UIKit.EMBER,
				HORIZONTAL_ALIGNMENT_LEFT, 6))
		UIKit.on_tap(card, func(): UIManager.toast("The towers open after clearing %s." % GameManager.feature_unlock_label("tower"), "info"))
	v.add_child(row)
	return card


## Card shell: layered scenery (or the tower backdrop), a dark gradient for text
## contrast, and a frame. Returns the card; its text column is meta "body".
func _card(node_name: String, bg: String, open: bool) -> PanelFrame:
	var card := PanelFrame.make("panel", 8)
	card.name = node_name
	card.custom_minimum_size = Vector2(0, CARD_H)
	var clip := Control.new()
	clip.clip_contents = true
	clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.add_child(clip)
	var art := Control.new()
	art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(art)
	if bg.is_empty():
		var t := UIKit.tex_rect(load("res://assets/environments/bg_tower.png"), Vector2.ZERO)
		t.size = t.texture.get_size() * 6
		art.add_child(t)
		art.set_meta("src", t.texture.get_size() * 6.0 / ART_SCALE)
	else:
		for layer in ["far", "mid", "ground"]:
			var path := "res://assets/environments/battle/%s_%s.png" % [bg, layer]
			if ResourceLoader.exists(path):
				var t := UIKit.tex_rect(load(path), Vector2.ZERO)
				t.size = t.texture.get_size() * ART_SCALE
				art.add_child(t)
				art.set_meta("src", t.texture.get_size())
	if not open:
		art.modulate = Color(0.35, 0.33, 0.4)
	clip.resized.connect(func():
		# centre the art horizontally and show the band just above the ground line
		var src: Vector2 = art.get_meta("src", Vector2(200, 270))
		art.position = Vector2((clip.size.x - src.x * ART_SCALE) / 2.0, clip.size.y - src.y * ART_SCALE * 0.72))
	var shade := TextureRect.new()
	var g := Gradient.new()
	g.set_color(0, Color(0.03, 0.02, 0.05, 0.85))
	g.set_color(1, Color(0.03, 0.02, 0.05, 0.1))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill_from = Vector2(0, 0.5)
	gt.fill_to = Vector2(1, 0.5)
	shade.texture = gt
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(shade)
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, UIKit.SP_XL)
	clip.add_child(margin)
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var v := UIKit.vbox(UIKit.SP_XS)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(v)
	card.set_meta("body", v)
	return card
