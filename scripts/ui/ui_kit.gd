class_name UIKit
extends RefCounted
## Cinderbound UI facade (theme v2: worn iron, dark stone, ember edges).
## Thin helpers that build the reusable components in scripts/ui/components.
##
## Pixel rules enforced here:
##  * text sizes snap to multiples of 10 so every font pixel is a whole
##    number of screen pixels (Cinder Pixel is a 10-unit grid font)
##  * icons (16x16 art) snap to multiples of 16 -> integer scaling only

# ------------------------------------------------------------------ palette & type scale
const TEXT := Color("#f4ecdc")
const MUTED := Color("#a8a0b0")
const GOLD := Color("#ffd35a")
const EMBER := Color("#ff9a4a")
const DANGER := Color("#ff5a4a")
const GOOD := Color("#8ae05a")
const SKY := Color("#8ad8ff")
const SHADOW := Color(0.04, 0.02, 0.05, 0.95)

# Typography roles (Cinder Pixel is a 10-unit grid font: sizes are multiples of 10).
const T_DISPLAY := 120  # VICTORY, RANK UP, EVOLVED
const T_TITLE := 80     # banners, big stage titles
const T_HEAD := 50      # screen titles (header), popup titles
const T_NAME := 40      # unit names, big values, primary button labels
const T_BODY := 30      # body text, secondary button labels, currency values
const T_SMALL := 20     # secondary text, metadata, tags
const T_SCREEN := T_HEAD
const T_PANEL := T_BODY
const T_UNIT := T_NAME
const T_BUTTON := T_NAME
const T_BUTTON_S := T_BODY
const T_CURRENCY := T_BODY
const T_META := T_SMALL

# Spacing scale (design pixels at 1080x1920 = 1.5x of a 720x1280 phone).
const SP_XS := 4
const SP_S := 8
const SP_M := 12
const SP_L := 16
const SP_XL := 24
const SP_XXL := 32
const MARGIN := 16        # standard horizontal screen margin
const TOUCH_MIN := 88     # minimum touch target (about 7 mm on a phone)

# Semantic button kinds -> art styles. Colour always means the same thing:
#   primary  (ember)   main action / confirm       secondary (steel) alternative action
#   quiet    (stone)   cancel / back / low weight  reward    (gold)  claim, summon, collect
#   danger   (crimson) destructive or risky        disabled  greyed metal (automatic)
const BUTTON_KINDS := {"primary": "ember", "confirm": "ember", "secondary": "steel", "quiet": "stone",
		"reward": "gold", "danger": "crimson"}

const FONT_PATH := "res://assets/fonts/cinder_pixel.ttf"
const UI_DIR := "res://assets/ui/"
const TOP_BAR_H := 150
const NAV_H := 200

static var _font: FontFile
static var _theme: Theme


# ------------------------------------------------------------------ theme
static func font() -> FontFile:
	if _font == null:
		_font = load(FONT_PATH) as FontFile
		if _font:
			_font.antialiasing = TextServer.FONT_ANTIALIASING_NONE
			_font.hinting = TextServer.HINTING_NONE
			_font.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
			_font.generate_mipmaps = false
	return _font


