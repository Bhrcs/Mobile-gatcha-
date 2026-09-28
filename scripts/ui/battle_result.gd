class_name BattleResult
extends Control
## Victory: a sequenced reveal -
##   VICTORY -> party cards -> EXP counts up and bars fill (LEVEL UP flash + sound)
##   -> gold counts up -> reward items pop into slots -> first-clear bonus ->
##   unlocks / rank -> CONTINUE.   Tap anywhere to fast-forward.
## A SKIP button (or a tap anywhere) fast-forwards; Enter continues on PC.
## Defeat: short - DEFEAT, one useful tip, then RETRY / EDIT SQUAD / STAGE SELECT.

signal next_pressed
signal retry_pressed
signal home_pressed
signal party_pressed
signal stage_select_pressed

var _content: VBoxContainer
var _panel: PanelFrame
var _fast := false
var sequence_done := false     # the reveal animation has finished
var _skip: FantasyButton
var _default: FantasyButton    # Enter presses this once the sequence is done

const FEATURE_NAMES := {"auto": "Auto Battle", "units": "Units", "squad": "Squad (5 heroes)", "training": "Training",
		"tower": "Elemental Towers", "evolution": "Evolution", "summon": "Embergate Summoning",
		"missions": "Missions", "world2": "World 2: Saltglass Reach"}


func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		_skip_now()


func _skip_now() -> void:
	_fast = true
	if is_instance_valid(_skip):
		_skip.visible = false


func _unhandled_key_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo and (e.keycode == KEY_ENTER or e.keycode == KEY_KP_ENTER):
		get_viewport().set_input_as_handled()
		if not sequence_done:
			_skip_now()
		elif is_instance_valid(_default) and not _default.disabled and UIManager.top_popup() == null:
			_default.pressed.emit()


func _add_skip() -> void:
	_skip = UIKit.btn("SKIP", "quiet", Vector2(200, 88))
	_skip.name = "SkipResults"
	_skip.position = Vector2(get_viewport_rect().size.x - 230, get_viewport_rect().size.y - 140 - UIKit.safe_bottom())
	_skip.pressed.connect(_skip_now)
	add_child(_skip)


func _step(t: float) -> void:
	await get_tree().create_timer(t * (0.15 if _fast else 1.0)).timeout


func _frame(title: String, color: Color, variant := "panel") -> void:
	var dim := ColorRect.new()
	dim.color = Color(0.03, 0.02, 0.05, 0.7)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(center)
	_panel = PanelFrame.make(variant, 30)
	_panel.custom_minimum_size = Vector2(1030, 0)
	center.add_child(_panel)
	_content = UIKit.vbox(16)
	_panel.add_child(_content)
	var t := UIKit.heading(title, 120, color)
	t.add_theme_constant_override("outline_size", 20)
	t.add_theme_color_override("font_outline_color", Color("#2a0a04"))
	t.name = "ResultTitle"
	_content.add_child(t)
	_panel.modulate.a = 0.0
	_panel.pivot_offset = Vector2(515, 300)
	_panel.scale = Vector2(0.9, 0.9)
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_panel, "modulate:a", 1.0, 0.2)
	tw.tween_property(_panel, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_BACK)
	t.pivot_offset = Vector2(485, 60)
	var shine := t.create_tween().set_loops()
	shine.tween_property(t, "modulate", Color(1.3, 1.2, 1.0), 0.7).set_trans(Tween.TRANS_SINE)
	shine.tween_property(t, "modulate", Color.WHITE, 0.7).set_trans(Tween.TRANS_SINE)


