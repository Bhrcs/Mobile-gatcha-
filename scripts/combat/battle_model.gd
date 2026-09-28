class_name BattleModel
extends RefCounted
## Rules-only battle state: waves, turn order, action planning and resolution.
## The battle scene drives this model and animates the results; automated
## tests and the balance simulator drive it directly with no visuals.
##
## Action lifecycle:  plan_action() -> apply_hit() per hit -> finish_action()
## Damage is decided up front (so numbers can be shown per hit) but applied hit
## by hit, which means a target that dies mid-combo simply ignores later hits.
##
## Enemy turns: EnemyAI.decide() returns what an enemy wants to do (attack, use a
## skill, start charging, summon); the controller / simulator then calls
## begin_charge(), summon_minions() or plan_action() accordingly.

signal enemy_defeated(enemy: Combatant)
signal wave_spawned(index: int)

const MAX_ENEMIES_ALIVE := 4
const MAX_SUMMONED := 2

var stage: Dictionary = {}
var waves: Array = []
var wave_index := -1
var round_number := 0
var players: Array = []    # Array[Combatant]
var enemies: Array = []    # Array[Combatant] of the current wave (incl. summons)
var rng := RandomNumberGenerator.new()

# rewards accumulated during the battle
var xp_earned := 0
var gold_earned := 0
var items_earned: Dictionary = {}
var enemies_defeated := 0
var bosses_defeated := 0

# star objectives
var total_rounds := 0
var players_ko := 0
var bursts_used: Dictionary = {}     # uid -> count


func setup(stage_id: String, party_units: Array, seed_value: int = -1) -> void:
	stage = Database.get_stage(stage_id)
	waves = stage.get("waves", [])
	if seed_value >= 0:
		rng.seed = seed_value
	else:
		rng.randomize()
	players.clear()
	for i in party_units.size():
		players.append(Combatant.from_player_unit(party_units[i], i))
	_apply_team_bonuses()
	wave_index = -1
	advance_wave()


## Team passives (scope "allies") and the leader skill of the first hero.
func _apply_team_bonuses() -> void:
	for p in players:
		for e in p.def.get("passive", {}).get("effects", []):
			if e.get("scope", "self") == "allies":
				for ally in players:
					ally.apply_aura(e)
	if players.is_empty():
		return
	for e in players[0].def.get("leader_skill", {}).get("effects", []):
		for ally in players:
			if e.has("element") and e["element"] != ally.element:
				continue
			if e.has("stat"):
				ally.apply_stat_bonus(e["stat"], float(e.get("value", 0.0)))
			elif e.has("kind"):
				ally.apply_aura(e)


func leader_element() -> String:
	return players[0].element if not players.is_empty() else "fire"


# ------------------------------------------------------------------ waves
func wave_count() -> int:
	return waves.size()


func has_next_wave() -> bool:
	return wave_index + 1 < waves.size()


func advance_wave() -> Array:
	wave_index += 1
	enemies.clear()
	if wave_index > 0:
		_wave_recovery()
	if wave_index >= waves.size():
		return enemies
	var spawns: Array = waves[wave_index]
	for i in spawns.size():
		var spawn: Dictionary = spawns[i]
		var enemy_id: String = spawn.get("enemy", "")
		if spawn.has("enemy_by_leader_element"):
			enemy_id = spawn["enemy_by_leader_element"].get(leader_element(), enemy_id)
		if Database.get_enemy(enemy_id).is_empty():
			push_error("Stage %s references unknown enemy '%s'" % [stage.get("id", "?"), enemy_id])
			continue
		enemies.append(Combatant.from_enemy(enemy_id, int(spawn.get("level", 1)), i, float(spawn.get("hp_scale", 1.0))))
	round_number = 0
	start_player_phase()
	wave_spawned.emit(wave_index)
	return enemies


## Survivors catch their breath between waves (percent of max HP).
func _wave_recovery() -> void:
	var pct := float(Database.balance("combat", "wave_recovery_percent", 0.0))
	for p in alive(players):
		p.statuses = p.statuses.filter(func(s): return not Database.get_status(s["id"]).get("negative", false))
		p.statuses_changed.emit()
		if pct > 0.0:
			p.heal(int(round(p.max_hp * pct)))