static func build_theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	t.default_font = font()
	t.default_font_size = T_BODY
	var fb := FantasyButton.new()
	fb.apply_style("steel")
	for st in ["normal", "hover", "pressed", "hover_pressed", "disabled", "focus"]:
		t.set_stylebox(st, "Button", fb.get_theme_stylebox(st))
	fb.free()
	t.set_color("font_color", "Button", Color.WHITE)
	t.set_color("font_hover_color", "Button", Color("#fff6d0"))
	t.set_color("font_pressed_color", "Button", Color("#e0d8c8"))
	t.set_color("font_hover_pressed_color", "Button", Color("#e0d8c8"))
	t.set_color("font_disabled_color", "Button", Color("#8a8690"))
	t.set_color("font_outline_color", "Button", Color("#120a0c"))
	t.set_constant("outline_size", "Button", 10)
	t.set_constant("h_separation", "Button", 12)
	t.set_font_size("font_size", "Button", T_NAME)

	var panel := PanelFrame.make("panel")
	t.set_stylebox("panel", "PanelContainer", panel.get_theme_stylebox("panel"))
	t.set_stylebox("panel", "Panel", panel.get_theme_stylebox("panel"))
	panel.free()

	t.set_color("font_color", "Label", TEXT)
	t.set_color("font_shadow_color", "Label", SHADOW)
	t.set_constant("shadow_offset_x", "Label", 3)
	t.set_constant("shadow_offset_y", "Label", 3)
	t.set_constant("line_spacing", "Label", 6)

	t.set_stylebox("background", "ProgressBar", flat(Color("#0a080c"), Color("#5a5660"), 3))
	t.set_stylebox("fill", "ProgressBar", flat(GOOD))

	# scrollbars: slim iron track, iron grabber that lights ember when used
	var track := tex_style("p5_scroll.png", 6, 4, false)
	var grab := tex_style("p5_scroll_grab.png", 6, 4, false)
	var grab_hot := tex_style("p5_scroll_grab_hot.png", 6, 4, false)
	for cls in ["VScrollBar", "HScrollBar"]:
		t.set_stylebox("scroll", cls, track)
		t.set_stylebox("scroll_focus", cls, track)
		t.set_stylebox("grabber", cls, grab)
		t.set_stylebox("grabber_highlight", cls, grab_hot)
		t.set_stylebox("grabber_pressed", cls, grab_hot)
	t.set_constant("scrollbar_margin_right", "ScrollContainer", 0)

	# sliders: bar frame track, ember fill, big gold knob (easy to drag on touch)
	var slider := tex_style("v2_bar.png", 18, 10, false)
	slider.content_margin_top = 12
	slider.content_margin_bottom = 12
	t.set_stylebox("slider", "HSlider", slider)
	var fill_sb := tex_style("v2_fill_stat.png", 0, 0, false)
	fill_sb.content_margin_top = 12
	fill_sb.content_margin_bottom = 12
	t.set_stylebox("grabber_area", "HSlider", fill_sb)
	t.set_stylebox("grabber_area_highlight", "HSlider", fill_sb)
	var knob: Texture2D = load(UI_DIR + "p5_knob.png")
	t.set_icon("grabber", "HSlider", knob)
	t.set_icon("grabber_highlight", "HSlider", knob)
	t.set_constant("center_grabber", "HSlider", 1)

	# switches (CheckButton) use the pixel ON / OFF switch art
	var sw_on: Texture2D = load(UI_DIR + "p5_switch_on.png")
	var sw_off: Texture2D = load(UI_DIR + "p5_switch_off.png")
	for cls in ["CheckBox", "CheckButton"]:
		t.set_icon("checked", cls, sw_on)
		t.set_icon("unchecked", cls, sw_off)
		for st in ["normal", "hover", "pressed", "focus", "hover_pressed"]:
			t.set_stylebox(st, cls, StyleBoxEmpty.new())
		t.set_color("font_color", cls, TEXT)
		t.set_color("font_hover_color", cls, Color("#ffe2b0"))
		t.set_color("font_pressed_color", cls, TEXT)

	# tooltips (desktop hover) share the Cinder tooltip plate
	var tip := tex_style("p5_tip.png", 9, 14, false)
	t.set_stylebox("panel", "TooltipPanel", tip)
	t.set_color("font_color", "TooltipLabel", TEXT)
	t.set_font_size("font_size", "TooltipLabel", T_SMALL)

	# text entry
	var le := tex_style("v2_inset.png", 15, 18)
	t.set_stylebox("normal", "LineEdit", le)
	t.set_stylebox("focus", "LineEdit", tex_style("v2_inset.png", 15, 18))
	t.set_color("font_color", "LineEdit", TEXT)
	t.set_color("caret_color", "LineEdit", GOLD)
	t.set_color("selection_color", "LineEdit", Color(0.9, 0.45, 0.15, 0.5))

	# type variations used by labels/buttons created in the editor or by code
	for v in [["DisplayLabel", T_DISPLAY, GOLD], ["TitleLabel", T_HEAD, Color("#fff0c0")], ["PanelTitle", T_PANEL, GOLD],
			["UnitName", T_UNIT, Color("#fff0c0")], ["BodyLabel", T_BODY, TEXT], ["MetaLabel", T_META, MUTED]]:
		t.set_type_variation(v[0], "Label")
		t.set_font_size("font_size", v[0], v[1])
		t.set_color("font_color", v[0], v[2])
	_theme = t
	return t


