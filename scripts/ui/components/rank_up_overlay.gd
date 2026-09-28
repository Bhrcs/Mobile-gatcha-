class_name RankUpOverlay
extends Control
## Full-screen RANK UP presentation: the new rank stamps in, then its rewards
## (Energy refilled, Max Energy up, milestone Gems). Tap or OK to continue.

signal closed


static func play(parent: Node, ups: Array) -> void:
	if ups.is_empty():
		return
	var o := RankUpOverlay.new()
	o.name = "RankUpOverlay"
	parent.add_child(o)
	o._build(ups)
	await o.closed


func _build(ups: Array) -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	z_index = 60
	gui_input.connect(_on_input)
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.01, 0.05, 0.82)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var col := UIKit.vbox(18)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.custom_minimum_size.x = 900
	center.add_child(col)
	var title := UIKit.heading("RANK UP!", 130, UIKit.GOLD)
	title.add_theme_constant_override("outline_size", 20)
	title.add_theme_color_override("font_outline_color", Color("#3a1404"))
	col.add_child(title)
	var last: Dictionary = ups[-1]
	var badge := PanelFrame.make("slot", 20)
	badge.custom_minimum_size = Vector2(260, 220)
	badge.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var bv := UIKit.vbox(0)
	bv.alignment = BoxContainer.ALIGNMENT_CENTER
	badge.add_child(bv)
	var ic := UIKit.icon("res://assets/icons/rank.png", 80)
	ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	bv.add_child(ic)
	var num := UIKit.label("RANK %d" % int(last["rank"]), UIKit.T_HEAD, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 10)
	num.name = "RankNumber"
	bv.add_child(num)
	col.add_child(badge)
	var energy_up := 0
	var gems := 0
	for u in ups:
		energy_up += int(u.get("energy_max_up", 0))
		gems += int(u.get("gems", 0))
	var lines: Array = [["res://assets/icons/energy.png", "Energy fully restored! (%d / %d)" % [GameManager.energy(), GameManager.max_energy()]]]
	if energy_up > 0:
		lines.append(["res://assets/icons/energy.png", "Max Energy +%d" % energy_up])
	if gems > 0:
		lines.append(["res://assets/icons/gem.png", "Rank reward: +%d Gems" % gems])
	var line_nodes: Array = []
	for l in lines:
		var h := UIKit.hbox(12)
		h.alignment = BoxContainer.ALIGNMENT_CENTER
		h.add_child(UIKit.icon(l[0], 48))
		h.add_child(UIKit.label(l[1], UIKit.T_BODY, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_LEFT, 6))
		h.modulate.a = 0.0
		col.add_child(h)
		line_nodes.append(h)
	var ok := FantasyButton.make("OK", "ember", Vector2(320, 116))
	ok.name = "RankUpOK"
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	ok.modulate.a = 0.0
	col.add_child(ok)
	ok.pressed.connect(_close)
	UIKit.sparkle(self, Rect2(80, 500, 920, 600), Color("#ffe08a"), 20)
	AudioManager.play_sfx("rank_up")
	# animate
	title.pivot_offset = Vector2(450, 70)
	title.scale = Vector2(2.2, 2.2)
	title.modulate.a = 0.0
	badge.pivot_offset = badge.custom_minimum_size / 2
	badge.scale = Vector2(0.3, 0.3)
	var tw := create_tween()
	tw.tween_property(title, "modulate:a", 1.0, 0.12)
	tw.parallel().tween_property(title, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK)
	tw.tween_property(badge, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK)
	for n in line_nodes:
		tw.tween_property(n, "modulate:a", 1.0, 0.18)
	tw.tween_property(ok, "modulate:a", 1.0, 0.15)


func _on_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		_close()


func _close() -> void:
	if is_queued_for_deletion():
		return
	closed.emit()
	queue_free()
