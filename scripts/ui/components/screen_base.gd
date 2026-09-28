class_name ScreenBase
extends Control
## Base for every menu screen. Builds the shared layers in order:
##   stone backdrop -> scene art -> dim -> status bar -> header -> content -> nav
## and respects mobile safe areas.
## Back (header button, Esc on PC) goes through on_back(): by default it returns
## along the navigation history (SceneRouter.back) or to `back_fallback`.

var content: Control          # area between header and nav bar
var status_bar_node: Control
var header: ScreenHeader
var nav_bar: NavBar
var back_fallback := "home"
var _back_override: Callable


## on_back: optional custom handler; leave empty for the standard history Back.
## opts: help (topic string), no_back (bool)
func build_frame(bg_name: String, title: String, nav_tab: String, on_back: Callable = Callable(),
		dim := 0.45, with_status := true, opts := {}) -> Control:
	_back_override = on_back
	UIKit.screen_background(self, bg_name, dim)
	var top := UIKit.safe_top()
	if with_status:
		status_bar_node = UIKit.status_bar(self)
		top += UIKit.TOP_BAR_H
	if not title.is_empty():
		var cb := Callable() if opts.get("no_back", false) else on_back_pressed
		header = ScreenHeader.attach(self, title, cb, top + 4, opts.get("help", ""))
		top += ScreenHeader.HEIGHT + 12
	content = Control.new()
	content.name = "Content"
	content.set_anchors_preset(Control.PRESET_FULL_RECT)
	content.offset_top = top
	content.offset_left = 14
	content.offset_right = -14
	content.offset_bottom = -(NavBar.HEIGHT + UIKit.safe_bottom() + 10) if not nav_tab.is_empty() else -(UIKit.safe_bottom() + 14)
	content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(content)
	if not nav_tab.is_empty():
		nav_bar = NavBar.attach(self, nav_tab)
	return content


func on_back_pressed() -> void:
	on_back()


## Esc / header Back. Screens may override.
func on_back() -> void:
	if SceneRouter.transitioning:
		return
	if _back_override.is_valid():
		UIManager.sfx("back")
		_back_override.call()
	else:
		SceneRouter.back(back_fallback)


func require_profile() -> bool:
	if GameManager.has_profile() or GameManager.continue_game():
		return true
	SceneRouter.go.call_deferred("main_menu")
	return false
