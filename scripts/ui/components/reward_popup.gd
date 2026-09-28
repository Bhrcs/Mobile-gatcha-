class_name RewardPopup
extends RefCounted
## Shows granted rewards (gems / gold / soul shards / items) as popping slots.


static func open(parent: Control, title: String, r: Dictionary, sub := "") -> FantasyPopup:
	var p := FantasyPopup.open(parent, title, 900, "boss")
	p.name = "RewardPopup"
	if not sub.is_empty():
		var s := UIKit.wrap_label(sub, UIKit.T_BODY, Color("#fff0c0"))
		s.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		s.custom_minimum_size.x = 820
		p.content.add_child(s)
	var row := HFlowContainer.new()
	row.alignment = FlowContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("h_separation", 14)
	row.custom_minimum_size.x = 820
	p.content.add_child(row)
	var slots: Array = []
	if int(r.get("gems", 0)) > 0:
		slots.append(RewardItem.make("res://assets/icons/gem.png", "%d" % int(r["gems"]), "GEMS", 120))
	if int(r.get("gold", 0)) > 0:
		slots.append(RewardItem.make("res://assets/icons/gold.png", UIKit.format_number(int(r["gold"])), "GOLD", 120))
	if int(r.get("soul_shards", 0)) > 0:
		slots.append(RewardItem.make("res://assets/icons/soul_shard.png", "%d" % int(r["soul_shards"]), "SHARDS", 120))
	for item_id in r.get("items", {}).keys():
		slots.append(RewardItem.make(Database.get_item(item_id).get("icon", ""), "x%d" % int(r["items"][item_id]),
				Database.item_name(item_id).get_slice(" ", 0).to_upper(), 120))
	var k := 0
	for s in slots:
		row.add_child(s)
		s.pop(0.08 * k)
		k += 1
	UIKit.sparkle(p.panel, Rect2(0, 0, 900, 400), UIKit.GOLD, 10)
	var ok := FantasyButton.make("OK", "ember", Vector2(300, 110))
	ok.name = "RewardOK"
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	ok.pressed.connect(p.close)
	p.content.add_child(ok)
	return p
