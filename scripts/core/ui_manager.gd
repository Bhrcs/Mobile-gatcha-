extends Node
## UIManager (autoload)
## One place for the interface services every screen shares:
##   * toasts          short, non-blocking feedback ("Squad saved", "Not enough Gold")
##   * tooltips        hover (PC) / press-and-hold (touch); always kept on screen
##   * dialogs         the universal confirmation dialog and message box
##   * popup stack     Esc closes the top popup, Enter confirms simple dialogs
##   * loading overlay shown only while a real load takes longer than a moment
##   * UI sounds       one sound per meaning (press, back, confirm, error, coin...)
##   * haptics         optional hooks for phones (no-op on desktop)
## Gameplay logic never lives here.

const SOUNDS := {"press": "click", "back": "ui_back", "cancel": "ui_back", "confirm": "ui_confirm", "error": "ui_error",
		"coin": "coin", "claim": "claim", "mission": "mission", "level_up": "level_up", "evolve": "evolve",
		"summon": "summon_reveal", "open": "menu_open", "close": "menu_close", "select": "unit_select",
		"stage": "stage_select", "toggle": "click", "reward": "reward"}
const HAPTIC_MS := {"light": 12, "confirm": 20, "burst": 30, "reveal": 45, "evolve": 60}
const TOAST_COLORS := {"info": Color("#f4ecdc"), "success": Color("#8ae05a"), "error": Color("#ff7a5a"),
		"warning": Color("#ffd35a"), "reward": Color("#ffd35a")}
const TOAST_ICONS := {"info": "res://assets/icons/info.png", "success": "res://assets/icons/check.png",
		"error": "res://assets/icons/warning.png", "warning": "res://assets/icons/warning.png",
		"reward": "res://assets/icons/chest_open.png"}

var popups: Array = []            # open FantasyPopups, oldest first
var _layer: CanvasLayer
var _toasts: VBoxContainer
var _tip: PanelContainer
var _tip_owner: Control
var _tip_timer: SceneTreeTimer
var _loading: Control
var _loading_label: Label


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_layer = CanvasLayer.new()
	_layer.layer = 90          # above screens and popups, below the scene fade (100)
	add_child(_layer)
	var root := Control.new()
	root.name = "UIRoot"
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UIKit.build_theme()
	_layer.add_child(root)
	_toasts = UIKit.vbox(UIKit.SP_S)
	_toasts.name = "Toasts"
	_toasts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_toasts.alignment = BoxContainer.ALIGNMENT_BEGIN
	_toasts.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	_toasts.offset_top = UIKit.TOP_BAR_H + 150
	_toasts.offset_left = 60
	_toasts.offset_right = -60
	root.add_child(_toasts)


func ui_root() -> Control:
	return _layer.get_node("UIRoot")


# ------------------------------------------------------------------ sounds & haptics
func sfx(kind: String, volume_db := -2.0) -> void:
	AudioManager.play_sfx(SOUNDS.get(kind, kind), 0.03, volume_db)


## Light vibration on phones for key moments. Off on desktop / when disabled.
func haptic(kind := "light") -> void:
	if not OS.has_feature("mobile") or not bool(GameManager.settings.get("haptics", true)):
		return
	Input.vibrate_handheld(int(HAPTIC_MS.get(kind, 15)))