static func _box_icon(color: Color, w: int, h: int) -> ImageTexture:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(color)
	for x in w:
		for y in [0, 1, 2, h - 3, h - 2, h - 1]:
			img.set_pixel(x, y, Color("#16121a"))
	for y in h:
		for x in [0, 1, 2, w - 3, w - 2, w - 1]:
			img.set_pixel(x, y, Color("#16121a"))
	return ImageTexture.create_from_image(img)


static func tex_style(file: String, margin: int, content: int, tile := true) -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = load(UI_DIR + file)
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		sb.set_texture_margin(side, margin)
		sb.set_content_margin(side, content)
	if tile:
		sb.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE_FIT
		sb.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_TILE_FIT
	return sb


static func flat(color: Color, border: Color = Color(0, 0, 0, 0), border_w: int = 0) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.border_color = border
	sb.set_border_width_all(border_w)
	sb.anti_aliasing = false
	return sb


# ------------------------------------------------------------------ safe areas
## Top / bottom insets (notches, gesture bars) in viewport units. 0 on desktop.
static func safe_top() -> float:
	return _safe_insets().x


static func safe_bottom() -> float:
	return _safe_insets().y


## Extra margin chosen in Settings > Graphics > Screen Margins (for phones whose
## notch / rounded corners are not reported), 0 / 30 / 60 / 90 px.
static func _extra_margin() -> float:
	return float(int(GameManager.settings.get("safe_area", 0)) * 30)


static func _safe_insets() -> Vector2:
	var extra := _extra_margin()
	if not OS.has_feature("mobile"):
		return Vector2(extra, extra)
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null:
		return Vector2.ZERO
	var win_size := Vector2(DisplayServer.window_get_size())
	var safe := DisplayServer.get_display_safe_area()
	var vp := tree.root.get_visible_rect().size
	if win_size.y <= 0:
		return Vector2.ZERO
	var k := vp.y / win_size.y
	return Vector2(safe.position.y * k + extra, (win_size.y - safe.end.y) * k + extra)


# ------------------------------------------------------------------ text
static func snap_text(size: int) -> int:
	return max(20, int(round(size / 10.0)) * 10)


static func label(text: String, size: int = T_BODY, color: Color = TEXT, align := HORIZONTAL_ALIGNMENT_LEFT,
		outline := 0) -> Label:
	var l := Label.new()
	l.text = text
	size = snap_text(size)
	l.add_theme_font_override("font", font())
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", SHADOW)
	var sh := int(size / 10)
	l.add_theme_constant_override("shadow_offset_x", sh)
	l.add_theme_constant_override("shadow_offset_y", sh)
	if outline > 0:
		l.add_theme_constant_override("outline_size", outline)
		l.add_theme_color_override("font_outline_color", Color("#140806"))
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


static func heading(text: String, size: int = T_HEAD, color: Color = GOLD) -> Label:
	return label(text, size, color, HORIZONTAL_ALIGNMENT_CENTER, max(8, snap_text(size) / 6))


