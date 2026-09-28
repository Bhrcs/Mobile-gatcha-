extends ScreenBase
## Squad editor (5 slots). The leader slot carries the flame-crown emblem and
## the leader's Leader Skill is shown with the squad's power. Tap a slot to
## select it; tap another slot to swap; use the actions below. Reserve heroes are
## added with a tap. A hero can only be in the squad once.

var slots_row: HBoxContainer
var bench: GridContainer
var action_row: HBoxContainer
var info: Label
var leader_label: Label
var power_label: Label
var selected := -1
var stage_id := ""               # set when opened from a stage's PREPARE
var matchup: VBoxContainer


func _ready() -> void:
	if not require_profile():
		return
	var back_to: String = SceneRouter.params.get("from_uid", "")
	var return_to: String = SceneRouter.params.get("return_to", "")
	stage_id = SceneRouter.params.get("stage_id", "")
	if not return_to.is_empty():
		back_fallback = return_to
	elif not back_to.is_empty():
		back_fallback = "units"
	var area := build_frame("bg_camp", "SQUAD", "units", Callable(), 0.6, true, {"help": "squad"})
	var col := UIKit.vbox(14)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)

	var party_panel := PanelFrame.make("panel", 22)
	col.add_child(party_panel)
	var pv := UIKit.vbox(12)
	party_panel.add_child(pv)
	pv.add_child(UIKit.label("PARTY  (MAX %d)" % GameManager.max_party_size(), UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	slots_row = UIKit.hbox(10)
	slots_row.alignment = BoxContainer.ALIGNMENT_CENTER
	pv.add_child(slots_row)
	var lrow := UIKit.hbox(10)
	lrow.add_child(UIKit.icon("res://assets/icons/leader.png", 40))
	leader_label = UIKit.wrap_label("", UIKit.T_SMALL, UIKit.GOLD)
	leader_label.name = "LeaderSkill"
	leader_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	lrow.add_child(leader_label)
	power_label = UIKit.label("", UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_RIGHT, 6)
	power_label.name = "SquadPower"
	lrow.add_child(power_label)
	pv.add_child(lrow)
	info = UIKit.label("", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	pv.add_child(info)
	action_row = UIKit.hbox(12)
	action_row.alignment = BoxContainer.ALIGNMENT_CENTER
	pv.add_child(action_row)
	matchup = UIKit.vbox(0)
	pv.add_child(matchup)

	col.add_child(UIKit.label("RESERVE", UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	var center := CenterContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(center)
	bench = GridContainer.new()
	bench.columns = 4
	bench.add_theme_constant_override("h_separation", 12)
	bench.add_theme_constant_override("v_separation", 12)
	center.add_child(bench)
	_refresh()


func _slot_width() -> int:
	var n := GameManager.max_party_size()
	return clampi(int((1000 - (n - 1) * 10) / n), 180, 330)


func _refresh() -> void:
	for c in slots_row.get_children():
		c.queue_free()
	for c in bench.get_children():
		c.queue_free()
	for c in action_row.get_children():
		c.queue_free()
	var party := GameManager.party_units()
	var ls := GameManager.leader_skill()
	leader_label.text = "LEADER SKILL: %s - %s" % [ls.get("name", ""), ls.get("description", "")] if not ls.is_empty() else ""
	power_label.text = "POWER %s" % UIKit.format_number(GameManager.squad_power())
	for c in matchup.get_children():
		c.queue_free()
	if not stage_id.is_empty() and not Database.get_stage(stage_id).is_empty():
		matchup.add_child(StageInfo.matchup_row(party, Database.get_stage(stage_id), self))
	var w := _slot_width()
	for i in GameManager.max_party_size():
		slots_row.add_child(_slot(party[i] if i < party.size() else {}, i, w))
	var any_bench := false
	for u in GameManager.owned_units():
		if GameManager.is_in_party(u["uid"]):
			continue
		any_bench = true
		var card := UnitCard.make(u)
		var uid: String = u["uid"]
		card.tapped.connect(func(_id): _add(uid))
		bench.add_child(card)
	if not any_bench:
		var l := UIKit.wrap_label("Every hero you own is already in the party. New heroes will appear here.", UIKit.T_BODY, UIKit.MUTED)
		l.custom_minimum_size.x = 900
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		bench.add_child(l)
	if selected >= 0 and selected < party.size():
		var uid: String = party[selected]["uid"]
		info.text = Database.get_character(party[selected]["char_id"]).get("name", "") + " selected - tap another slot to swap"
		if selected > 0:
			var lead := FantasyButton.make("MAKE LEADER", "gold", Vector2(380, 104), "res://assets/icons/leader.png")
			lead.name = "MakeLeader"
			lead.add_theme_font_size_override("font_size", 30)
			lead.pressed.connect(func():
				GameManager.set_leader(uid)
				AudioManager.play_sfx("unit_select")
				UIManager.toast("%s now leads the squad." % Database.get_character(GameManager.get_unit(uid).get("char_id", "")).get("name", ""), "success")
				selected = 0
				_refresh())
			action_row.add_child(lead)
		var rem := FantasyButton.make("REMOVE", "stone", Vector2(260, 104))
		rem.add_theme_font_size_override("font_size", 30)
		rem.disabled = party.size() <= 1
		rem.pressed.connect(func():
			GameManager.toggle_party(uid)
			selected = -1
			_refresh())
		action_row.add_child(rem)
		var view := FantasyButton.make("DETAILS", "steel", Vector2(260, 104))
		view.add_theme_font_size_override("font_size", 30)
		view.pressed.connect(func(): SceneRouter.go("unit_detail", {"uid": uid}))
		action_row.add_child(view)
	else:
		selected = -1
		info.text = "Tap a hero to select. The leader stands at the front."


func _slot(u: Dictionary, index: int, w: int) -> Control:
	var leader := index == 0
	var v := UIKit.vbox(6)
	v.name = "Slot_%d" % index
	var head := UIKit.hbox(6)
	head.alignment = BoxContainer.ALIGNMENT_CENTER
	if leader:
		head.add_child(UIKit.icon("res://assets/icons/leader.png", 48))
	head.add_child(UIKit.label("LEADER" if leader else "SLOT %d" % (index + 1), UIKit.T_SMALL,
			UIKit.GOLD if leader else UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 5))
	v.add_child(head)
	var frame: PanelFrame
	if u.is_empty():
		frame = PanelFrame.make("inset", 12)
		frame.custom_minimum_size = Vector2(w, w * 1.2)
		var l := UIKit.label("EMPTY", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		frame.add_child(l)
	else:
		var def := Database.get_character(u["char_id"])
		var el: String = def.get("element", "neutral")
		frame = PanelFrame.make("card_%s%s" % [el, "_lit" if index == selected else ""], 10)
		frame.custom_minimum_size = Vector2(w, w * 1.2)
		var stack := UIKit.vbox(4)
		stack.mouse_filter = Control.MOUSE_FILTER_IGNORE
		frame.add_child(stack)
		stack.add_child(UIKit.portrait_art(def, Vector2(w - 20, w - 40)))
		var row := UIKit.hbox(6)
		row.alignment = BoxContainer.ALIGNMENT_CENTER
		row.add_child(UIKit.orb(el, 32))
		row.add_child(UIKit.label("%s Lv%d" % [String(def.get("name", "")).split(" ")[0], int(u["level"])], UIKit.T_SMALL,
				UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 5))
		stack.add_child(row)
		if index == selected:
			frame.modulate = Color(1.1, 1.08, 0.95)
	if leader:
		UIKit.sparkle(frame, Rect2(0, 0, w, w * 1.2), Color("#ffd35a"), 5)
	var idx := index
	UIKit.on_tap(frame, func(): _on_slot(idx))
	v.add_child(frame)
	return v


func _on_slot(index: int) -> void:
	var size := GameManager.party_uids().size()
	if index >= size:
		selected = -1
		_refresh()
		return
	if selected >= 0 and selected != index:
		GameManager.swap_party_slots(selected, index)
		AudioManager.play_sfx("unit_select")
		selected = -1
	else:
		selected = index if selected != index else -1
		AudioManager.play_sfx("unit_select", 0.03, -4.0)
	_refresh()


func _add(uid: String) -> void:
	if GameManager.party_uids().size() >= GameManager.max_party_size():
		UIManager.toast("The squad is full. Select a squad slot and REMOVE a hero first.", "warning")
		return
	GameManager.toggle_party(uid)
	AudioManager.play_sfx("unit_select")
	_refresh()
