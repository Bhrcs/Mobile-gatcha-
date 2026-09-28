class_name Combatant
extends RefCounted
## Runtime battle state for one unit (player or enemy). Pure logic, no nodes:
## HP, Burst, statuses and derived stats. The battle view observes it via signals.

signal hp_changed(current: int, maximum: int)
signal burst_changed(current: float, maximum: float)
signal statuses_changed
signal died

var id := ""                # character / enemy definition id
var uid := ""               # owned-unit id for players
var display_name := ""
var element := "fire"
var level := 1
var is_player := false
var is_boss := false
var slot := 0
var def: Dictionary = {}    # source definition (character or enemy)

var base_stats: Dictionary = {"hp": 1, "atk": 1, "def": 1, "rec": 0, "spd": 1}
var max_hp := 1
var hp := 1
var burst := 0.0
var burst_max := 100.0

var normal_skill := ""
var burst_skill := ""
var special_skill := ""     # enemies only
var skill_chance := 0.3     # enemies only

var acted := false          # has taken its action this round
var guarding := false
## [{id, value, turns}]  (for "shield" the value is the HP it still absorbs)
var statuses: Array = []

# ---- Phase 4: progression, passives, leader skill, auras
var burst_level := 1
var is_elite := false
var summoned := false
var summon_index := 0
var passive_stats: Array = []     # [{stat, value, condition?, threshold?}]
var heal_received_up := 0.0       # +% healing received
var damage_taken_down := 0.0      # -% damage taken
var burst_gain_mult := 1.0        # multiplier on Burst gauge gains
var regen_aura := 0.0             # % max HP healed at the end of each round
var crit_bonus := 0.0
var guard_bonus := 0.0            # extra damage reduction while guarding
var bonus_vs_low_hp := 0.0
var low_hp_threshold := 0.5
var bonus_vs_debuffed := 0.0
var enrage := 0.0                 # permanent ATK bonus (boss phase 2)
var last_absorbed := 0            # shield absorption of the latest take_damage()
var _skill_cache: Dictionary = {}

# ---- Phase 4: enemy AI state
var ai_turn := 0
var pattern_index := 0
var turns_since_summon := 0
var charging_skill := ""
var phase2 := false
var pending_skill := ""
var hp_events_done: Array = []
var last_action := ""


static func from_player_unit(unit: Dictionary, slot_index: int) -> Combatant:
	var c := Combatant.new()
	var d := Database.get_character(unit.get("char_id", ""))
	c.def = d
	c.id = d.get("id", "")
	c.uid = unit.get("uid", "")
	c.display_name = d.get("name", "???")
	c.element = d.get("element", "fire")
	c.level = int(unit.get("level", 1))
	c.is_player = true
	c.slot = slot_index
	c.base_stats = Progression.unit_stats(d, c.level)
	c.max_hp = int(c.base_stats["hp"])
	c.hp = c.max_hp
	c.normal_skill = d.get("normal_attack", "")
	c.burst_skill = d.get("burst", "")
	c.burst_level = clampi(int(unit.get("burst_level", 1)), 1, int(Database.balance("burst_levels", "max", 5)))
	c.burst_max = Progression.burst_cost(Database.get_skill(c.burst_skill), c.burst_level)
	c._apply_own_passive()
	return c


## Self-only passive effects. Team-wide ones (scope "allies") are applied by BattleModel.
func _apply_own_passive() -> void:
	for e in def.get("passive", {}).get("effects", []):
		if e.get("scope", "self") == "allies":
			continue
		apply_aura(e)


## Applies one passive / aura effect to this unit.
func apply_aura(e: Dictionary) -> void:
	var v := float(e.get("value", 0.0))
	match e.get("kind", ""):
		"stat_up":
			passive_stats.append(e)
		"heal_received_up":
			heal_received_up += v
		"damage_taken_down":
			damage_taken_down += v
		"burst_gain_up":
			burst_gain_mult += v
		"regen":
			regen_aura += v
		"crit_up":
			crit_bonus += v
		"guard_bonus":
			guard_bonus += v
		"damage_vs_low_hp":
			bonus_vs_low_hp += v
			low_hp_threshold = float(e.get("threshold", 0.5))
		"damage_vs_debuffed":
			bonus_vs_debuffed += v


