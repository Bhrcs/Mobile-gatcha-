class_name GameMenu
extends RefCounted
## MENU tab: squad, items, missions, codex, profile, settings and the title screen.
## Features that are still locked say where they open.


static func open(parent: Node) -> void:
	var p := FantasyPopup.open(parent, "MENU", 860)
	var v := p.content
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 16)
	grid.add_theme_constant_override("v_separation", 14)
	grid.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(grid)
	var items := [
		["SQUAD", "ember", "squad", "squad", "res://assets/icons/leader.png"],
		["ITEMS", "steel", "inventory", "", "res://assets/icons/nav_bag.png"],
		["MISSIONS", "steel", "missions", "missions", "res://assets/icons/missions.png"],
		["CODEX", "steel", "codex", "units", "res://assets/icons/codex.png"],
		["TOWERS", "steel", "tower", "tower", "res://assets/icons/tower.png"],
		["PROFILE", "steel", "profile", "", "res://assets/icons/profile.png"],
	]
	for it in items:
		var b := FantasyButton.make(it[0], it[1], Vector2(380, 110), it[4])
		b.name = "Menu_" + it[0]
		b.add_theme_font_size_override("font_size", 34)
		var scene: String = it[2]
		var feature: String = it[3]
		if not feature.is_empty() and not GameManager.feature_unlocked(feature):
			b.modulate = Color(0.55, 0.53, 0.58)
			b.pressed.connect(func(): UIKit.toast(parent, "Unlocks after clearing %s." % GameManager.feature_unlock_label(feature),
					UIKit.MUTED))
		else:
			b.pressed.connect(func():
				p.close()
				SceneRouter.go(scene))
			if scene == "missions" and GameManager.missions_claimable() > 0:
				UIKit.badge(b, str(GameManager.missions_claimable()))
		grid.add_child(b)
	var row := UIKit.hbox(16)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var st := FantasyButton.make("SETTINGS", "steel", Vector2(380, 104))
	st.name = "Menu_SETTINGS"
	st.pressed.connect(func(): SettingsPanel.open(parent))
	row.add_child(st)
	var title := FantasyButton.make("TITLE SCREEN", "stone", Vector2(380, 104))
	title.pressed.connect(func():
		p.close()
		SceneRouter.go("main_menu"))
	row.add_child(title)
	v.add_child(row)
	var close := FantasyButton.make("CLOSE", "stone", Vector2(320, 100))
	close.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	close.pressed.connect(p.close)
	v.add_child(close)