# ------------------------------------------------------------------ turn flow
func start_player_phase() -> void:
	round_number += 1
	total_rounds += 1
	for p in players:
		p.acted = not p.is_alive()
		p.guarding = false


func players_can_act() -> bool:
	for p in players:
		if p.can_act():
			return true
	return false


func first_ready_player() -> Combatant:
	for p in players:
		if p.can_act():
			return p
	return null


func alive(list: Array) -> Array:
	return list.filter(func(c): return c.is_alive())


func all_enemies_dead() -> bool:
	return alive(enemies).is_empty()


func all_players_dead() -> bool:
	return alive(players).is_empty()


## Enemies act in speed order (ties keep formation order).
func enemy_turn_order() -> Array:
	var order := alive(enemies)
	order.sort_custom(func(a, b): return a.get_stat("spd") > b.get_stat("spd") or \
		(a.get_stat("spd") == b.get_stat("spd") and a.slot < b.slot))
	return order


## End-of-round statuses. Returns [{unit, type: dot|hot, status, amount}] events to apply.
func end_round() -> Array:
	var events: Array = []
	for c in alive(players) + alive(enemies):
		for e in c.tick_statuses():
			events.append({"unit": c, "type": e["type"], "status": e["status"], "amount": e["amount"]})
	return events


func apply_dot(unit: Combatant, amount: int) -> int:
	var dealt := unit.take_damage(amount)
	_check_death(unit)
	return dealt


func apply_hot(unit: Combatant, amount: int) -> int:
	return unit.heal(amount)


# ------------------------------------------------------------------ actions
func allies_of(c: Combatant) -> Array:
	return players if c.is_player else enemies


func foes_of(c: Combatant) -> Array:
	return enemies if c.is_player else players


func gain_burst(unit: Combatant, amount: float) -> void:
	unit.add_burst(amount * unit.burst_gain_mult)


func guard(unit: Combatant) -> void:
	unit.guarding = true
	unit.acted = true
	gain_burst(unit, float(Database.balance("burst", "gain_guard", 15)))


## Builds the full plan for a skill. `use_burst` consumes the Burst gauge.
func plan_action(user: Combatant, skill_id: String, target: Combatant, use_burst := false) -> Dictionary:
	var skill := user.skill_data(skill_id)
	var plan := {"skill_id": skill_id, "skill": skill, "user": user, "targets": [], "is_burst": use_burst,
				 "ally_target": null}
	if use_burst:
		user.reset_burst()
		if user.is_player:
			bursts_used[user.uid] = int(bursts_used.get(user.uid, 0)) + 1
	user.last_action = skill_id
	var foes := foes_of(user)
	match skill.get("target", "enemy_single"):
		"enemy_single":
			if target == null or not target.is_alive() or not foes.has(target):
				var living := alive(foes)
				target = living[rng.randi_range(0, living.size() - 1)] if not living.is_empty() else null
			if target:
				plan["targets"].append(_plan_target(user, target, skill))
		"enemy_all":
			for f in alive(foes):
				plan["targets"].append(_plan_target(user, f, skill))
		"ally_lowest":
			var allies := alive(allies_of(user))
			allies.sort_custom(func(a, b): return a.hp_ratio() < b.hp_ratio())
			plan["ally_target"] = allies[0] if not allies.is_empty() else user
		_:
			pass  # ally_all / self: resolved in finish_action
	return plan


func _plan_target(user: Combatant, target: Combatant, skill: Dictionary) -> Dictionary:
	var dmg := DamageCalculator.calculate(user, target, skill, rng)
	return {"unit": target, "hits": dmg["hits"], "crit": dmg["crit"], "tag": dmg["tag"],
			"total": dmg["total"], "dealt": 0, "absorbed": 0, "landed": false, "burst_given": false}


