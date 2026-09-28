extends Control
## Starter selection (portrait): three hero tiles on top, large detail card below.

var starters: Array[String] = []
var selected_id := ""
var cards: Dictionary = {}
var detail_box: VBoxContainer
var hero_sprite: UnitSpriteDisplay
var hero_stage: Control


func _ready() -> void:
	UIKit.screen_background(self, "bg_camp", 0.3)
	ScreenHeader.attach(self, "CHOOSE YOUR HERO", func(): SceneRouter.go("main_menu"), 10 + UIKit.safe_top())
	starters = Database.starter_ids()

	var body := UIKit.vbox(18)
	body.set_anchors_preset(Control.PRESET_FULL_RECT)
	body.offset_left = 20
	body.offset_right = -20
	body.offset_top = 144 + UIKit.safe_top()
	body.offset_bottom = -24
	add_child(body)

	var row := UIKit.hbox(16)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	body.add_child(row)
	for id in starters:
		var card := _make_card(id)
		row.add_child(card)
		cards[id] = card

	var detail := UIKit.panel()
	detail.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(detail)
	detail_box = UIKit.vbox(14)
	detail.add_child(detail_box)

	var buttons := UIKit.hbox(16)
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	var b_select := UIKit.button("SELECT", "", Vector2(330, 120), "ember")
	var b_skills := UIKit.button("SKILLS", "", Vector2(330, 120))
	var b_back := UIKit.button("BACK", "", Vector2(300, 120), "stone")
	b_select.pressed.connect(_on_select_pressed)
	b_skills.pressed.connect(func(): _show_skills(Database.get_character(selected_id)))
	b_back.pressed.connect(func(): SceneRouter.go("main_menu"))
	for b in [b_select, b_skills, b_back]:
		b.add_theme_font_size_override("font_size", 40)
		buttons.add_child(b)
	body.add_child(buttons)
	AudioManager.play_music("menu")
	_select(starters[0])


func _make_card(id: String) -> PanelContainer:
	var def := Database.get_character(id)
	var card := PanelFrame.make("card_" + str(def.get("element", "neutral")))
	card.name = "Starter_" + id
	card.custom_minimum_size = Vector2(330, 0)
	card.mouse_filter = Control.MOUSE_FILTER_STOP
	card.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	var v := UIKit.vbox(6)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	card.add_child(v)
	var pf := UIKit.portrait_frame(def, 220)
	pf.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(pf)
	v.add_child(UIKit.label(def.get("name", "").split(" ")[0], 40, UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 6))
	v.add_child(UIKit.label(def.get("role", ""), 20, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
	UIKit.on_tap(card, func(): _select(id))
	return card


func _select(id: String) -> void:
	selected_id = id
	for cid in cards.keys():
		var c: PanelFrame = cards[cid]
		var el := str(Database.get_character(cid).get("element", "neutral"))
		c.set_variant("card_%s%s" % [el, "_lit" if cid == id else ""])
		c.modulate = Color.WHITE if cid == id else Color(0.66, 0.66, 0.72)
	if not cards.is_empty():
		AudioManager.play_sfx("unit_select", 0.03, -4.0)
	_build_detail(Database.get_character(id))


func _build_detail(def: Dictionary) -> void:
	for ch in detail_box.get_children():
		ch.queue_free()
	var title := UIKit.hbox(14)
	title.add_child(UIKit.orb(def.get("element", ""), 60))
	var nm := UIKit.label(def.get("name", ""), 50, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 8)
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.add_child(nm)
	title.add_child(UIKit.stars(int(def.get("rarity", 3)), 48))
	detail_box.add_child(title)

	# hero on an element-coloured stage
	var stage := PanelFrame.make("inset", 6)
	stage.custom_minimum_size = Vector2(0, 432)
	detail_box.add_child(stage)
	var holder := Control.new()
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	stage.add_child(holder)
	var portrait := UIKit.portrait_art(def, Vector2(420, 420))
	portrait.position = Vector2(0, 0)
	portrait.size = Vector2(420, 420)
	holder.add_child(portrait)
	var sprite := UnitSpriteDisplay.new()
	sprite.setup(def.get("sprite", {}), 10.0, true, "victory")
	sprite.position = Vector2(540, 410 - sprite.custom_minimum_size.y)
	sprite.size = sprite.custom_minimum_size
	holder.add_child(sprite)

	var info := UIKit.hbox(30)
	info.add_child(UIKit.element_badge(def.get("element", ""), 30))
	info.add_child(UIKit.label(def.get("role", ""), 30, UIKit.TEXT))
	detail_box.add_child(info)
	var stats: Dictionary = def.get("base_stats", {})
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 80)
	grid.add_theme_constant_override("v_separation", 6)
	for key in ["hp", "atk", "def", "rec"]:
		grid.add_child(UIKit.stat_row(key.to_upper(), str(stats.get(key, 0)), 40))
	detail_box.add_child(grid)
	var desc := UIKit.wrap_label(def.get("description", ""), 30)
	desc.custom_minimum_size.x = 900
	detail_box.add_child(desc)
	for pair in [["NORMAL", def.get("normal_attack", ""), Color("#d06a1e")], ["BURST", def.get("burst", ""), Color("#2a6ad0")]]:
		var sk := Database.get_skill(pair[1])
		detail_box.add_child(UIKit.strip(pair[0], sk.get("name", ""), pair[2]))
		var d := UIKit.wrap_label(sk.get("description", ""), 30, Color("#e0d6c6"))
		d.custom_minimum_size.x = 900
		detail_box.add_child(d)


func _show_skills(def: Dictionary) -> void:
	var m := UIKit.modal(self, "SKILLS", 1000)
	var v: VBoxContainer = m["content"]
	for pair in [["NORMAL", def.get("normal_attack", ""), UIKit.EMBER], ["BURST", def.get("burst", ""), Color("#3a78d8")]]:
		var sk := Database.get_skill(pair[1])
		v.add_child(UIKit.strip(pair[0], sk.get("name", ""), pair[2]))
		var d := UIKit.wrap_label(sk.get("description", ""), 30)
		d.custom_minimum_size.x = 920
		v.add_child(d)
	var ok := UIKit.button("CLOSE", "", Vector2(320, 110), "stone")
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(ok)
	var popup: FantasyPopup = m["root"]
	ok.pressed.connect(popup.close)


func _on_select_pressed() -> void:
	var def := Database.get_character(selected_id)
	UIKit.confirm(self, "Begin your journey with %s?" % def.get("name", ""), func():
		GameManager.new_game(selected_id)
		AudioManager.play_sfx("level_up")
		SceneRouter.go("intro"))
