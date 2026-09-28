class_name BattleHUD
extends CanvasLayer
## Battle interface (portrait):
##   top    : stage plate, wave pips, loot counters, MENU
##   below  : enemy plates (boss gets the large crimson frame), tap to target
##   field  : (world) - wave / boss banners, Burst cut-ins and impact flashes
##   bottom : element-framed unit cards (2 columns, grows with party size), action log
## Emits intent signals only; BattleController decides what is allowed.

signal unit_selected(c: Combatant)
signal card_action(c: Combatant, action: String)
signal menu_requested
signal target_requested(c: Combatant)
signal auto_toggled(on: bool)
signal speed_toggled(speed: float)

const CARD_H := PartyCard.H
const LOG_LINES := 2
const TOP_H := 124
const LOG_H := 100

var bottom_block := 560.0       # height of everything under the battlefield (depends on party rows)
var _block: Control

var root: Control
var stage_label: Label
var stage_num: Label
var wave_label: Label
var wave_pips: HBoxContainer
var gold_label: Label
var drops_label: Label
var btn_menu: Button
var btn_auto: FantasyButton
var btn_speed: FantasyButton
var auto_on := false
var auto_available := true
var speed := 1.0
var enemy_row: HBoxContainer
var plates: Dictionary = {}          # Combatant -> EnemyPlate
var cards_grid: GridContainer
var cards: Dictionary = {}          # Combatant -> PartyCard
var log_box: VBoxContainer
var banner_layer: Control
var cutin: Control
var flash_rect: ColorRect
var _target: Combatant


func _ready() -> void:
	layer = 10
	root = Control.new()
	root.theme = UIKit.build_theme()    # CanvasLayers do not inherit the window theme
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	flash_rect = ColorRect.new()
	flash_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	flash_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	flash_rect.color = Color(1, 1, 1, 0)
	root.add_child(flash_rect)
	_build_top()
	_build_enemy_row()
	_build_bottom()
	banner_layer = Control.new()
	banner_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	banner_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(banner_layer)
	cutin = Control.new()
	cutin.set_anchors_preset(Control.PRESET_FULL_RECT)
	cutin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cutin.visible = false
	root.add_child(cutin)


## World-space y of the bottom edge of the battlefield.
func field_bottom() -> float:
	return root.get_viewport_rect().size.y - bottom_block


## World-space y below which the enemy HUD no longer covers the field.
func field_top() -> float:
	return UIKit.safe_top() + TOP_H + 160


