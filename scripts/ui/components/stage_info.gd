class_name StageInfo
extends RefCounted
## Shared stage / tower-floor details used by the Quest map and the Towers:
## energy cost, recommended vs squad power, star objectives, possible drops and
## first-clear rewards. Also opens the PREPARE popup (squad check + DEPART).


## Enemy species that can appear (leader-element variants resolved for the current leader).
static func species(stage: Dictionary) -> Array:
	var out: Array = []
	var leader_el := "fire"
	var party := GameManager.party_units()
	if not party.is_empty():
		leader_el = Database.get_character(party[0]["char_id"]).get("element", "fire")
	for wave in stage.get("waves", []):
		for spawn in wave:
			var eid: String = spawn.get("enemy", "")
			if spawn.has("enemy_by_leader_element"):
				eid = spawn["enemy_by_leader_element"].get(leader_el, eid)
			if not eid.is_empty() and not out.has(eid):
				out.append(eid)
			var sm: Dictionary = Database.get_enemy(eid).get("ai", {}).get("summon", {})
			if not sm.is_empty() and not out.has(sm.get("enemy", "")):
				out.append(sm["enemy"])
	return out


static func elements(stage: Dictionary) -> Array:
	var out: Array = []
	for eid in species(stage):
		var el: String = Database.get_enemy(eid).get("element", "")
		if not el.is_empty() and not out.has(el):
			out.append(el)
	return out


## Every item this stage can drop (stage drops first, then enemy drop tables).
static func possible_drops(stage: Dictionary) -> Array:
	var out: Array = []
	for d in stage.get("drops", []):
		if not out.has(d["item"]):
			out.append(d["item"])
	for eid in species(stage):
		for item_id in Progression.table_items(Database.get_enemy(eid).get("drop_table", [])):
			if not out.has(item_id):
				out.append(item_id)
	out.sort_custom(func(a, b): return int(Database.get_item(a).get("sort", 99)) < int(Database.get_item(b).get("sort", 99)))
	return out


