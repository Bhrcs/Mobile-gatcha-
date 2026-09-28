class_name EnemyAI
extends RefCounted
## Readable, data-driven enemy behaviour. Each enemy's "ai" block picks a profile:
##
##   attacker  normal attack; special with `skill_chance`
##   healer    heals the most injured ally when someone is below 60% HP
##   tank      raises its shell (shield + provoke) every third turn
##   buffer    buffs allies when nobody is buffed yet
##   debuffer  curses the strongest hero (highest ATK) when they are not cursed yet
##   charger   every `charge_every` turns spends a turn CHARGING, then releases its special
##   boss      follows a `pattern` list: "normal", "charge", "curse", "heal";
##             optional `summon` {enemy, every, count, max}, `hp_events` [{below, skill}],
##             `phase2` {below, atk_up, pattern, announce, skill}
##
## Elites add `extra_every`: every Nth turn they use skills.extra.
## Targeting: "random" (Provoke-weighted), "lowest_hp", "highest_atk". A provoking
## hero always overrides smart targeting, so Guard + Provoke tanks stay reliable.
##
## decide() returns one of:
##   {type: "skill",  skill_id, target}       - normal attack or skill
##   {type: "charge", skill_id}               - start charging (telegraph)
##   {type: "summon"}                         - call minions


static func decide(enemy: Combatant, model: BattleModel) -> Dictionary:
	var ai: Dictionary = enemy.def.get("ai", {})
	var skills: Dictionary = enemy.def.get("skills", {})
	var foes: Array = model.foes_of(enemy)
	var rng := model.rng
	enemy.ai_turn += 1
	enemy.turns_since_summon += 1

	# 1) a charged attack is always released first
	if not enemy.charging_skill.is_empty():
		var s := enemy.charging_skill
		enemy.charging_skill = ""
		enemy.remove_status("charging")
		return _skill(enemy, s, foes, rng)
	# 2) queued reactions (phase 2 skill)
	if not enemy.pending_skill.is_empty():
		var p := enemy.pending_skill
		enemy.pending_skill = ""
		return _skill(enemy, p, foes, rng)
	# 3) one-time HP threshold reactions
	for i in ai.get("hp_events", []).size():
		var ev: Dictionary = ai["hp_events"][i]
		if not enemy.hp_events_done.has(i) and enemy.hp_ratio() < float(ev.get("below", 0.5)):
			enemy.hp_events_done.append(i)
			return _skill(enemy, ev["skill"], foes, rng)
	# 4) summons
	var sm: Dictionary = ai.get("summon", {})
	if not sm.is_empty() and enemy.turns_since_summon >= maxi(int(sm.get("every", 3)), 1) and model.can_summon(enemy):
		enemy.turns_since_summon = 0
		return {"type": "summon"}
	# 5) elite extra skill
	var extra_every := int(ai.get("extra_every", 0))
	if extra_every > 0 and skills.has("extra") and enemy.ai_turn % extra_every == 0:
		return _skill(enemy, skills["extra"], foes, rng)

	var special: String = enemy.special_skill
	match ai.get("profile", "attacker"):
		"boss":
			var pattern: Array = ai.get("pattern", ["normal"])
			if enemy.phase2:
				pattern = ai.get("phase2", {}).get("pattern", pattern)
			var step: String = pattern[enemy.pattern_index % pattern.size()] if not pattern.is_empty() else "normal"
			enemy.pattern_index += 1
			match step:
				"charge":
					if not special.is_empty():
						return {"type": "charge", "skill_id": special}
				"curse":
					if ai.has("curse"):
						return _skill(enemy, ai["curse"], foes, rng)
				"heal":
					if ai.has("heal") and _most_injured(model.allies_of(enemy)) != null:
						return _skill(enemy, ai["heal"], foes, rng)
		"charger":
			if not special.is_empty() and enemy.ai_turn % maxi(int(ai.get("charge_every", 3)), 1) == 0:
				return {"type": "charge", "skill_id": special}
		"healer":
			if not special.is_empty() and enemy.last_action != special and _most_injured(model.allies_of(enemy)) != null:
				return _skill(enemy, special, foes, rng)
		"tank":
			if not special.is_empty() and enemy.ai_turn % 3 == 1 and not enemy.has_status("taunt"):
				return _skill(enemy, special, foes, rng)
		"buffer":
			if not special.is_empty() and not _anyone_has(model.alive(model.allies_of(enemy)), "atk_up") \
					and rng.randf() < maxf(enemy.skill_chance, 0.5):
				return _skill(enemy, special, foes, rng)
		"debuffer":
			if not special.is_empty() and rng.randf() < enemy.skill_chance:
				return _skill(enemy, special, foes, rng)
		_:
			if not special.is_empty() and rng.randf() < enemy.skill_chance:
				return _skill(enemy, special, foes, rng)
	return _skill(enemy, enemy.normal_skill, foes, rng)


static func _skill(enemy: Combatant, skill_id: String, foes: Array, rng: RandomNumberGenerator) -> Dictionary:
	return {"type": "skill", "skill_id": skill_id, "target": choose_target(enemy, foes, rng, skill_id)}


static func _most_injured(allies: Array) -> Combatant:
	var best: Combatant = null
	for a in allies:
		if a.is_alive() and a.hp_ratio() < 0.6 and (best == null or a.hp_ratio() < best.hp_ratio()):
			best = a
	return best


static func _anyone_has(units: Array, status_id: String) -> bool:
	for u in units:
		if u.has_status(status_id):
			return true
	return false


## Legacy helper (tests / older callers): {skill_id, target}.
static func choose_action(enemy: Combatant, foes: Array, rng: RandomNumberGenerator) -> Dictionary:
	var skill_id := enemy.normal_skill
	if not enemy.special_skill.is_empty() and rng.randf() < enemy.skill_chance:
		skill_id = enemy.special_skill
	return {"skill_id": skill_id, "target": choose_target(enemy, foes, rng)}


static func choose_target(enemy: Combatant, foes: Array, rng: RandomNumberGenerator, skill_id := "") -> Combatant:
	var alive: Array = foes.filter(func(f): return f.is_alive())
	if alive.is_empty():
		return null
	for f in alive:
		if f.has_status("taunt"):
			return _weighted_random(alive, rng)
	var mode: String = enemy.def.get("ai", {}).get("targeting", "random")
	match mode:
		"lowest_hp":
			alive.sort_custom(func(a, b): return a.hp_ratio() < b.hp_ratio())
			return alive[0]
		"highest_atk":
			# prefer a strong hero that is not already cursed by this skill
			var st := ""
			for e in Database.get_skill(skill_id).get("effects", []):
				if e.get("type", "") == "status":
					st = e.get("status", "")
			alive.sort_custom(func(a, b): return a.get_stat("atk") > b.get_stat("atk"))
			for f in alive:
				if st.is_empty() or not f.has_status(st):
					return f
			return alive[0]
		_:
			return _weighted_random(alive, rng)


static func _weighted_random(alive: Array, rng: RandomNumberGenerator) -> Combatant:
	var total := 0.0
	for f in alive:
		total += f.taunt_weight()
	var roll := rng.randf() * total
	for f in alive:
		roll -= f.taunt_weight()
		if roll <= 0.0:
			return f
	return alive[alive.size() - 1]