# ------------------------------------------------------------------ layout
func _build_top() -> void:
	var top := PanelFrame.make("plank", 10)
	top.name = "TopBar"
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top.offset_left = 6
	top.offset_right = -6
	top.offset_top = 4 + UIKit.safe_top()
	top.offset_bottom = TOP_H + UIKit.safe_top()
	root.add_child(top)
	var row := UIKit.hbox(12)
	top.add_child(row)
	var badge := PanelFrame.make("slot", 6)
	badge.custom_minimum_size = Vector2(84, 84)
	stage_num = UIKit.label("", UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8)
	stage_num.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	badge.add_child(stage_num)
	row.add_child(badge)
	var mid := UIKit.vbox(2)
	mid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(mid)
	stage_label = UIKit.label("", UIKit.T_BODY, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_LEFT, 6)
	stage_label.clip_text = true
	mid.add_child(stage_label)
	var wrow := UIKit.hbox(8)
	wave_label = UIKit.label("", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5)
	wave_label.name = "WaveLabel"
	wrow.add_child(wave_label)
	wave_pips = UIKit.hbox(6)
	wave_pips.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	wrow.add_child(wave_pips)
	mid.add_child(wrow)
	var loot := UIKit.vbox(0)
	var g := UIKit.hbox(6)
	g.add_child(UIKit.icon("res://assets/icons/gold.png", 32))
	gold_label = UIKit.label("0", UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5)
	gold_label.custom_minimum_size.x = 90
	g.add_child(gold_label)
	loot.add_child(g)
	var d := UIKit.hbox(6)
	d.add_child(UIKit.icon("res://assets/icons/nav_bag.png", 32))
	drops_label = UIKit.label("0", UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 5)
	d.add_child(drops_label)
	loot.add_child(d)
	row.add_child(loot)
	btn_speed = FantasyButton.make("1x", "steel", Vector2(96, 88))
	btn_speed.name = "SpeedButton"
	btn_speed.add_theme_font_size_override("font_size", 30)
	btn_speed.pressed.connect(func(): set_speed(2.0 if speed < 1.5 else 1.0, true))
	row.add_child(btn_speed)
	btn_auto = FantasyButton.make("AUTO", "stone", Vector2(122, 88))
	btn_auto.name = "AutoButton"
	btn_auto.add_theme_font_size_override("font_size", 28)
	btn_auto.pressed.connect(func():
		if auto_available:
			set_auto(not auto_on, true)
		else:
			add_log("Auto Battle unlocks after clearing Stage 1-4.", UIKit.MUTED))
	row.add_child(btn_auto)
	btn_menu = FantasyButton.make("MENU", "stone", Vector2(128, 88))
	btn_menu.name = "BattleMenu"
	btn_menu.add_theme_font_size_override("font_size", 28)
	btn_menu.pressed.connect(func(): menu_requested.emit())
	row.add_child(btn_menu)


func _build_enemy_row() -> void:
	enemy_row = UIKit.hbox(6)
	enemy_row.name = "EnemyRow"
	enemy_row.set_anchors_preset(Control.PRESET_TOP_WIDE)
	enemy_row.offset_left = 8
	enemy_row.offset_right = -8
	enemy_row.offset_top = TOP_H + 8 + UIKit.safe_top()
	enemy_row.offset_bottom = TOP_H + 158 + UIKit.safe_top()
	enemy_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(enemy_row)


func _build_bottom() -> void:
	var block := Control.new()
	_block = block
	block.name = "BottomBlock"
	block.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	block.offset_top = -bottom_block
	block.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(block)
	var base := PanelFrame.make("panel", 0)
	base.set_anchors_preset(Control.PRESET_FULL_RECT)
	base.offset_left = -12
	base.offset_right = 12
	base.offset_bottom = 30
	base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	block.add_child(base)

	var v := UIKit.vbox(8)
	v.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 10
	v.offset_right = -10
	v.offset_top = 14
	v.offset_bottom = -8 - UIKit.safe_bottom()
	block.add_child(v)

	cards_grid = GridContainer.new()
	cards_grid.columns = 2
	cards_grid.add_theme_constant_override("h_separation", 8)
	cards_grid.add_theme_constant_override("v_separation", 8)
	v.add_child(cards_grid)

	var log_panel := PanelFrame.make("inset", 12)
	log_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(log_panel)
	var lh := UIKit.hbox(10)
	log_panel.add_child(lh)
	log_box = UIKit.vbox(0)
	log_box.alignment = BoxContainer.ALIGNMENT_END
	log_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	lh.add_child(log_box)
	var hint := UIKit.vbox(0)
	hint.name = "GestureHint"
	for pair in [["res://assets/icons/hand.png", "TAP  ATTACK"], ["res://assets/icons/gesture_up.png", "UP  BURST"],
			["res://assets/icons/gesture_down.png", "DOWN  GUARD"]]:
		var r := UIKit.hbox(4)
		r.add_child(UIKit.icon(pair[0], 16))
		r.add_child(UIKit.label(pair[1], UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4))
		hint.add_child(r)
	lh.add_child(hint)


# ------------------------------------------------------------------ auto / speed
func set_auto(on: bool, emit := false) -> void:
	auto_on = on and auto_available
	btn_auto.apply_style("ember" if auto_on else "stone")
	btn_auto.text = "AUTO" if auto_available else "AUTO"
	btn_auto.modulate = Color.WHITE if auto_available else Color(0.6, 0.6, 0.6)
	if emit:
		auto_toggled.emit(auto_on)


