# Porting the Godot UI to C++ / Axmol

The game logic already lives in `Source/logic/` (Database `DB`, GameManager `GM`,
Progression, SummonSystem, SaveManager, Battle model + AI). The presentation layer
is ported file by file from `scripts/**.gd` onto a small Godot-style toolkit, so the
C++ reads like the GDScript it came from. Keep ports faithful and plain: same
layout, same numbers, same names — no redesigns, no extra features.

## Where things are
| Godot | C++ |
|---|---|
| Control / containers / Label / TextureRect / ColorRect / Button / ScrollContainer / HSlider / LineEdit / Tween / CPUParticles2D / AnimatedSprite2D | `Source/ui/Gui.h` (namespace `gd`) |
| `UIKit`, PanelFrame, FantasyButton, FantasyPopup, ScreenBase, ScreenHeader, NavBar, StatusBar, ResourceBar, CoachMark | `Source/ui/UIKit.h` |
| SpriteFactory, UnitSpriteDisplay | `Source/ui/Sprites.h` |
| AudioManager, SceneRouter, UIManager, quit/apply settings | `Source/app/App.h` |
| shared components used by several screens | declared in `Source/screens/Screens.h`, implemented in `Source/screens/components/*.cpp` |
| Database / GameManager / Progression | `Source/logic/*.h` (`DB.character(id)`, `GM.unit(uid)`, ...) |

Each screen is one `.cpp` in `Source/screens/` with a class deriving `ScreenBase`,
building itself in `ready()` and registering with `REGISTER_SCREEN("key", Class)`.
Screen keys: main_menu, starter_select, intro, home, world_select, stage_select,
battle, units, unit_detail, train, inventory, squad, tower, summon, codex, missions,
profile, evolve, menu, settings, help. `SceneRouter::params` holds the arguments.

