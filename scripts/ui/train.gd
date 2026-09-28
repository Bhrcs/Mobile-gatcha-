extends ScreenBase
## TRAINING: feed Wisps (+ Gold) to one hero. Each material card has -1 / +1 /
## +5 / MAX; the preview (level, EXP bar, stat gains, Gold cost) updates live.
## Same-element Wisps give +50% EXP. Nothing is spent until TRAIN is pressed.

const WISPS := ["ember_wisp", "tide_wisp", "verdant_wisp", "radiant_wisp"]
const STAT_KEYS := ["hp", "atk", "def", "rec"]

var uid := ""
var unit: Dictionary = {}
var def: Dictionary = {}
var sel: Dictionary = {}          # wisp id -> amount chosen
var hero_box: VBoxContainer
var cards: GridContainer
var footer: VBoxContainer


func _ready() -> void:
	if not require_profile():
		return
	uid = SceneRouter.params.get("uid", "")
	if GameManager.get_unit(uid).is_empty():
		uid = GameManager.leader_uid()
	back_fallback = "units"
	var area := build_frame("bg_camp", "TRAINING", "units", Callable(), 0.6, true, {"help": "units"})
	var col := UIKit.vbox(UIKit.SP_M)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	var hp := PanelFrame.make("panel", 18)
	hp.name = "TrainPreview"
	col.add_child(hp)
	hero_box = UIKit.vbox(UIKit.SP_S)
	hp.add_child(hero_box)
	col.add_child(UIKit.label("WISPS", UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	cards = GridContainer.new()
	cards.columns = 2
	cards.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cards.add_theme_constant_override("h_separation", UIKit.SP_M)
	cards.add_theme_constant_override("v_separation", UIKit.SP_M)
	scroll.add_child(cards)
	var fp := PanelFrame.make("plank", 14)
	col.add_child(fp)
	footer = UIKit.vbox(UIKit.SP_S)
	fp.add_child(footer)
	_render()


func _render() -> void:
	unit = GameManager.get_unit(uid)
	def = Database.get_character(unit.get("char_id", ""))
	var pv := GameManager.preview_training(uid, sel)
	_render_hero(pv)
	_render_cards(pv)
	_render_footer(pv)


func _render_hero(pv: Dictionary) -> void:
	for c in hero_box.get_children():
		c.queue_free()
	var h := UIKit.hbox(UIKit.SP_L)
	hero_box.add_child(h)
	var fr := PanelFrame.make("rarity_%d" % clampi(int(def.get("rarity", 3)), 3, 6), 6)
	fr.add_child(UIKit.portrait_art(def, Vector2(200, 200)))
	h.add_child(fr)
	var v := UIKit.vbox(UIKit.SP_XS)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(v)
	var nh := UIKit.hbox(UIKit.SP_S)
	nh.add_child(UIKit.orb(def.get("element", ""), 40))
	var nm := UIKit.label(def.get("name", ""), UIKit.T_NAME, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_LEFT, 8)
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nh.add_child(nm)
	v.add_child(nh)
	var lb := int(pv.get("level_before", unit.get("level", 1)))
	var la := int(pv.get("level_after", lb))
	var max_l := int(def.get("max_level", 20))
	var lv := UIKit.label("Lv.%d" % lb + ("  >  Lv.%d" % la if la > lb else "") + ("  (MAX %d)" % max_l if la >= max_l else "  / %d" % max_l),
			UIKit.T_HEAD if la > lb else UIKit.T_NAME, UIKit.GOLD if la > lb else UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 8)
	lv.name = "PreviewLevel"
	v.add_child(lv)
	# EXP bar: where the hero will end up after training
	var xb := ResourceBar.make("xp", 28)
	xb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var exp_after := int(pv.get("exp_after", unit.get("exp", 0)))
	var need := Progression.xp_to_next(la) if la < max_l else 1
	xb.ready.connect(func(): xb.set_values(exp_after if la < max_l else 1, need, false))
	v.add_child(xb)
	var g: Dictionary = pv.get("gains", {})
	var stats := GameManager.unit_stats(unit)
	var sg := GridContainer.new()
	sg.columns = 4
	sg.add_theme_constant_override("h_separation", UIKit.SP_XL)
	for key in STAT_KEYS:
		var cell := UIKit.vbox(0)
		cell.add_child(UIKit.label(key.to_upper(), UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
		var gain := int(g.get(key, 0))
		var val := UIKit.label("%d" % int(stats.get(key, 0)) + ("  +%d" % gain if gain > 0 else ""), UIKit.T_BODY,
				UIKit.GOOD if gain > 0 else UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6)
		val.name = "Gain_" + key
		cell.add_child(val)
		sg.add_child(cell)
	v.add_child(sg)
	if int(pv.get("wasted_xp", 0)) > 0:
		hero_box.add_child(UIKit.label("Reaches the level cap - extra EXP would be wasted.", UIKit.T_SMALL, UIKit.EMBER,
				HORIZONTAL_ALIGNMENT_CENTER, 5))
	if bool(pv.get("at_cap", false)):
		var cap := "Max level reached." + (" Evolve to raise the cap." if def.get("evolution") is Dictionary else "")
		hero_box.add_child(UIKit.label(cap, UIKit.T_BODY, UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 6))


func _render_cards(pv: Dictionary) -> void:
	for c in cards.get_children():
		c.queue_free()
	var full := bool(pv.get("at_cap", false)) or int(pv.get("wasted_xp", 0)) > 0 or \
			int(pv.get("used_xp", 0)) >= Progression.xp_to_cap(unit)
	for w in WISPS:
		var have := GameManager.item_count(w)
		var n := int(sel.get(w, 0))
		var card := PanelFrame.make("inset" if n == 0 else "boss", 12)
		card.name = "Wisp_" + w
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var v := UIKit.vbox(UIKit.SP_XS)
		card.add_child(v)
		var h := UIKit.hbox(UIKit.SP_S)
		var item := Database.get_item(w)
		h.add_child(UIKit.icon(item.get("icon", ""), 64))
		var tv := UIKit.vbox(0)
		tv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var nm := UIKit.label(Database.item_name(w), UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6)
		UIKit.fit_label(nm, 300)
		tv.add_child(nm)
		var bonus: bool = item.get("element", "") == def.get("element", "-")
		tv.add_child(UIKit.label("+%d EXP%s" % [Progression.item_xp(w, def), "  x1.5" if bonus else ""], UIKit.T_SMALL,
				UIKit.GOOD if bonus else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4))
		h.add_child(tv)
		var cnt := UIKit.label("%d / %d" % [n, have], UIKit.T_NAME, UIKit.GOLD if n > 0 else UIKit.MUTED, HORIZONTAL_ALIGNMENT_RIGHT, 8)
		cnt.name = "Count"
		h.add_child(cnt)
		v.add_child(h)
		var row := UIKit.hbox(UIKit.SP_S)
		for step in [["-1", -1], ["+1", 1], ["+5", 5], ["MAX", 999]]:
			var b := UIKit.btn(step[0], "quiet" if int(step[1]) < 0 else "secondary", Vector2(0, UIKit.TOUCH_MIN))
			b.name = "Step_%s" % String(step[0]).replace("+", "p").replace("-", "m")
			b.press_cooldown = 0.0
			b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			b.add_theme_font_size_override("font_size", UIKit.T_BODY)
			b.disabled = (n <= 0) if int(step[1]) < 0 else (n >= have or full)
			var d: int = step[1]
			b.pressed.connect(func(): _change(w, d))
			row.add_child(b)
		v.add_child(row)
		if have <= 0:
			card.modulate = Color(0.6, 0.6, 0.65)
			var src := UIKit.btn("WHERE TO FIND", "quiet", Vector2(0, 72))
			src.name = "Source_" + w
			src.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			src.add_theme_font_size_override("font_size", UIKit.T_SMALL)
			src.pressed.connect(func(): ItemSources.open(self, w))
			v.add_child(src)
		cards.add_child(card)


func _render_footer(pv: Dictionary) -> void:
	for c in footer.get_children():
		c.queue_free()
	var cost := int(pv.get("gold", 0))
	var enough := GameManager.gold() >= cost
	var cl := UIKit.hbox(UIKit.SP_S)
	cl.alignment = BoxContainer.ALIGNMENT_CENTER
	cl.add_child(UIKit.label("+%s EXP" % UIKit.format_number(int(pv.get("used_xp", 0))), UIKit.T_BODY, UIKit.TEXT,
			HORIZONTAL_ALIGNMENT_LEFT, 6))
	cl.add_child(UIKit.label("   COST", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	cl.add_child(UIKit.icon("res://assets/icons/gold.png", 40))
	var cost_l := UIKit.label("%s  (you have %s)" % [UIKit.format_number(cost), UIKit.format_compact(GameManager.gold())],
			UIKit.T_BODY, UIKit.GOLD if enough else UIKit.DANGER, HORIZONTAL_ALIGNMENT_LEFT, 6)
	cost_l.name = "TrainCost"
	cl.add_child(cost_l)
	footer.add_child(cl)
	var row := UIKit.hbox(UIKit.SP_M)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var auto := UIKit.btn("AUTO", "secondary", Vector2(240, 110))
	auto.name = "AutoSelect"
	auto.tooltip_text = "Pick wisps up to the next level cap (best match first)"
	auto.pressed.connect(_auto_select)
	row.add_child(auto)
	var clear := UIKit.btn("CLEAR", "quiet", Vector2(220, 110))
	clear.name = "ClearSelection"
	clear.disabled = sel.is_empty()
	clear.pressed.connect(func():
		sel = {}
		_render())
	row.add_child(clear)
	var ok := UIKit.btn("TRAIN", "primary", Vector2(340, 120))
	ok.name = "ConfirmTrain"
	ok.disabled = sel.is_empty() or bool(pv.get("at_cap", false))
	ok.pressed.connect(func():
		if not enough:
			UIManager.not_enough("Gold", cost, GameManager.gold(), "Remove some wisps or earn Gold from stages.")
			return
		_confirm())
	row.add_child(ok)
	footer.add_child(row)


func _change(w: String, d: int) -> void:
	var have := GameManager.item_count(w)
	var n := int(sel.get(w, 0))
	if d >= 999:
		# MAX: as many as needed to reach the level cap (or all owned)
		var target := n
		while target < have:
			var trial := sel.duplicate()
			trial[w] = target + 1
			var pv := GameManager.preview_training(uid, trial)
			target += 1
			if int(pv.get("wasted_xp", 0)) > 0 or int(pv.get("used_xp", 0)) >= Progression.xp_to_cap(unit):
				break
		n = target
	else:
		n = clampi(n + d, 0, have)
		# never step past the cap
		while n > int(sel.get(w, 0)) and n > 0:
			var trial2 := sel.duplicate()
			trial2[w] = n - 1
			if int(GameManager.preview_training(uid, trial2).get("used_xp", 0)) < Progression.xp_to_cap(unit):
				break
			n -= 1
	if n <= 0:
		sel.erase(w)
	else:
		sel[w] = n
	UIManager.sfx("press", -6.0)
	_render()


## Picks wisps (best element match first) until the next level cap or Gold runs out.
func _auto_select() -> void:
	sel = {}
	var order := WISPS.duplicate()
	# same-element wisps first (they give +50%), then the smallest to waste least
	var el: String = def.get("element", "")
	order.sort_custom(func(a, b):
		var ma: bool = Database.get_item(a).get("element", "") == el
		var mb: bool = Database.get_item(b).get("element", "") == el
		if ma != mb:
			return ma
		return Progression.item_xp(a, def) < Progression.item_xp(b, def))
	var need := Progression.xp_to_cap(unit)
	var got := 0
	for w in order:
		var have := GameManager.item_count(w)
		var xp := Progression.item_xp(w, def)
		while have > 0 and got < need:
			if Progression.training_gold(mini(got + xp, need)) > GameManager.gold():
				break
			sel[w] = int(sel.get(w, 0)) + 1
			got += xp
			have -= 1
	if sel.is_empty():
		UIManager.toast("No wisps to use, or not enough Gold." if Progression.xp_to_cap(unit) > 0 else "This hero is at max level.", "info")
	_render()


func _confirm() -> void:
	var r := GameManager.train_unit_with(uid, sel)
	if not r.get("ok", false):
		UIManager.toast(r.get("reason", "Cannot train."), "error")
		return
	sel = {}
	UIManager.sfx("level_up")
	UIManager.haptic("confirm")
	_render()
	var up := int(r["level_after"]) > int(r["level_before"])
	var p := FantasyPopup.open(self, "LEVEL UP!" if up else "TRAINED", 760, "boss")
	p.name = "TrainResult"
	p.content.add_child(UIKit.heading("Lv.%d  >  Lv.%d" % [int(r["level_before"]), int(r["level_after"])], UIKit.T_TITLE, UIKit.TEXT))
	var g: Dictionary = r["gains"]
	for key in STAT_KEYS:
		p.content.add_child(UIKit.label("%s  +%d" % [key.to_upper(), int(g[key])], UIKit.T_NAME, UIKit.GOOD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	if up:
		UIKit.sparkle(p.panel, Rect2(0, 0, 760, 400), UIKit.GOLD, 12)
	var ok := UIKit.btn("OK", "primary", Vector2(300, 110))
	ok.name = "TrainResultOK"
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(ok)
	ok.pressed.connect(p.close)
	p.default_action = p.close
