class_name EnergyPopup
extends RefCounted
## "Not enough Energy" dialog: shows current / needed Energy and a live countdown
## to the next point. Energy also refills completely on every Rank Up.


static func open(parent: Node, stage_id: String) -> FantasyPopup:
	var need := GameManager.stage_energy(stage_id)
	var p := FantasyPopup.open(parent, "NOT ENOUGH ENERGY", 900)
	var row := UIKit.hbox(14)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(UIKit.icon("res://assets/icons/energy.png", 64))
	var amount := UIKit.label("", UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6)
	row.add_child(amount)
	p.content.add_child(row)
	var timer := UIKit.label("", UIKit.T_BODY, UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 5)
	p.content.add_child(timer)
	var tip := UIKit.wrap_label("Energy recovers by itself, even while the game is closed, and refills completely whenever your Rank goes up.", UIKit.T_SMALL)
	tip.custom_minimum_size.x = 820
	tip.add_theme_color_override("font_color", UIKit.MUTED)
	p.content.add_child(tip)
	var ok := FantasyButton.make("OK", "ember", Vector2(320, 110))
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(ok)
	ok.pressed.connect(p.close)
	var refresh := func():
		if not is_instance_valid(amount):
			return
		amount.text = "%d / %d   (need %d)" % [GameManager.energy(), GameManager.max_energy(), need]
		var secs := GameManager.energy_seconds_to_next()
		var missing := maxi(need - GameManager.energy(), 0)
		if missing <= 0:
			timer.text = "You have enough Energy now!"
		else:
			var total := secs + (missing - 1) * int(Database.balance("energy", "regen_seconds", 180))
			timer.text = "Next +1 in %s  -  ready in %s" % [UIKit.format_time(secs), UIKit.format_time(total)]
	refresh.call()
	var t := Timer.new()
	t.wait_time = 1.0
	t.autostart = true
	t.timeout.connect(refresh)
	p.add_child(t)
	return p