## Leader skill stat bonus (multiplies the base stat for the whole battle).
func apply_stat_bonus(stat: String, value: float) -> void:
	if not base_stats.has(stat):
		return
	base_stats[stat] = float(base_stats[stat]) * (1.0 + value)
	if stat == "hp":
		max_hp = int(round(float(base_stats["hp"])))
		hp = max_hp


## Skill data for this unit; Burst skills are scaled by the hero's Burst level.
func skill_data(skill_id: String) -> Dictionary:
	if is_player and skill_id == burst_skill and burst_level > 1:
		if not _skill_cache.has(skill_id):
			_skill_cache[skill_id] = Progression.scaled_burst(Database.get_skill(skill_id), burst_level)
		return _skill_cache[skill_id]
	return Database.get_skill(skill_id)


static func from_enemy(enemy_id: String, level: int, slot_index: int, hp_scale: float = 1.0) -> Combatant:
	var c := Combatant.new()
	var d := Database.get_enemy(enemy_id)
	c.def = d
	c.id = enemy_id
	c.display_name = d.get("name", "???")
	c.element = d.get("element", "fire")
	c.level = level
	c.is_player = false
	c.is_boss = bool(d.get("boss", false))
	c.slot = slot_index
	c.base_stats = Progression.enemy_stats(d, level, hp_scale)
	c.max_hp = int(c.base_stats["hp"])
	c.hp = c.max_hp
	c.normal_skill = d.get("skills", {}).get("normal", "")
	c.special_skill = d.get("skills", {}).get("special", "")
	c.skill_chance = float(d.get("ai", {}).get("skill_chance", 0.3))
	c.is_elite = bool(d.get("elite", false))
	return c


# ------------------------------------------------------------------ state
func is_alive() -> bool:
	return hp > 0


func can_act() -> bool:
	return is_alive() and not acted


func burst_ready() -> bool:
	return is_alive() and not burst_skill.is_empty() and burst >= burst_max


func hp_ratio() -> float:
	return float(hp) / float(max(max_hp, 1))


## Stat including active buffs/debuffs (DEF Up, ATK Down...), passives and enrage.
func get_stat(stat: String) -> float:
	var value := float(base_stats.get(stat, 0))
	var bonus := 0.0
	for s in statuses:
		var sdef := Database.get_status(s["id"])
		if sdef.get("kind") == "stat_mod" and sdef.get("stat") == stat:
			bonus += float(s.get("value", 0.0)) * float(sdef.get("sign", 1))
	for p in passive_stats:
		if p.get("stat", "") != stat:
			continue
		if p.get("condition", "") == "hp_above" and hp_ratio() <= float(p.get("threshold", 0.0)):
			continue
		bonus += float(p.get("value", 0.0))
	if stat == "atk":
		bonus += enrage
	return value * maxf(1.0 + bonus, 0.1)


## Extra damage this unit deals to `target` from passives (e.g. vs low-HP or debuffed foes).
func damage_bonus_vs(target: Combatant) -> float:
	var b := 0.0
	if bonus_vs_low_hp > 0.0 and target.hp_ratio() < low_hp_threshold:
		b += bonus_vs_low_hp
	if bonus_vs_debuffed > 0.0 and target.has_negative_status():
		b += bonus_vs_debuffed
	return b


func has_negative_status() -> bool:
	for s in statuses:
		if Database.get_status(s["id"]).get("negative", false):
			return true
	return false


func shield_amount() -> int:
	for s in statuses:
		if s["id"] == "shield":
			return int(s.get("value", 0))
	return 0


func add_shield(amount: int, turns: int) -> void:
	add_status("shield", float(amount), turns)


func remove_status(status_id: String) -> void:
	for s in statuses.duplicate():
		if s["id"] == status_id:
			statuses.erase(s)
			statuses_changed.emit()


