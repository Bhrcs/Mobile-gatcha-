extends ScreenBase
## Help & Guide: short topics a player can look up at any time. Opened from MENU,
## from the "?" in screen headers (with a topic) and from the battle pause menu.

const TOPICS := ["BASICS", "BATTLE", "ELEMENTS", "HEROES", "PROGRESS"]
## topic -> [[icon, heading, text], ...]
const PAGES := {
	"BASICS": [
		["res://assets/icons/nav_quest.png", "Quest", "Pick a world, then a stage on its map. Stages cost Energy and give EXP, Gold, items and up to 3 stars."],
		["res://assets/icons/energy.png", "Energy", "Energy refills over time, even while the game is closed, and fully on every Rank Up."],
		["res://assets/icons/nav_units.png", "Units", "Your heroes. Train them with Wisps, evolve them at max level and pick your squad."],
		["res://assets/icons/nav_summon.png", "Summon", "Spend Gems at the Embergate for new heroes. Duplicates become Soul Shards."],
		["res://assets/icons/back.png", "Getting around", "BACK (top left) always returns to where you came from. On PC, Esc works as Back and Enter confirms."],
	],
	"BATTLE": [
		["res://assets/icons/sword.png", "Attack", "Tap an enemy to target it, then tap a hero card to attack. Each hero acts once per turn."],
		["res://assets/icons/burst.png", "Burst", "When a hero's Burst gauge is full, swipe UP on their card for their Burst skill. Attacking, guarding and taking hits fill it."],
		["res://assets/icons/shield.png", "Guard", "Swipe DOWN on a card to Guard: half damage this turn and extra Burst gauge. Guard when an enemy shows WARNING."],
		["res://assets/icons/auto.png", "Auto & speed", "AUTO lets heroes fight on their own (they Burst and Guard sensibly). 1x / 2x changes battle speed."],
		["res://assets/icons/status_burn.png", "Status effects", "Icons under a unit show effects such as Burn, Poison, Shield or ATK Up. Tap or hover an icon to read it."],
		["res://assets/icons/star.png", "Stars", "Each stage has three star goals (for example: clear it, no hero knocked out, clear within a number of turns)."],
	],
	"ELEMENTS": [],
	"HEROES": [
		["res://assets/icons/xp.png", "Training", "Feed Wisps and Gold to level a hero up. Wisps of the hero's own element give +50% EXP."],
		["res://assets/icons/star.png", "Evolution", "At max level a hero can evolve into a stronger form. WHERE TO FIND shows where each material drops."],
		["res://assets/icons/leader.png", "Leader", "Your leader's Leader Skill boosts the whole squad. Set the leader in SQUAD."],
		["res://assets/icons/role_attacker.png", "Roles", "Attackers deal damage, Defenders protect, Healers restore HP, Supporters buff and Breakers weaken enemies."],
		["res://assets/icons/soul_shard.png", "Soul Shards", "Duplicate summons turn into Soul Shards. Spend them on any hero to raise their Burst level."],
	],
	"PROGRESS": [
		["res://assets/icons/rank.png", "Rank", "Battles give Rank EXP. Rank Ups refill Energy, raise Max Energy and sometimes give Gems."],
		["res://assets/icons/tower.png", "Elemental Towers", "Ember, Tide and Verdant Towers are the best source of evolution materials. Each floor is harder."],
		["res://assets/icons/missions.png", "Missions", "Daily and weekly missions give Gems, Gold and Wisps. Log in each day for the 7-day reward track."],
		["res://assets/icons/lock.png", "Unlocks", "New features open as you clear World 1. A locked button always says which stage opens it."],
	],
}

var body: VBoxContainer
var tabs: CinderTabs


func _ready() -> void:
	if not require_profile():
		return
	back_fallback = "menu"
	var area := build_frame("bg_camp", "HELP & GUIDE", "menu", Callable(), 0.6)
	var col := UIKit.vbox(UIKit.SP_L)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	var topic := String(SceneRouter.params.get("topic", "BASICS")).to_upper()
	# header "?" topics map onto the guide pages
	topic = {"SQUAD": "ELEMENTS", "UNITS": "HEROES", "SUMMON": "HEROES", "TOWER": "PROGRESS"}.get(topic, topic)
	var start := maxi(0, TOPICS.find(topic))
	tabs = CinderTabs.make(TOPICS, start, _show, 88)
	col.add_child(tabs)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	body = UIKit.vbox(UIKit.SP_M)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)
	_show(start)


func _show(i: int) -> void:
	SceneRouter.remember({"topic": TOPICS[i]})
	for c in body.get_children():
		body.remove_child(c)
		c.queue_free()
	if TOPICS[i] == "ELEMENTS":
		var p := PanelFrame.make("panel", 20)
		body.add_child(p)
		var v := UIKit.vbox(UIKit.SP_M)
		p.add_child(v)
		var chart := ElementChart.make()
		chart.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		v.add_child(chart)
		for line in ElementChart.explanation():
			var l := UIKit.wrap_label(line, UIKit.T_BODY)
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			v.add_child(l)
		body.add_child(_entry(["res://assets/icons/info.png", "In battle",
				"ADVANTAGE numbers mean a strong hit, RESIST numbers a weak one. The squad screen warns you when your team is weak against a stage."]))
		return
	for e in PAGES.get(TOPICS[i], []):
		body.add_child(_entry(e))


func _entry(e: Array) -> Control:
	var p := PanelFrame.make("inset", 16)
	var h := UIKit.hbox(UIKit.SP_L)
	p.add_child(h)
	var ic := UIKit.icon(e[0], 64)
	ic.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	h.add_child(ic)
	var v := UIKit.vbox(UIKit.SP_XS)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(UIKit.label(e[1], UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 8))
	v.add_child(UIKit.wrap_label(e[2], UIKit.T_BODY))
	h.add_child(v)
	return p
