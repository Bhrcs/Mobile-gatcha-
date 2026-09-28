extends ScreenBase
## Missions: 5 daily missions with a daily chest (claim 4), weekly missions and
## the 7-day login calendar. Progress resets at local midnight / on Mondays.

const TABS := ["daily", "weekly", "login"]

var body: VBoxContainer
var tab := "daily"
var tabs: CinderTabs
var claim_all: FantasyButton
var _reset_l: Label


func _ready() -> void:
	if not require_profile():
		return
	var area := build_frame("bg_camp", "MISSIONS", "missions", Callable(), 0.6)
	if not GameManager.feature_unlocked("missions"):
		var lock := UIKit.wrap_label("Missions unlock after clearing %s." % GameManager.feature_unlock_label("missions"), UIKit.T_NAME, UIKit.MUTED)
		lock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lock.set_anchors_preset(Control.PRESET_CENTER)
		lock.custom_minimum_size.x = 900
		area.add_child(lock)
		return
	var col := UIKit.vbox(12)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	tabs = CinderTabs.make(["DAILY", "WEEKLY", "LOGIN"], 0, func(i: int): _set_tab(TABS[i]))
	col.add_child(tabs)
	var top := UIKit.hbox(UIKit.SP_M)
	_reset_l = UIKit.label("", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4)
	_reset_l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(_reset_l)
	claim_all = UIKit.btn("CLAIM ALL", "reward", Vector2(300, 90))
	claim_all.name = "ClaimAll"
	claim_all.pressed.connect(_claim_all)
	top.add_child(claim_all)
	col.add_child(top)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	body = UIKit.vbox(10)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	var start: String = SceneRouter.params.get("tab", "daily")
	_set_tab(start if start in TABS else "daily")


func _set_tab(t: String) -> void:
	tab = t
	SceneRouter.remember({"tab": t})
	tabs.select(TABS.find(t), false)
	var total := 0
	for k in ["daily", "weekly"]:
		var n := 0
		for m in Database.missions.get(k, []):
			if not GameManager.mission_claimed(k, m["id"]) and GameManager.mission_progress(k, m) >= int(m.get("target", 1)):
				n += 1
		if k == "daily" and GameManager.can_claim_chest():
			n += 1
		tabs.set_badge(TABS.find(k), str(n) if n > 0 else "")
		total += n
	tabs.set_badge(2, "!" if GameManager.login_available() else "")
	claim_all.visible = total > 0 and t != "login"
	claim_all.text = "CLAIM ALL (%d)" % total
	_render()


func _claim_all() -> void:
	var r := GameManager.claim_all_missions()
	if int(r.get("count", 0)) <= 0:
		UIManager.toast("Nothing to claim yet.", "info")
		return
	UIManager.sfx("claim")
	UIManager.haptic("confirm")
	RewardPopup.open(self, "%d REWARDS CLAIMED" % int(r["count"]), r)
	_set_tab(tab)


func _render() -> void:
	for ch in body.get_children():
		ch.queue_free()
	_update_reset_label()
	match tab:
		"daily":
			body.add_child(_chest())
			for m in Database.missions.get("daily", []):
				body.add_child(_mission_row("daily", m))
		"weekly":
			for m in Database.missions.get("weekly", []):
				body.add_child(_mission_row("weekly", m))
		"login":
			_login_calendar()


func _update_reset_label() -> void:
	var now := int(GameManager.now())
	var dt := Time.get_datetime_dict_from_system()
	var secs_to_midnight := 86400 - (int(dt["hour"]) * 3600 + int(dt["minute"]) * 60 + int(dt["second"]))
	if tab == "weekly":
		var wd := int(dt["weekday"])     # 0 = Sunday
		var days := (8 - wd) % 7
		if days == 0:
			days = 7
		_reset_l.text = "Weekly missions reset in %dd %s" % [days - 1, UIKit.format_time(secs_to_midnight)]
	else:
		_reset_l.text = "Daily missions reset in %s" % UIKit.format_time(secs_to_midnight)
	if now < 0:
		_reset_l.text = ""