func damage_reduction() -> float:
	var r := 0.0
	for s in statuses:
		if Database.get_status(s["id"]).get("kind") == "damage_reduction":
			r = max(r, float(s.get("value", 0.0)))
	return clampf(r, 0.0, 0.9)


func taunt_weight() -> float:
	for s in statuses:
		if Database.get_status(s["id"]).get("kind") == "taunt":
			return float(Database.balance("combat", "taunt_weight", 4.0))
	return 1.0


# ------------------------------------------------------------------ mutation
## Applies damage. A Shield absorbs first (see last_absorbed).
## Returns the HP damage actually dealt (clamped to remaining HP).
func take_damage(amount: int) -> int:
	last_absorbed = 0
	if not is_alive():
		return 0
	for s in statuses:
		if s["id"] == "shield" and amount > 0:
			var absorb := mini(int(s["value"]), amount)
			s["value"] = int(s["value"]) - absorb
			amount -= absorb
			last_absorbed = absorb
			if int(s["value"]) <= 0:
				statuses.erase(s)
			statuses_changed.emit()
			break
	var dealt: int = clampi(amount, 0, hp)
	hp -= dealt
	hp_changed.emit(hp, max_hp)
	if hp <= 0:
		hp = 0
		burst = 0.0
		statuses.clear()
		statuses_changed.emit()
		died.emit()
	return dealt


func heal(amount: int) -> int:
	if not is_alive():
		return 0
	var healed: int = clampi(amount, 0, max_hp - hp)
	hp += healed
	hp_changed.emit(hp, max_hp)
	return healed


func add_burst(amount: float) -> void:
	if not is_alive() or burst_skill.is_empty() or amount == 0.0:
		return
	var before := burst
	burst = clampf(burst + amount, 0.0, burst_max)
	if burst != before:
		burst_changed.emit(burst, burst_max)


func reset_burst() -> void:
	burst = 0.0
	burst_changed.emit(burst, burst_max)


## Adds or refreshes a status (same id keeps the stronger value / longer duration).
func add_status(status_id: String, value: float, turns: int) -> void:
	if not is_alive() or Database.get_status(status_id).is_empty():
		return
	for s in statuses:
		if s["id"] == status_id:
			s["value"] = max(float(s["value"]), value)
			s["turns"] = max(int(s["turns"]), turns)
			statuses_changed.emit()
			return
	statuses.append({"id": status_id, "value": value, "turns": turns})
	statuses_changed.emit()


func has_status(status_id: String) -> bool:
	for s in statuses:
		if s["id"] == status_id:
			return true
	return false


## Removes up to `count` negative statuses. Returns removed ids.
func cleanse(count: int) -> Array:
	var removed: Array = []
	for s in statuses.duplicate():
		if removed.size() >= count:
			break
		if Database.get_status(s["id"]).get("negative", false):
			statuses.erase(s)
			removed.append(s["id"])
	if not removed.is_empty():
		statuses_changed.emit()
	return removed


## End-of-round processing. Returns [{type:"dot"|"hot", status, amount}] events.
## Burn/Poison damage, Regen (status value = % max HP) and passive regen auras.
func tick_statuses() -> Array:
	var events: Array = []
	if not is_alive():
		return events
	var regen := regen_aura
	for s in statuses:
		var sdef := Database.get_status(s["id"])
		match sdef.get("kind"):
			"dot":
				var dmg: int = max(1, int(round(max_hp * float(sdef.get("dot_percent_max_hp", 0.05)))))
				events.append({"type": "dot", "status": s["id"], "amount": dmg})
			"hot":
				regen += float(s.get("value", 0.05))
	if regen > 0.0 and hp < max_hp:
		events.append({"type": "hot", "status": "regen", "amount": max(1, int(round(max_hp * regen * (1.0 + heal_received_up))))})
	for s in statuses.duplicate():
		if s["id"] == "charging":
			continue          # released (and removed) by the unit's next action
		s["turns"] = int(s["turns"]) - 1
		if s["turns"] <= 0:
			statuses.erase(s)
	statuses_changed.emit()
	return events
