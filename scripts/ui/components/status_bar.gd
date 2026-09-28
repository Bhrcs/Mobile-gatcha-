class_name StatusBar
extends PanelFrame
## Top resource bar (CinderResourceBar) shown on every menu screen:
##   [Rank + EXP]  [Energy cur/max  +1 in m:ss]  [Gems]  [Gold]
## * values use compact formatting (12.4K / 1.3M); the exact value is in the tooltip
## * changes count up/down briefly and flash (green = gained, red = spent)
## * energy regenerates live (also offline); tapping the rank opens the Profile
## * a screen can swap the third chip for the currency it cares about
##   (e.g. Soul Shards on the Summon screen) with show_currency("shards").

const CURRENCIES := {
	"gems": ["res://assets/icons/gem.png", Color("#9ae8ff"), "Gems",
			"Used to summon heroes and refill Energy.\nEarned from first clears, rank-ups, missions and login rewards."],
	"gold": ["res://assets/icons/gold.png", Color("#ffd35a"), "Gold",
			"Used for training and evolution.\nEarned from every stage and tower floor."],
	"shards": ["res://assets/icons/soul_shard.png", Color("#d9a8ff"), "Soul Shards",
			"Made from duplicate heroes.\nTrade them for heroes in the Codex."],
}

var _energy_l: Label
var _timer_l: Label
var _chips := {}          # key -> {label, shown, tween}
var _tick: Timer
var _third := "gems"


static func create() -> StatusBar:
	var b := StatusBar.new()
	b.name = "StatusBar"
	b.set_variant("panel", 12)
	return b


func _ready() -> void:
	var row := UIKit.hbox(UIKit.SP_M)
	add_child(row)
	# rank (tap -> profile)
	var rank_box := UIKit.hbox(UIKit.SP_S)
	rank_box.name = "RankBox"
	rank_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rank_box.add_child(UIKit.icon("res://assets/icons/rank.png", 56))
	var left := UIKit.vbox(2)
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var r := UIKit.hbox(UIKit.SP_S)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.add_child(UIKit.label("RANK", UIKit.T_SMALL, UIKit.SKY, HORIZONTAL_ALIGNMENT_LEFT, 5))
	var rank_l := UIKit.label(str(GameManager.rank()), UIKit.T_NAME, UIKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 7)
	rank_l.name = "RankValue"
	r.add_child(rank_l)
	left.add_child(r)
	var xb := ResourceBar.make("xp", 20)
	xb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var rank_xp := int(GameManager.profile.get("player", {}).get("rank_xp", 0))
	var need := Progression.rank_xp_to_next(GameManager.rank())
	xb.ready.connect(func(): xb.set_values(rank_xp, need, false))
	left.add_child(xb)
	rank_box.add_child(left)
	row.add_child(rank_box)
	UIKit.on_tap(rank_box, func(): SceneRouter.go("profile"))
	UIManager.attach_tooltip(rank_box, "Rank %d" % GameManager.rank(),
			"EXP %s / %s\nRank up to refill Energy and raise its maximum." % [UIKit.format_number(rank_xp), UIKit.format_number(need)])
	# energy
	var en := _chip("res://assets/icons/energy.png", "EnergyChip", 250)
	var ev := UIKit.vbox(0)
	ev.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_energy_l = UIKit.label("", UIKit.T_BODY, Color("#ffe07a"), HORIZONTAL_ALIGNMENT_LEFT, 6)
	_energy_l.name = "EnergyValue"
	_timer_l = UIKit.label("", UIKit.T_SMALL, UIKit.MUTED, HORIZONTAL_ALIGNMENT_LEFT, 4)
	ev.add_child(_energy_l)
	ev.add_child(_timer_l)
	en.get_child(0).add_child(ev)
	row.add_child(en)
	UIKit.on_tap(en, _energy_info)
	# two currency chips
	row.add_child(_currency_chip("gems", "GemsChip", 190))
	row.add_child(_currency_chip("gold", "GoldChip", 230))
	_refresh()
	_tick = Timer.new()
	_tick.wait_time = 1.0
	_tick.autostart = true
	_tick.timeout.connect(_refresh_energy)
	add_child(_tick)
	GameManager.gold_changed.connect(_on_change)
	GameManager.gems_changed.connect(_on_change)
	GameManager.energy_changed.connect(_on_energy)
	GameManager.profile_changed.connect(_refresh)


func _exit_tree() -> void:
	for pair in [[GameManager.gold_changed, _on_change], [GameManager.gems_changed, _on_change],
			[GameManager.energy_changed, _on_energy], [GameManager.profile_changed, _refresh]]:
		if pair[0].is_connected(pair[1]):
			pair[0].disconnect(pair[1])


