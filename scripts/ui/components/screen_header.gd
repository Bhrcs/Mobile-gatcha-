class_name ScreenHeader
extends Control
## Reusable screen header (CinderHeader): [< BACK]  TITLE  [? help / right widget].
## Back is always in the same place, the title is centred and auto-fits, and the
## right slot holds a help button or a screen-specific widget. Esc = Back on PC.

const HEIGHT := 120

var title_label: Label
var back_button: FantasyButton
var right_slot: HBoxContainer


static func attach(parent: Control, title: String, on_back: Callable, top: float, help_topic := "") -> ScreenHeader:
	var h := ScreenHeader.new()
	h.name = "Header"
	h.set_anchors_preset(Control.PRESET_TOP_WIDE)
	h.offset_top = top
	h.offset_bottom = top + HEIGHT
	h.offset_left = UIKit.MARGIN - 4
	h.offset_right = -(UIKit.MARGIN - 4)
	parent.add_child(h)
	h._build(title, on_back, help_topic)
	return h


func _build(title: String, on_back: Callable, help_topic: String) -> void:
	var plank := PanelFrame.make("plank", 10)
	plank.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(plank)
	var row := UIKit.hbox(UIKit.SP_L)
	plank.add_child(row)
	var left := Control.new()
	left.custom_minimum_size = Vector2(200, 96)
	left.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(left)
	if on_back.is_valid():
		back_button = UIKit.btn("BACK", "quiet", Vector2(200, 96), "res://assets/icons/back.png")
		back_button.name = "BackButton"
		back_button.add_theme_font_size_override("font_size", UIKit.T_BODY)
		back_button.add_theme_constant_override("h_separation", 6)
		back_button.pressed.connect(on_back)
		left.add_child(back_button)
	title_label = UIKit.label(title, UIKit.T_SCREEN, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_CENTER, 10)
	title_label.name = "Title"
	title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	title_label.clip_text = true
	row.add_child(title_label)
	right_slot = UIKit.hbox(UIKit.SP_S)
	right_slot.custom_minimum_size = Vector2(200, 96)
	right_slot.alignment = BoxContainer.ALIGNMENT_END
	row.add_child(right_slot)
	if not help_topic.is_empty():
		add_help(help_topic)
	# long titles shrink, then truncate (full title in the tooltip)
	resized.connect(func(): UIKit.fit_label(title_label, max(120.0, size.x - 460.0), UIKit.T_BODY))


## "?" button that opens the Help & Guide screen on the given topic.
func add_help(topic: String) -> void:
	var b := UIKit.btn("", "quiet", Vector2(96, 96), "res://assets/icons/help.png")
	b.name = "HelpButton"
	b.tooltip_text = "Help & Guide"
	b.pressed.connect(func(): SceneRouter.go("help", {"topic": topic}))
	right_slot.add_child(b)


func set_title(t: String) -> void:
	title_label.text = t
	UIKit.fit_label(title_label, max(120.0, size.x - 460.0), UIKit.T_BODY)
