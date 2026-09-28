extends ScreenBase
## Unit collection: rarity-framed cards with indicators in fixed places, quick
## element chips and a FILTER & SORT overlay (element, rarity, role, can evolve,
## favourites; level / rarity / power / stats / name / recent). The choice is
## remembered between sessions.

const ELEMENTS := ["all", "fire", "water", "nature"]

var grid: GridContainer
var count_label: Label
var sort_button: FantasyButton
var filter_button: FantasyButton
var state: Dictionary = {}
var _chips: Dictionary = {}
var _cards: Array[UnitCard] = []


func _ready() -> void:
	if not require_profile():
		return
	state = UnitFilter.load_state()
	var area := build_frame("bg_camp", "UNITS", "units", Callable(), 0.55, true, {"help": "units"})
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
	var codex := UIKit.btn("", "secondary", Vector2(96, 96), "res://assets/icons/codex.png")
	codex.name = "CodexButton"
	codex.tooltip_text = "Codex"
	codex.pressed.connect(func(): SceneRouter.go("codex"))
	row.add_child(codex)
	filter_button = UIKit.btn("FILTER", "secondary", Vector2(190, 96), "res://assets/icons/filter.png")
	filter_button.name = "FilterButton"
	filter_button.add_theme_font_size_override("font_size", UIKit.T_SMALL)
	filter_button.pressed.connect(_open_filter)
	row.add_child(filter_button)
	sort_button = UIKit.btn("", "secondary", Vector2(210, 96), "res://assets/icons/sort.png")
	sort_button.name = "SortButton"
	sort_button.add_theme_font_size_override("font_size", UIKit.T_SMALL)
	sort_button.pressed.connect(_open_filter)
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
	state["el"] = el
	UnitFilter.save_state(state)
	_rebuild()


func _open_filter() -> void:
	UnitFilter.open(self, state, func(_st): _rebuild())


func _rebuild() -> void:
	sort_button.text = UnitFilter.sort_label(state)
	var active := UnitFilter.active_count(state)
	filter_button.text = "FILTER" if active == 0 else "FILTER %d" % active
	filter_button.set_selected(active > 0)
	for el in _chips.keys():
		var chip: Button = _chips[el]
		var on: bool = el == state["el"]
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
		if not UnitFilter.matches(state, u, def):
			continue
		units.append({"unit": u, "def": def, "idx": i, "stats": GameManager.unit_stats(u)})
	units.sort_custom(func(a, b): return UnitFilter.compare(state, a, b))
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
		# empty state: say why and how to get out of it
		var box := UIKit.vbox(UIKit.SP_M)
		box.custom_minimum_size = Vector2(1000, 260)
		box.alignment = BoxContainer.ALIGNMENT_CENTER
		box.add_child(UIKit.label("No heroes match these filters.", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		var clear := UIKit.btn("CLEAR FILTERS", "secondary", Vector2(360, 100))
		clear.name = "ClearFilters"
		clear.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		clear.pressed.connect(func():
			for k in UnitFilter.DEFAULT:
				state[k] = UnitFilter.DEFAULT[k]
			UnitFilter.save_state(state)
			_rebuild())
		box.add_child(clear)
		grid.add_child(box)
