class_name SettingsPanel
extends RefCounted
## Settings content, grouped in AUDIO / GAMEPLAY / GRAPHICS / ACCOUNT.
## Used by the Settings screen (from MENU) and, as a popup, from the title
## screen and the battle pause menu. Every change applies and saves instantly.

const CATEGORIES := ["AUDIO", "GAMEPLAY", "GRAPHICS", "ACCOUNT"]


## Popup version (title screen, battle). `category` picks the first tab.
static func open(parent: Control, category := 0) -> FantasyPopup:
	var p := FantasyPopup.open(parent, "SETTINGS", 960)
	p.name = "SettingsPopup"
	var body := UIKit.vbox(UIKit.SP_L)
	body.custom_minimum_size = Vector2(900, 700)
	var tabs := CinderTabs.make(_categories(), category, func(i: int): fill(body, _categories()[i], parent), 88)
	p.content.add_child(tabs)
	p.content.add_child(body)
	fill(body, _categories()[category], parent)
	var close := UIKit.btn("CLOSE", "primary", Vector2(320, 110))
	close.name = "CloseSettings"
	close.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(close)
	close.pressed.connect(p.close)
	p.default_action = p.close
	return p


static func _categories() -> Array:
	# the account page only makes sense once a journey exists
	return CATEGORIES if GameManager.has_profile() else CATEGORIES.slice(0, 3)


## Rebuilds `v` with the rows of one category.
static func fill(v: VBoxContainer, category: String, host: Control) -> void:
	for c in v.get_children():
		v.remove_child(c)
		c.queue_free()
	match category:
		"AUDIO":
			v.add_child(_slider_row("Master Volume", "master_volume"))
			v.add_child(_slider_row("Music Volume", "music_volume"))
			v.add_child(_slider_row("Effects Volume", "sfx_volume"))
			v.add_child(_note("Effects include button sounds and battle impacts."))
		"GAMEPLAY":
			v.add_child(_speed_row())
			v.add_child(_toggle_row("Start Battles on AUTO", "auto_battle", "Heroes act on their own until you turn AUTO off."))
			v.add_child(_toggle_row("Damage Numbers", "damage_numbers", "Show damage and healing values in battle."))
			if OS.has_feature("mobile"):
				v.add_child(_toggle_row("Vibration", "haptics", "Short vibrations for bursts, summons and evolutions."))
			if GameManager.has_profile():
				v.add_child(_tutorial_row(host))
		"GRAPHICS":
			if not OS.has_feature("mobile"):
				v.add_child(_toggle_row("Fullscreen", "fullscreen", "F11 also toggles fullscreen."))
			v.add_child(_toggle_row("Screen Shake", "screen_shake", "Camera shake on heavy hits and bursts."))
			v.add_child(_toggle_row("Battle Effects", "battle_effects", "Particles, flashes and burst cut-ins."))
			v.add_child(_toggle_row("Reduce Motion", "reduce_motion", "Menus switch without sliding."))
			v.add_child(_margin_row())
		"ACCOUNT":
			_account(v)


static func _row(title: String, desc := "") -> Array:
	var panel := PanelFrame.make("inset", 14)
	var row := UIKit.hbox(UIKit.SP_L)
	panel.add_child(row)
	var col := UIKit.vbox(2)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_child(UIKit.label(title, UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6))
	if not desc.is_empty():
		var d := UIKit.wrap_label(desc, UIKit.T_SMALL, UIKit.MUTED)
		col.add_child(d)
	row.add_child(col)
	return [panel, row]


static func _note(text: String) -> Label:
	var l := UIKit.wrap_label(text, UIKit.T_SMALL, UIKit.MUTED)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return l


static func _slider_row(title: String, key: String) -> Control:
	var r := _row(title)
	var row: HBoxContainer = r[1]
	var s := HSlider.new()
	s.name = "Slider_" + key
	s.min_value = 0.0
	s.max_value = 1.0
	s.step = 0.05
	s.value = float(GameManager.settings.get(key, 0.8))
	s.custom_minimum_size = Vector2(360, 56)
	s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	s.focus_mode = Control.FOCUS_NONE
	row.add_child(s)
	var pct := UIKit.label("%d%%" % int(s.value * 100), UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 6)
	pct.custom_minimum_size.x = 100
	row.add_child(pct)
	s.value_changed.connect(func(val: float):
		pct.text = "%d%%" % int(val * 100)
		GameManager.set_setting(key, val))
	# one test sound when the player lets go (not a burst of clicks while dragging)
	s.drag_ended.connect(func(_changed: bool): UIManager.sfx("press", -4.0))
	return r[0]