func set_auto_available(on: bool) -> void:
	auto_available = on
	set_auto(auto_on and on)


func set_speed(v: float, emit := false) -> void:
	speed = 2.0 if v >= 1.5 else 1.0
	btn_speed.text = "2x" if speed > 1.0 else "1x"
	btn_speed.apply_style("ember" if speed > 1.0 else "steel")
	if emit:
		speed_toggled.emit(speed)


## Red warning band for telegraphed enemy attacks.
func show_warning(text: String, sub: String) -> void:
	AudioManager.play_sfx("warning")
	flash_screen(Color("#ff3a2a"), 0.25, 0.25)
	await show_banner(text, Color("#ff7a5a"), 0.9, "boss", sub)


# ------------------------------------------------------------------ enemies
func set_enemies(enemies: Array) -> void:
	for ch in enemy_row.get_children():
		ch.queue_free()
	plates.clear()
	for e in enemies:
		var p := EnemyPlate.create(e)
		enemy_row.add_child(p)
		p.tapped.connect(func(c): target_requested.emit(c))
		plates[e] = p
	# boss plates take more room
	var any_boss := false
	for e in enemies:
		if bool(e.def.get("boss", false)):
			any_boss = true
	enemy_row.offset_bottom = enemy_row.offset_top + (170 if any_boss else 130)


# ------------------------------------------------------------------ party
func set_party(players: Array) -> void:
	for ch in cards_grid.get_children():
		ch.queue_free()
	cards.clear()
	for c in players:
		var card := PartyCard.new()
		cards_grid.add_child(card)
		card.setup(c)
		card.pressed.connect(func(cc): unit_selected.emit(cc))
		card.action.connect(func(cc, a): card_action.emit(cc, a))
		cards[c] = card
	# one wide card for a solo hero, otherwise two columns (grows to 3 rows for 5-6 heroes)
	cards_grid.columns = 1 if players.size() <= 1 else 2
	var rows: int = int(ceil(players.size() / float(cards_grid.columns)))
	rows = max(rows, 1)
	bottom_block = 22 + rows * (CARD_H + 8) + LOG_H + 16 + UIKit.safe_bottom()
	_block.offset_top = -bottom_block


func set_header(stage: Dictionary, wave: int, wave_total: int, _turn: int) -> void:
	stage_num.text = str(int(stage.get("number", 0)))
	stage_label.text = stage.get("name", "")
	wave_label.text = "WAVE %d/%d" % [wave + 1, wave_total]
	for ch in wave_pips.get_children():
		ch.queue_free()
	for i in wave_total:
		var pip := ColorRect.new()
		pip.custom_minimum_size = Vector2(24, 16)
		pip.color = UIKit.GOLD if i < wave else (UIKit.EMBER if i == wave else Color(0.2, 0.18, 0.22))
		pip.mouse_filter = Control.MOUSE_FILTER_IGNORE
		wave_pips.add_child(pip)


func set_loot(gold: int, drops: int) -> void:
	var old := gold_label.text
	gold_label.text = UIKit.format_number(gold)
	drops_label.text = str(drops)
	if old != gold_label.text and gold > 0:
		gold_label.pivot_offset = Vector2(0, 15)
		var tw := create_tween()
		tw.tween_property(gold_label, "scale", Vector2(1.3, 1.3), 0.06)
		tw.tween_property(gold_label, "scale", Vector2.ONE, 0.12)


func set_target_text(target: Combatant) -> void:
	_target = target
	for c in plates.keys():
		plates[c].set_targeted(c == target)


## Enables/disables the cards according to the battle state.
func refresh(can_input: bool, selected: Combatant) -> void:
	for c in cards.keys():
		cards[c].set_enabled(can_input)
		cards[c].set_selected(c == selected)
	btn_menu.disabled = not can_input


