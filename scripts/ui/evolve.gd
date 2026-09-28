extends ScreenBase
## EVOLVE: current form -> next form, stat changes, required materials (owned /
## needed, each with OBTAINED FROM navigation), gold cost and the level
## requirement. Confirming plays the evolution ceremony and shows the new form.
## No duplicate heroes are needed - only materials and Gold.

const STAT_KEYS := ["hp", "atk", "def", "rec"]

var uid := ""
var body: VBoxContainer


func _ready() -> void:
	if not require_profile():
		return
	uid = SceneRouter.params.get("uid", GameManager.leader_uid())
	var area := build_frame("bg_camp", "EVOLUTION", "units", Callable(), 0.65)
	var scroll := ScrollContainer.new()
	scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	area.add_child(scroll)
	body = UIKit.vbox(14)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	_build()


func _build() -> void:
	for ch in body.get_children():
		ch.queue_free()
	var unit := GameManager.get_unit(uid)
	var def := Database.get_character(unit.get("char_id", ""))
	var st := GameManager.evolution_status(uid)
	if st.get("final", false) or not st.has("into"):
		body.add_child(UIKit.heading("FINAL FORM", UIKit.T_HEAD))
		body.add_child(UIKit.label("%s has reached their final form." % def.get("name", ""), UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		return
	var nxt := Database.get_character(st["into"])

	# ---- forms
	var forms := PanelFrame.make("card_%s_lit" % def.get("element", "neutral"), 16)
	forms.name = "EvolutionForms"
	body.add_child(forms)
	var fr := UIKit.hbox(10)
	fr.alignment = BoxContainer.ALIGNMENT_CENTER
	forms.add_child(fr)
	fr.add_child(_form_card(def, "Lv.%d / %d" % [int(unit["level"]), int(def.get("max_level", 15))]))
	var arrow := UIKit.vbox(4)
	arrow.alignment = BoxContainer.ALIGNMENT_CENTER
	arrow.add_child(UIKit.label(">>", UIKit.T_TITLE, UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 12))
	fr.add_child(arrow)
	fr.add_child(_form_card(nxt, "Lv.1 / %d" % int(nxt.get("max_level", 25))))

	# ---- stats
	var sp := PanelFrame.make("panel", 20)
	sp.name = "EvolutionStats"
	body.add_child(sp)
	var sv := UIKit.vbox(6)
	sp.add_child(sv)
	sv.add_child(UIKit.label("STATS  (now  >  new form Lv.1  /  new max)", UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var now := GameManager.unit_stats(unit)
	var at1 := Progression.unit_stats(nxt, 1)
	var atmax := Progression.unit_stats(nxt, int(nxt.get("max_level", 25)))
	for k in STAT_KEYS:
		var r := UIKit.hbox(12)
		var n := UIKit.label(k.to_upper(), UIKit.T_BODY, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 6)
		n.custom_minimum_size.x = 110
		r.add_child(n)
		r.add_child(UIKit.label(str(int(now[k])), UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6))
		r.add_child(UIKit.label(">", UIKit.T_BODY, UIKit.EMBER, HORIZONTAL_ALIGNMENT_LEFT, 6))
		var diff := int(at1[k]) - int(now[k])
		r.add_child(UIKit.label("%d (%s%d)" % [int(at1[k]), "+" if diff >= 0 else "", diff], UIKit.T_BODY, UIKit.GOOD if diff >= 0 else UIKit.EMBER,
				HORIZONTAL_ALIGNMENT_LEFT, 6))
		r.add_child(UIKit.spacer())
		r.add_child(UIKit.label("MAX %d" % int(atmax[k]), UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 6))
		sv.add_child(r)
	var changes: Array = []
	if nxt.get("burst", "") != def.get("burst", ""):
		changes.append("New Burst: %s" % Database.get_skill(nxt["burst"]).get("name", ""))
	changes.append("Passive: %s" % nxt.get("passive", {}).get("description", ""))
	changes.append("Leader Skill: %s" % nxt.get("leader_skill", {}).get("description", ""))
	changes.append("Level resets to 1 with a higher cap. Burst level is kept.")
	for ctext in changes:
		var cl := UIKit.wrap_label(ctext, UIKit.T_SMALL, Color("#e8dece"))
		cl.custom_minimum_size.x = 960
		sv.add_child(cl)

	# ---- requirements
	var rp := PanelFrame.make("panel", 20)
	rp.name = "EvolutionRequirements"
	body.add_child(rp)
	var rv := UIKit.vbox(8)
	rp.add_child(rv)
	rv.add_child(UIKit.label("REQUIREMENTS", UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var max_ok := int(unit["level"]) >= int(def.get("max_level", 15))
	var lr := UIKit.hbox(10)
	lr.add_child(UIKit.icon("res://assets/icons/check.png" if max_ok else "res://assets/icons/lock.png", 40))
	lr.add_child(UIKit.label("Reach Lv.%d (max level)" % int(def.get("max_level", 15)), UIKit.T_BODY, UIKit.GOOD if max_ok else UIKit.DANGER,
			HORIZONTAL_ALIGNMENT_LEFT, 6))
	if not max_ok and GameManager.feature_unlocked("training"):
		lr.add_child(UIKit.spacer())
		var tb := FantasyButton.make("TRAIN", "gold", Vector2(200, 80))
		tb.add_theme_font_size_override("font_size", 28)
		tb.pressed.connect(func(): SceneRouter.go("unit_detail", {"uid": uid, "open_train": true}))
		lr.add_child(tb)
	rv.add_child(lr)
	var mats: Dictionary = st.get("materials", {})
	for m in mats.keys():
		rv.add_child(_material_row(m, int(mats[m])))
	var gold_need := int(st.get("gold", 0))
	var gr := UIKit.hbox(10)
	gr.add_child(UIKit.icon("res://assets/icons/gold.png", 56))
	gr.add_child(UIKit.label("%s Gold  (you have %s)" % [UIKit.format_number(gold_need), UIKit.format_number(GameManager.gold())],
			UIKit.T_BODY, UIKit.GOOD if GameManager.gold() >= gold_need else UIKit.DANGER, HORIZONTAL_ALIGNMENT_LEFT, 6))
	rv.add_child(gr)

	# ---- action
	var b := FantasyButton.make("EVOLVE", "ember", Vector2(560, 140))
	b.name = "ConfirmEvolve"
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.add_theme_font_size_override("font_size", UIKit.T_HEAD)
	b.disabled = not st.get("ok", false)
	if st.get("ok", false):
		b.add_shine()
	b.pressed.connect(func(): UIKit.confirm(self, "Evolve %s into %s?" % [def.get("name", ""), nxt.get("name", "")], _do_evolve, "EVOLVE"))
	body.add_child(b)
	for reason in st.get("reasons", []):
		body.add_child(UIKit.label(reason, UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 5))


func _form_card(d: Dictionary, sub: String) -> Control:
	var v := UIKit.vbox(4)
	var frame := PanelFrame.make("rarity_%d" % clampi(int(d.get("rarity", 3)), 3, 6), 8)
	frame.add_child(UIKit.portrait_art(d, Vector2(380, 380)))
	v.add_child(frame)
	var n := UIKit.label(d.get("name", ""), UIKit.T_BODY, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_CENTER, 6)
	n.custom_minimum_size.x = 400
	n.clip_text = true
	v.add_child(n)
	var s := UIKit.stars(int(d.get("rarity", 3)), 32)
	s.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(s)
	v.add_child(UIKit.label(sub, UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 5))
	return v


func _material_row(item_id: String, need: int) -> Control:
	var have := GameManager.item_count(item_id)
	var row := PanelFrame.make("plank", 8)
	row.name = "Material_" + item_id
	var h := UIKit.hbox(12)
	row.add_child(h)
	h.add_child(UIKit.icon(Database.get_item(item_id).get("icon", ""), 64))
	var v := UIKit.vbox(0)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(UIKit.label(Database.item_name(item_id), UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6))
	v.add_child(UIKit.label("%d / %d" % [have, need], UIKit.T_BODY, UIKit.GOOD if have >= need else UIKit.DANGER, HORIZONTAL_ALIGNMENT_LEFT, 6))
	h.add_child(v)
	var src := FantasyButton.make("OBTAINED FROM", "steel", Vector2(300, 80))
	src.name = "Source_" + item_id
	src.add_theme_font_size_override("font_size", 24)
	src.pressed.connect(func(): ItemSources.open(self, item_id))
	h.add_child(src)
	return row


## Evolution ceremony: light gathers, the old form dissolves into a silhouette,
## the new form bursts out with its rarity stars.
func _do_evolve() -> void:
	var unit := GameManager.get_unit(uid)
	var before := Database.get_character(unit.get("char_id", ""))
	var r := GameManager.evolve(uid)
	if not r.get("ok", false):
		UIKit.toast(self, "Cannot evolve: %s" % ", ".join(r.get("reasons", [])), UIKit.DANGER)
		return
	var after := Database.get_character(r["into"])
	var o := Control.new()
	o.name = "EvolveCeremony"
	o.set_anchors_preset(Control.PRESET_FULL_RECT)
	o.mouse_filter = Control.MOUSE_FILTER_STOP
	o.z_index = 70
	add_child(o)
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.01, 0.04, 0.0)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	o.add_child(dim)
	var vp := get_viewport_rect().size
	var col := Database.element_color(after.get("element", ""))
	var sp_old := UnitSpriteDisplay.new()
	sp_old.setup(before.get("sprite", {}), 12.0, false)
	sp_old.size = sp_old.custom_minimum_size
	sp_old.position = Vector2(vp.x / 2 - sp_old.size.x / 2, vp.y * 0.55 - sp_old.size.y)
	o.add_child(sp_old)
	AudioManager.play_sfx("evolve")
	var tw := create_tween()
	tw.tween_property(dim, "color:a", 0.9, 0.4)
	await tw.finished
	UIKit.sparkle(o, Rect2(vp.x / 2 - 300, vp.y * 0.25, 600, 700), col.lightened(0.4), 30)
	var ring := func(delay: float):
		var rr := ColorRect.new()
		rr.color = Color(col.r, col.g, col.b, 0.35)
		rr.size = Vector2(40, 40)
		rr.position = Vector2(vp.x / 2 - 20, vp.y * 0.45 - 20)
		rr.pivot_offset = Vector2(20, 20)
		o.add_child(rr)
		var t2 := rr.create_tween()
		t2.tween_interval(delay)
		t2.tween_property(rr, "scale", Vector2(30, 30), 0.6)
		t2.parallel().tween_property(rr, "modulate:a", 0.0, 0.6)
		t2.tween_callback(rr.queue_free)
	for i in 3:
		ring.call(i * 0.25)
	var t3 := create_tween()
	t3.tween_property(sp_old, "modulate", Color(3, 3, 3, 1), 0.6)
	t3.tween_property(sp_old, "modulate:a", 0.0, 0.25)
	await t3.finished
	var flash := ColorRect.new()
	flash.color = Color(1, 1, 1, 0.9)
	flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	o.add_child(flash)
	var sp_new := UnitSpriteDisplay.new()
	sp_new.setup(after.get("sprite", {}), 12.0, false, "victory")
	sp_new.size = sp_new.custom_minimum_size
	sp_new.position = Vector2(vp.x / 2 - sp_new.size.x / 2, vp.y * 0.55 - sp_new.size.y)
	o.add_child(sp_new)
	AudioManager.play_sfx("summon_rare")
	var t4 := create_tween()
	t4.tween_property(flash, "color:a", 0.0, 0.5)
	var title := UIKit.heading("EVOLVED!", 110, UIKit.GOLD)
	title.position = Vector2(0, vp.y * 0.12)
	title.size = Vector2(vp.x, 140)
	o.add_child(title)
	var nm := UIKit.label(after.get("name", ""), UIKit.T_HEAD, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_CENTER, 10)
	nm.position = Vector2(0, vp.y * 0.6)
	nm.size = Vector2(vp.x, 70)
	o.add_child(nm)
	var stars := UIKit.stars(int(after.get("rarity", 4)), 64)
	stars.position = Vector2(vp.x / 2 - int(after.get("rarity", 4)) * 32, vp.y * 0.6 + 80)
	o.add_child(stars)
	var ok := FantasyButton.make("CONTINUE", "ember", Vector2(420, 130))
	ok.name = "EvolveContinue"
	ok.position = Vector2(vp.x / 2 - 210, vp.y * 0.6 + 200)
	o.add_child(ok)
	ok.pressed.connect(func(): SceneRouter.go("unit_detail", {"uid": uid}))