# ------------------------------------------------------------------ toasts
## kind: info | success | error | warning | reward. Errors also play the error sound.
func toast(text: String, kind := "info") -> void:
	if _toasts == null:
		return
	# the same message twice in a row just refreshes
	for t in _toasts.get_children():
		if t.get_meta("text", "") == text and not t.is_queued_for_deletion():
			t.set_meta("ttl", 1.6)
			return
	while _toasts.get_child_count() >= 3:
		var old := _toasts.get_child(0)
		_toasts.remove_child(old)
		old.queue_free()
	var p := PanelFrame.make("inset", 14)
	p.name = "Toast"
	p.set_meta("text", text)
	p.set_meta("ttl", 1.6)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var h := UIKit.hbox(UIKit.SP_M)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(h)
	h.add_child(UIKit.icon(TOAST_ICONS.get(kind, TOAST_ICONS["info"]), 32))
	var l := UIKit.label(text, UIKit.T_BODY, TOAST_COLORS.get(kind, UIKit.TEXT), HORIZONTAL_ALIGNMENT_LEFT, 6)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = min(820.0, UIKit.font().get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, UIKit.T_BODY).x + 8)
	h.add_child(l)
	_toasts.add_child(p)
	if kind == "error":
		sfx("error", -4.0)
	p.modulate.a = 0.0
	var tw := p.create_tween()
	tw.tween_property(p, "modulate:a", 1.0, 0.12)
	_run_toast(p)


func _run_toast(p: Control) -> void:
	while is_instance_valid(p):
		await get_tree().process_frame
		if not is_instance_valid(p):
			return
		var ttl: float = p.get_meta("ttl") - get_process_delta_time()
		p.set_meta("ttl", ttl)
		if ttl <= 0.0:
			var tw := p.create_tween()
			tw.tween_property(p, "modulate:a", 0.0, 0.2)
			tw.tween_callback(p.queue_free)
			return


## "Not enough Gold. Need 1,200 - you have 840." (with the next useful action)
func not_enough(resource: String, need: int, have: int, hint := "") -> void:
	var msg := "Not enough %s. Need %s - you have %s." % [resource, UIKit.format_number(need), UIKit.format_number(have)]
	if not hint.is_empty():
		msg += " " + hint
	toast(msg, "error")


# ------------------------------------------------------------------ tooltips
## Adds a tooltip to any control. Hover on PC, press-and-hold (or tap, for
## non-button controls) on touch. `body` may contain line breaks.
func attach_tooltip(c: Control, title: String, body := "", icon_path := "") -> void:
	c.set_meta("tip", [title, body, icon_path])
	if c.has_meta("tip_hooked"):
		return
	c.set_meta("tip_hooked", true)
	if c.mouse_filter == Control.MOUSE_FILTER_IGNORE:
		c.mouse_filter = Control.MOUSE_FILTER_PASS
	c.mouse_entered.connect(func():
		if not DisplayServer.is_touchscreen_available():
			_tip_timer = get_tree().create_timer(0.35)
			var t := _tip_timer
			t.timeout.connect(func():
				if t == _tip_timer and is_instance_valid(c) and c.is_visible_in_tree():
					_show_tip_for(c)))
	c.mouse_exited.connect(func():
		_tip_timer = null
		if _tip_owner == c:
			hide_tooltip())
	c.gui_input.connect(func(e: InputEvent):
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
			if e.pressed:
				if c is BaseButton:
					_tip_timer = get_tree().create_timer(0.45)
					var t := _tip_timer
					t.timeout.connect(func():
						if t == _tip_timer and is_instance_valid(c):
							_show_tip_for(c))
				else:
					if _tip_owner == c:
						hide_tooltip()
					else:
						_show_tip_for(c)
			else:
				_tip_timer = null)
	c.tree_exiting.connect(func():
		if _tip_owner == c:
			hide_tooltip())


func _show_tip_for(c: Control) -> void:
	var d: Array = c.get_meta("tip", ["", "", ""])
	show_tooltip(c, d[0], d[1], d[2])


