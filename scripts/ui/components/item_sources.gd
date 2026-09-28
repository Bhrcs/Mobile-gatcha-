class_name ItemSources
extends RefCounted
## "OBTAINED FROM" popup: every stage / tower floor / mission / login day that
## gives an item. Reachable stages have a GO button that jumps straight to them.


static func open(parent: Control, item_id: String) -> FantasyPopup:
	var item := Database.get_item(item_id)
	var p := FantasyPopup.open(parent, "OBTAINED FROM", 960)
	p.name = "ItemSourcesPopup"
	var head := UIKit.hbox(14)
	head.alignment = BoxContainer.ALIGNMENT_CENTER
	head.add_child(UIKit.icon(item.get("icon", ""), 80))
	var hv := UIKit.vbox(2)
	hv.add_child(UIKit.label(item.get("name", item_id), UIKit.T_NAME, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 8))
	hv.add_child(UIKit.label("Owned: %d" % GameManager.item_count(item_id), UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	head.add_child(hv)
	p.content.add_child(head)
	var use := UIKit.wrap_label(item.get("use", ""), UIKit.T_SMALL, UIKit.MUTED)
	use.custom_minimum_size.x = 880
	use.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	p.content.add_child(use)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(900, 620)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	p.content.add_child(scroll)
	var list := UIKit.vbox(8)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	var sources := GameManager.item_sources(item_id)
	if sources.is_empty():
		list.add_child(UIKit.label("No known source yet.", UIKit.T_BODY, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER))
	for src in sources.slice(0, 16):
		var row := PanelFrame.make("plank" if src["unlocked"] else "inset", 8)
		row.name = "Src_" + str(src["id"])
		var h := UIKit.hbox(10)
		row.add_child(h)
		var icon_path := "res://assets/icons/tower.png" if src["kind"] == "tower" else \
				("res://assets/icons/missions.png" if src["kind"] == "missions" else \
				("res://assets/icons/login.png" if src["kind"] == "login" else "res://assets/icons/world.png"))
		h.add_child(UIKit.icon(icon_path, 48))
		var v := UIKit.vbox(0)
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		v.add_child(UIKit.label(src["label"], UIKit.T_BODY, UIKit.TEXT if src["unlocked"] else UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 6))
		if src["kind"] in ["stage", "tower"]:
			var st := Database.get_stage(src["id"])
			v.add_child(UIKit.label(st.get("name", ""), UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4))
		h.add_child(v)
		if src["unlocked"]:
			var go := FantasyButton.make("GO", "ember", Vector2(150, 80))
			go.add_theme_font_size_override("font_size", 30)
			var sid: String = src["id"]
			var kind: String = src["kind"]
			go.pressed.connect(func():
				p.close()
				_go(parent, kind, sid))
			h.add_child(go)
		else:
			h.add_child(UIKit.icon("res://assets/icons/lock.png", 40))
			h.add_child(UIKit.label("LOCKED", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4))
		list.add_child(row)
	var close := FantasyButton.make("CLOSE", "stone", Vector2(280, 100))
	close.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	close.pressed.connect(p.close)
	p.content.add_child(close)
	return p


static func _go(parent: Control, kind: String, sid: String) -> void:
	match kind:
		"stage":
			SceneRouter.go("stage_select", {"highlight": sid})
		"tower":
			SceneRouter.go("tower", {"highlight": sid})
		"missions":
			SceneRouter.go("missions")
		_:
			UIKit.toast(parent, "Log in each day to collect login rewards.", UIKit.GOLD)