## Adds a line to the action log (older lines fade).
func add_log(text: String, color: Color = UIKit.TEXT) -> void:
	var l := UIKit.label(text, UIKit.T_SMALL, color, HORIZONTAL_ALIGNMENT_LEFT, 5)
	l.clip_text = true
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	log_box.add_child(l)
	while log_box.get_child_count() > LOG_LINES:
		var old := log_box.get_child(0)
		log_box.remove_child(old)
		old.queue_free()
	var n := log_box.get_child_count()
	for i in n:
		log_box.get_child(i).modulate.a = 0.5 + 0.5 * float(i + 1) / n


# ------------------------------------------------------------------ presentation
## Brief full-screen flash (impact frame). Respects the Battle Effects setting.
func flash_screen(color: Color, strength: float = 0.35, time: float = 0.12) -> void:
	if not bool(GameManager.settings.get("battle_effects", true)):
		strength *= 0.4
	flash_rect.color = Color(color.r, color.g, color.b, strength)
	var tw := create_tween()
	tw.tween_property(flash_rect, "color:a", 0.0, time)


## Centered banner that sweeps in, holds and sweeps out.
## style: "wave" (iron plank) or "boss" (crimson frame).
func show_banner(text: String, color: Color = UIKit.GOLD, hold: float = 0.7, style := "wave", sub := "") -> void:
	var vp := root.get_viewport_rect().size
	var p := PanelFrame.make("boss" if style == "boss" else "plank", 18)
	p.name = "Banner"
	p.custom_minimum_size = Vector2(vp.x + 40, 0)
	banner_layer.add_child(p)
	var v := UIKit.vbox(0)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	p.add_child(v)
	var big := UIKit.label(text, UIKit.T_TITLE if style != "victory" else 120, color, HORIZONTAL_ALIGNMENT_CENTER, 14)
	big.add_theme_color_override("font_outline_color", Color("#1a0806"))
	v.add_child(big)
	if not sub.is_empty():
		v.add_child(UIKit.label(sub, UIKit.T_BODY, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_CENTER, 6))
	await get_tree().process_frame
	var y := (field_top() + field_bottom()) * 0.5 - p.size.y * 0.5 - 80
	p.position = Vector2(-vp.x - 40, y)
	var sparks := UIKit.sparkle(banner_layer, Rect2(0, y, vp.x, p.size.y), color.lightened(0.3), 14)
	var tw := create_tween()
	tw.tween_property(p, "position:x", -20.0, 0.18).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_property(big, "scale", Vector2(1.06, 1.06), 0.08)
	tw.tween_property(big, "scale", Vector2.ONE, 0.08)
	tw.tween_interval(hold)
	tw.tween_property(p, "position:x", vp.x + 40, 0.18).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	big.pivot_offset = Vector2(vp.x / 2.0, 50)
	await tw.finished
	p.queue_free()
	sparks.emitting = false
	get_tree().create_timer(1.5).timeout.connect(sparks.queue_free)


