extends ScreenBase
## Unit detail: showcase, identity (lock / favourite), stats + power, passive,
## leader skill, Burst (level, EXP, what the next level improves, Burst training),
## normal attack, evolution path, TRAIN (wisps + gold, with a preview),
## EVOLVE (opens the evolution screen), SQUAD and lore.

const STAT_KEYS := ["hp", "atk", "def", "rec"]
const CLASS_COLORS := {"ATTACKER": Color("#b8401e"), "HEALER": Color("#2a6ab0"), "GUARDIAN": Color("#3a7a2a"),
		"SUPPORT": Color("#9a6a1a"), "BREAKER": Color("#6a2a8a")}
const WISPS := ["ember_wisp", "tide_wisp", "verdant_wisp", "radiant_wisp"]

var uid := ""
var unit: Dictionary = {}
var body: VBoxContainer
var scroll: ScrollContainer
var _sprite: UnitSpriteDisplay


func _ready() -> void:
	if not require_profile():
		return
	uid = SceneRouter.params.get("uid", "")
	if GameManager.get_unit(uid).is_empty() and not GameManager.owned_units().is_empty():
		uid = GameManager.owned_units()[0]["uid"]
	var back: String = SceneRouter.params.get("back", "units" if GameManager.feature_unlocked("units") else "home")
	back_fallback = back
	var area := build_frame("bg_camp", "UNIT DETAILS", "units", Callable(), 0.6)
	scroll = ScrollContainer.new()
	scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	area.add_child(scroll)
	body = UIKit.vbox(14)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	GameManager.mark_unit_seen(uid)
	_build()
	if SceneRouter.params.get("open_train", false) and GameManager.feature_unlocked("training"):
		_open_train.call_deferred()


## Stat bar reference: best value any unit reaches at its level cap (+15%).
static func stat_reference(key: String) -> int:
	var best := 1
	for id in Database.characters.keys():
		var def := Database.get_character(id)
		var s := Progression.unit_stats(def, int(def.get("max_level", 20)))
		best = max(best, int(s.get(key, 0)))
	return int(best * 1.15)


