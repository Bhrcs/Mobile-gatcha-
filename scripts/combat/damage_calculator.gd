class_name DamageCalculator
extends RefCounted
## Damage formula (all knobs in data/progression.json -> "combat"):
##   raw       = ATK x skill power
##   mitigated = raw - DEF x def_factor          (never below raw x min_damage_ratio, never below 1)
##   final     = mitigated x element x crit x variance x (1 - damage reduction) x guard
## The total is then split across the skill's hits (optionally weighted).


## Returns {total, hits: Array[int], crit, element_mult, tag}
## tag is "", "WEAK" (strong element hit) or "RESIST".
static func calculate(attacker: Combatant, target: Combatant, skill: Dictionary,
		rng: RandomNumberGenerator) -> Dictionary:
	var cfg: Dictionary = Database.progression.get("combat", {})
	var power := float(skill.get("power", 1.0))
	var hits: int = max(1, int(skill.get("hits", 1)))

	var raw := attacker.get_stat("atk") * power
	var mitigated := raw - target.get_stat("def") * float(cfg.get("def_factor", 0.3))
	mitigated = max(mitigated, raw * float(cfg.get("min_damage_ratio", 0.1)), 1.0)

	var elem := Database.element_multiplier(attacker.element, target.element)
	var crit := rng.randf() < float(cfg.get("crit_chance", 0.05)) + attacker.crit_bonus
	var crit_mult := float(cfg.get("crit_multiplier", 1.5)) if crit else 1.0
	var variance := rng.randf_range(float(cfg.get("variance_min", 0.95)), float(cfg.get("variance_max", 1.05)))
	var reduction := (1.0 - target.damage_reduction()) * (1.0 - clampf(target.damage_taken_down, 0.0, 0.5))
	var guard := (1.0 - minf(float(cfg.get("guard_reduction", 0.5)) + target.guard_bonus, 0.8)) if target.guarding else 1.0
	var bonus := 1.0 + attacker.damage_bonus_vs(target)

	var total: int = max(hits, int(round(mitigated * elem * crit_mult * variance * reduction * guard * bonus)))
	var tag := ""
	if elem > 1.0:
		tag = "WEAK"
	elif elem < 1.0:
		tag = "RESIST"
	return {"total": total, "hits": split_hits(total, hits, skill.get("hit_weights", [])),
			"crit": crit, "element_mult": elem, "tag": tag}


## Splits a total across hits using optional weights. Always sums to total,
## every hit deals at least 1.
static func split_hits(total: int, hits: int, weights: Array = []) -> Array:
	var w: Array = []
	for i in hits:
		w.append(float(weights[i]) if i < weights.size() else 1.0)
	var wsum := 0.0
	for x in w:
		wsum += x
	var out: Array = []
	var assigned := 0
	for i in hits:
		var v := int(floor(total * w[i] / wsum))
		v = max(v, 1)
		out.append(v)
		assigned += v
	# put rounding remainder on the final hit
	out[hits - 1] = max(1, int(out[hits - 1]) + (total - assigned))
	return out


## Healing: percent of target max HP + caster REC x multiplier.
static func heal_amount(caster: Combatant, target: Combatant, effect: Dictionary) -> int:
	var amount := target.max_hp * float(effect.get("percent_max_hp", 0.0)) \
			+ caster.get_stat("rec") * float(effect.get("rec_multiplier", 0.0))
	return max(1, int(round(amount * (1.0 + target.heal_received_up))))