## Applies one hit of a planned action. Returns {dealt, absorbed, killed, skipped}.
func apply_hit(plan: Dictionary, target_index: int, hit_index: int) -> Dictionary:
	var entry: Dictionary = plan["targets"][target_index]
	var unit: Combatant = entry["unit"]
	if not unit.is_alive() or hit_index >= entry["hits"].size():
		return {"dealt": 0, "absorbed": 0, "killed": false, "skipped": true}
	var dealt := unit.take_damage(int(entry["hits"][hit_index]))
	var absorbed := unit.last_absorbed
	entry["dealt"] = int(entry["dealt"]) + dealt
	entry["absorbed"] = int(entry["absorbed"]) + absorbed
	entry["landed"] = true
	if unit.is_player and (dealt > 0 or absorbed > 0) and not entry["burst_given"]:
		gain_burst(unit, float(Database.balance("burst", "gain_damaged", 6)))
		entry["burst_given"] = true
	var killed := _check_death(unit)
	return {"dealt": dealt, "absorbed": absorbed, "killed": killed, "skipped": false}


## Bookkeeping when a unit reaches 0 HP. Returns true if it is dead.
func _check_death(unit: Combatant) -> bool:
	if unit.is_alive():
		return false
	if unit.get_meta("counted", false):
		return true
	unit.set_meta("counted", true)
	if unit.is_player:
		players_ko += 1
	else:
		_on_enemy_killed(unit)
	return true


## Applies after-effects (statuses, heals, shields, buffs), burst gain and marks
## the user as having acted. Returns a list of events for the view to display.
func finish_action(plan: Dictionary) -> Array:
	var user: Combatant = plan["user"]
	var skill: Dictionary = plan["skill"]
	var events: Array = []
	for effect in skill.get("effects", []):
		var recipients: Array = []
		match effect.get("on", "target"):
			"target":
				for entry in plan["targets"]:
					if entry["unit"].is_alive() and entry.get("landed", false):
						recipients.append(entry["unit"])
			"allies":
				recipients = alive(allies_of(user))
			"foes":
				recipients = alive(foes_of(user))
			"target_ally":
				var t = plan.get("ally_target")
				if t != null and t.is_alive():
					recipients = [t]
			"self":
				if user.is_alive():
					recipients = [user]
		for r in recipients:
			match effect.get("type", ""):
				"heal":
					var healed: int = r.heal(DamageCalculator.heal_amount(user, r, effect))
					events.append({"type": "heal", "unit": r, "amount": healed})
				"cleanse":
					for sid in r.cleanse(int(effect.get("count", 1))):
						events.append({"type": "cleanse", "unit": r, "status": sid})
				"status":
					if rng.randf() < float(effect.get("chance", 1.0)):
						r.add_status(effect["status"], float(effect.get("value", 0.0)), int(effect.get("duration", 1)))
						events.append({"type": "status", "unit": r, "status": effect["status"]})
				"shield":
					var amount := int(round(user.max_hp * float(effect.get("percent_caster_hp", 0.1))))
					r.add_shield(amount, int(effect.get("duration", 2)))
					events.append({"type": "shield", "unit": r, "amount": amount})
				"burst":
					if r != user:
						r.add_burst(float(effect.get("value", 0.0)))
						events.append({"type": "burst", "unit": r, "amount": int(effect.get("value", 0.0))})
	if user.is_player and not plan["is_burst"] and user.is_alive():
		gain_burst(user, float(Database.balance("burst", "gain_attack", 34)))
	user.acted = true
	return events


## Resolves an action instantly (used by tests and the balance simulator).
func resolve_instant(plan: Dictionary) -> Array:
	for ti in plan["targets"].size():
		for hi in plan["targets"][ti]["hits"].size():
			apply_hit(plan, ti, hi)
	return finish_action(plan)


# ------------------------------------------------------------------ enemy mechanics
## Starts a telegraphed attack: the enemy spends this turn charging and releases
## `skill_id` on its next action (the player sees a warning and can Guard).
func begin_charge(enemy: Combatant, skill_id: String) -> void:
	enemy.charging_skill = skill_id
	enemy.add_status("charging", 1.0, 9)
	enemy.acted = true