func show_tooltip(anchor: Control, title: String, body := "", icon_path := "") -> void:
	hide_tooltip()
	_tip_owner = anchor
	_tip = PanelContainer.new()
	_tip.name = "Tooltip"
	_tip.add_theme_stylebox_override("panel", UIKit.tex_style("p5_tip.png", 9, 16, false))
	_tip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tip.z_index = 20
	var v := UIKit.vbox(UIKit.SP_XS)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tip.add_child(v)
	var h := UIKit.hbox(UIKit.SP_S)
	if not icon_path.is_empty():
		h.add_child(UIKit.icon(icon_path, 32))
	h.add_child(UIKit.label(title, UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	v.add_child(h)
	if not body.is_empty():
		var b := UIKit.label(body, UIKit.T_SMALL, UIKit.TEXT)
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		b.custom_minimum_size.x = min(640.0, max(300.0, UIKit.font().get_string_size(body, HORIZONTAL_ALIGNMENT_LEFT, -1, UIKit.T_SMALL).x + 8))
		v.add_child(b)
	ui_root().add_child(_tip)
	_tip.modulate.a = 0.0
	await get_tree().process_frame
	if not is_instance_valid(_tip) or not is_instance_valid(anchor):
		return
	_tip.size = _tip.get_combined_minimum_size()
	var vp := ui_root().get_viewport_rect().size
	var r := anchor.get_global_rect()
	# prefer above the control, else below; always inside the screen margins
	var pos := Vector2(r.get_center().x - _tip.size.x / 2.0, r.position.y - _tip.size.y - UIKit.SP_S)
	if pos.y < UIKit.safe_top() + UIKit.SP_L:
		pos.y = r.end.y + UIKit.SP_S
	pos.x = clampf(pos.x, UIKit.MARGIN, vp.x - _tip.size.x - UIKit.MARGIN)
	pos.y = clampf(pos.y, UIKit.MARGIN + UIKit.safe_top(), vp.y - _tip.size.y - UIKit.MARGIN - UIKit.safe_bottom())
	_tip.position = pos
	_tip.create_tween().tween_property(_tip, "modulate:a", 1.0, 0.1)


func hide_tooltip() -> void:
	if is_instance_valid(_tip):
		_tip.queue_free()
	_tip = null
	_tip_owner = null


func tooltip_visible() -> bool:
	return is_instance_valid(_tip)


# ------------------------------------------------------------------ popups & dialogs
func register_popup(p: Control) -> void:
	popups.append(p)
	p.tree_exiting.connect(func(): popups.erase(p))
	hide_tooltip()


func top_popup() -> Control:
	for i in range(popups.size() - 1, -1, -1):
		var p = popups[i]
		if is_instance_valid(p) and p.is_inside_tree() and not p.get("_closing"):
			return p
	return null


func has_popup(popup_name: String) -> bool:
	for p in popups:
		if is_instance_valid(p) and p.name == popup_name and not p.get("_closing"):
			return true
	return false


## The universal confirmation dialog. Only one can be open at a time, so
## repeated taps never stack it.
## opts: danger (bool), cancel_text, on_cancel (Callable), lines ([[icon, text, color], ...]),
##       name (node name), parent (Control)
func confirm(title: String, body: String, confirm_text: String, on_confirm: Callable, opts := {}) -> FantasyPopup:
	if has_popup("ConfirmDialog"):
		return null
	var parent: Node = opts.get("parent", get_tree().current_scene)
	if parent == null:
		parent = ui_root()
	var p := FantasyPopup.open(parent, title, 900)
	p.name = opts.get("name", "ConfirmDialog")
	if not body.is_empty():
		# an untitled dialog shows its question a size larger
		var msg := UIKit.wrap_label(body, UIKit.T_NAME if title.is_empty() else UIKit.T_BODY)
		msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		msg.custom_minimum_size.x = 820
		p.content.add_child(msg)
	for line in opts.get("lines", []):
		var h := UIKit.hbox(UIKit.SP_M)
		h.alignment = BoxContainer.ALIGNMENT_CENTER
		if not String(line[0]).is_empty():
			h.add_child(UIKit.icon(line[0], 48))
		h.add_child(UIKit.label(line[1], UIKit.T_BODY, line[2] if line.size() > 2 else UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 6))
		p.content.add_child(h)
	var row := UIKit.hbox(UIKit.SP_XL)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var no := UIKit.btn(opts.get("cancel_text", "CANCEL"), "quiet", Vector2(340, 116))
	no.name = "DialogCancel"
	var yes := UIKit.btn(confirm_text, "danger" if opts.get("danger", false) else "primary", Vector2(380, 116))
	yes.name = "DialogConfirm"
	row.add_child(no)
	row.add_child(yes)
	p.content.add_child(row)
	var on_cancel: Callable = opts.get("on_cancel", Callable())
	yes.pressed.connect(func():
		if p._closing:
			return
		sfx("confirm")
		haptic("confirm")
		p.close()
		on_confirm.call())
	no.pressed.connect(func():
		p.close()
		if on_cancel.is_valid():
			on_cancel.call())
	p.cancel_action = func():
		p.close()
		if on_cancel.is_valid():
			on_cancel.call()
	p.default_action = func(): yes.pressed.emit()
	return p


## Simple message box with one button (Enter / Esc close it).
func message(title: String, body: String, ok_text := "OK", parent: Node = null) -> FantasyPopup:
	if parent == null:
		parent = get_tree().current_scene if get_tree().current_scene else ui_root()
	var p := FantasyPopup.open(parent, title, 900)
	p.name = "MessageDialog"
	var msg := UIKit.wrap_label(body, UIKit.T_BODY)
	msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	msg.custom_minimum_size.x = 820
	p.content.add_child(msg)
	var ok := UIKit.btn(ok_text, "primary", Vector2(320, 110))
	ok.name = "DialogOK"
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(ok)
	ok.pressed.connect(p.close)
	p.default_action = p.close
	return p


# ------------------------------------------------------------------ guided tutorial
## Reusable first-time guide for menus ("Tap QUEST", "Select Stage 1-1"): a
## non-blocking coach mark on `target` that is shown until the player presses it
## once. Each step is remembered in the save (Settings can reset them).
## Returns the CoachMark (or null when the step is already done / not possible).
func guide(step: String, target: Control, text: String, gesture := "tap") -> CoachMark:
	if target == null or not GameManager.has_profile() or GameManager.coach_done(step):
		return null
	var scene := get_tree().current_scene
	if scene == null or not (scene is Control):
		return null
	var c := CoachMark.show_on(scene, target, text, gesture, false)
	c.name = "Guide_" + step
	var done := func():
		GameManager.mark_coach_done(step)
		if is_instance_valid(c):
			c.finish()
	if target is BaseButton:
		(target as BaseButton).pressed.connect(done, CONNECT_ONE_SHOT)
	else:
		target.gui_input.connect(func(e: InputEvent):
			if e is InputEventMouseButton and not e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
				done.call())
	return c


# ------------------------------------------------------------------ loading
func show_loading(text := "") -> void:
	if is_instance_valid(_loading):
		return
	_loading = LoadingOverlay.create(text)
	ui_root().add_child(_loading)


func hide_loading() -> void:
	if is_instance_valid(_loading):
		_loading.queue_free()
	_loading = null


# ------------------------------------------------------------------ keyboard (PC)
## Esc: hide tooltip > close the top popup > go Back. Enter confirms simple dialogs.
## Battles handle their own Esc (pause menu) before this runs.
func _unhandled_key_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	if event.keycode == KEY_ESCAPE:
		get_viewport().set_input_as_handled()
		if tooltip_visible():
			hide_tooltip()
			return
		var p := top_popup()
		if p:
			if p.has_method("cancel"):
				p.cancel()
			return
		if SceneRouter.transitioning:
			return
		var cs := get_tree().current_scene
		if cs and cs.has_method("on_back"):
			cs.on_back()
	elif event.keycode == KEY_ENTER or event.keycode == KEY_KP_ENTER:
		var p := top_popup()
		if p and p.has_method("confirm_default"):
			get_viewport().set_input_as_handled()
			p.confirm_default()