static func wrap_label(text: String, size: int = T_BODY, color: Color = TEXT) -> Label:
	var l := label(text, size, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = 100
	return l


## Carved title plate used at the top of popups.
static func title_plate(text: String, size: int = T_HEAD) -> Control:
	var p := PanelFrame.make("plank", 10)
	p.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.custom_minimum_size.x = 520
	p.add_child(label(text, size, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_CENTER, 10))
	return p


static func separator() -> TextureRect:
	var r := TextureRect.new()
	r.texture = load(UI_DIR + "v2_separator.png")
	r.stretch_mode = TextureRect.STRETCH_SCALE
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.custom_minimum_size = Vector2(0, 15)
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


static func tag(text: String, color: Color) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := flat(color, Color("#ffd35a"), 3)
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 2
	sb.content_margin_bottom = 2
	p.add_theme_stylebox_override("panel", sb)
	p.add_child(label(text, T_SMALL, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 6))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return p


# ------------------------------------------------------------------ buttons & panels
## Semantic button: kind = primary | secondary | quiet | reward | danger (see BUTTON_KINDS).
static func btn(text: String, kind := "primary", min_size := Vector2(320, 110), icon_path := "") -> FantasyButton:
	var b := FantasyButton.make(text, BUTTON_KINDS.get(kind, kind), min_size, icon_path)
	b.set_meta("kind", kind)
	if min_size.y < 100:
		b.add_theme_font_size_override("font_size", T_BUTTON_S)
	return b


## style: steel (default) | ember (primary) | gold | stone. Legacy "blue"/"red" map to steel/ember.
static func button(text: String, icon_path: String = "", min_size := Vector2(320, 110), style := "steel") -> Button:
	style = {"blue": "steel", "red": "ember"}.get(style, style)
	return FantasyButton.make(text, style, min_size, icon_path)


static func hook_sounds(b: BaseButton) -> void:
	b.mouse_entered.connect(func():
		if not b.disabled:
			AudioManager.play_sfx("hover", 0.02, -12.0))
	b.pressed.connect(func(): AudioManager.play_sfx("click", 0.03))


## Legacy style names map onto PanelFrame variants.
static func panel(style: String = "panel") -> PanelContainer:
	var v: String = {"frame": "panel", "dark": "panel", "red": "boss", "ember": "boss", "tile": "inset",
			  "card": "card_neutral", "plate": "plank"}.get(style, style)
	return PanelFrame.make(v)


# ------------------------------------------------------------------ images
static func snap_icon(size: int) -> int:
	return max(16, int(round(size / 16.0)) * 16)


static func icon(path: String, size: int = 48) -> TextureRect:
	var r := TextureRect.new()
	r.texture = load(path) if ResourceLoader.exists(path) else null
	size = snap_icon(size)
	r.custom_minimum_size = Vector2(size, size)
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


static func tex_rect(tex: Texture2D, size: Vector2) -> TextureRect:
	var r := TextureRect.new()
	r.texture = tex
	r.custom_minimum_size = size
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


static func orb(element: String, size: int = 48) -> TextureRect:
	return icon("res://assets/icons/orb_%s.png" % element, size)


static func stars(count: int, size: int = 32) -> HBoxContainer:
	var h := hbox(0)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for i in count:
		h.add_child(icon("res://assets/icons/star.png", size))
	return h


static func element_badge(element: String, size: int = T_BODY) -> HBoxContainer:
	var h := hbox(8)
	h.add_child(orb(element, 48))
	h.add_child(label(Database.element_name(element), size, Database.element_color(element).lightened(0.25), HORIZONTAL_ALIGNMENT_LEFT, 6))
	return h


## Portrait on an element-lit backdrop (no frame). Portraits are drawn at 96px,
## so the art is shown at the largest whole multiple that fits `box`.
static func portrait_art(char_def: Dictionary, box: Vector2) -> Control:
	var holder := Control.new()
	holder.custom_minimum_size = box
	holder.clip_contents = true
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var col := Database.element_color(char_def.get("element", ""))
	var grad := Gradient.new()
	grad.set_color(0, col.darkened(0.15))
	grad.set_color(1, col.darkened(0.82))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill_from = Vector2(0.5, 0.0)
	gt.fill_to = Vector2(0.5, 1.0)
	var bg := TextureRect.new()
	bg.texture = gt
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(bg)
	var tex := Database.load_texture(char_def.get("portrait", ""))
	if tex:
		var ts := tex.get_size()
		# largest whole scale that fills the box; up to ~25% may be cropped
		var k: float = max(1.0, round(max(box.x / ts.x, box.y / ts.y) - 0.1))
		var r := tex_rect(tex, ts * k)
		r.size = ts * k
		r.position = Vector2((box.x - ts.x * k) / 2.0, box.y - ts.y * k)
		holder.add_child(r)
	return holder


## Framed portrait (element card frame) with element orb.
static func portrait_frame(char_def: Dictionary, size: int = 192, show_orb := true) -> Control:
	var el: String = char_def.get("element", "neutral")
	var frame := PanelFrame.make("card_" + el, 9)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var stack := Control.new()
	stack.custom_minimum_size = Vector2(size, size)
	stack.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(stack)
	var art := portrait_art(char_def, Vector2(size, size))
	stack.add_child(art)
	if show_orb:
		var o := orb(el, 32 if size < 160 else 48)
		o.position = Vector2(-4, size - o.custom_minimum_size.y + 4)
		o.size = o.custom_minimum_size
		stack.add_child(o)
	return frame


## Small ambient twinkles over a control (used for high rarity & ready states).
static func sparkle(parent: Control, area: Rect2, color := Color("#fff0b0"), amount := 6) -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.amount = amount
	p.lifetime = 1.4
	p.position = area.get_center()
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = area.size / 2.0
	p.gravity = Vector2(0, -20)
	p.initial_velocity_min = 0
	p.initial_velocity_max = 10
	p.scale_amount_min = 3
	p.scale_amount_max = 6
	var grad := Gradient.new()
	grad.set_color(0, color)
	grad.set_color(1, Color(color.r, color.g, color.b, 0))
	p.color_ramp = grad
	parent.add_child(p)
	return p


# ------------------------------------------------------------------ layout helpers
static func hbox(sep: int = 12) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	return h


static func vbox(sep: int = 12) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", sep)
	return v


static func spacer(h_expand := true, v_expand := false) -> Control:
	var c := Control.new()
	if h_expand:
		c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if v_expand:
		c.size_flags_vertical = Control.SIZE_EXPAND_FILL
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


static func stat_row(stat_name: String, value: String, size: int = T_BODY, value_color: Color = TEXT) -> HBoxContainer:
	var h := hbox(8)
	var n := label(stat_name, size, SKY)
	n.custom_minimum_size.x = size * 4
	h.add_child(n)
	h.add_child(label(value, size, value_color))
	return h


## Coloured header strip ("BURST  Inferno Break").
static func strip(title: String, value: String, color: Color) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := flat(color.darkened(0.35), color.lightened(0.2), 3)
	sb.content_margin_left = 18
	sb.content_margin_right = 18
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	p.add_theme_stylebox_override("panel", sb)
	var h := hbox(20)
	h.add_child(label(title, T_BODY, Color.WHITE, HORIZONTAL_ALIGNMENT_LEFT, 6))
	var v := label(value, T_BODY, GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(v)
	p.add_child(h)
	return p


# ------------------------------------------------------------------ screen furniture
static func screen_background(parent: Control, bg_name: String, dim: float = 0.35) -> TextureRect:
	var stone := TextureRect.new()
	stone.texture = load(UI_DIR + "m_stone.png")
	stone.stretch_mode = TextureRect.STRETCH_TILE
	stone.set_anchors_preset(Control.PRESET_FULL_RECT)
	stone.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	stone.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	stone.modulate = Color(0.55, 0.5, 0.6)
	stone.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(stone)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/environments/%s.png" % bg_name)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	bg.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(bg)
	if dim > 0:
		var d := ColorRect.new()
		d.color = Color(0.05, 0.03, 0.07, dim)
		d.set_anchors_preset(Control.PRESET_FULL_RECT)
		d.mouse_filter = Control.MOUSE_FILTER_IGNORE
		parent.add_child(d)
	return bg


static func stone_rect() -> TextureRect:
	var stone := TextureRect.new()
	stone.texture = load(UI_DIR + "m_stone.png")
	stone.stretch_mode = TextureRect.STRETCH_TILE
	stone.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	stone.modulate = Color(0.5, 0.46, 0.56)
	stone.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return stone


## Compact top bar: rank badge + EXP bar (left), gold (right).
static func status_bar(parent: Control) -> Control:
	var bar := StatusBar.create()
	bar.set_anchors_preset(Control.PRESET_TOP_WIDE)
	bar.offset_left = 8
	bar.offset_right = -8
	bar.offset_top = 6 + safe_top()
	bar.offset_bottom = TOP_BAR_H - 4 + safe_top()
	parent.add_child(bar)
	return bar


## Small red notification marker (optionally with a number) for a corner of `c`.
static func badge(c: Control, text := "!") -> Control:
	var old := c.get_node_or_null("Badge")
	if old:
		old.queue_free()
	var p := PanelContainer.new()
	p.name = "Badge"
	var sb := flat(Color("#d8281e"), Color("#ffe08a"), 3)
	sb.set_corner_radius_all(22)
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 2
	sb.content_margin_bottom = 2
	p.add_theme_stylebox_override("panel", sb)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.custom_minimum_size = Vector2(46, 46)
	var l := label(text, 28, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 6)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	p.add_child(l)
	p.z_index = 5
	p.top_level = false
	c.add_child(p)
	var place := func():
		if is_instance_valid(p) and is_instance_valid(c):
			p.size = p.get_combined_minimum_size()
			p.position = Vector2(c.size.x - p.size.x + 6, -12)
	place.call()
	c.resized.connect(place)
	var tw := p.create_tween().set_loops()
	tw.tween_property(p, "modulate", Color(1.3, 1.3, 1.3), 0.5)
	tw.tween_property(p, "modulate", Color.WHITE, 0.5)
	return p


static func nav_bar(parent: Control, current: String) -> Control:
	return NavBar.attach(parent, current)


# ------------------------------------------------------------------ popups (legacy API)
static func modal(parent: Node, title_text: String, min_width: int = 940) -> Dictionary:
	var p := FantasyPopup.open(parent, title_text, min_width)
	return {"root": p, "content": p.content, "panel": p.panel}


static func confirm(parent: Node, text: String, on_yes: Callable, yes_text := "CONFIRM", no_text := "CANCEL",
		on_no: Callable = Callable(), danger := false) -> Control:
	return UIManager.confirm("", text, yes_text, on_yes,
			{"cancel_text": no_text, "on_cancel": on_no, "parent": parent, "danger": danger})


static func message(parent: Node, title_text: String, text: String, ok_text := "OK") -> Control:
	return UIManager.message(title_text, text, ok_text, parent)


## Legacy colour-based toast -> semantic UIManager toast.
static func toast(_parent: Node, text: String, color: Color = TEXT) -> void:
	var kind := "info"
	if color == DANGER:
		kind = "error"
	elif color == GOOD or color == GOLD:
		kind = "success"
	UIManager.toast(text, kind)


# ------------------------------------------------------------------ input
## Tap handler for non-button controls: fires on release if the pointer barely moved.
static func on_tap(c: Control, cb: Callable) -> void:
	c.mouse_filter = Control.MOUSE_FILTER_STOP
	c.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	c.gui_input.connect(func(e):
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
			if e.pressed:
				c.set_meta("tap_start", e.position)
				c.pivot_offset = c.size / 2.0
				c.scale = Vector2(0.97, 0.97)
			elif c.has_meta("tap_start"):
				var start: Vector2 = c.get_meta("tap_start")
				c.remove_meta("tap_start")
				c.scale = Vector2.ONE
				if e.position.distance_to(start) < 30.0:
					AudioManager.play_sfx("click")
					cb.call())


## Compact numbers for small widgets: 999 / 9,999 / 12.4K / 1.3M / 2.1B.
## Full values belong in tooltips and detail screens (format_number).
static func format_compact(n: int) -> String:
	var a: int = abs(n)
	var sign := "-" if n < 0 else ""
	if a < 10000:
		return sign + format_number(a)
	if a < 1000000:
		return sign + _trim_dec(a / 1000.0) + "K"
	if a < 1000000000:
		return sign + _trim_dec(a / 1000000.0) + "M"
	return sign + _trim_dec(a / 1000000000.0) + "B"


static func _trim_dec(v: float) -> String:
	if v >= 100.0:
		return str(int(floor(v)))
	var t: float = floor(v * 10.0) / 10.0
	return str(int(t)) if is_equal_approx(t, floor(t)) else "%.1f" % t


## Shrinks a label's font (in 10 px steps, down to `min_size`) until its text fits
## `max_width`; if it still does not fit, it is clipped with an ellipsis and the
## full text is available as a tooltip.
static func fit_label(l: Label, max_width: float, min_size := T_SMALL) -> Label:
	if not l.has_meta("fit_base"):
		l.set_meta("fit_base", int(l.get_theme_font_size("font_size")))
	var size: int = l.get_meta("fit_base")
	var f := font()
	l.text_overrun_behavior = TextServer.OVERRUN_NO_TRIMMING
	l.tooltip_text = ""
	while size > min_size and f.get_string_size(l.text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > max_width:
		size -= 10
	l.add_theme_font_size_override("font_size", size)
	if f.get_string_size(l.text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > max_width:
		l.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		l.clip_text = true
		l.tooltip_text = l.text
		l.mouse_filter = Control.MOUSE_FILTER_PASS
	l.custom_minimum_size.x = min(max_width, l.custom_minimum_size.x) if l.custom_minimum_size.x > 0 else 0
	return l


static func format_number(n: int) -> String:
	var s := str(abs(n))
	var out := ""
	while s.length() > 3:
		out = "," + s.substr(s.length() - 3) + out
		s = s.substr(0, s.length() - 3)
	return ("-" if n < 0 else "") + s + out


## 125 -> "2:05", 4000 -> "1:06:40"
static func format_time(seconds: int) -> String:
	seconds = maxi(seconds, 0)
	var h := seconds / 3600
	var m := (seconds % 3600) / 60
	var sec := seconds % 60
	if h > 0:
		return "%d:%02d:%02d" % [h, m, sec]
	return "%d:%02d" % [m, sec]