## Burst cut-in: the field darkens, an element-themed band sweeps in with the
## hero portrait, the hero name and the Burst name, then fades (about 1 second).
func play_burst_cutin(c: Combatant, skill: Dictionary) -> void:
	for ch in cutin.get_children():
		ch.queue_free()
	cutin.visible = true
	cutin.modulate.a = 1.0
	var vp := root.get_viewport_rect().size
	var col := Database.element_color(c.element)
	var y0 := (field_top() + field_bottom()) * 0.5 - 220
	var band := Control.new()
	band.position = Vector2(0, y0)
	band.size = Vector2(vp.x, 360)
	band.clip_contents = true
	band.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cutin.add_child(band)
	var bg := ColorRect.new()
	bg.color = Color(0.03, 0.02, 0.05, 0.92)
	bg.size = band.size
	band.add_child(bg)
	var tint := ColorRect.new()
	tint.color = Color(col.r, col.g, col.b, 0.22)
	tint.size = band.size
	band.add_child(tint)
	CutinDecor.add(band, c.element)
	for yy in [0.0, 352.0]:
		var stripe := ColorRect.new()
		stripe.color = col.lightened(0.2)
		stripe.position = Vector2(0, yy)
		stripe.size = Vector2(vp.x, 8)
		band.add_child(stripe)
	var art := UIKit.portrait_art(c.def, Vector2(384, 344))
	art.position = Vector2(vp.x + 40, 8)
	art.size = Vector2(384, 344)
	band.add_child(art)
	var name_l := UIKit.label(c.display_name.to_upper(), UIKit.T_NAME, col.lightened(0.45), HORIZONTAL_ALIGNMENT_LEFT, 8)
	name_l.position = Vector2(-760, 70)
	name_l.size = Vector2(700, 50)
	band.add_child(name_l)
	var burst_l := UIKit.label(String(skill.get("name", "")).to_upper(), UIKit.T_TITLE, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 14)
	burst_l.add_theme_color_override("font_outline_color", Color("#2a0a04"))
	burst_l.position = Vector2(-900, 150)
	burst_l.size = Vector2(900, 100)
	band.add_child(burst_l)
	var tag := UIKit.label("BURST", UIKit.T_BODY, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_LEFT, 6)
	tag.position = Vector2(-300, 262)
	tag.size = Vector2(300, 40)
	band.add_child(tag)
	band.scale = Vector2(1, 0.1)
	band.pivot_offset = Vector2(vp.x / 2, 180)
	var tw := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_property(band, "scale", Vector2.ONE, 0.12)
	tw.tween_property(art, "position:x", vp.x - 420, 0.24).set_delay(0.05)
	tw.tween_property(name_l, "position:x", 40.0, 0.22).set_delay(0.08)
	tw.tween_property(burst_l, "position:x", 40.0, 0.26).set_delay(0.14)
	tw.tween_property(tag, "position:x", 44.0, 0.26).set_delay(0.2)
	tw.chain().tween_interval(0.5)
	tw.chain().tween_property(cutin, "modulate:a", 0.0, 0.16)
	await tw.finished
	cutin.visible = false
	for ch in cutin.get_children():
		ch.queue_free()


## Boss entrance title: darkened band, ANCIENT FOE and the boss name.
func play_boss_title(boss_name: String) -> void:
	await show_banner("ANCIENT FOE", Color("#ff6a4a"), 1.0, "boss", boss_name.to_upper())


## Tutorial popup. Resolves when the player presses GOT IT.
func show_hint(hint: Dictionary) -> void:
	var p := FantasyPopup.open(root, hint.get("title", "Tip"), 980)
	for line in hint.get("lines", []):
		var l := UIKit.wrap_label(line, UIKit.T_BODY)
		l.custom_minimum_size.x = 900
		p.content.add_child(l)
	var ok := FantasyButton.make("GOT IT", "ember", Vector2(340, 110))
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(ok)
	await ok.pressed
	p.close()


func show_menu(on_retreat: Callable) -> void:
	var p := FantasyPopup.open(root, "PAUSED", 820)
	var resume := FantasyButton.make("RESUME", "ember", Vector2(520, 116))
	var settings := FantasyButton.make("SETTINGS", "steel", Vector2(520, 110))
	var retreat := FantasyButton.make("RETREAT", "stone", Vector2(520, 110))
	for b in [resume, settings, retreat]:
		b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		p.content.add_child(b)
	p.content.add_child(UIKit.label("Retreating ends the battle without rewards (Energy is not refunded).", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
	resume.pressed.connect(p.close)
	settings.pressed.connect(func(): SettingsPanel.open(root))
	retreat.pressed.connect(func():
		p.close()
		on_retreat.call())
