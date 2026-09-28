class_name NavBar
extends PanelFrame
## Persistent bottom navigation (CinderBottomNav): HOME / QUEST / UNITS / SUMMON / MENU.
## The selected tab is raised and lit, its icon hops, and a gold marker slides
## over from the previously selected tab. Features that unlock later show a lock
## (tap explains where it opens); red markers flag things worth a look.

const ITEMS := [
	["HOME", "home", "home", ""], ["QUEST", "quest", "world_select", ""], ["UNITS", "units", "units", "units"],
	["SUMMON", "summon", "summon", "summon"], ["MENU", "menu", "menu", ""],
]
## Which tab lights up for a given screen.
const TAB_OF := {"home": "home", "world_select": "world_select", "stage_select": "world_select", "tower": "world_select",
		"units": "units", "unit_detail": "units", "codex": "units", "squad": "units", "train": "units", "evolve": "units",
		"summon": "summon", "menu": "menu", "inventory": "menu", "missions": "menu", "profile": "menu",
		"settings": "menu", "help": "menu"}
const HEIGHT := 200

static var _last_index := -1

var current := ""
var buttons: Array = []
var _marker: ColorRect


static func attach(parent: Control, current_tab: String) -> NavBar:
	var n := NavBar.new()
	n.name = "NavBar"
	n.current = TAB_OF.get(current_tab, current_tab)
	n.set_variant("plank", 8)
	n.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	n.offset_top = -HEIGHT - UIKit.safe_bottom()
	n.offset_bottom = -UIKit.safe_bottom()
	parent.add_child(n)
	return n


func _ready() -> void:
	var row := UIKit.hbox(8)
	add_child(row)
	var active_index := -1
	for i in ITEMS.size():
		var item: Array = ITEMS[i]
		var b := Button.new()
		b.name = "Nav_" + item[0]
		b.text = item[0]
		b.icon = load("res://assets/icons/nav_%s.png" % item[1])
		b.expand_icon = true
		b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.custom_minimum_size = Vector2(0, 176)
		b.focus_mode = Control.FOCUS_NONE
		b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		b.add_theme_font_size_override("font_size", UIKit.T_BODY)
		b.add_theme_constant_override("outline_size", 8)
		b.add_theme_constant_override("icon_max_width", 80)
		var active: bool = item[2] == current
		if active:
			active_index = i
		var sb := StyleBoxTexture.new()
		sb.texture = load("res://assets/ui/v2_nav_on.png" if active else "res://assets/ui/v2_nav.png")
		for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
			sb.set_texture_margin(side, 12)
			sb.set_content_margin(side, 10)
		sb.content_margin_top = 8 if active else 16
		var pressed := sb.duplicate()
		pressed.modulate_color = Color(0.8, 0.8, 0.8)
		pressed.content_margin_top = sb.content_margin_top + 6
		var hover := sb.duplicate()
		hover.modulate_color = Color(1.15, 1.1, 1.05)
		for st in ["normal", "disabled"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_stylebox_override("hover", hover)
		b.add_theme_stylebox_override("pressed", pressed)
		b.add_theme_stylebox_override("hover_pressed", pressed)
		b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
		b.add_theme_color_override("font_color", UIKit.GOLD if active else UIKit.MUTED)
		b.add_theme_color_override("font_hover_color", Color.WHITE)
		b.add_theme_color_override("font_pressed_color", UIKit.GOLD)
		if not active:
			b.modulate = Color(0.82, 0.8, 0.84)
		UIKit.hook_sounds(b)
		var target: String = item[2]
		var feature: String = item[3]
		var locked := not feature.is_empty() and not GameManager.feature_unlocked(feature)
		if locked:
			b.modulate = Color(0.55, 0.53, 0.58)
			var lk := UIKit.icon("res://assets/icons/lock.png", 40)
			lk.position = Vector2(8, 8)
			b.add_child(lk)
			b.pressed.connect(func(): UIManager.toast("%s unlocks after clearing %s." % [String(item[0]).capitalize(),
					GameManager.feature_unlock_label(feature)], "info"))
		elif not active:
			b.pressed.connect(func(): SceneRouter.go(target, {}, "tab"))
		else:
			# tapping the current tab returns to its root screen (e.g. Unit Detail -> Units)
			b.pressed.connect(func():
				var cs := get_tree().current_scene
				if cs and SceneRouter.current != target:
					SceneRouter.go(target, {}, "tab"))
		row.add_child(b)
		buttons.append(b)
		if not locked:
			var show := false
			match target:
				"units":
					show = GameManager.units_badge()
				"summon":
					show = GameManager.summon_badge()
				"menu":
					show = GameManager.missions_claimable() > 0
			if show:
				UIKit.badge(b)
	if active_index >= 0:
		_animate_selection.call_deferred(active_index)


## Gold marker slides from the previous tab; the new tab's icon hops once.
func _animate_selection(index: int) -> void:
	var b: Button = buttons[index]
	await get_tree().process_frame
	if not is_instance_valid(b) or b.size.x <= 0:
		return
	# the marker lives inside the selected button (the bar itself is a container)
	_marker = ColorRect.new()
	_marker.name = "NavMarker"
	_marker.color = UIKit.GOLD
	_marker.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_marker.size = Vector2(b.size.x * 0.5, 6)
	b.add_child(_marker)
	var target_x := b.size.x * 0.25
	var y := b.size.y - 18
	var from_x := target_x
	if _last_index >= 0 and _last_index != index and _last_index < buttons.size():
		var pb: Button = buttons[_last_index]
		from_x = pb.global_position.x - b.global_position.x + pb.size.x * 0.25
	_marker.position = Vector2(from_x, y)
	_last_index = index
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_marker, "position:x", target_x, 0.22).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	b.pivot_offset = b.size / 2.0
	b.scale = Vector2(0.94, 0.94)
	tw.tween_property(b, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
