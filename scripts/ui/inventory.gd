extends ScreenBase
## Inventory: tabs MATERIALS / TRAINING / ITEMS / OTHER. Items stack in a grid of
## slots (icon + quantity); the docked detail panel shows the selected item with
## WHERE TO FIND, and USE only for items that can be used from here.
## OTHER lists the currencies: Gems, Gold, Soul Shards and Energy.

const TABS := [["MATERIALS", "material"], ["TRAINING", "training"], ["ITEMS", "item"], ["OTHER", "other"]]
const DETAIL_H := 360

var list: VBoxContainer
var grid: GridContainer
var detail: VBoxContainer
var detail_panel: PanelFrame
var category := ""
var selected := ""
var tabs: CinderTabs


func _ready() -> void:
	if not require_profile():
		return
	back_fallback = "menu"
	var area := build_frame("bg_camp", "ITEMS", "inventory", Callable(), 0.6)
	var col := UIKit.vbox(UIKit.SP_M)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	var labels: Array = []
	for t in TABS:
		labels.append(t[0])
	var start: String = SceneRouter.params.get("tab", "material")
	var idx := 0
	for i in TABS.size():
		if TABS[i][1] == start:
			idx = i
	tabs = CinderTabs.make(labels, idx, func(i: int): _set_category(TABS[i][1]))
	col.add_child(tabs)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	list = UIKit.vbox(UIKit.SP_M)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	detail_panel = PanelFrame.make("panel", 18)
	detail_panel.name = "ItemDetail"
	detail_panel.custom_minimum_size.y = DETAIL_H
	col.add_child(detail_panel)
	detail = UIKit.vbox(UIKit.SP_S)
	detail_panel.add_child(detail)
	_set_category(TABS[idx][1])


func _set_category(cat: String) -> void:
	category = cat
	SceneRouter.remember({"tab": cat})
	for ch in list.get_children():
		ch.queue_free()
	detail_panel.visible = cat != "other"
	if cat == "other":
		_currencies()
		return
	var inv: Dictionary = GameManager.profile.get("inventory", {})
	var ids: Array = inv.keys().filter(func(k):
		return int(inv[k]) > 0 and Database.get_item(k).get("category", "") == cat)
	ids.sort_custom(func(a, b): return int(Database.get_item(a).get("sort", 99)) < int(Database.get_item(b).get("sort", 99)))
	if ids.is_empty():
		var p := PanelFrame.make("inset", 30)
		var empty := UIKit.wrap_label({"material": "No materials yet. Tower floors and later stages drop evolution materials.",
				"training": "No wisps yet. Wisps drop from stages, bosses, towers, missions and login rewards.",
				"item": "No items yet. Herbs and treasures drop from stages."}.get(cat, "Nothing here yet."),
				UIKit.T_BODY, UIKit.MUTED)
		empty.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		p.add_child(empty)
		list.add_child(p)
		selected = ""
		_show_detail("")
		return
	grid = GridContainer.new()
	grid.columns = 5
	grid.add_theme_constant_override("h_separation", UIKit.SP_M)
	grid.add_theme_constant_override("v_separation", UIKit.SP_M)
	grid.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	list.add_child(grid)
	for item_id in ids:
		grid.add_child(_slot(item_id, int(inv[item_id])))
	if not ids.has(selected):
		selected = ids[0]
	_show_detail(selected)


func _slot(item_id: String, qty: int) -> Control:
	var item := Database.get_item(item_id)
	var cell := PanelFrame.make("boss" if item_id == selected else "slot", 10)
	cell.name = "Item_" + item_id
	cell.custom_minimum_size = Vector2(186, 186)
	var holder := Control.new()
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cell.add_child(holder)
	var ic := UIKit.icon(item.get("icon", ""), 112)
	ic.position = Vector2(26, 10)
	holder.add_child(ic)
	var q := UIKit.label("x" + UIKit.format_compact(qty), UIKit.T_BODY, Color.WHITE, HORIZONTAL_ALIGNMENT_RIGHT, 8)
	q.position = Vector2(0, 118)
	q.size = Vector2(160, 40)
	holder.add_child(q)
	UIKit.on_tap(cell, func(): _select(item_id))
	return cell


func _select(item_id: String) -> void:
	selected = item_id
	for c in grid.get_children():
		(c as PanelFrame).set_variant("boss" if c.name == "Item_" + item_id else "slot", 10)
	_show_detail(item_id)


func _show_detail(item_id: String) -> void:
	for c in detail.get_children():
		c.queue_free()
	if item_id.is_empty():
		detail.add_child(UIKit.label("Select an item to see what it does.", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
		return
	var item := Database.get_item(item_id)
	var h := UIKit.hbox(UIKit.SP_L)
	detail.add_child(h)
	var slot := PanelFrame.make("slot", 10)
	slot.add_child(UIKit.icon(item.get("icon", ""), 96))
	h.add_child(slot)
	var v := UIKit.vbox(UIKit.SP_XS)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var top := UIKit.hbox(UIKit.SP_M)
	var nm := UIKit.label(item.get("name", item_id), UIKit.T_NAME, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 8)
	nm.name = "DetailName"
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(nm)
	top.add_child(UIKit.label("x%s" % UIKit.format_number(GameManager.item_count(item_id)), UIKit.T_NAME, UIKit.GOLD,
			HORIZONTAL_ALIGNMENT_RIGHT, 8))
	v.add_child(top)
	v.add_child(UIKit.label(item.get("use", ""), UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	v.add_child(UIKit.wrap_label(item.get("description", ""), UIKit.T_SMALL, Color("#e0d6c6")))
	h.add_child(v)
	var row := UIKit.hbox(UIKit.SP_M)
	row.alignment = BoxContainer.ALIGNMENT_END
	var src := UIKit.btn("WHERE TO FIND", "secondary", Vector2(340, 96))
	src.name = "DetailSources"
	src.pressed.connect(func(): ItemSources.open(self, item_id))
	row.add_child(src)
	# USE only where using it from here makes sense (wisps -> pick a hero to train)
	if item.get("category", "") == "training" and GameManager.feature_unlocked("training"):
		var use := UIKit.btn("USE", "primary", Vector2(220, 96))
		use.name = "DetailUse"
		use.pressed.connect(func():
			UIManager.toast("Pick a hero, then press TRAIN.", "info")
			SceneRouter.go("units"))
		row.add_child(use)
	detail.add_child(row)


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