func _build() -> void:
	var keep_scroll := scroll.scroll_vertical
	for ch in body.get_children():
		ch.queue_free()
	unit = GameManager.get_unit(uid)
	var def := Database.get_character(unit.get("char_id", ""))
	var el: String = def.get("element", "neutral")
	var stats := GameManager.unit_stats(unit)
	var max_level := int(def.get("max_level", 20))
	var level := int(unit.get("level", 1))

	# ---- showcase: portrait + animated sprite on element-lit card
	var show := PanelFrame.make("card_%s_lit" % el, 12)
	show.custom_minimum_size = Vector2(0, 500)
	body.add_child(show)
	var stage := Control.new()
	stage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	show.add_child(stage)
	var art := UIKit.portrait_art(def, Vector2(460, 460))
	art.position = Vector2(4, 4)
	art.size = Vector2(460, 460)
	stage.add_child(art)
	_sprite = UnitSpriteDisplay.new()
	_sprite.setup(def.get("sprite", {}), 8.0, true)
	_sprite.position = Vector2(740 - _sprite.custom_minimum_size.x / 2.0, 450 - _sprite.custom_minimum_size.y)
	_sprite.size = _sprite.custom_minimum_size
	_sprite.name = "ShowcaseSprite"
	stage.add_child(_sprite)
	UIKit.on_tap(_sprite, _poke_sprite)
	var tap_hint := UIKit.label("TAP TO ANIMATE", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 5)
	tap_hint.position = Vector2(540, 452)
	tap_hint.size = Vector2(400, 30)
	stage.add_child(tap_hint)
	var flags := UIKit.hbox(8)
	flags.position = Vector2(720, 8)
	flags.add_child(_flag_button("locked", "res://assets/icons/lock.png", "LOCK"))
	flags.add_child(_flag_button("favorite", "res://assets/icons/fav.png", "FAV"))
	stage.add_child(flags)
	if int(def.get("rarity", 3)) >= 5:
		UIKit.sparkle(stage, Rect2(0, 0, 1000, 460))
	UIKit.sparkle(stage, Rect2(560, 120, 400, 320), Database.element_color(el).lightened(0.4), 5)

	# ---- identity plate
	var plate := PanelFrame.make("plank", 14)
	body.add_child(plate)
	var pv := UIKit.vbox(8)
	plate.add_child(pv)
	var r1 := UIKit.hbox(14)
	r1.add_child(UIKit.orb(el, 64))
	var nm := UIKit.label(def.get("name", ""), UIKit.T_HEAD, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_LEFT, 10)
	nm.name = "UnitName"
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nm.clip_text = true
	r1.add_child(nm)
	r1.add_child(UIKit.stars(int(def.get("rarity", 3)), 48))
	pv.add_child(r1)
	var r2 := UIKit.hbox(16)
	var cls: String = def.get("class", "ATTACKER")
	r2.add_child(UIKit.tag(cls, CLASS_COLORS.get(cls, Color("#5a4a6a"))))
	r2.add_child(UIKit.label(Database.element_name(el), UIKit.T_BODY, Database.element_color(el).lightened(0.3), HORIZONTAL_ALIGNMENT_LEFT, 6))
	r2.add_child(UIKit.label("POWER %s" % UIKit.format_number(GameManager.unit_power(unit)), UIKit.T_BODY, UIKit.SKY,
			HORIZONTAL_ALIGNMENT_LEFT, 6))
	r2.add_child(UIKit.spacer())
	var lv_text := "Lv.MAX (%d)" % max_level if level >= max_level else "Lv.%d / %d" % [level, max_level]
	var lvl_l := UIKit.label(lv_text, UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 8)
	lvl_l.name = "LevelLabel"
	r2.add_child(lvl_l)
	pv.add_child(r2)
	var r3 := UIKit.hbox(12)
	r3.add_child(UIKit.label("EXP", UIKit.T_SMALL, UIKit.EMBER, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var xb := ResourceBar.make("xp", 30)
	xb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	xb.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var exp_now := int(unit.get("exp", 0))
	var exp_need := Progression.xp_to_next(level) if level < max_level else 1
	xb.ready.connect(func(): xb.set_values(exp_now if level < max_level else 1, exp_need, false))
	r3.add_child(xb)
	r3.add_child(UIKit.label("NEXT %d" % (exp_need - exp_now) if level < max_level else "MAX", UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_RIGHT, 5))
	pv.add_child(r3)

	# ---- actions
	var buttons := UIKit.hbox(12)
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	body.add_child(buttons)
	var b_train := FantasyButton.make("TRAIN" if level < max_level else "MAX LEVEL", "gold", Vector2(330, 120),
			"res://assets/icons/radiant_wisp.png")
	b_train.name = "TrainButton"
	if not GameManager.feature_unlocked("training"):
		b_train.modulate = Color(0.55, 0.53, 0.58)
		b_train.pressed.connect(func(): UIKit.toast(self, "Training unlocks after clearing %s." % GameManager.feature_unlock_label("training"), UIKit.MUTED))
	else:
		b_train.disabled = level >= max_level
		b_train.pressed.connect(_open_train)
	buttons.add_child(b_train)
	var evo = def.get("evolution")
	var b_evo := FantasyButton.make("EVOLVE" if evo is Dictionary else "FINAL FORM", "ember", Vector2(330, 120))
	b_evo.name = "EvolveButton"
	if not evo is Dictionary:
		b_evo.disabled = true
	elif not GameManager.feature_unlocked("evolution"):
		b_evo.modulate = Color(0.55, 0.53, 0.58)
		b_evo.pressed.connect(func(): UIKit.toast(self, "Evolution unlocks after clearing %s." % GameManager.feature_unlock_label("evolution"), UIKit.MUTED))
	else:
		b_evo.pressed.connect(func(): SceneRouter.go("evolve", {"uid": uid}))
		if GameManager.can_evolve(uid):
			UIKit.badge(b_evo)
			b_evo.add_shine()
	buttons.add_child(b_evo)
	var b_squad := FantasyButton.make("SQUAD", "steel", Vector2(280, 120))
	b_squad.name = "SquadButton"
	if GameManager.feature_unlocked("squad"):
		b_squad.pressed.connect(func(): SceneRouter.go("squad", {"from_uid": uid}))
	else:
		b_squad.modulate = Color(0.55, 0.53, 0.58)
		b_squad.pressed.connect(func(): UIKit.toast(self, "Squad unlocks after clearing %s." % GameManager.feature_unlock_label("squad"), UIKit.MUTED))
	buttons.add_child(b_squad)
	if level >= max_level and evo is Dictionary:
		var note := UIKit.label("Max level reached - evolve to grow stronger!", UIKit.T_SMALL, UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 5)
		body.add_child(note)

	# ---- stats
	var sp := PanelFrame.make("panel", 24)
	body.add_child(sp)
	var sv := UIKit.vbox(10)
	sp.add_child(sv)
	sv.add_child(UIKit.label("STATS", UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	for key in STAT_KEYS:
		var row := StatRow.make(key.to_upper(), int(stats.get(key, 0)), stat_reference(key))
		row.name = "Stat_" + key
		sv.add_child(row)

	# ---- passive + leader skill
	body.add_child(_ability_panel("PASSIVE", def.get("passive", {}), "res://assets/icons/star_obj.png", UIKit.SKY))
	body.add_child(_ability_panel("LEADER SKILL", def.get("leader_skill", {}), "res://assets/icons/leader.png", UIKit.GOLD))

	# ---- skills
	body.add_child(_burst_panel(def))
	body.add_child(_skill_panel("ATTACK", def.get("normal_attack", ""), false))

	# ---- evolution path
	body.add_child(_evolution_path(def))

	# ---- lore
	var lp := PanelFrame.make("inset", 22)
	body.add_child(lp)
	var lv := UIKit.vbox(8)
	lp.add_child(lv)
	lv.add_child(UIKit.label("LORE", UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var lore := UIKit.wrap_label(def.get("lore", ""), UIKit.T_BODY, Color("#e0d6c6"))
	lore.custom_minimum_size.x = 960
	lv.add_child(lore)
	body.add_child(UIKit.spacer(false, false))
	await get_tree().process_frame
	if is_instance_valid(scroll):
		scroll.scroll_vertical = keep_scroll


func _flag_button(flag: String, icon_path: String, text: String) -> Control:
	var on := bool(unit.get(flag, false))
	var b := FantasyButton.make(text, "gold" if on else "stone", Vector2(130, 72), icon_path)
	b.name = "Flag_" + flag
	b.add_theme_font_size_override("font_size", 22)
	b.add_theme_constant_override("icon_max_width", 32)
	b.tooltip_text = "Locked heroes are protected from future selling/fusing." if flag == "locked" else "Favourites sort first."
	b.pressed.connect(func():
		GameManager.set_unit_flag(uid, flag, not bool(GameManager.get_unit(uid).get(flag, false)))
		_build())
	return b


func _ability_panel(kind: String, data: Dictionary, icon_path: String, color: Color) -> Control:
	var p := PanelFrame.make("inset", 18)
	p.name = kind.replace(" ", "")
	var v := UIKit.vbox(6)
	p.add_child(v)
	var head := UIKit.hbox(12)
	head.add_child(UIKit.icon(icon_path, 40))
	head.add_child(UIKit.label(kind, UIKit.T_SMALL, color, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var n := UIKit.label(data.get("name", "-"), UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6)
	n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(n)
	v.add_child(head)
	var d := UIKit.wrap_label(data.get("description", ""), UIKit.T_BODY, Color("#e8dece"))
	d.custom_minimum_size.x = 960
	v.add_child(d)
	return p


func _burst_panel(def: Dictionary) -> Control:
	var p := _skill_panel("BURST", def.get("burst", ""), true)
	var v: VBoxContainer = p.get_child(0)
	var sk := Database.get_skill(def.get("burst", ""))
	var bl := int(unit.get("burst_level", 1))
	var bmax := int(Database.balance("burst_levels", "max", 5))
	var bxp := int(unit.get("burst_xp", 0))
	var row := UIKit.hbox(12)
	row.name = "BurstLevel"
	row.add_child(UIKit.label("BURST Lv.%d%s" % [bl, " (MAX)" if bl >= bmax else ""], UIKit.T_BODY, UIKit.EMBER, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var bar := ResourceBar.make("burst", 24)
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var lo := Progression.burst_xp_for_level(bl)
	var hi := Progression.burst_xp_for_level(mini(bl + 1, bmax))
	bar.ready.connect(func(): bar.set_values(bxp - lo if bl < bmax else 1, maxi(hi - lo, 1) if bl < bmax else 1, false))
	row.add_child(bar)
	row.add_child(UIKit.label("%d/%d" % [bxp - lo, hi - lo] if bl < bmax else "MAX", UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_RIGHT, 5))
	v.add_child(row)
	var cost := Progression.burst_cost(sk, bl)
	var info := "Gauge cost %d.  %s" % [int(cost), Progression.burst_level_text(sk)]
	var il := UIKit.wrap_label(info, UIKit.T_SMALL, UIKit.MUTED)
	il.custom_minimum_size.x = 960
	v.add_child(il)
	v.add_child(UIKit.label("Burst EXP: +1 each time this hero uses Burst in a won battle.", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4))
	if bl < bmax:
		var br := UIKit.hbox(12)
		var sig := GameManager.item_count("spark_sigil")
		var b1 := FantasyButton.make("SPARK SIGIL (%d)" % sig, "steel", Vector2(420, 90), "res://assets/icons/spark_sigil.png")
		b1.name = "BurstSigil"
		b1.add_theme_font_size_override("font_size", 26)
		b1.disabled = sig <= 0
		b1.pressed.connect(func(): _burst_train("sigil"))
		br.add_child(b1)
		var cost_s := int(Database.balance("burst_levels", "shards_per_step", 20))
		var b2 := FantasyButton.make("%d SOUL SHARDS" % cost_s, "steel", Vector2(420, 90), "res://assets/icons/soul_shard.png")
		b2.name = "BurstShards"
		b2.add_theme_font_size_override("font_size", 26)
		b2.disabled = GameManager.soul_shards() < cost_s
		b2.pressed.connect(func(): _burst_train("shards"))
		br.add_child(b2)
		v.add_child(br)
		v.add_child(UIKit.label("You have %d Soul Shards (earned from duplicate summons)." % GameManager.soul_shards(), UIKit.T_SMALL,
				UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4))
	return p


func _burst_train(method: String) -> void:
	var r := GameManager.train_burst(uid, method)
	if not r.get("ok", false):
		UIKit.toast(self, r.get("reason", "Cannot train."), UIKit.DANGER)
		return
	AudioManager.play_sfx("level_up" if int(r["after"]) > int(r["before"]) else "reward")
	UIKit.toast(self, ("BURST LEVEL UP! Lv.%d" % int(r["after"])) if int(r["after"]) > int(r["before"]) else "+%d Burst EXP" % int(r["xp"]),
			UIKit.GOLD)
	_build()


func _skill_panel(kind: String, skill_id: String, is_burst: bool) -> Control:
	var sk := Database.get_skill(skill_id)
	var p := PanelFrame.make("panel" if is_burst else "inset", 24 if is_burst else 20)
	p.name = "Skill_" + kind
	var v := UIKit.vbox(8)
	p.add_child(v)
	var head := UIKit.hbox(14)
	head.add_child(UIKit.icon("res://assets/icons/burst.png" if is_burst else "res://assets/icons/sword.png", 48))
	head.add_child(UIKit.label(kind, UIKit.T_BODY, UIKit.SKY if is_burst else UIKit.EMBER, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var n := UIKit.label(sk.get("name", ""), UIKit.T_NAME, UIKit.GOLD if is_burst else UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 8)
	n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(n)
	v.add_child(head)
	var d := UIKit.wrap_label(sk.get("description", ""), UIKit.T_BODY, Color("#e8dece"))
	d.custom_minimum_size.x = 960
	v.add_child(d)
	var granted: Array = []
	for eff in sk.get("effects", []):
		if eff.get("type", "") == "status":
			granted.append(eff)
	if not granted.is_empty():
		var row := HFlowContainer.new()
		row.add_theme_constant_override("h_separation", 12)
		row.add_child(UIKit.label("EFFECTS", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 5))
		for eff in granted:
			var sid: String = eff.get("status", "")
			var ic := StatusIcon.make(sid, 0, float(eff.get("value", 0.0)), 48)
			row.add_child(ic)
			var sdef := Database.get_status(sid)
			var txt := "%s %dT" % [sdef.get("name", sid), int(eff.get("duration", 0))]
			if float(eff.get("chance", 1.0)) < 1.0:
				txt += " (%d%%)" % int(round(float(eff["chance"]) * 100))
			row.add_child(UIKit.label(txt, UIKit.T_SMALL, Color(sdef.get("color", "#ffffff")), HORIZONTAL_ALIGNMENT_LEFT, 5))
		v.add_child(row)
	return p


func _evolution_path(def: Dictionary) -> Control:
	var p := PanelFrame.make("inset", 18)
	p.name = "EvolutionPath"
	var v := UIKit.vbox(8)
	p.add_child(v)
	v.add_child(UIKit.label("EVOLUTION PATH", UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var row := UIKit.hbox(8)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var forms := Database.family_forms(def.get("family", ""))
	for i in forms.size():
		var fd := Database.get_character(forms[i])
		var cell := UIKit.vbox(2)
		var frame := PanelFrame.make("rarity_%d" % clampi(int(fd.get("rarity", 3)), 3, 6), 6)
		frame.add_child(UIKit.portrait_art(fd, Vector2(180, 180)))
		if forms[i] != def.get("id", ""):
			frame.modulate = Color(0.7, 0.7, 0.75)
		cell.add_child(frame)
		cell.add_child(UIKit.label(String(fd.get("name", "")).get_slice(" ", 1) if " " in fd.get("name", "") else fd.get("name", ""),
				UIKit.T_SMALL, UIKit.GOLD if forms[i] == def.get("id", "") else UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 5))
		cell.add_child(UIKit.stars(int(fd.get("rarity", 3)), 20))
		row.add_child(cell)
		if i < forms.size() - 1:
			row.add_child(UIKit.label(">", UIKit.T_HEAD, UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 6))
	v.add_child(row)
	return p


func _poke_sprite() -> void:
	if _sprite == null or _sprite.sprite == null:
		return
	var anim := "attack" if randf() < 0.6 else "victory"
	_sprite.play(anim)
	AudioManager.play_sfx("unit_select", 0.05, -4.0)
	if not _sprite.sprite.animation_finished.is_connected(_back_to_idle):
		_sprite.sprite.animation_finished.connect(_back_to_idle)


func _back_to_idle() -> void:
	if _sprite and _sprite.sprite:
		_sprite.play("idle")


# ------------------------------------------------------------------ training
var _train_popup: FantasyPopup
var _train_sel: Dictionary = {}


## TRAIN: pick wisps (same-element wisps give +50%), see the new level, stat gains
## and gold cost, then confirm.
func _open_train() -> void:
	_train_sel = {}
	_train_popup = FantasyPopup.open(self, "TRAIN", 1000)
	_train_popup.name = "TrainPopup"
	_render_train()


func _render_train() -> void:
	var c := _train_popup.content
	for ch in c.get_children():
		ch.queue_free()
	var def := Database.get_character(unit.get("char_id", ""))
	var pv := GameManager.preview_training(uid, _train_sel)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 16)
	grid.add_theme_constant_override("v_separation", 10)
	grid.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var any := false
	for w in WISPS:
		var have := GameManager.item_count(w)
		var cell := PanelFrame.make("plank", 10)
		cell.name = "Wisp_" + w
		cell.custom_minimum_size = Vector2(450, 0)
		var h := UIKit.hbox(8)
		cell.add_child(h)
		h.add_child(UIKit.icon(Database.get_item(w).get("icon", ""), 64))
		var vv := UIKit.vbox(0)
		vv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		vv.add_child(UIKit.label(Database.item_name(w), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 5))
		var xp := Progression.item_xp(w, def)
		var bonus: bool = Database.get_item(w).get("element", "") == def.get("element", "-")
		vv.add_child(UIKit.label("+%d EXP%s   own %d" % [xp, "  x1.5!" if bonus else "", have], UIKit.T_SMALL,
				UIKit.GOOD if bonus else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4))
		h.add_child(vv)
		var n := int(_train_sel.get(w, 0))
		var minus := FantasyButton.make("-", "stone", Vector2(64, 64))
		minus.name = "Minus"
		minus.disabled = n <= 0
		minus.pressed.connect(func(): _change_sel(w, -1))
		h.add_child(minus)
		h.add_child(UIKit.label(str(n), UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 6))
		var plus := FantasyButton.make("+", "steel", Vector2(64, 64))
		plus.name = "Plus"
		plus.disabled = n >= have or bool(pv.get("at_cap", false)) or int(pv.get("wasted_xp", 0)) > 0
		plus.pressed.connect(func(): _change_sel(w, 1))
		h.add_child(plus)
		if have <= 0:
			cell.modulate = Color(0.6, 0.6, 0.65)
		else:
			any = true
		grid.add_child(cell)
	c.add_child(grid)
	if not any:
		var l := UIKit.wrap_label("No wisps yet. Wisps drop from stages, bosses, towers, missions and login rewards.", UIKit.T_BODY, UIKit.MUTED)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.custom_minimum_size.x = 900
		c.add_child(l)
	# preview
	var prev := PanelFrame.make("inset", 16)
	prev.name = "TrainPreview"
	var pvv := UIKit.vbox(6)
	prev.add_child(pvv)
	var lv_line := "Lv.%d  >  Lv.%d" % [int(pv.get("level_before", 1)), int(pv.get("level_after", 1))]
	var ll := UIKit.label(lv_line, UIKit.T_HEAD, UIKit.GOLD if int(pv.get("level_after", 1)) > int(pv.get("level_before", 1)) else UIKit.TEXT,
			HORIZONTAL_ALIGNMENT_CENTER, 10)
	ll.name = "PreviewLevel"
	pvv.add_child(ll)
	var g: Dictionary = pv.get("gains", {})
	pvv.add_child(UIKit.label("HP +%d   ATK +%d   DEF +%d   REC +%d" % [int(g.get("hp", 0)), int(g.get("atk", 0)), int(g.get("def", 0)),
			int(g.get("rec", 0))], UIKit.T_BODY, UIKit.GOOD, HORIZONTAL_ALIGNMENT_CENTER, 6))
	var cost := int(pv.get("gold", 0))
	var enough := GameManager.gold() >= cost
	pvv.add_child(UIKit.label("+%s EXP   Cost %s Gold   (you have %s)" % [UIKit.format_number(int(pv.get("used_xp", 0))),
			UIKit.format_number(cost), UIKit.format_number(GameManager.gold())], UIKit.T_BODY, UIKit.TEXT if enough else UIKit.DANGER,
			HORIZONTAL_ALIGNMENT_CENTER, 6))
	if int(pv.get("wasted_xp", 0)) > 0:
		pvv.add_child(UIKit.label("Reaches the level cap - extra EXP would be wasted.", UIKit.T_SMALL, UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 5))
	c.add_child(prev)
	var row := UIKit.hbox(14)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var auto := FantasyButton.make("AUTO SELECT", "steel", Vector2(300, 110))
	auto.name = "AutoSelect"
	auto.add_theme_font_size_override("font_size", 30)
	auto.pressed.connect(_auto_select)
	row.add_child(auto)
	var ok := FantasyButton.make("TRAIN", "gold", Vector2(300, 120))
	ok.name = "ConfirmTrain"
	ok.disabled = _train_sel.is_empty() or not enough or bool(pv.get("at_cap", false))
	ok.pressed.connect(_confirm_train)
	row.add_child(ok)
	var cancel := FantasyButton.make("CLOSE", "stone", Vector2(240, 110))
	cancel.pressed.connect(_train_popup.close)
	row.add_child(cancel)
	c.add_child(row)


func _change_sel(w: String, d: int) -> void:
	var n := clampi(int(_train_sel.get(w, 0)) + d, 0, GameManager.item_count(w))
	if n <= 0:
		_train_sel.erase(w)
	else:
		_train_sel[w] = n
	AudioManager.play_sfx("click", 0.03, -6.0)
	_render_train()


## Picks wisps (best element match first) until the next level cap or gold runs out.
func _auto_select() -> void:
	_train_sel = {}
	var def := Database.get_character(unit.get("char_id", ""))
	var order := WISPS.duplicate()
	order.sort_custom(func(a, b): return Progression.item_xp(a, def) < Progression.item_xp(b, def))
	var need := Progression.xp_to_cap(unit)
	var got := 0
	for w in order:
		var have := GameManager.item_count(w)
		var xp := Progression.item_xp(w, def)
		while have > 0 and got < need:
			var trial := _train_sel.duplicate()
			trial[w] = int(trial.get(w, 0)) + 1
			if Progression.training_gold(mini(got + xp, need)) > GameManager.gold():
				break
			_train_sel = trial
			got += xp
			have -= 1
	if _train_sel.is_empty():
		UIKit.toast(self, "No wisps to use (or not enough Gold).", UIKit.MUTED)
	_render_train()


func _confirm_train() -> void:
	var r := GameManager.train_unit_with(uid, _train_sel)
	if not r.get("ok", false):
		UIKit.toast(self, r.get("reason", "Cannot train."), UIKit.DANGER)
		return
	_train_popup.close()
	AudioManager.play_sfx("level_up")
	_build()
	var p := FantasyPopup.open(self, "LEVEL UP!" if int(r["level_after"]) > int(r["level_before"]) else "TRAINED", 760, "boss")
	p.name = "TrainResult"
	p.content.add_child(UIKit.heading("Lv.%d  >  Lv.%d" % [int(r["level_before"]), int(r["level_after"])], UIKit.T_TITLE, UIKit.TEXT))
	var g: Dictionary = r["gains"]
	for key in STAT_KEYS:
		p.content.add_child(UIKit.label("%s  +%d" % [key.to_upper(), int(g[key])], UIKit.T_NAME, UIKit.GOOD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	UIKit.sparkle(p.panel, Rect2(0, 0, 760, 400), UIKit.GOLD, 12)
	var ok := FantasyButton.make("OK", "ember", Vector2(300, 110))
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(ok)
	ok.pressed.connect(p.close)