static func chip(label_text: String, value: String, color: Color = UIKit.TEXT, icon_path := "") -> Control:
	var h := UIKit.hbox(6)
	if not icon_path.is_empty():
		h.add_child(UIKit.icon(icon_path, 40))
	h.add_child(UIKit.label(label_text, UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	h.add_child(UIKit.label(value, UIKit.T_BODY, color, HORIZONTAL_ALIGNMENT_LEFT, 6))
	return h


## Energy / power / waves / foes row.
static func info_row(stage: Dictionary) -> Control:
	var info := UIKit.hbox(22)
	info.name = "StageInfoRow"
	var cost := int(stage.get("energy", 0))
	info.add_child(chip("", "%d" % cost, Color("#ffe07a") if GameManager.energy() >= cost else UIKit.DANGER,
			"res://assets/icons/energy.png"))
	var rec := int(stage.get("recommended_power", 0))
	var sp := GameManager.squad_power()
	info.add_child(chip("POWER", "%s / %s" % [UIKit.format_number(sp), UIKit.format_number(rec)],
			UIKit.GOOD if sp >= rec else (UIKit.EMBER if sp >= rec * 0.8 else UIKit.DANGER)))
	info.add_child(chip("WAVES", str(stage.get("waves", []).size())))
	var foes := UIKit.hbox(4)
	for el in elements(stage):
		foes.add_child(UIKit.orb(el, 40))
	info.add_child(foes)
	return info


## Three star objectives with earned state.
static func stars_row(stage: Dictionary) -> Control:
	var col := UIKit.vbox(2)
	col.name = "StarObjectives"
	var got: Array = GameManager.stage_stars(stage.get("id", ""))
	var objs: Array = stage.get("stars", [])
	for i in objs.size():
		var h := UIKit.hbox(8)
		var on := i < got.size() and bool(got[i])
		h.add_child(UIKit.icon("res://assets/icons/star_obj.png" if on else "res://assets/icons/star_obj_empty.png", 36))
		h.add_child(UIKit.label(objs[i].get("text", ""), UIKit.T_SMALL, UIKit.TEXT if on else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 5))
		col.add_child(h)
	return col


## Possible drops + first clear rewards.
static func rewards_row(stage: Dictionary, px := 88) -> Control:
	var col := UIKit.vbox(6)
	var cleared := GameManager.is_stage_cleared(stage.get("id", ""))
	var h := UIKit.hbox(10)
	h.name = "PossibleDrops"
	h.add_child(UIKit.label("POSSIBLE\nDROPS", UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var rewards: Dictionary = stage.get("rewards", {})
	var xp_i := RewardItem.make("res://assets/icons/xp.png", "%d" % int(rewards.get("xp", 0)), "", px)
	UIManager.attach_tooltip(xp_i, "EXP  %d" % int(rewards.get("xp", 0)), "Shared by the heroes in your squad.", "res://assets/icons/xp.png")
	var gold_i := RewardItem.make("res://assets/icons/gold.png", "%d" % int(rewards.get("gold", 0)), "", px)
	UIManager.attach_tooltip(gold_i, "Gold  %d" % int(rewards.get("gold", 0)), "Base Gold for a clear.", "res://assets/icons/gold.png")
	var items: Array = [xp_i, gold_i]
	for item_id in possible_drops(stage).slice(0, 7):
		var def := Database.get_item(item_id)
		var ri := RewardItem.make(def.get("icon", ""), "", "", px)
		ri.name = "Drop_" + item_id
		UIManager.attach_tooltip(ri, Database.item_name(item_id), String(def.get("description", "")), def.get("icon", ""))
		items.append(ri)
	for it in items:
		it.hidden_start = false
		h.add_child(it)
	col.add_child(h)
	var fc: Dictionary = stage.get("first_clear", {})
	if not cleared and (int(fc.get("gems", 0)) > 0 or not fc.get("items", {}).is_empty()):
		var f := UIKit.hbox(10)
		f.name = "FirstClearRewards"
		f.add_child(UIKit.label("FIRST CLEAR", UIKit.T_SMALL, UIKit.EMBER, HORIZONTAL_ALIGNMENT_LEFT, 5))
		if int(fc.get("gems", 0)) > 0:
			f.add_child(UIKit.icon("res://assets/icons/gem.png", 40))
			f.add_child(UIKit.label("+%d" % int(fc["gems"]), UIKit.T_BODY, Color("#9ae8ff"), HORIZONTAL_ALIGNMENT_LEFT, 6))
		if int(rewards.get("first_clear_gold", 0)) > 0:
			f.add_child(UIKit.icon("res://assets/icons/gold.png", 40))
			f.add_child(UIKit.label("+%d" % int(rewards["first_clear_gold"]), UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
		for item_id in fc.get("items", {}).keys():
			f.add_child(UIKit.icon(Database.get_item(item_id).get("icon", ""), 40))
			f.add_child(UIKit.label("x%d" % int(fc["items"][item_id]), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 5))
		col.add_child(f)
	return col


# ------------------------------------------------------------------ element matchup
## Squad elements vs the stage's foes, with one line of advice. Advice only:
## it never blocks departing.
static func matchup_row(party: Array, stage: Dictionary, host: Control) -> Control:
	var foes := elements(stage)
	var mine: Array = []
	for u in party:
		var el: String = Database.get_character(u["char_id"]).get("element", "")
		if not mine.has(el):
			mine.append(el)
	var box := PanelFrame.make("inset", 12)
	box.name = "ElementMatchup"
	var v := UIKit.vbox(UIKit.SP_S)
	box.add_child(v)
	var h := UIKit.hbox(UIKit.SP_M)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.add_child(UIKit.label("SQUAD", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	for el in mine:
		h.add_child(UIKit.orb(el, 44))
	h.add_child(UIKit.label("VS", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 6))
	h.add_child(UIKit.label("FOES", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	for el in foes:
		h.add_child(UIKit.orb(el, 44))
	var chart := UIKit.btn("", "quiet", Vector2(88, 88), "res://assets/icons/element_chart.png")
	chart.name = "MatchupChart"
	chart.tooltip_text = "Element chart"
	chart.pressed.connect(func(): ElementChart.popup(host))
	h.add_child(chart)
	v.add_child(h)
	var advice := matchup_advice(mine, foes)
	var line := UIKit.hbox(UIKit.SP_S)
	line.alignment = BoxContainer.ALIGNMENT_CENTER
	line.add_child(UIKit.icon("res://assets/icons/warning.png" if advice[1] else "res://assets/icons/check.png", 36))
	var l := UIKit.wrap_label(advice[0], UIKit.T_SMALL, UIKit.EMBER if advice[1] else UIKit.GOOD)
	l.name = "MatchupAdvice"
	l.custom_minimum_size.x = 780
	line.add_child(l)
	v.add_child(line)
	return box


## Returns [text, is_warning].
static func matchup_advice(mine: Array, foes: Array) -> Array:
	var uncovered: Array = []
	for f in foes:
		var covered := false
		for m in mine:
			if Database.element_multiplier(m, f) > 1.0:
				covered = true
		if not covered:
			uncovered.append(f)
	var threatened: Array = []
	for m in mine:
		for f in foes:
			if Database.element_multiplier(f, m) > 1.0 and not threatened.has(m):
				threatened.append(m)
	if not uncovered.is_empty():
		var f: String = uncovered[0]
		var counter := ""
		for el in Database.elements.keys():
			if Database.element_multiplier(el, f) > 1.0:
				counter = Database.element_name(el)
		return ["No hero in your squad beats %s foes. %s heroes deal extra damage to them." % [Database.element_name(f), counter], true]
	if not threatened.is_empty() and threatened.size() == mine.size():
		return ["Every hero in your squad is weak to a foe here. Consider mixing elements.", true]
	return ["Good matchup: your squad has an advantage against these foes.", false]


# ------------------------------------------------------------------ prepare
## Squad check before departing. Power is advice only - it never blocks.
static func open_prepare(parent: Control, stage_id: String, back_scene := "stage_select") -> FantasyPopup:
	var stage := Database.get_stage(stage_id)
	var p := FantasyPopup.open(parent, "PREPARE", 1000)
	p.name = "PreparePopup"
	var sname: String = stage.get("name", "")
	p.content.add_child(UIKit.label(GameManager.stage_label(stage_id) if sname.begins_with("Floor") else "%s  -  %s" % [GameManager.stage_label(stage_id), sname], UIKit.T_BODY,
			Color("#fff0c0"), HORIZONTAL_ALIGNMENT_CENTER, 6))
	var slots := UIKit.hbox(8)
	slots.alignment = BoxContainer.ALIGNMENT_CENTER
	slots.name = "PrepareSquad"
	var party := GameManager.party_units()
	for i in GameManager.max_party_size():
		var cell := PanelFrame.make("slot", 6)
		cell.custom_minimum_size = Vector2(176, 200)
		var v := UIKit.vbox(2)
		v.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_child(v)
		if i < party.size():
			var def := Database.get_character(party[i]["char_id"])
			var art := UIKit.portrait_art(def, Vector2(160, 140))
			v.add_child(art)
			v.add_child(UIKit.label("Lv.%d" % int(party[i]["level"]), UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 5))
			if i == 0:
				var em := UIKit.icon("res://assets/icons/leader.png", 40)
				em.position = Vector2(2, 2)
				art.add_child(em)
		else:
			var l := UIKit.label("EMPTY", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
			l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			l.size_flags_vertical = Control.SIZE_EXPAND_FILL
			v.add_child(l)
		slots.add_child(cell)
	p.content.add_child(slots)
	var ls := GameManager.leader_skill()
	if not ls.is_empty():
		var lr := UIKit.hbox(10)
		lr.add_child(UIKit.icon("res://assets/icons/leader.png", 40))
		var lt := UIKit.wrap_label("LEADER: %s - %s" % [ls.get("name", ""), ls.get("description", "")], UIKit.T_SMALL, UIKit.GOLD)
		lt.custom_minimum_size.x = 860
		lr.add_child(lt)
		p.content.add_child(lr)
	var rec := int(stage.get("recommended_power", 0))
	var sp := GameManager.squad_power()
	var pw := UIKit.hbox(14)
	pw.alignment = BoxContainer.ALIGNMENT_CENTER
	pw.add_child(UIKit.label("SQUAD POWER %s" % UIKit.format_number(sp), UIKit.T_BODY,
			UIKit.GOOD if sp >= rec else UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 6))
	pw.add_child(UIKit.label("RECOMMENDED %s" % UIKit.format_number(rec), UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 6))
	p.content.add_child(pw)
	if sp < rec:
		var warn := UIKit.wrap_label("Your squad is below the recommended power. You can still depart - training, evolving or adding heroes will help.",
				UIKit.T_SMALL, UIKit.EMBER)
		warn.name = "PowerWarning"
		warn.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		warn.custom_minimum_size.x = 900
		p.content.add_child(warn)
	p.content.add_child(matchup_row(party, stage, p))
	var cost := int(stage.get("energy", 0))
	p.content.add_child(UIKit.label("Energy: %d / %d   (cost %d)" % [GameManager.energy(), GameManager.max_energy(), cost],
			UIKit.T_BODY, Color("#ffe07a") if GameManager.energy() >= cost else UIKit.DANGER, HORIZONTAL_ALIGNMENT_CENTER, 6))
	var row := UIKit.hbox(16)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var edit := FantasyButton.make("EDIT SQUAD", "steel", Vector2(320, 116))
	edit.name = "EditSquad"
	if GameManager.feature_unlocked("squad"):
		edit.pressed.connect(func():
			p.close()
			SceneRouter.remember({"highlight": stage_id, "prepare": true})
			SceneRouter.go("squad", {"return_to": back_scene, "stage_id": stage_id}))
	else:
		edit.modulate = Color(0.55, 0.53, 0.58)
		edit.pressed.connect(func(): UIKit.toast(parent, "Squad unlocks after clearing %s." % GameManager.feature_unlock_label("squad"),
				UIKit.MUTED))
	row.add_child(edit)
	var depart := FantasyButton.make("DEPART", "ember", Vector2(360, 130))
	depart.name = "DepartButton"
	depart.add_theme_font_size_override("font_size", UIKit.T_NAME)
	depart.add_shine()
	depart.pressed.connect(func():
		var r: Dictionary = GameManager.try_start_stage(stage_id)
		if r["ok"]:
			p.close()
			AudioManager.play_sfx("energy", 0.02, -4.0)
			SceneRouter.go("battle", {"stage_id": stage_id})
		elif r["reason"] == "energy":
			EnergyPopup.open(parent, stage_id)
		else:
			UIKit.toast(parent, "This stage is locked.", UIKit.DANGER))
	row.add_child(depart)
	p.content.add_child(row)
	var cancel := FantasyButton.make("CANCEL", "stone", Vector2(280, 96))
	cancel.name = "CancelPrepare"
	cancel.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	cancel.pressed.connect(p.close)
	p.content.add_child(cancel)
	return p
