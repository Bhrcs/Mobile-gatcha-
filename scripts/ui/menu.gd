extends ScreenBase
## MENU tab: everything that is not a main tab, as large labelled tiles.
## Locked features stay visible, dimmed with a lock, and say where they open.

const ITEMS := [
	# label, icon, scene, feature, description
	["SQUAD", "res://assets/icons/leader.png", "squad", "squad", "Choose who fights and who leads"],
	["ITEMS", "res://assets/icons/nav_bag.png", "inventory", "", "Materials, wisps and treasures"],
	["MISSIONS", "res://assets/icons/missions.png", "missions", "missions", "Daily & weekly goals, login bonus"],
	["TOWERS", "res://assets/icons/tower.png", "tower", "tower", "Evolution materials"],
	["CODEX", "res://assets/icons/codex.png", "codex", "units", "Every hero you have met"],
	["PROFILE", "res://assets/icons/profile.png", "profile", "", "Rank, records and your name"],
	["SETTINGS", "res://assets/icons/nav_settings.png", "settings", "", "Audio, gameplay, graphics"],
	["HELP", "res://assets/icons/help.png", "help", "", "Guide, elements and tips"],
]


func _ready() -> void:
	if not require_profile():
		return
	var area := build_frame("bg_camp", "MENU", "menu", Callable(), 0.6)
	var scroll := ScrollContainer.new()
	scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	area.add_child(scroll)
	var v := UIKit.vbox(UIKit.SP_L)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(v)
	var grid := GridContainer.new()
	grid.name = "MenuGrid"
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", UIKit.SP_M)
	grid.add_theme_constant_override("v_separation", UIKit.SP_M)
	v.add_child(grid)
	for it in ITEMS:
		grid.add_child(_tile(it))
	var title := UIKit.btn("TITLE SCREEN", "quiet", Vector2(420, 100))
	title.name = "Menu_TITLE"
	title.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	title.pressed.connect(func(): SceneRouter.go("main_menu"))
	v.add_child(title)
	var ver := UIKit.label("Cinderbound v%s" % ProjectSettings.get_setting("application/config/version", ""), UIKit.T_SMALL,
			UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	v.add_child(ver)


func _tile(it: Array) -> Control:
	var b := UIKit.btn("", "secondary", Vector2(0, 170))
	b.name = "Menu_" + it[0]
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var h := UIKit.hbox(UIKit.SP_M)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 26
	h.offset_right = -16
	h.offset_top = 8
	h.offset_bottom = -14
	b.add_child(h)
	h.add_child(UIKit.icon(it[1], 80))
	var col := UIKit.vbox(2)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_child(UIKit.label(it[0], UIKit.T_NAME, Color.WHITE, HORIZONTAL_ALIGNMENT_LEFT, 10))
	var d := UIKit.label(it[4], UIKit.T_SMALL, Color("#d8d0e0"), HORIZONTAL_ALIGNMENT_LEFT, 5)
	d.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	col.add_child(d)
	h.add_child(col)
	var scene: String = it[2]
	var feature: String = it[3]
	if not feature.is_empty() and not GameManager.feature_unlocked(feature):
		b.modulate = Color(0.55, 0.53, 0.58)
		var lk := UIKit.icon("res://assets/icons/lock.png", 40)
		lk.position = Vector2(12, 12)
		b.add_child(lk)
		d.text = "Opens after %s" % GameManager.feature_unlock_label(feature)
		b.pressed.connect(func(): UIManager.toast("%s unlocks after clearing %s." % [String(it[0]).capitalize(),
				GameManager.feature_unlock_label(feature)], "info"))
	else:
		b.pressed.connect(func(): SceneRouter.go(scene))
		if scene == "missions":
			var mc := GameManager.missions_claimable()
			if mc > 0:
				UIKit.badge(b, str(mc))
			elif GameManager.login_available():
				UIKit.badge(b)
	return b
