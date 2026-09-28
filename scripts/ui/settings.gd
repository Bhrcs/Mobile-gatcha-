extends ScreenBase
## Settings screen (from MENU): AUDIO / GAMEPLAY / GRAPHICS / ACCOUNT tabs.
## The rows themselves live in SettingsPanel so the title screen and the battle
## pause menu show exactly the same options.

var body: VBoxContainer
var tabs: CinderTabs


func _ready() -> void:
	if not require_profile():
		return
	back_fallback = "menu"
	var area := build_frame("bg_camp", "SETTINGS", "menu", Callable(), 0.6)
	var col := UIKit.vbox(UIKit.SP_L)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	var cats := SettingsPanel._categories()
	var start := clampi(int(SceneRouter.params.get("tab", 0)), 0, cats.size() - 1)
	tabs = CinderTabs.make(cats, start, _on_tab)
	col.add_child(tabs)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	body = UIKit.vbox(UIKit.SP_M)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	SettingsPanel.fill(body, cats[start], self)


func _on_tab(i: int) -> void:
	SceneRouter.remember({"tab": i})
	SettingsPanel.fill(body, SettingsPanel._categories()[i], self)