## Cheat sheet
| GDScript | C++ |
|---|---|
| `X.new()` for a Control subclass | `gd::make<X>()` or the class' `create()/make()` |
| `add_child(c)` | `parent->add(c)` (returns c) |
| `c.name = "Foo"` / `find_child("Foo", true, false)` | `c->set_name("Foo")` / `root->find("Foo")` |
| `custom_minimum_size = Vector2(w, h)` / `.x = w` | `set_custom_min(Vec2(w, h))` / `set_min_w(w)` |
| `size_flags_horizontal = SIZE_EXPAND_FILL` | `set_h_flags(gd::SIZE_EXPAND_FILL)` |
| `set_anchors_preset(PRESET_FULL_RECT)`; `offset_top = 10` | `set_anchors_preset(gd::PRESET_FULL_RECT)`; `set_offset(gd::SIDE_TOP, 10)` / `set_offsets(l, t, r, b)` |
| `position` / `size` (free children of a plain Control) | `set_position(Vec2)` / `set_size(Vec2)` |
| `add_theme_constant_override("separation", n)` | `box->separation = n` (`h_separation`/`v_separation` on Grid/Flow) |
| `alignment = BoxContainer.ALIGNMENT_CENTER` | `box->alignment = gd::ALIGNMENT_CENTER` |
| `GridContainer.new(); columns = 3` | `gd::GridContainer::create(3)` |
| `HFlowContainer` | `gd::FlowContainer::create()` |
| `label.text = s` | `label->set_text(s)` |
| label font size / colour / outline | `set_font_size`, `set_color`, `set_outline(size, col)` / `set_outline_color` |
| `horizontal_alignment` / `vertical_alignment` | `set_align(gd::ALIGN_CENTER, gd::VALIGN_CENTER)` |
| `autowrap_mode = ...` / `clip_text` | `set_autowrap(true)` / `set_clip_text(true)` |
| `visible_ratio` | `set_visible_ratio(r)` |
| `button.pressed.connect(f)` / `.disabled = true` | `b->pressed.connect(f)` / `b->set_disabled(true)` |
| `button.text` / `icon` / `add_theme_font_size_override` | `set_text` / `set_icon(path)` / `set_font_size` |
| `modulate = Color(...)` / `modulate.a = x` | `set_modulate(Col(...))` / `set_alpha(x)` (values > 1 clamp to 1: no over-bright) |
| `scale = Vector2(s, s)` + `pivot_offset` | `setScale(s)` + `set_pivot(Vec2)` |
| `z_index = n` | `set_z(n)` (orders siblings) |
| `clip_contents = true` | `set_clip(true)` |
| `mouse_filter = MOUSE_FILTER_IGNORE` | `set_mouse_filter(gd::MOUSE_IGNORE)` |
| `visible = false` | `setVisible(false)` |
| `queue_free()` / free all children | `queue_free()` / `clear_children()` |
| `Color("#ffd35a")`, `.darkened(k)`, `.lightened(k)`, `.lerp` | `Col("#ffd35a")`, same methods |
| `"%d/%d" % [a, b]` | `UIKit::fmt("%d/%d", a, b)` |
| `load("res://assets/x.png")` | paths drop `res://`: `"assets/x.png"`; `gd::texture(path)`; JSON paths may keep `res://` (helpers strip it) |
| `create_tween()...tween_property(n, "modulate:a", 1.0, 0.2)` | `auto tw = gd::tween(this); tw->alpha(n, 1.0f, 0.2f);` |
| `.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)` | `.trans(gd::TRANS_SINE).ease(gd::EASE_OUT)` |
| `set_parallel(true)`, `.parallel()`, `set_loops()`, `tween_interval`, `tween_callback`, `tween_method` | `set_parallel()`, `parallel()`, `loops()`, `interval(t)`, `callback(f)`, `method(f, from, to, t)` |
| `tween_property(n, "position:y", ...)`, `"scale"`, `"rotation"` | `position_y(n, ...)`, `scale(n, Vec2, t)`, `rotation(n, deg, t)`; anything else: `prop(get, set, to, t)` |
| `await tw.finished` | `tw->on_finished(f)` |
| `await get_tree().create_timer(t).timeout` | `gd::after(this, t, f)` (cancelled if `this` leaves the tree) |
| `call_deferred` / `await get_tree().process_frame` | `gd::defer(f)` (runs after the next layout pass: sizes are valid) |
| `await popup.tree_exited` / `closed` | `popup->closed.connect(f)` (or `tree_exiting`) |
| `GameManager.gold_changed.connect(f)` in a screen | `gd::listen(this, GM.gold_changed, f)` (auto-disconnects) |
| `_process(delta)` | `scheduleUpdate();` + `void update(float dt) override` |
| `Timer` | `schedule([this](float){...}, interval, "key")` |
| `Engine.time_scale = x` | `ax::Director::getInstance()->getScheduler()->setTimeScale(x)` |
| `CPUParticles2D` | `gd::ParticleCfg c; ... gd::Particles::create(c)` (a Control positioned with `set_position`) |
| `GradientTexture2D` | `gd::gradient_texture({{0, colA}, {1, colB}}, w, h, radial)` |
| `Polygon2D` / `draw_*` | `ax::DrawNode` inside a `gd::Node2D`, coordinates via `gd::p2(x, y)` |
| `Node2D` / `Sprite2D` world (battle) | raw `ax::Node` / `ax::Sprite` under a `gd::Node2D`; positions `gd::p2(x, y)` (Godot y-down) |
| `AnimatedSprite2D` + SpriteFrames | `SpriteFactory::unit(def)` / `SpriteFactory::effect(name)` (`gd::AnimatedSprite`) |
| `CanvasItemMaterial BLEND_MODE_ADD` | `TextureRect::additive`, `ColorRect::additive`, `sprite->setBlendFunc(ax::BlendFunc::ADDITIVE)` |
| shaders | not ported: use tints, tweens, additive quads |
| Dictionaries | `Json` + non-throwing accessors from `logic/Json.h`: `S(j,"k","def")`, `I(j,"k",0)`, `F`, `B`, `A(j,"k")` (array), `O(j,"k")` (object), `at(j, i)` |
| `Database.get_character(id)` / `GameManager.get_unit(uid)` | `DB.character(id)` / `GM.unit(uid)` (null Json when missing) |

## Rules
- Layout is recomputed at the end of a frame after tree/size changes. Sizes are 0 while a
  screen is being built: read them in `gd::defer`, a `resized` handler, or later.
  After changing a plain field (`separation`, `alignment`, `h_align`...) of a widget that
  is already laid out, call `gd::Root::mark_dirty()`.
- Popups belong to the screen: `FantasyPopup::open(this, ...)`.
- Lambdas that capture `this` are fine when the signal/tween/timer belongs to `this` or
  one of its children (they die together). Never keep raw pointers to nodes of another screen.
- Inside a Control the Axmol origin is the bottom-left corner; use the gd API and
  `gd::Node2D`/`gd::p2` so you never deal with it.
- Syntax-check every file you touch: `/home/claude/axcheck.sh Source/screens/Foo.cpp`.
  Full builds and screenshots run on GitHub Actions (`.github/workflows/build.yml`).
