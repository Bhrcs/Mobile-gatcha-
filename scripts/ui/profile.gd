extends ScreenBase
## Player profile: name (editable), rank, energy, currencies, collection and
## progress (stars per world, tower floors) and battle statistics.

var body: VBoxContainer


func _ready() -> void:
	if not require_profile():
		return
	var area := build_frame("bg_camp", "PROFILE", "", Callable(), 0.6)
	var scroll := ScrollContainer.new()
	scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	area.add_child(scroll)
	body = UIKit.vbox(12)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	_build()


func _build() -> void:
	for ch in body.get_children():
		ch.queue_free()
	var pl: Dictionary = GameManager.profile["player"]
	# identity
	var head := PanelFrame.make("panel", 20)
	body.add_child(head)
	var hh := UIKit.hbox(18)
	head.add_child(hh)
	var leader := GameManager.get_unit(GameManager.leader_uid())
	if not leader.is_empty():
		var fr := PanelFrame.make("rarity_%d" % clampi(int(Database.get_character(leader["char_id"]).get("rarity", 3)), 3, 6), 6)
		fr.add_child(UIKit.portrait_art(Database.get_character(leader["char_id"]), Vector2(200, 200)))
		hh.add_child(fr)
	var v := UIKit.vbox(6)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var nm := UIKit.label(pl.get("name", "Wayfarer"), UIKit.T_HEAD, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_LEFT, 10)
	nm.name = "PlayerName"
	v.add_child(nm)
	v.add_child(UIKit.label("RANK %d" % GameManager.rank(), UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 8))
	var xb := ResourceBar.make("xp", 26)
	var need := Progression.rank_xp_to_next(GameManager.rank())
	var have := int(pl.get("rank_xp", 0))
	xb.ready.connect(func(): xb.set_values(have, need, false))
	v.add_child(xb)
	v.add_child(UIKit.label("Rank EXP %d / %d   -   next Gem reward at Rank %d" % [have, need, _next_gem_rank()], UIKit.T_SMALL,
			UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 5))
	hh.add_child(v)
	var rn := FantasyButton.make("RENAME", "steel", Vector2(220, 90))
	rn.name = "RenameButton"
	rn.add_theme_font_size_override("font_size", 28)
	rn.pressed.connect(_rename)
	hh.add_child(rn)

	body.add_child(_section("RESOURCES", [
		["Energy", "%d / %d" % [GameManager.energy(), GameManager.max_energy()]],
		["Gems", UIKit.format_number(GameManager.gems())],
		["Gold", UIKit.format_number(GameManager.gold())],
		["Soul Shards", UIKit.format_number(GameManager.soul_shards())],
	]))
	var story_rows: Array = []
	for w in Database.world_order:
		var wd: Dictionary = Database.worlds[w]
		var cleared := 0
		for st in wd.get("stages", []):
			if GameManager.is_stage_cleared(st["id"]):
				cleared += 1
		story_rows.append([wd.get("name", w), "%d / %d cleared   %d / %d stars" % [cleared, wd.get("stages", []).size(),
				GameManager.total_stars(w), wd.get("stages", []).size() * 3]])
	for t in Database.tower_order:
		story_rows.append([Database.towers[t].get("name", t), "Best floor %d / %d" % [GameManager.tower_highest_floor(t),
				Database.towers[t].get("stages", []).size()]])
	body.add_child(_section("PROGRESS", story_rows))
	var stats: Dictionary = GameManager.profile.get("stats", {})
	body.add_child(_section("COLLECTION & RECORDS", [
		["Heroes owned", str(GameManager.owned_units().size())],
		["Codex", "%d / %d" % [GameManager.profile.get("codex", []).size(), Database.family_ids().size()]],
		["Battles won / lost", "%d / %d" % [int(stats.get("battles_won", 0)), int(stats.get("battles_lost", 0))]],
		["Enemies defeated", str(int(stats.get("enemies_defeated", 0)))],
		["Bosses defeated", str(int(stats.get("bosses_defeated", 0)))],
		["Summons", str(int(stats.get("summons", 0)))],
		["Login days", str(int(GameManager.profile.get("login", {}).get("total", 0)))],
		["Play time", _play_time(int(pl.get("play_seconds", 0)))],
		["Adventure began", _date(int(pl.get("created", 0)))],
	]))


func _next_gem_rank() -> int:
	var every := int(Database.progression.get("rank_rewards", {}).get("gems_every", 5))
	return (GameManager.rank() / every + 1) * every


func _section(title: String, rows: Array) -> Control:
	var p := PanelFrame.make("plank", 16)
	p.name = "Section_" + title.replace(" ", "_")
	var v := UIKit.vbox(6)
	p.add_child(v)
	v.add_child(UIKit.label(title, UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	for r in rows:
		var h := UIKit.hbox(10)
		var l := UIKit.label(r[0], UIKit.T_BODY, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5)
		l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		h.add_child(l)
		h.add_child(UIKit.label(r[1], UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_RIGHT, 5))
		v.add_child(h)
	return p


func _play_time(s: int) -> String:
	return "%dh %02dm" % [s / 3600, (s % 3600) / 60]


func _date(ts: int) -> String:
	if ts <= 0:
		return "-"
	var d := Time.get_datetime_dict_from_unix_time(ts)
	return "%04d-%02d-%02d" % [d["year"], d["month"], d["day"]]


func _rename() -> void:
	var p := FantasyPopup.open(self, "YOUR NAME", 860)
	var e := LineEdit.new()
	e.name = "NameEdit"
	e.text = GameManager.profile["player"].get("name", "Wayfarer")
	e.max_length = 16
	e.custom_minimum_size = Vector2(700, 90)
	e.add_theme_font_size_override("font_size", UIKit.T_NAME)
	e.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(e)
	var row := UIKit.hbox(14)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var ok := FantasyButton.make("SAVE", "ember", Vector2(280, 110))
	ok.pressed.connect(func():
		GameManager.set_player_name(e.text)
		p.close()
		_build())
	row.add_child(ok)
	var c := FantasyButton.make("CANCEL", "stone", Vector2(280, 110))
	c.pressed.connect(p.close)
	row.add_child(c)
	p.content.add_child(row)
