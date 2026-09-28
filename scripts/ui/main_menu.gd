extends Control
## Title screen (portrait): key art of the three heroes, logo, and
## CONTINUE / NEW GAME / SETTINGS / EXIT.

var btn_continue: Button


func _ready() -> void:
	UIKit.screen_background(self, "bg_title", 0.0)
	_add_embers()
	_add_key_art()

	var top := UIKit.vbox(0)
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top.offset_top = 150
	add_child(top)
	var logo := UIKit.heading("CINDERBOUND", 130, Color("#ffb04a"))
	logo.add_theme_color_override("font_outline_color", Color("#3a0e08"))
	logo.add_theme_constant_override("outline_size", 22)
	top.add_child(logo)
	var sub := UIKit.title_plate("EMBERS OF THE ASHROOT WILDS", 30)
	sub.custom_minimum_size.x = 760
	top.add_child(sub)
	logo.pivot_offset = Vector2(540, 70)
	var tw := logo.create_tween().set_loops()
	tw.tween_property(logo, "modulate", Color(1.25, 1.1, 0.95), 1.2).set_trans(Tween.TRANS_SINE)
	tw.tween_property(logo, "modulate", Color.WHITE, 1.2).set_trans(Tween.TRANS_SINE)

	var buttons := UIKit.vbox(22)
	buttons.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	buttons.offset_left = -320
	buttons.offset_right = 320
	buttons.offset_top = -700
	buttons.offset_bottom = -140
	add_child(buttons)
	btn_continue = UIKit.button("CONTINUE", "", Vector2(640, 130), "ember")
	var btn_new := UIKit.button("NEW GAME", "", Vector2(640, 130), "gold")
	var btn_settings := UIKit.button("SETTINGS", "res://assets/icons/nav_settings.png", Vector2(640, 110))
	var btn_exit := UIKit.button("EXIT", "", Vector2(640, 110), "stone")
	for b in [btn_continue, btn_new, btn_settings, btn_exit]:
		b.add_theme_font_size_override("font_size", 50 if b.custom_minimum_size.y > 120 else 40)
		buttons.add_child(b)
	btn_continue.pressed.connect(_on_continue)
	(btn_continue as FantasyButton).add_shine()
	btn_new.pressed.connect(_on_new_game)
	btn_settings.pressed.connect(func(): SettingsPanel.open(self))
	btn_exit.pressed.connect(func(): GameManager.quit_game(0))
	btn_continue.disabled = not GameManager.can_continue()

	var ver := UIKit.label("Prototype v%s  -  original art & audio" % ProjectSettings.get_setting("application/config/version", "0.1"),
			20, Color(1, 1, 1, 0.6), HORIZONTAL_ALIGNMENT_CENTER)
	ver.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	ver.offset_top = -70
	ver.offset_bottom = -30
	add_child(ver)

	AudioManager.play_music("menu")
	if SaveManager.last_load_status == "corrupted":
		UIKit.message(self, "Save Problem", "Your save file could not be read and no backup was found. You can start a new game; settings are unaffected.")
	elif SaveManager.last_load_status == "recovered_backup":
		UIKit.toast(self, "Save restored from backup", UIKit.GOLD)


## The three starters posed together in front of the burning cliff.
func _add_key_art() -> void:
	var glow := ColorRect.new()
	glow.color = Color(1.0, 0.45, 0.15, 0.10)
	glow.set_anchors_preset(Control.PRESET_FULL_RECT)
	glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(glow)
	var poses := [["mira_tidesong", Vector2(-300, 1180), 10.0, "idle"],
				  ["thorne_mossguard", Vector2(300, 1190), 10.0, "idle"],
				  ["kael_emberclaw", Vector2(0, 1250), 12.0, "victory"]]
	for p in poses:
		var def := Database.get_character(p[0])
		var d := UnitSpriteDisplay.new()
		d.setup(def.get("sprite", {}), p[2], p[1].x > 0, p[3])
		d.position = Vector2(540 + p[1].x - d.custom_minimum_size.x / 2.0, p[1].y - d.custom_minimum_size.y)
		d.size = d.custom_minimum_size
		add_child(d)


func _add_embers() -> void:
	var p := CPUParticles2D.new()
	p.amount = 70
	p.lifetime = 7.0
	p.position = Vector2(540, 1980)
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(600, 10)
	p.direction = Vector2(0, -1)
	p.spread = 25
	p.gravity = Vector2(0, -8)
	p.initial_velocity_min = 80
	p.initial_velocity_max = 170
	p.scale_amount_min = 5
	p.scale_amount_max = 9
	var grad := Gradient.new()
	grad.set_color(0, Color("#ffd35a"))
	grad.set_color(1, Color(1, 0.3, 0.1, 0))
	p.color_ramp = grad
	add_child(p)


func _on_continue() -> void:
	if GameManager.continue_game():
		SceneRouter.go("home")
	else:
		btn_continue.disabled = true
		UIKit.message(self, "No Save Found", "There is no saved journey yet. Choose NEW GAME to begin.")


func _on_new_game() -> void:
	if GameManager.can_continue():
		UIKit.confirm(self, "Start a new journey? Your current progress will be erased.",
				func(): SceneRouter.go("starter_select"), "NEW GAME", "CANCEL")
	else:
		SceneRouter.go("starter_select")
