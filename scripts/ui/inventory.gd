extends ScreenBase
## Inventory: tabs MATERIALS / TRAINING / ITEMS / OTHER. Items stack (one row
## per item with its quantity). Tap a row for OBTAINED FROM (with GO buttons).
## OTHER lists the currencies: Gems, Gold and Soul Shards.

const TABS := [["MATERIALS", "material"], ["TRAINING", "training"], ["ITEMS", "item"], ["OTHER", "other"]]

var list: VBoxContainer
var category := ""
var _tab_buttons: Array[FantasyButton] = []


func _ready() -> void:
	if not require_profile():
		return
	var area := build_frame("bg_camp", "ITEMS", "inventory", Callable(), 0.6)
	var col := UIKit.vbox(12)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	var tabs := UIKit.hbox(10)
	for t in TABS:
		var b := FantasyButton.make(t[0], "steel", Vector2(0, 96))
		b.name = "Tab_" + t[0]
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", 30)
		var cat: String = t[1]
		b.pressed.connect(func(): _set_category(cat))
		tabs.add_child(b)
		_tab_buttons.append(b)
	col.add_child(tabs)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	list = UIKit.vbox(12)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	_set_category(SceneRouter.params.get("tab", "material"))


func _set_category(cat: String) -> void:
	category = cat
	for i in TABS.size():
		_tab_buttons[i].apply_style("gold" if TABS[i][1] == cat else "steel")
	for ch in list.get_children():
		ch.queue_free()
	if cat == "other":
		_currencies()
		return
	var inv: Dictionary = GameManager.profile.get("inventory", {})
	var ids: Array = inv.keys().filter(func(k):
		return int(inv[k]) > 0 and (cat.is_empty() or Database.get_item(k).get("category", "") == cat))
	ids.sort_custom(func(a, b): return int(Database.get_item(a).get("sort", 99)) < int(Database.get_item(b).get("sort", 99)))
	if ids.is_empty():
		var p := PanelFrame.make("inset", 30)
		var empty := UIKit.wrap_label("Nothing here yet. Clear stages and tower floors to find materials and wisps.",
				UIKit.T_BODY, UIKit.MUTED)
		empty.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		p.add_child(empty)
		list.add_child(p)
	var k := 0
	for item_id in ids:
		var row := _row(item_id, int(inv[item_id]))
		list.add_child(row)
		row.modulate.a = 0.0
		row.create_tween().tween_property(row, "modulate:a", 1.0, 0.15).set_delay(0.03 * k)
		k += 1


func _row(item_id: String, qty: int) -> Control:
	var item := Database.get_item(item_id)
	var row := PanelFrame.make("plank", 14)
	row.name = "Item_" + item_id
	var h := UIKit.hbox(20)
	row.add_child(h)
	var slot := PanelFrame.make("slot", 10)
	slot.add_child(UIKit.icon(item.get("icon", ""), 96))
	h.add_child(slot)
	var v := UIKit.vbox(4)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(v)
	var top := UIKit.hbox(16)
	var nm := UIKit.label(item.get("name", item_id), UIKit.T_NAME, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 8)
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(nm)
	top.add_child(UIKit.label("x%d" % qty, UIKit.T_HEAD, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 10))
	v.add_child(top)
	var cat := String(item.get("category", ""))
	v.add_child(UIKit.label(item.get("use", cat.to_upper()), UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var d := UIKit.wrap_label(item.get("description", ""), UIKit.T_SMALL, Color("#e0d6c6"))
	d.custom_minimum_size.x = 760
	v.add_child(d)
	UIKit.on_tap(row, func(): ItemSources.open(self, item_id))
	return row


func _currencies() -> void:
	for c in [["res://assets/icons/gem.png", "Gems", GameManager.gems(), "Summon heroes at the Embergate. Earned from first clears (5, bosses 25), rank-ups, missions and login rewards."],
			["res://assets/icons/gold.png", "Gold", GameManager.gold(), "Pays for training and evolution. Earned from every battle."],
			["res://assets/icons/soul_shard.png", "Soul Shards", GameManager.soul_shards(), "Made from duplicate summons. Spend them to train any hero's Burst level."],
			["res://assets/icons/energy.png", "Energy", GameManager.energy(), "Spent to enter stages. Refills over time and on every Rank Up."]]:
		var row := PanelFrame.make("plank", 14)
		row.name = "Currency_" + String(c[1]).replace(" ", "")
		var h := UIKit.hbox(20)
		row.add_child(h)
		var slot := PanelFrame.make("slot", 10)
		slot.add_child(UIKit.icon(c[0], 96))
		h.add_child(slot)
		var v := UIKit.vbox(4)
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var top := UIKit.hbox(12)
		var nm := UIKit.label(c[1], UIKit.T_NAME, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 8)
		nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		top.add_child(nm)
		top.add_child(UIKit.label(UIKit.format_number(int(c[2])), UIKit.T_HEAD, UIKit.GOLD, HORIZONTAL_ALIGNMENT_RIGHT, 10))
		v.add_child(top)
		var d := UIKit.wrap_label(c[3], UIKit.T_SMALL, Color("#e0d6c6"))
		d.custom_minimum_size.x = 760
		v.add_child(d)
		h.add_child(v)
		list.add_child(row)
