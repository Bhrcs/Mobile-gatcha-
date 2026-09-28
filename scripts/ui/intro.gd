extends Control
## Short story introduction shown after choosing a starter (tutorial start).

var pages: Array = []
var page := 0
var text_label: Label
var page_label: Label
var btn_next: Button


func _ready() -> void:
	UIKit.screen_background(self, "bg_forest", 0.45)
	var starter := Database.get_character(GameManager.profile.get("starter_id", ""))
	var name_s: String = starter.get("name", "The hero")
	pages = [
		"The Ashroot Wilds were once the quietest forest in the realm - old trees, cold streams and broken stones from a forgotten age.",
		"Then the ground began to smoulder. Streams boiled. Beasts grew restless, and something ancient stirred at the Heart of the forest.",
		"%s has come to the edge of the Wilds to find out why.\n\n%s" % [name_s, starter.get("lore", "")],
		"Fight through ten stages, grow stronger with every victory, and reach the Heart of Ashroot.\n\nYour first battle awaits.",
	]
	var col := UIKit.vbox(24)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	col.offset_left = 30
	col.offset_right = -30
	col.offset_top = 90
	col.offset_bottom = -60
	add_child(col)
	col.add_child(UIKit.title_plate("ASHROOT WILDS"))
	var pf := UIKit.portrait_frame(starter, 480)
	pf.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(pf)
	var p := UIKit.panel()
	p.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(p)
	var v := UIKit.vbox(20)
	p.add_child(v)
	text_label = UIKit.wrap_label("", 40)
	text_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(text_label)
	page_label = UIKit.label("", 30, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
	v.add_child(page_label)
	var bottom := UIKit.hbox(24)
	bottom.alignment = BoxContainer.ALIGNMENT_CENTER
	var skip := UIKit.button("SKIP", "", Vector2(320, 120), "stone")
	btn_next = UIKit.button("NEXT", "", Vector2(420, 120), "ember")
	for b in [skip, btn_next]:
		b.add_theme_font_size_override("font_size", 40)
	bottom.add_child(skip)
	bottom.add_child(btn_next)
	col.add_child(bottom)
	skip.pressed.connect(_finish)
	btn_next.pressed.connect(_next)
	AudioManager.play_music("world")
	_show_page()


func _show_page() -> void:
	text_label.text = pages[page]
	text_label.visible_ratio = 0.0
	create_tween().tween_property(text_label, "visible_ratio", 1.0, 0.6)
	page_label.text = "%d / %d" % [page + 1, pages.size()]
	btn_next.text = "BEGIN" if page == pages.size() - 1 else "NEXT"


func _next() -> void:
	if page < pages.size() - 1:
		page += 1
		_show_page()
	else:
		_finish()


func _finish() -> void:
	GameManager.mark_intro_seen()
	SceneRouter.go("stage_select", {"highlight": Database.stage_order[0]})
