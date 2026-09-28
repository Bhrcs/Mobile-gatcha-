class_name LoadingOverlay
extends Control
## Full-screen loading cover. Only shown while a real load is in progress
## (UIManager / SceneRouter show it when loading takes longer than a moment)
## - never used to fake a delay.

const TIPS := [
	"Fire beats Nature, Nature beats Water, Water beats Fire.",
	"Light and Dark deal bonus damage to each other.",
	"Tap a status icon in battle to see what it does.",
	"Clear a stage without losing a hero for its third star.",
	"Duplicate heroes become Soul Shards - use them to level up Bursts.",
	"Tower floors give the evolution materials you need.",
	"Your leader's skill works for the whole squad.",
]

var _spin: TextureRect


static func create(text := "") -> LoadingOverlay:
	var o := LoadingOverlay.new()
	o.name = "LoadingOverlay"
	o.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	o.mouse_filter = Control.MOUSE_FILTER_STOP
	var dim := ColorRect.new()
	dim.color = Color(0.05, 0.03, 0.07, 0.96)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	o.add_child(dim)
	var v := UIKit.vbox(UIKit.SP_XL)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	o.add_child(v)
	var holder := Control.new()
	holder.custom_minimum_size = Vector2(96, 96)
	holder.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(holder)
	o._spin = UIKit.icon("res://assets/icons/fire.png", 96)
	o._spin.pivot_offset = Vector2(48, 48)
	holder.add_child(o._spin)
	v.add_child(UIKit.label(text if not text.is_empty() else "LOADING", UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER))
	var tip := UIKit.wrap_label(TIPS[randi() % TIPS.size()], UIKit.T_BODY, UIKit.MUTED)
	tip.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tip.custom_minimum_size.x = 860
	tip.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(tip)
	return o


func _process(_delta: float) -> void:
	if _spin:
		# gentle pulse rather than a fast spinner (pixel art does not rotate well)
		var t := Time.get_ticks_msec() / 1000.0
		_spin.modulate.a = 0.6 + 0.4 * sin(t * 4.0)
		_spin.scale = Vector2.ONE * (1.0 + 0.06 * sin(t * 4.0))