static func _toggle_row(title: String, key: String, desc := "") -> Control:
	var r := _row(title, desc)
	var on := bool(GameManager.settings.get(key, key != "fullscreen" and key != "auto_battle" and key != "reduce_motion"))
	var sw := CinderSwitch.make(on, func(now: bool): GameManager.set_setting(key, now))
	sw.name = "Toggle_" + key
	(r[1] as HBoxContainer).add_child(sw)
	return r[0]


static func _speed_row() -> Control:
	var r := _row("Default Battle Speed", "Speed used when a battle starts.")
	var fast := float(GameManager.settings.get("battle_speed", 1.0)) >= 1.5
	var seg := CinderTabs.make(["1x", "2x"], 1 if fast else 0, func(i: int): GameManager.set_setting("battle_speed", 2.0 if i == 1 else 1.0), 80)
	seg.name = "Toggle_battle_speed"
	seg.custom_minimum_size.x = 250
	(r[1] as HBoxContainer).add_child(seg)
	return r[0]


static func _margin_row() -> Control:
	var r := _row("Screen Margins", "Extra space at the top and bottom for phones with a notch or rounded corners.")
	var row: HBoxContainer = r[1]
	var names := ["NONE", "SMALL", "MEDIUM", "LARGE"]
	var cur := int(GameManager.settings.get("safe_area", 0))
	var minus := UIKit.btn("", "quiet", Vector2(88, 88), "res://assets/icons/minus.png")
	minus.name = "MarginMinus"
	var val := UIKit.label(names[cur], UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 6)
	val.custom_minimum_size.x = 150
	var plus := UIKit.btn("", "quiet", Vector2(88, 88), "res://assets/icons/plus.png")
	plus.name = "MarginPlus"
	var change := func(d: int):
		var n := clampi(int(GameManager.settings.get("safe_area", 0)) + d, 0, 3)
		GameManager.set_setting("safe_area", n)
		val.text = names[n]
		UIManager.toast("Screen margins apply when a screen opens.", "info")
	minus.pressed.connect(func(): change.call(-1))
	plus.pressed.connect(func(): change.call(1))
	row.add_child(minus)
	row.add_child(val)
	row.add_child(plus)
	return r[0]


static func _tutorial_row(_host: Control) -> Control:
	var r := _row("Tutorial Tips", "Show the first-time hints and guides again.")
	var reset := UIKit.btn("RESET", "quiet", Vector2(220, 88))
	reset.name = "ResetTutorial"
	reset.pressed.connect(func():
		GameManager.reset_tutorial()
		reset.disabled = true
		reset.text = "DONE"
		UIManager.toast("Tutorial tips will show again.", "success"))
	(r[1] as HBoxContainer).add_child(reset)
	return r[0]


static func _account(v: VBoxContainer) -> void:
	var r := _row(GameManager.player_name(), "Rank %d  -  %d heroes  -  %d stars" % [GameManager.rank(),
			GameManager.owned_units().size(), GameManager.all_stars()])
	var prof := UIKit.btn("PROFILE", "secondary", Vector2(240, 88))
	prof.name = "OpenProfile"
	prof.pressed.connect(func(): SceneRouter.go("profile"))
	(r[1] as HBoxContainer).add_child(prof)
	v.add_child(r[0])
	var s := _row("Save Data", "Progress is saved automatically after every battle, summon and upgrade.")
	var chk := UIKit.icon("res://assets/icons/check.png", 48)
	(s[1] as HBoxContainer).add_child(chk)
	v.add_child(s[0])
	var t := _row("Title Screen", "Return to the title screen. Your progress stays saved.")
	var tb := UIKit.btn("TITLE", "quiet", Vector2(220, 88))
	tb.name = "ToTitle"
	tb.pressed.connect(func(): SceneRouter.go("main_menu"))
	(t[1] as HBoxContainer).add_child(tb)
	v.add_child(t[0])
	v.add_child(_note("Cinderbound  v%s" % ProjectSettings.get_setting("application/config/version", "")))
