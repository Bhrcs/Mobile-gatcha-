extends ScreenBase
## Unit collection: rarity-framed cards, element filter chips and sort options.
## Only filters/sorts backed by real data are offered.

const SORTS := [["RECENT", "recent"], ["POWER", "power"], ["LEVEL", "level"], ["RARITY", "rarity"], ["ELEMENT", "element"],
		["FAVORITE", "favorite"]]
const ELEMENTS := ["all", "fire", "water", "nature"]

var grid: GridContainer
var count_label: Label
var sort_button: FantasyButton
var element_filter := "all"
var sort_key := "recent"
var _chips: Dictionary = {}
var _cards: Array[UnitCard] = []


func _ready() -> void:
	if not require_profile():
		return
	var area := build_frame("bg_camp", "UNITS", "units", Callable(), 0.55)
	var col := UIKit.vbox(12)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)

	# filter + sort bar
	var bar := PanelFrame.make("plank", 10)
	col.add_child(bar)
	var row := UIKit.hbox(8)
	bar.add_child(row)
	for el in ELEMENTS:
		var chip := Button.new()
		chip.name = "Filter_" + el
		chip.custom_minimum_size = Vector2(96, 96)
		chip.focus_mode = Control.FOCUS_NONE
		if el == "all":
			chip.text = "ALL"
			chip.add_theme_font_size_override("font_size", 30)
		else:
			chip.icon = load("res://assets/icons/orb_%s.png" % el)
			chip.expand_icon = true
			chip.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		chip.tooltip_text = "Show %s units" % ("all" if el == "all" else Database.element_name(el))
		UIKit.hook_sounds(chip)
		var e: String = el
		chip.pressed.connect(func(): _set_filter(e))
		row.add_child(chip)
		_chips[el] = chip
	row.add_child(UIKit.spacer())
	var codex := FantasyButton.make("CODEX", "steel", Vector2(200, 96), "res://assets/icons/codex.png")
	codex.name = "CodexButton"
	codex.add_theme_font_size_override("font_size", 28)
	codex.pressed.connect(func(): SceneRouter.go("codex"))
	row.add_child(codex)
	sort_button = FantasyButton.make("", "steel", Vector2(300, 96))
	sort_button.name = "SortButton"
	sort_button.add_theme_font_size_override("font_size", 30)
	sort_button.pressed.connect(_cycle_sort)
	row.add_child(sort_button)

	var info := UIKit.hbox(12)
	var hint := UIKit.label("Tap a hero to train, evolve or inspect.", UIKit.T_SMALL, UIKit.MUTED)
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.add_child(hint)
	count_label = UIKit.label("", UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 6)
	info.add_child(count_label)
	col.add_child(info)

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
	grid.add_theme_constant_override("v_separation", 14)
	center.add_child(grid)
	AudioManager.play_music("menu")
	_rebuild()


func _set_filter(el: String) -> void:
	element_filter = el
	_rebuild()


func _cycle_sort() -> void:
	var i := 0
	for n in SORTS.size():
		if SORTS[n][1] == sort_key:
			i = n
	sort_key = SORTS[(i + 1) % SORTS.size()][1]
	_rebuild()


func _sort_label() -> String:
	for s in SORTS:
		if s[1] == sort_key:
			return "SORT: " + s[0]
	return "SORT"


func _rebuild() -> void:
	sort_button.text = _sort_label()
	for el in _chips.keys():
		var chip: Button = _chips[el]
		var on: bool = el == element_filter
		var sb := UIKit.tex_style("v2_chip_on.png" if on else "v2_chip.png", 9, 6, false)
		for st in ["normal", "hover", "pressed", "hover_pressed", "focus"]:
			chip.add_theme_stylebox_override(st, sb)
		chip.modulate = Color.WHITE if on else Color(0.75, 0.74, 0.8)
	for c in grid.get_children():
		c.queue_free()
	_cards.clear()
	var units: Array = []
	var owned := GameManager.owned_units()
	for i in owned.size():
		var u: Dictionary = owned[i]
		var def := Database.get_character(u.get("char_id", ""))
		if element_filter != "all" and def.get("element", "") != element_filter:
			continue
		units.append({"unit": u, "def": def, "idx": i, "stats": GameManager.unit_stats(u)})
	units.sort_custom(_compare)
	for entry in units:
		var card := UnitCard.make(entry["unit"])
		card.tapped.connect(func(uid: String):
			AudioManager.play_sfx("unit_select", 0.03)
			SceneRouter.go("unit_detail", {"uid": uid}))
		grid.add_child(card)
		_cards.append(card)
	count_label.text = "UNITS  %d / %d    CODEX %d / %d" % [units.size(), owned.size(),
			GameManager.profile.get("codex", []).size(), Database.family_ids().size()]
	if units.is_empty():
		var empty := UIKit.label("No units of this element yet.", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
		empty.custom_minimum_size = Vector2(1000, 200)
		grid.add_child(empty)


func _compare(a: Dictionary, b: Dictionary) -> bool:
	match sort_key:
		"power":
			return GameManager.unit_power(a["unit"]) > GameManager.unit_power(b["unit"])
		"element":
			var order := ["fire", "water", "nature"]
			return order.find(a["def"].get("element", "")) < order.find(b["def"].get("element", "")) or \
				(a["def"].get("element", "") == b["def"].get("element", "") and int(a["unit"]["level"]) > int(b["unit"]["level"]))
		"favorite":
			var fa := 1 if a["unit"].get("favorite", false) else 0
			var fb := 1 if b["unit"].get("favorite", false) else 0
			return fa > fb or (fa == fb and int(a["idx"]) > int(b["idx"]))
		"level":
			return int(a["unit"].get("level", 1)) > int(b["unit"].get("level", 1))
		"rarity":
			return int(a["def"].get("rarity", 3)) > int(b["def"].get("rarity", 3))
		"atk":
			return int(a["stats"].get("atk", 0)) > int(b["stats"].get("atk", 0))
		"hp":
			return int(a["stats"].get("hp", 0)) > int(b["stats"].get("hp", 0))
	return int(a["idx"]) > int(b["idx"])   # recent: newest first