func _chest() -> Control:
	var info: Dictionary = Database.missions.get("daily_chest", {})
	var need := int(info.get("needed", 4))
	var done := GameManager.daily_completed()
	var p := PanelFrame.make("boss" if GameManager.can_claim_chest() else "panel", 16)
	p.name = "DailyChest"
	var h := UIKit.hbox(14)
	p.add_child(h)
	var claimed := bool(GameManager.profile["missions"].get("chest_claimed", false))
	h.add_child(UIKit.icon("res://assets/icons/chest_open.png" if claimed else "res://assets/icons/chest.png", 96))
	var v := UIKit.vbox(4)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(UIKit.label("DAILY CHEST", UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 8))
	v.add_child(UIKit.label("Claim %d daily missions: %d / %d" % [need, mini(done, need), need], UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6))
	v.add_child(_reward_line(info.get("reward", {})))
	h.add_child(v)
	var b := FantasyButton.make("CLAIMED" if claimed else "CLAIM", "gold", Vector2(220, 100))
	b.name = "ClaimChest"
	b.disabled = not GameManager.can_claim_chest()
	b.pressed.connect(func():
		var r := GameManager.claim_chest()
		if not r.is_empty():
			AudioManager.play_sfx("claim")
			_reward_popup(r)
		_set_tab(tab))
	h.add_child(b)
	return p