## Boss phase 2 (once, below the HP threshold). Returns the phase2 data or {}.
func check_phase2(enemy: Combatant) -> Dictionary:
	var p2: Dictionary = enemy.def.get("ai", {}).get("phase2", {})
	if p2.is_empty() or enemy.phase2 or not enemy.is_alive() or enemy.hp_ratio() > float(p2.get("below", 0.5)):
		return {}
	enemy.phase2 = true
	enemy.enrage = float(p2.get("atk_up", 0.0))
	enemy.pattern_index = 0
	if p2.has("skill"):
		enemy.pending_skill = p2["skill"]
	return p2


## Spawns the boss's minions into free formation slots. Returns the new combatants.
func summon_minions(boss: Combatant) -> Array:
	var sm: Dictionary = boss.def.get("ai", {}).get("summon", {})
	var out: Array = []
	if sm.is_empty() or Database.get_enemy(sm.get("enemy", "")).is_empty():
		return out
	var used_idx := {}
	for e in alive(enemies):
		if e.summoned:
			used_idx[e.summon_index] = true
	for i in int(sm.get("count", 1)):
		if not can_summon(boss):
			break
		var idx := 0
		while used_idx.has(idx):
			idx += 1
		used_idx[idx] = true
		var lvl := maxi(1, boss.level + int(sm.get("level_offset", -2)))
		var c := Combatant.from_enemy(sm["enemy"], lvl, _free_slot(), 1.0)
		c.summoned = true
		c.summon_index = idx
		c.acted = true
		enemies.append(c)
		out.append(c)
	boss.acted = true
	return out


func can_summon(boss: Combatant) -> bool:
	var sm: Dictionary = boss.def.get("ai", {}).get("summon", {})
	if sm.is_empty():
		return false
	var minions := 0
	for e in alive(enemies):
		if e.summoned:
			minions += 1
	return minions < mini(int(sm.get("max", MAX_SUMMONED)), MAX_SUMMONED) and alive(enemies).size() < MAX_ENEMIES_ALIVE


func _free_slot() -> int:
	var used := {}
	for e in enemies:
		used[e.slot] = true
	var s := 0
	while used.has(s):
		s += 1
	return s


# ------------------------------------------------------------------ rewards
func _on_enemy_killed(enemy: Combatant) -> void:
	enemies_defeated += 1
	if enemy.is_boss:
		bosses_defeated += 1
	var xp := Progression.enemy_xp(enemy.def, enemy.level)
	var loot := Progression.roll_enemy_loot(enemy.def, enemy.level, rng)
	if enemy.summoned:
		# summoned minions give a little XP / Gold but no item drops (no farming a boss forever)
		xp = int(xp / 2)
		loot["gold"] = int(int(loot["gold"]) / 2)
		loot["items"] = {}
	xp_earned += xp
	gold_earned += int(loot["gold"])
	for item_id in loot["items"].keys():
		items_earned[item_id] = int(items_earned.get(item_id, 0)) + int(loot["items"][item_id])
	enemy_defeated.emit(enemy)


func total_bursts() -> int:
	var n := 0
	for k in bursts_used.keys():
		n += int(bursts_used[k])
	return n


## Evaluates the stage's three star objectives for this run.
func evaluate_stars() -> Array:
	var out: Array = []
	for obj in stage.get("stars", [{"type": "clear"}]):
		match obj.get("type", "clear"):
			"clear":
				out.append(true)
			"no_ko":
				out.append(players_ko == 0)
			"turns":
				out.append(total_rounds <= int(obj.get("max", 99)))
			"burst":
				out.append(total_bursts() >= int(obj.get("min", 1)))
			_:
				out.append(false)
	while out.size() < 3:
		out.append(false)
	return out


## Rolls the stage's own drop list (on top of enemy drops) once, on victory.
func roll_stage_drops() -> Dictionary:
	var drops := Progression.roll_table({"rolls": stage.get("drops", [])}, rng)
	for item_id in drops.keys():
		items_earned[item_id] = int(items_earned.get(item_id, 0)) + int(drops[item_id])
	return drops


## Everything GameManager.apply_battle_result() needs after a win.
func victory_data() -> Dictionary:
	return {"xp": xp_earned, "gold": gold_earned, "items": items_earned.duplicate(), "stars": evaluate_stars(),
			"bursts": bursts_used.duplicate(), "enemies_defeated": enemies_defeated,
			"bosses_defeated": bosses_defeated, "rounds": total_rounds}
