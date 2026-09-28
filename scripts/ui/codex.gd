extends ScreenBase
## Hero Codex: every hero line in the realm (Owned X / 12). Owned heroes show
## their art, element, rarity path and lore; unknown heroes are silhouettes with
## only their element. Tapping an owned entry shows all of its forms.

var grid: GridContainer


func _ready() -> void:
	if not require_profile():
		return
	back_fallback = "units"
	var area := build_frame("bg_camp", "CODEX", "units", Callable(), 0.6)
	var col := UIKit.vbox(12)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	var owned: Array = GameManager.profile.get("codex", [])
	var fams := Database.family_ids()
	var head := PanelFrame.make("plank", 12)
	var hh := UIKit.hbox(12)
	head.add_child(hh)
	hh.add_child(UIKit.icon("res://assets/icons/codex.png", 56))
	var t := UIKit.label("OWNED  %d / %d" % [owned.size(), fams.size()], UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 8)
	t.name = "CodexCount"
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hh.add_child(t)
	hh.add_child(UIKit.label("Find more heroes at the Embergate.", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_RIGHT, 5))
	col.add_child(head)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	var center := CenterContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(center)
	grid = GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 12)
	center.add_child(grid)
	for cid in fams:
		var d := Database.get_character(cid)
		grid.add_child(_entry(d, owned.has(d.get("family", ""))))
	AudioManager.play_music("menu")


func _entry(d: Dictionary, known: bool) -> Control:
	var el: String = d.get("element", "neutral")
	var p := PanelFrame.make("card_%s" % el if known else "inset", 10)
	p.name = "Codex_%s" % d.get("family", "")
	p.custom_minimum_size = Vector2(244, 320)
	var v := UIKit.vbox(4)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(v)
	var art := UIKit.portrait_art(d, Vector2(216, 216))
	if not known:
		for ch in art.get_children():
			if ch is TextureRect and ch.texture is Texture2D and not ch.texture is GradientTexture2D:
				ch.modulate = Color(0, 0, 0, 0.9)     # silhouette
			elif ch is TextureRect:
				ch.modulate = Color(0.25, 0.25, 0.3)
	v.add_child(art)
	var name_l := UIKit.label(String(d.get("name", "")).get_slice(" ", 0) if known else "? ? ?", UIKit.T_SMALL,
			UIKit.TEXT if known else UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER, 5)
	v.add_child(name_l)
	var row := UIKit.hbox(4)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(UIKit.orb(el, 28))
	if known:
		var forms := Database.family_forms(d.get("family", ""))
		var top := Database.get_character(forms[-1])
		row.add_child(UIKit.label("%d-%d*" % [int(d.get("rarity", 3)), int(top.get("rarity", 3))], UIKit.T_SMALL, UIKit.GOLD,
				HORIZONTAL_ALIGNMENT_LEFT, 5))
	v.add_child(row)
	if known:
		UIKit.on_tap(p, func(): _details(d))
	else:
		UIKit.on_tap(p, func(): UIKit.toast(self, "An unknown %s hero. Summon at the Embergate to meet them." % Database.element_name(el),
				UIKit.MUTED))
	return p


func _details(d: Dictionary) -> void:
	var p := FantasyPopup.open(self, String(d.get("name", "")).to_upper(), 1000)
	p.name = "CodexDetails"
	var row := UIKit.hbox(10)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var forms := Database.family_forms(d.get("family", ""))
	for i in forms.size():
		var fd := Database.get_character(forms[i])
		var cell := UIKit.vbox(2)
		var frame := PanelFrame.make("rarity_%d" % clampi(int(fd.get("rarity", 3)), 3, 6), 6)
		frame.add_child(UIKit.portrait_art(fd, Vector2(220, 220)))
		cell.add_child(frame)
		var n := UIKit.label(fd.get("name", ""), UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 5)
		n.custom_minimum_size.x = 240
		n.clip_text = true
		cell.add_child(n)
		var s := UIKit.stars(int(fd.get("rarity", 3)), 24)
		s.alignment = BoxContainer.ALIGNMENT_CENTER
		cell.add_child(s)
		row.add_child(cell)
		if i < forms.size() - 1:
			row.add_child(UIKit.label(">", UIKit.T_HEAD, UIKit.EMBER, HORIZONTAL_ALIGNMENT_CENTER, 6))
	p.content.add_child(row)
	for line in ["%s  -  %s" % [d.get("role", ""), Database.element_name(d.get("element", ""))],
			"Burst: %s" % Database.get_skill(d.get("burst", "")).get("name", ""),
			"Passive: %s" % d.get("passive", {}).get("description", ""),
			"Leader: %s" % d.get("leader_skill", {}).get("description", ""), d.get("lore", "")]:
		var w := UIKit.wrap_label(line, UIKit.T_SMALL, Color("#e0d6c6"))
		w.custom_minimum_size.x = 920
		p.content.add_child(w)
	var u := GameManager.unit_of_family(d.get("family", ""))
	var br := UIKit.hbox(14)
	br.alignment = BoxContainer.ALIGNMENT_CENTER
	if not u.is_empty():
		var go := FantasyButton.make("VIEW HERO", "ember", Vector2(320, 110))
		var uid: String = u["uid"]
		go.pressed.connect(func():
			p.close()
			SceneRouter.go("unit_detail", {"uid": uid, "back": "codex"}))
		br.add_child(go)
	var close := FantasyButton.make("CLOSE", "stone", Vector2(260, 110))
	close.pressed.connect(p.close)
	br.add_child(close)
	p.content.add_child(br)