func _mission_row(kind: String, m: Dictionary) -> Control:
	var prog := GameManager.mission_progress(kind, m)
	var target := int(m.get("target", 1))
	var claimed := GameManager.mission_claimed(kind, m["id"])
	var done := prog >= target
	var p := PanelFrame.make("plank" if not claimed else "inset", 12)
	p.name = "Mission_" + m["id"]
	var h := UIKit.hbox(12)
	p.add_child(h)
	var v := UIKit.vbox(4)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(UIKit.label(m.get("text", ""), UIKit.T_BODY, UIKit.TEXT if not claimed else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var pr := UIKit.hbox(10)
	var bar := ResourceBar.make("xp", 22)
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	bar.ready.connect(func(): bar.set_values(prog, target, false))
	pr.add_child(bar)
	pr.add_child(UIKit.label("%d / %d" % [prog, target], UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 5))
	v.add_child(pr)
	v.add_child(_reward_line(m.get("reward", {})))
	h.add_child(v)
	var b := FantasyButton.make("DONE" if claimed else ("CLAIM" if done else "GO"), "gold" if done and not claimed else "stone",
			Vector2(200, 96))
	b.name = "Claim_" + m["id"]
	b.add_theme_font_size_override("font_size", 30)
	if claimed:
		b.disabled = true
	elif done:
		b.pressed.connect(func():
			var r := GameManager.claim_mission(kind, m["id"])
			if not r.is_empty():
				AudioManager.play_sfx("claim")
				_reward_popup(r)
			_set_tab(tab))
	else:
		var ev: String = m.get("event", "")
		b.pressed.connect(func(): _go_for(ev))
	h.add_child(b)
	return p


func _go_for(ev: String) -> void:
	match ev:
		"tower_clear":
			SceneRouter.go("tower")
		"train":
			SceneRouter.go("units")
		"summon":
			SceneRouter.go("summon")
		_:
			SceneRouter.go("stage_select")


func _reward_line(r: Dictionary) -> Control:
	var h := UIKit.hbox(8)
	h.add_child(UIKit.label("REWARD", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	if int(r.get("gems", 0)) > 0:
		h.add_child(UIKit.icon("res://assets/icons/gem.png", 36))
		h.add_child(UIKit.label(str(int(r["gems"])), UIKit.T_SMALL, Color("#9ae8ff"), HORIZONTAL_ALIGNMENT_LEFT, 5))
	if int(r.get("gold", 0)) > 0:
		h.add_child(UIKit.icon("res://assets/icons/gold.png", 36))
		h.add_child(UIKit.label(UIKit.format_number(int(r["gold"])), UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	for item_id in r.get("items", {}).keys():
		h.add_child(UIKit.icon(Database.get_item(item_id).get("icon", ""), 36))
		h.add_child(UIKit.label("x%d" % int(r["items"][item_id]), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 5))
	return h


func _login_calendar() -> void:
	var cycle: Array = Database.login_rewards.get("cycle", [])
	var today := GameManager.login_day_index()
	var avail := GameManager.login_available()
	var info := UIKit.wrap_label("Log in on any day to claim the next reward. Missed days never reset the calendar.", UIKit.T_SMALL, UIKit.MUTED)
	info.custom_minimum_size.x = 1000
	info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	body.add_child(info)
	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	grid.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	body.add_child(grid)
	var claimed_count := int(GameManager.profile["login"].get("day_index", 0)) % maxi(cycle.size(), 1)
	for i in cycle.size():
		var is_next := i == today
		var done := i < claimed_count
		var cell := PanelFrame.make("boss" if is_next and avail else ("inset" if done else "panel"), 10)
		cell.name = "LoginDay_%d" % (i + 1)
		cell.custom_minimum_size = Vector2(240, 230)
		var v := UIKit.vbox(4)
		v.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_child(v)
		v.add_child(UIKit.label("DAY %d" % (i + 1), UIKit.T_BODY, UIKit.GOLD if is_next else UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 6))
		var r: Dictionary = cycle[i].get("reward", {})
		var icon_path := "res://assets/icons/chest.png"
		if int(r.get("gems", 0)) > 0:
			icon_path = "res://assets/icons/gem.png"
		elif int(r.get("gold", 0)) > 0:
			icon_path = "res://assets/icons/gold.png"
		elif not r.get("items", {}).is_empty():
			icon_path = String(Database.get_item(String(r["items"].keys()[0])).get("icon", icon_path))
		var ic := UIKit.icon(icon_path, 80)
		ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		v.add_child(ic)
		v.add_child(UIKit.label(_reward_text(r), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 5))
		if done:
			var ch := UIKit.hbox(4)
			ch.alignment = BoxContainer.ALIGNMENT_CENTER
			ch.mouse_filter = Control.MOUSE_FILTER_IGNORE
			ch.add_child(UIKit.icon("res://assets/icons/check.png", 32))
			ch.add_child(UIKit.label("CLAIMED", UIKit.T_SMALL, UIKit.GOOD, HORIZONTAL_ALIGNMENT_CENTER, 5))
			v.add_child(ch)
			ic.modulate = Color(0.6, 0.6, 0.65)
		elif is_next and avail:
			v.add_child(UIKit.label("TODAY", UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 5))
		grid.add_child(cell)
	var b := FantasyButton.make("CLAIM DAY %d" % (today + 1) if avail else "COME BACK TOMORROW", "gold" if avail else "stone", Vector2(560, 120))
	b.name = "ClaimLogin"
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.disabled = not avail
	b.pressed.connect(func():
		var r := GameManager.claim_login()
		if not r.is_empty():
			AudioManager.play_sfx("claim")
			_reward_popup(r)
		_set_tab("login"))
	body.add_child(b)


static func _reward_text(r: Dictionary) -> String:
	var parts: Array = []
	if int(r.get("gems", 0)) > 0:
		parts.append("%d Gems" % int(r["gems"]))
	if int(r.get("gold", 0)) > 0:
		parts.append("%s Gold" % UIKit.format_number(int(r["gold"])))
	for item_id in r.get("items", {}).keys():
		parts.append("%s x%d" % [Database.item_name(item_id), int(r["items"][item_id])])
	return "\n".join(parts)


func _reward_popup(r: Dictionary) -> void:
	RewardPopup.open(self, "REWARD CLAIMED", r)