## Replace the Gems chip with another currency relevant to this screen.
func show_currency(key: String) -> void:
	if not CURRENCIES.has(key) or not _chips.has(_third):
		return
	var c: Dictionary = _chips[_third]
	_chips.erase(_third)
	_third = key
	var chip: Control = c["chip"]
	chip.name = {"gems": "GemsChip", "shards": "ShardsChip", "gold": "GoldChip"}.get(key, key)
	var ic: TextureRect = chip.get_child(0).get_child(0)
	ic.texture = load(CURRENCIES[key][0])
	var l: Label = c["label"]
	l.name = chip.name.replace("Chip", "Value")
	l.add_theme_color_override("font_color", CURRENCIES[key][1])
	c["shown"] = _value(key)
	_chips[key] = c
	UIManager.attach_tooltip(chip, CURRENCIES[key][2], CURRENCIES[key][3], CURRENCIES[key][0])
	_refresh()


func _chip(icon_path: String, node_name: String, w: int) -> PanelFrame:
	var p := PanelFrame.make("inset", 8)
	p.name = node_name
	p.custom_minimum_size = Vector2(w, 0)
	var h := UIKit.hbox(6)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(h)
	h.add_child(UIKit.icon(icon_path, 48))
	return p


func _currency_chip(key: String, node_name: String, w: int) -> PanelFrame:
	var chip := _chip(CURRENCIES[key][0], node_name, w)
	var l := UIKit.label("", UIKit.T_CURRENCY, CURRENCIES[key][1], HORIZONTAL_ALIGNMENT_RIGHT, 6)
	l.name = node_name.replace("Chip", "Value")
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chip.get_child(0).add_child(l)
	chip.pivot_offset = Vector2(w / 2.0, 50)
	_chips[key] = {"chip": chip, "label": l, "shown": _value(key), "tween": null}
	UIManager.attach_tooltip(chip, CURRENCIES[key][2], CURRENCIES[key][3], CURRENCIES[key][0])
	return chip


func _value(key: String) -> int:
	match key:
		"gems":
			return GameManager.gems()
		"gold":
			return GameManager.gold()
		"shards":
			return GameManager.soul_shards()
	return 0


func _on_change(_v: int) -> void:
	_refresh()


func _on_energy(_c: int, _m: int) -> void:
	_refresh_energy()


func _refresh() -> void:
	if not GameManager.has_profile():
		return
	_refresh_energy()
	for key in _chips:
		_update_chip(key)


func _refresh_energy() -> void:
	if not GameManager.has_profile():
		return
	var cur := GameManager.energy()
	var mx := GameManager.max_energy()
	_energy_l.text = "%d/%d" % [cur, mx]
	_timer_l.text = "FULL" if cur >= mx else "+1 in %s" % UIKit.format_time(GameManager.energy_seconds_to_next())


## Counts from the shown value to the real one and flashes the chip.
func _update_chip(key: String) -> void:
	var c: Dictionary = _chips[key]
	var target := _value(key)
	var l: Label = c["label"]
	var chip: Control = c["chip"]
	chip.set_meta("tip", ["%s  %s" % [CURRENCIES[key][2], UIKit.format_number(target)], CURRENCIES[key][3], CURRENCIES[key][0]])
	var from: int = c["shown"]
	if from == target or not is_inside_tree() or not is_visible_in_tree():
		c["shown"] = target
		l.text = UIKit.format_compact(target)
		return
	if c["tween"] and (c["tween"] as Tween).is_valid():
		(c["tween"] as Tween).kill()
	var gain := target > from
	var tw := create_tween()
	c["tween"] = tw
	tw.tween_method(func(x: float): l.text = UIKit.format_compact(int(round(x))), float(from), float(target), 0.45)
	c["shown"] = target
	var flash := Color(0.75, 1.3, 0.75) if gain else Color(1.35, 0.7, 0.65)
	chip.modulate = flash
	chip.scale = Vector2(1.06, 1.06)
	var tw2 := create_tween().set_parallel(true)
	tw2.tween_property(chip, "modulate", Color.WHITE, 0.45)
	tw2.tween_property(chip, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_QUAD)
	if gain and key == "gold":
		UIManager.sfx("coin", -8.0)


func _energy_info() -> void:
	var p := FantasyPopup.open(get_parent(), "ENERGY", 860)
	p.name = "EnergyInfo"
	var lines := [
		"Entering a stage or tower floor costs Energy.",
		"You recover 1 Energy every %d minutes, even while the game is closed." % int(Database.balance("energy", "regen_seconds", 180) / 60),
		"Every Rank Up refills your Energy, and Max Energy grows as your Rank rises.",
		"Current: %d / %d" % [GameManager.energy(), GameManager.max_energy()],
	]
	for l in lines:
		var w := UIKit.wrap_label(l, UIKit.T_BODY)
		w.custom_minimum_size.x = 780
		p.content.add_child(w)
	var ok := UIKit.btn("OK", "primary", Vector2(300, 110))
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	ok.pressed.connect(p.close)
	p.default_action = p.close
	p.tap_outside_closes = true
	p.content.add_child(ok)
