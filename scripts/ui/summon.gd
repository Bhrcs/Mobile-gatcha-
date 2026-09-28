extends ScreenBase
## EMBERGATE - the summon hall. A standard banner with transparent, data-driven
## rates (DETAILS), single (100 Gems) and x10 (1000 Gems) summons, a summon
## ceremony (fragments -> gate glow -> rarity -> silhouette -> reveal -> NEW),
## results with duplicates converted to Soul Shards, and the NEW hero flow
## (DETAILS / ADD TO SQUAD / CONTINUE). Results are saved before any animation.

const GATE_SCALE := 6
const RARITY_COLORS := {3: Color("#e0a060"), 4: Color("#d8e4f4"), 5: Color("#ffd84a")}

var banner: Dictionary = {}
var gems_label: Label
var shards_label: Label
var vortex: TextureRect
var _vortex_frame := 0
var _busy := false


func _ready() -> void:
	if not require_profile():
		return
	banner = GameManager.summon_banner("standard")
	var area := build_frame("bg_title", "EMBERGATE", "summon", Callable(), 0.55)
	if not GameManager.feature_unlocked("summon"):
		var lock := UIKit.wrap_label("The Embergate awakens after clearing %s." % GameManager.feature_unlock_label("summon"),
				UIKit.T_NAME, UIKit.MUTED)
		lock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lock.set_anchors_preset(Control.PRESET_CENTER)
		lock.custom_minimum_size.x = 900
		area.add_child(lock)
		return
	GameManager.mark_summon_seen()
	var col := UIKit.vbox(12)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)

	# banner
	var bp := PanelFrame.make("panel", 10)
	bp.name = "Banner"
	col.add_child(bp)
	var bv := UIKit.vbox(6)
	bp.add_child(bv)
	var art := UIKit.tex_rect(load(banner.get("art", "res://assets/ui/banner_standard.png")), Vector2(900, 360))
	art.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	bv.add_child(art)
	var br := UIKit.hbox(10)
	var bt := UIKit.vbox(0)
	bt.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bt.add_child(UIKit.label(String(banner.get("name", "")).to_upper(), UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 8))
	var desc := UIKit.wrap_label(banner.get("description", ""), UIKit.T_SMALL, Color("#e0d6c6"))
	desc.custom_minimum_size.x = 640
	bt.add_child(desc)
	var rr: Dictionary = SummonSystem.rates(banner)
	bt.add_child(UIKit.label("5* %s   4* %s   3* %s" % [_pct(rr.get("5", 0.0)), _pct(rr.get("4", 0.0)), _pct(rr.get("3", 0.0))],
			UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	br.add_child(bt)
	var details := FantasyButton.make("DETAILS", "steel", Vector2(230, 96))
	details.name = "SummonDetails"
	details.add_theme_font_size_override("font_size", 30)
	details.pressed.connect(_open_details)
	br.add_child(details)
	bv.add_child(br)

	# gate
	var gate := Control.new()
	gate.name = "Gate"
	gate.custom_minimum_size = Vector2(0, 128 * GATE_SCALE * 0.62)
	gate.size_flags_vertical = Control.SIZE_EXPAND_FILL
	gate.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(gate)
	var frame := UIKit.tex_rect(load("res://assets/ui/embergate_frame.png"), Vector2(96, 128) * GATE_SCALE * 0.62)
	gate.add_child(frame)
	vortex = TextureRect.new()
	vortex.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	vortex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vortex.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var at := AtlasTexture.new()
	at.atlas = load("res://assets/ui/embergate_vortex.png")
	at.region = Rect2(0, 0, 64, 64)
	vortex.texture = at
	gate.add_child(vortex)
	gate.move_child(vortex, 0)
	gate.resized.connect(func():
		var fs := frame.size
		frame.position = Vector2((gate.size.x - fs.x) / 2.0, (gate.size.y - fs.y) / 2.0)
		var k := fs.x / 96.0
		vortex.size = Vector2(56, 56) * k
		vortex.position = frame.position + Vector2(20, 34) * k)
	var t := Timer.new()
	t.wait_time = 0.12
	t.autostart = true
	t.timeout.connect(func():
		_vortex_frame = (_vortex_frame + 1) % 6
		(vortex.texture as AtlasTexture).region = Rect2(_vortex_frame * 64, 0, 64, 64))
	add_child(t)
	UIKit.sparkle(gate, Rect2(200, 60, 650, 500), Color("#ffb04a"), 10)

	# currency + buttons
	var cur := UIKit.hbox(24)
	cur.alignment = BoxContainer.ALIGNMENT_CENTER
	var g := UIKit.hbox(8)
	g.add_child(UIKit.icon("res://assets/icons/gem.png", 48))
	gems_label = UIKit.label("", UIKit.T_NAME, Color("#9ae8ff"), HORIZONTAL_ALIGNMENT_LEFT, 8)
	gems_label.name = "GemsOwned"
	g.add_child(gems_label)
	cur.add_child(g)
	var s := UIKit.hbox(8)
	s.add_child(UIKit.icon("res://assets/icons/soul_shard.png", 48))
	shards_label = UIKit.label("", UIKit.T_NAME, Color("#d0a8ff"), HORIZONTAL_ALIGNMENT_LEFT, 8)
	s.add_child(shards_label)
	cur.add_child(s)
	col.add_child(cur)
	var btns := UIKit.hbox(16)
	btns.alignment = BoxContainer.ALIGNMENT_CENTER
	var one := FantasyButton.make("SUMMON x1\n%d" % int(banner.get("single_cost", 100)), "steel", Vector2(440, 150),
			"res://assets/icons/gem.png")
	one.name = "SummonOne"
	one.add_theme_font_size_override("font_size", 34)
	one.pressed.connect(func(): _summon(1))
	btns.add_child(one)
	var ten := FantasyButton.make("SUMMON x%d\n%d" % [int(banner.get("multi_count", 10)), int(banner.get("multi_cost", 1000))], "ember",
			Vector2(440, 150), "res://assets/icons/gem.png")
	ten.name = "SummonTen"
	ten.add_theme_font_size_override("font_size", 34)
	ten.add_shine()
	ten.pressed.connect(func(): _summon(int(banner.get("multi_count", 10))))
	btns.add_child(ten)
	col.add_child(btns)
	var note := UIKit.label("Heroes you already own become Soul Shards (used for Burst training).", UIKit.T_SMALL, UIKit.MUTED,
			HORIZONTAL_ALIGNMENT_CENTER, 4)
	col.add_child(note)
	_refresh()
	AudioManager.play_music("summon")
	GameManager.profile_changed.connect(_refresh)


func _exit_tree() -> void:
	if GameManager.profile_changed.is_connected(_refresh):
		GameManager.profile_changed.disconnect(_refresh)


func _pct(v: float) -> String:
	return ("%.1f%%" % (v * 100.0)).replace(".0%", "%")


func _refresh() -> void:
	if gems_label:
		gems_label.text = UIKit.format_number(GameManager.gems())
		shards_label.text = UIKit.format_number(GameManager.soul_shards())


# ------------------------------------------------------------------ details
func _open_details() -> void:
	var p := FantasyPopup.open(self, "SUMMON DETAILS", 1000)
	p.name = "SummonDetailsPopup"
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(940, 1100)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	p.content.add_child(scroll)
	var v := UIKit.vbox(10)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(v)
	v.add_child(UIKit.label(String(banner.get("name", "")), UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	var costs := "Single: %d Gems     x%d: %d Gems" % [int(banner.get("single_cost", 100)), int(banner.get("multi_count", 10)),
			int(banner.get("multi_cost", 1000))]
	v.add_child(UIKit.label(costs, UIKit.T_BODY, Color("#9ae8ff"), HORIZONTAL_ALIGNMENT_CENTER, 6))
	v.add_child(UIKit.label("RARITY RATES", UIKit.T_BODY, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var rr := SummonSystem.rates(banner)
	for r in ["5", "4", "3"]:
		var h := UIKit.hbox(10)
		h.add_child(UIKit.stars(int(r), 32))
		h.add_child(UIKit.spacer())
		h.add_child(UIKit.label(_pct(rr.get(r, 0.0)), UIKit.T_BODY, RARITY_COLORS[int(r)], HORIZONTAL_ALIGNMENT_RIGHT, 6))
		v.add_child(h)
	v.add_child(UIKit.separator())
	v.add_child(UIKit.label("HEROES IN THIS GATE (chance per summon)", UIKit.T_BODY, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var hr := SummonSystem.hero_rates(banner)
	var ids: Array = hr.keys()
	ids.sort_custom(func(a, b): return int(Database.get_character(a)["rarity"]) > int(Database.get_character(b)["rarity"]) or \
		(int(Database.get_character(a)["rarity"]) == int(Database.get_character(b)["rarity"]) and a < b))
	for cid in ids:
		var d := Database.get_character(cid)
		var h := UIKit.hbox(10)
		h.add_child(UIKit.orb(d.get("element", ""), 36))
		var n := UIKit.label(d.get("name", ""), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 5)
		n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		h.add_child(n)
		h.add_child(UIKit.stars(int(d.get("rarity", 3)), 20))
		h.add_child(UIKit.label("%.2f%%" % (float(hr[cid]) * 100.0), UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 5))
		if GameManager.owns_family(d.get("family", "")):
			h.add_child(UIKit.tag("OWNED", Color("#2a5a9a")))
		v.add_child(h)
	v.add_child(UIKit.separator())
	var ds: Dictionary = Database.summon.get("duplicate_shards", {})
	for line in ["DUPLICATES", "If you already own a hero of the same line (any form), the summon becomes Soul Shards instead:",
			"3* = %d   4* = %d   5* = %d Soul Shards" % [int(ds.get("3", 10)), int(ds.get("4", 30)), int(ds.get("5", 100))],
			"Soul Shards train any hero's Burst level. No hero ever needs duplicates to evolve.",
			"Gems come from first clears, rank-ups, missions and login rewards. Nothing here can be bought with money."]:
		var w := UIKit.wrap_label(line, UIKit.T_SMALL, UIKit.TEXT)
		w.custom_minimum_size.x = 900
		v.add_child(w)
	var close := FantasyButton.make("CLOSE", "ember", Vector2(300, 100))
	close.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	close.pressed.connect(p.close)
	p.content.add_child(close)


# ------------------------------------------------------------------ summoning
func _summon(count: int) -> void:
	if _busy:
		return
	var cost := int(banner.get("single_cost", 100)) if count == 1 else int(banner.get("multi_cost", 1000))
	if GameManager.gems() < cost:
		UIManager.not_enough("Gems", cost, GameManager.gems(), "Earn Gems from first clears, rank-ups, missions and login rewards.")
		return
	UIManager.confirm("SUMMON x%d?" % count, "", "SUMMON", func(): _do_summon(count), {"name": "SummonConfirm", "lines": [
			["res://assets/icons/gem.png", "Cost  %s Gems" % UIKit.format_number(cost), Color("#9ae8ff")],
			["", "Gems left after:  %s" % UIKit.format_number(GameManager.gems() - cost), UIKit.MUTED]]})


func _do_summon(count: int) -> void:
	_busy = true
	var first_time := int(GameManager.profile.get("summon", {}).get("total", 0)) == 0
	var r := GameManager.summon("standard", count)
	if not r.get("ok", false):
		_busy = false
		UIManager.toast(r.get("reason", "The gate did not answer."), "error")
		return
	_refresh()
	var ceremony := SummonCeremony.new()
	ceremony.name = "SummonCeremony"
	add_child(ceremony)
	await ceremony.play(r["results"], not first_time)
	if not is_inside_tree():
		return
	ceremony.queue_free()
	_busy = false
	_show_results(r["results"])


func _show_results(results: Array) -> void:
	var p := FantasyPopup.open(self, "SUMMON RESULTS", 1020)
	p.name = "SummonResults"
	var grid := GridContainer.new()
	grid.columns = 5 if results.size() > 1 else 1
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	grid.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(grid)
	var shards := 0
	var new_ones: Array = []
	for e in results:
		var d := Database.get_character(e["char_id"])
		var cell := PanelFrame.make("rarity_%d" % clampi(int(e["rarity"]), 3, 6), 6)
		cell.name = "Result_%s" % e["char_id"]
		var px := 170 if results.size() > 1 else 360
		var v := UIKit.vbox(2)
		v.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_child(v)
		var art := UIKit.portrait_art(d, Vector2(px, px))
		v.add_child(art)
		v.add_child(UIKit.label(String(d.get("name", "")).get_slice(" ", 0), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 5))
		var st := UIKit.stars(int(e["rarity"]), 18 if results.size() > 1 else 32)
		st.position = Vector2(4, px - (22 if results.size() > 1 else 36))
		art.add_child(st)
		if e["is_new"]:
			var nt := UIKit.tag("NEW!", Color("#c8281e"))
			nt.position = Vector2(4, 4)
			art.add_child(nt)
			new_ones.append(e)
			var uid: String = e["uid"]
			UIKit.on_tap(cell, func(): _new_hero_popup(uid))
		else:
			# duplicates are marked clearly and show exactly what they became
			var dt := UIKit.tag("DUPLICATE", Color("#5a3a8a"))
			dt.position = Vector2(4, 4)
			art.add_child(dt)
			art.modulate = Color(0.8, 0.78, 0.85)
			shards += int(e["shards"])
			var sh := UIKit.hbox(2)
			sh.alignment = BoxContainer.ALIGNMENT_CENTER
			sh.mouse_filter = Control.MOUSE_FILTER_IGNORE
			sh.add_child(UIKit.icon("res://assets/icons/soul_shard.png", 24))
			sh.add_child(UIKit.label("+%d" % int(e["shards"]), UIKit.T_SMALL, Color("#d0a8ff"), HORIZONTAL_ALIGNMENT_CENTER, 5))
			v.add_child(sh)
			var entry: Dictionary = e
			UIKit.on_tap(cell, func(): _duplicate_popup(entry))
		grid.add_child(cell)
	if shards > 0:
		var w := UIKit.wrap_label("Duplicates were converted into %d Soul Shards - use them to train any hero's Burst." % shards,
				UIKit.T_SMALL, Color("#d0a8ff"))
		w.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		w.custom_minimum_size.x = 940
		p.content.add_child(w)
	p.content.add_child(UIKit.label("Tap a hero to inspect it." + (" NEW heroes can join your squad." if not new_ones.is_empty() else ""),
			UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 5))
	var row := UIKit.hbox(14)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	if new_ones.size() == 1:
		var uid: String = new_ones[0]["uid"]
		_add_new_hero_buttons(row, uid, p)
	var cont := FantasyButton.make("CONTINUE", "ember", Vector2(300, 116))
	cont.name = "ResultsContinue"
	cont.pressed.connect(p.close)
	row.add_child(cont)
	p.content.add_child(row)
	p.default_action = p.close


func _add_new_hero_buttons(row: Control, uid: String, popup: FantasyPopup) -> void:
	var det := FantasyButton.make("DETAILS", "steel", Vector2(260, 116))
	det.name = "NewHeroDetails"
	det.pressed.connect(func():
		popup.close()
		SceneRouter.go("unit_detail", {"uid": uid, "back": "summon"}))
	row.add_child(det)
	var add := FantasyButton.make("ADD TO SQUAD", "gold", Vector2(340, 116))
	add.name = "NewHeroAdd"
	add.disabled = GameManager.is_in_party(uid) or not GameManager.feature_unlocked("squad")
	add.pressed.connect(func():
		if GameManager.party_uids().size() >= GameManager.max_party_size():
			popup.close()
			UIManager.toast("Your squad is full - choose who to swap out.", "info")
			SceneRouter.go("squad")
		elif GameManager.toggle_party(uid):
			add.disabled = true
			add.text = "IN SQUAD"
			AudioManager.play_sfx("unit_select")
			UIManager.toast("Added to your squad.", "success"))
	row.add_child(add)


## Inspecting a duplicate result: which hero, and what it turned into.
func _duplicate_popup(e: Dictionary) -> void:
	var d := Database.get_character(e["char_id"])
	var p := FantasyPopup.open(self, "DUPLICATE", 860)
	p.name = "DuplicatePopup"
	p.tap_outside_closes = true
	var fr := PanelFrame.make("rarity_%d" % clampi(int(e["rarity"]), 3, 6), 6)
	fr.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	fr.add_child(UIKit.portrait_art(d, Vector2(240, 240)))
	p.content.add_child(fr)
	p.content.add_child(UIKit.label(d.get("name", ""), UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	var w := UIKit.wrap_label("You already have a hero of this line, so this summon became Soul Shards.", UIKit.T_BODY)
	w.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	w.custom_minimum_size.x = 780
	p.content.add_child(w)
	var h := UIKit.hbox(UIKit.SP_S)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_child(UIKit.icon("res://assets/icons/soul_shard.png", 56))
	h.add_child(UIKit.label("+%d Soul Shards" % int(e["shards"]), UIKit.T_NAME, Color("#d0a8ff"), HORIZONTAL_ALIGNMENT_LEFT, 8))
	p.content.add_child(h)
	p.content.add_child(UIKit.label("Spend them on any hero's Burst level (Unit Details).", UIKit.T_SMALL, UIKit.MUTED,
			HORIZONTAL_ALIGNMENT_CENTER, 5))
	var ok := UIKit.btn("OK", "primary", Vector2(260, 100))
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	ok.pressed.connect(p.close)
	p.content.add_child(ok)
	p.default_action = p.close


func _new_hero_popup(uid: String) -> void:
	var u := GameManager.get_unit(uid)
	var d := Database.get_character(u.get("char_id", ""))
	var p := FantasyPopup.open(self, "NEW HERO", 900)
	p.name = "NewHeroPopup"
	p.content.add_child(UIKit.label(d.get("name", ""), UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	var s := UIKit.stars(int(d.get("rarity", 3)), 40)
	s.alignment = BoxContainer.ALIGNMENT_CENTER
	p.content.add_child(s)
	var w := UIKit.wrap_label("%s  -  %s" % [d.get("role", ""), d.get("description", "")], UIKit.T_SMALL, Color("#e0d6c6"))
	w.custom_minimum_size.x = 820
	w.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	p.content.add_child(w)
	var row := UIKit.hbox(12)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	_add_new_hero_buttons(row, uid, p)
	var c := FantasyButton.make("CONTINUE", "stone", Vector2(260, 116))
	c.pressed.connect(p.close)
	row.add_child(c)
	p.content.add_child(row)