# ------------------------------------------------------------------ victory
func show_victory(summary: Dictionary, has_next: bool) -> void:
	_frame("VICTORY", UIKit.GOLD)
	UIKit.sparkle(self, Rect2(40, 200, 1000, 400), Color("#ffe08a"), 16)

	# star objectives
	var stage := Database.get_stage(GameManager.current_stage_id)
	var stars_box := UIKit.hbox(18)
	stars_box.alignment = BoxContainer.ALIGNMENT_CENTER
	stars_box.name = "StarRow"
	_content.add_child(stars_box)
	var star_nodes: Array = []
	var objs: Array = stage.get("stars", [])
	var run: Array = summary.get("stars_this_run", [])
	for i in objs.size():
		var col := UIKit.vbox(2)
		col.custom_minimum_size.x = 320
		var got := i < run.size() and bool(run[i])
		var ic := UIKit.icon("res://assets/icons/star_obj.png" if got else "res://assets/icons/star_obj_empty.png", 72)
		ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		ic.modulate.a = 0.0
		col.add_child(ic)
		var tl := UIKit.wrap_label(objs[i].get("text", ""), UIKit.T_SMALL, UIKit.TEXT if got else UIKit.MUTED)
		tl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		tl.custom_minimum_size.x = 300
		col.add_child(tl)
		stars_box.add_child(col)
		star_nodes.append([ic, got])

	# party with EXP bars
	var party_box := UIKit.vbox(8)
	_content.add_child(party_box)
	var rows: Array = []
	var compact: bool = summary.get("units", []).size() > 3
	for u in summary.get("units", []):
		var row := _unit_row(u, compact)
		row["node"].modulate.a = 0.0
		party_box.add_child(row["node"])
		rows.append(row)

	# counters
	var counters := UIKit.hbox(40)
	counters.alignment = BoxContainer.ALIGNMENT_CENTER
	var xp_l := _counter(counters, "res://assets/icons/xp.png", Color("#c0a8ff"))
	var gold_l := _counter(counters, "res://assets/icons/gold.png", UIKit.GOLD)
	counters.modulate.a = 0.0
	_content.add_child(counters)

	# reward slots
	var reward_row := HFlowContainer.new()
	reward_row.name = "RewardRow"
	reward_row.alignment = FlowContainer.ALIGNMENT_CENTER
	reward_row.add_theme_constant_override("h_separation", 14)
	reward_row.add_theme_constant_override("v_separation", 10)
	reward_row.custom_minimum_size = Vector2(960, 150)
	_content.add_child(reward_row)

	var extra := UIKit.vbox(6)
	_content.add_child(extra)

	var buttons := UIKit.hbox(20)
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	var b_next := FantasyButton.make("CONTINUE", "ember", Vector2(480, 130))
	b_next.name = "ContinueButton"
	b_next.add_theme_font_size_override("font_size", 50)
	var b_retry := FantasyButton.make("RETRY", "stone", Vector2(260, 110))
	b_next.pressed.connect(func(): next_pressed.emit())
	b_next.add_shine(2.0)
	b_retry.pressed.connect(func(): retry_pressed.emit())
	buttons.add_child(b_next)
	buttons.add_child(b_retry)
	buttons.modulate.a = 0.0
	b_next.disabled = true
	b_retry.disabled = true
	_content.add_child(buttons)
	_default = b_next
	_add_skip()

	# ---- sequence
	await _step(0.3)
	for sn in star_nodes:
		var ic: TextureRect = sn[0]
		ic.modulate.a = 1.0
		_pop(ic)
		if sn[1]:
			AudioManager.play_sfx("reward", 0.05, -8.0)
		await _step(0.14)
	await _step(0.1)
	for r in rows:
		create_tween().tween_property(r["node"], "modulate:a", 1.0, 0.18)
		AudioManager.play_sfx("unit_select", 0.03, -6.0)
		await _step(0.12)
	create_tween().tween_property(counters, "modulate:a", 1.0, 0.15)
	await _count(xp_l, int(summary.get("xp", 0)), "+%s EXP")
	for r in rows:
		_animate_xp(r)
	await _step(0.2)
	await _count(gold_l, int(summary.get("gold", 0)), "+%s G")
	AudioManager.play_sfx("reward", 0.02, -3.0)
	await _step(0.2)
	# items physically drop into slots
	var k := 0
	var items: Dictionary = summary.get("items", {})
	for item_id in items.keys():
		var it := Database.get_item(item_id)
		var ri := RewardItem.make(it.get("icon", ""), "x%d" % int(items[item_id]), "", 130)
		reward_row.add_child(ri)
		ri.pop(0.0)
		k += 1
		await _step(0.16)
	var fcr: Dictionary = summary.get("first_clear_reward", {})
	for item_id in fcr.get("items", {}).keys():
		var it2 := Database.get_item(item_id)
		var ri2 := RewardItem.make(it2.get("icon", ""), "x%d" % int(fcr["items"][item_id]), "FIRST", 130)
		reward_row.add_child(ri2)
		ri2.pop(0.0)
		await _step(0.16)
	if items.is_empty() and fcr.get("items", {}).is_empty():
		reward_row.add_child(UIKit.label("No items dropped this time.", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
	if summary.get("first_clear", false):
		await _step(0.15)
		var gems := int(fcr.get("gems", 0))
		var txt := "FIRST CLEAR  +%s G" % UIKit.format_number(int(summary.get("first_clear_gold", 0)))
		var fc := UIKit.hbox(12)
		fc.alignment = BoxContainer.ALIGNMENT_CENTER
		fc.add_child(UIKit.title_plate(txt, 40))
		if gems > 0:
			var gh := UIKit.hbox(6)
			gh.add_child(UIKit.icon("res://assets/icons/gem.png", 56))
			gh.add_child(UIKit.label("+%d" % gems, UIKit.T_NAME, Color("#9ae8ff"), HORIZONTAL_ALIGNMENT_LEFT, 8))
			fc.add_child(gh)
		fc.name = "FirstClear"
		extra.add_child(fc)
		_pop(fc)
		AudioManager.play_sfx("level_up", 0.0, -6.0)
	if int(summary.get("new_stars", 0)) > 0 and not summary.get("first_clear", false):
		extra.add_child(UIKit.label("NEW STAR%s EARNED!" % ("S" if int(summary["new_stars"]) > 1 else ""), UIKit.T_BODY, UIKit.GOLD,
				HORIZONTAL_ALIGNMENT_CENTER, 6))
	for u in summary.get("units", []):
		if u.get("burst_up", false):
			extra.add_child(UIKit.label("%s's Burst reached Lv.%d!" % [Database.get_character(u["char_id"]).get("name", ""),
					int(u["after"]["burst_level"])], UIKit.T_BODY, UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 6))
	for sid in summary.get("unlocked", []):
		extra.add_child(UIKit.label("NEW: %s" % GameManager.stage_label(sid).to_upper() + "  " + String(Database.get_stage(sid).get("name", sid)).to_upper(),
				UIKit.T_BODY, UIKit.GOOD, HORIZONTAL_ALIGNMENT_CENTER, 6))
	for f in summary.get("features", []):
		var fl := UIKit.label("UNLOCKED: %s" % String(FEATURE_NAMES.get(f, f)).to_upper(), UIKit.T_BODY, Color("#ffe08a"),
				HORIZONTAL_ALIGNMENT_CENTER, 6)
		extra.add_child(fl)
		_pop(fl)
	var gift: Dictionary = summary.get("gift", {})
	if gift.has("hero"):
		extra.add_child(UIKit.label("%s joins you!" % Database.get_character(gift["hero"]).get("name", ""), UIKit.T_NAME,
				UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	if int(gift.get("gems", 0)) > 0:
		extra.add_child(UIKit.label("Gift: +%d Gems" % int(gift["gems"]), UIKit.T_BODY, Color("#9ae8ff"), HORIZONTAL_ALIGNMENT_CENTER, 6))
	if summary.get("first_clear", false) and not has_next and not summary.get("tower", false):
		var world_id: String = stage.get("world_id", "")
		extra.add_child(UIKit.label("%s CLEARED!" % String(Database.worlds.get(world_id, {}).get("name", "")).to_upper(),
				UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8))
		var nxt := ""
		for w in Database.world_order:
			if Database.worlds[w].get("requires", "") == GameManager.current_stage_id:
				nxt = Database.worlds[w].get("name", "")
		extra.add_child(UIKit.label("New region open: %s" % nxt if not nxt.is_empty() else "More regions will open in a future update.",
				UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
	await _step(0.25)
	var ups: Array = summary.get("rank_ups", [])
	if not ups.is_empty():
		await RankUpOverlay.play(self, ups)
	create_tween().tween_property(buttons, "modulate:a", 1.0, 0.2)
	b_next.disabled = false
	b_retry.disabled = false
	sequence_done = true
	if is_instance_valid(_skip):
		_skip.queue_free()


func _counter(parent: Control, icon_path: String, color: Color) -> Label:
	var h := UIKit.hbox(10)
	h.add_child(UIKit.icon(icon_path, 64))
	var l := UIKit.label("+0", UIKit.T_HEAD, color, HORIZONTAL_ALIGNMENT_LEFT, 10)
	l.custom_minimum_size.x = 300
	h.add_child(l)
	parent.add_child(h)
	return l


func _count(l: Label, total: int, fmt: String) -> void:
	var t := 0.5 * (0.2 if _fast else 1.0)
	var tw := create_tween()
	tw.tween_method(func(v: float): l.text = fmt % UIKit.format_number(int(v)), 0.0, float(total), t)
	await tw.finished
	l.text = fmt % UIKit.format_number(total)
	_pop(l)


func _unit_row(u: Dictionary, compact := false) -> Dictionary:
	var def := Database.get_character(u["char_id"])
	var el: String = def.get("element", "neutral")
	var panel := PanelFrame.make("card_" + el, 8 if compact else 12)
	panel.name = "ResultUnit_%s" % u.get("uid", "")
	var h := UIKit.hbox(16)
	panel.add_child(h)
	var art := UIKit.portrait_art(def, Vector2(88, 88) if compact else Vector2(128, 128))
	h.add_child(art)
	var v := UIKit.vbox(6)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(v)
	var name_row := UIKit.hbox(16)
	var nm := UIKit.label(def.get("name", ""), UIKit.T_BODY, Color.WHITE, HORIZONTAL_ALIGNMENT_LEFT, 6)
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_row.add_child(nm)
	var lvl := UIKit.label("Lv.%d" % int(u["before"]["level"]), UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 8)
	name_row.add_child(lvl)
	v.add_child(name_row)
	var bar := ResourceBar.make("xp", 30)
	var before_need := Progression.xp_to_next(int(u["before"]["level"]))
	bar.ready.connect(func(): bar.set_values(int(u["before"]["exp"]), before_need, false))
	v.add_child(bar)
	var gains := UIKit.label("", UIKit.T_SMALL, UIKit.GOOD, HORIZONTAL_ALIGNMENT_LEFT, 5)
	v.add_child(gains)
	var stamp := UIKit.label("LEVEL UP!", UIKit.T_HEAD, Color("#fff0a0"), HORIZONTAL_ALIGNMENT_CENTER, 10)
	stamp.visible = false
	stamp.rotation = -0.1
	stamp.top_level = false
	stamp.size = Vector2(360, 60)
	stamp.pivot_offset = Vector2(180, 30)
	stamp.add_theme_color_override("font_outline_color", Color("#6a2a08"))
	var holder := Control.new()      # overlay so the stamp can sit on the card corner
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.custom_minimum_size = Vector2(0, 0)
	panel.add_child(holder)
	holder.add_child(stamp)
	panel.resized.connect(func(): stamp.position = Vector2(panel.size.x - 400, -40))
	return {"node": panel, "data": u, "bar": bar, "level": lvl, "gains": gains, "stamp": stamp, "art": art}


## Fills the XP bar, rolling over once per level gained (flash + LEVEL UP stamp).
func _animate_xp(row: Dictionary) -> void:
	var u: Dictionary = row["data"]
	var bar: ResourceBar = row["bar"]
	var level := int(u["before"]["level"])
	var start_level := level
	var n_ups: int = u["level_ups"].size()
	for up in u["level_ups"]:
		bar.set_values(bar.max_value, bar.max_value)
		await _step(0.35)
		if not is_inside_tree():
			return
		level = int(up["level"])
		row["level"].text = "Lv.%d > %d" % [start_level, level]
		# gains are shown as the total since the battle started (several levels add up)
		var total := GameManager.unit_stats({"char_id": u["char_id"], "level": level})
		var base := GameManager.unit_stats({"char_id": u["char_id"], "level": start_level})
		row["gains"].text = "HP +%d  ATK +%d  DEF +%d  REC +%d" % [int(total["hp"]) - int(base["hp"]), int(total["atk"]) - int(base["atk"]),
				int(total["def"]) - int(base["def"]), int(total["rec"]) - int(base["rec"])]
		AudioManager.play_sfx("level_up", 0.02, -2.0 if level - start_level == 1 else -6.0)
		var stamp: Label = row["stamp"]
		stamp.text = "LEVEL UP!" if n_ups <= 1 else "LEVEL UP x%d" % (level - start_level)
		stamp.visible = true
		_pop(stamp)
		_pop(row["level"])
		var card: Control = row["node"]
		var tw := card.create_tween()
		tw.tween_property(card, "modulate", Color(1.6, 1.5, 1.2), 0.08)
		tw.tween_property(card, "modulate", Color.WHITE, 0.3)
		bar.set_values(0, Progression.xp_to_next(level), false)
	var max_level := int(Database.get_character(u["char_id"]).get("max_level", 20))
	if level >= max_level:
		bar.set_values(1, 1, false)
		var evo = Database.get_character(u["char_id"]).get("evolution")
		row["gains"].text += "   MAX LEVEL" + ("  -  ready to Evolve!" if evo is Dictionary else "")
		return
	bar.set_values(float(u["after"]["exp"]), Progression.xp_to_next(level))


func _pop(c: Control) -> void:
	c.pivot_offset = c.size / 2
	c.scale = Vector2(1.4, 1.4)
	create_tween().tween_property(c, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_BACK)


# ------------------------------------------------------------------ defeat
func show_defeat() -> void:
	_frame("DEFEAT", UIKit.DANGER, "boss")
	var msg := UIKit.wrap_label("Your squad has fallen. Nothing is lost.", UIKit.T_BODY)
	msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	msg.custom_minimum_size.x = 940
	_content.add_child(msg)
	var tip := PanelFrame.make("inset", 16)
	tip.name = "DefeatTip"
	var th := UIKit.hbox(UIKit.SP_M)
	tip.add_child(th)
	th.add_child(UIKit.icon("res://assets/icons/info.png", 48))
	var tl := UIKit.wrap_label(defeat_tip(), UIKit.T_BODY, Color("#fff0c0"))
	tl.custom_minimum_size.x = 820
	th.add_child(tl)
	_content.add_child(tip)
	var buttons := UIKit.hbox(16)
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	var b_retry := UIKit.btn("RETRY", "primary", Vector2(300, 120))
	b_retry.name = "RetryButton"
	var b_party := UIKit.btn("EDIT SQUAD", "secondary", Vector2(320, 120))
	b_party.name = "EditSquadButton"
	var b_stage := UIKit.btn("STAGE SELECT", "quiet", Vector2(320, 120))
	b_stage.name = "StageSelectButton"
	b_stage.add_theme_font_size_override("font_size", UIKit.T_BODY)
	b_retry.pressed.connect(func(): retry_pressed.emit())
	b_party.pressed.connect(func(): party_pressed.emit())
	b_stage.pressed.connect(func(): stage_select_pressed.emit())
	for b in [b_retry, b_party, b_stage]:
		buttons.add_child(b)
	_content.add_child(buttons)
	var cost := int(Database.get_stage(GameManager.current_stage_id).get("energy", 0))
	_content.add_child(UIKit.label("Retry costs %d Energy (you have %d)." % [cost, GameManager.energy()], UIKit.T_SMALL, UIKit.MUTED,
			HORIZONTAL_ALIGNMENT_CENTER, 5))
	_default = b_retry
	sequence_done = true


## The most useful advice for this defeat: power first, then elements, then a general tip.
static func defeat_tip() -> String:
	var stage := Database.get_stage(GameManager.current_stage_id)
	var rec := int(stage.get("recommended_power", 0))
	var sp := GameManager.squad_power()
	if rec > 0 and sp < rec:
		return "Squad power %s is below the recommended %s. Train heroes with Wisps or evolve them, then try again." % [
				UIKit.format_number(sp), UIKit.format_number(rec)]
	var mine: Array = []
	for u in GameManager.party_units():
		var el: String = Database.get_character(u["char_id"]).get("element", "")
		if not mine.has(el):
			mine.append(el)
	var advice: Array = StageInfo.matchup_advice(mine, StageInfo.elements(stage))
	if advice[1]:
		return advice[0]
	var general := ["Swipe DOWN on a card to Guard when a foe shows DANGER - it halves the damage.",
			"Save Bursts for the last wave or the boss: swipe UP on a full card.",
			"A healer in the squad keeps everyone standing through long fights.",
			"Your leader's Leader Skill boosts the whole squad - pick a leader that matches your team."]
	return general[randi() % general.size()]
