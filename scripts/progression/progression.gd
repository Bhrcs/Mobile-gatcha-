class_name Progression
extends RefCounted
## Pure progression maths: XP curves, stat growth, enemy scaling, loot rolls.
## Kept free of scene/UI code so it can be unit tested and reused.

const STAT_KEYS := ["hp", "atk", "def", "rec", "spd"]


# ------------------------------------------------------------------ unit XP
## XP required to go from `level` to `level + 1`.
static func xp_to_next(level: int) -> int:
	var curve: Dictionary = Database.progression.get("unit_xp_curve", {})
	var base := float(curve.get("base", 50))
	var expo := float(curve.get("exponent", 1.5))
	return int(round(base * pow(max(level, 1), expo)))


static func rank_xp_to_next(rank: int) -> int:
	var curve: Dictionary = Database.progression.get("rank_xp_curve", {})
	return int(round(float(curve.get("base", 60)) * pow(max(rank, 1), float(curve.get("exponent", 1.35)))))


## Stats of a character definition at a level (before battle buffs).
static func unit_stats(char_def: Dictionary, level: int) -> Dictionary:
	var base: Dictionary = char_def.get("base_stats", {})
	var growth: Dictionary = char_def.get("growth", {})
	var out := {}
	for key in STAT_KEYS:
		out[key] = int(base.get(key, 0)) + int(growth.get(key, 0)) * (max(level, 1) - 1)
	return out


## Adds XP to a saved unit state {level, exp}. Returns an array of level-up
## records: [{level, gains: {hp, atk, def, rec}}] (empty if no level gained).
static func add_unit_xp(unit_state: Dictionary, amount: int) -> Array:
	var char_def := Database.get_character(unit_state.get("char_id", ""))
	var max_level := int(char_def.get("max_level", 20))
	var level_ups: Array = []
	unit_state["exp"] = int(unit_state.get("exp", 0)) + max(amount, 0)
	while int(unit_state["level"]) < max_level and int(unit_state["exp"]) >= xp_to_next(int(unit_state["level"])):
		unit_state["exp"] = int(unit_state["exp"]) - xp_to_next(int(unit_state["level"]))
		var before := unit_stats(char_def, int(unit_state["level"]))
		unit_state["level"] = int(unit_state["level"]) + 1
		var after := unit_stats(char_def, int(unit_state["level"]))
		var gains := {}
		for key in ["hp", "atk", "def", "rec"]:
			gains[key] = after[key] - before[key]
		level_ups.append({"level": unit_state["level"], "gains": gains})
	if int(unit_state["level"]) >= max_level:
		unit_state["exp"] = 0
	return level_ups


## Gold needed to instantly train a unit to its next level.
static func train_cost(unit_state: Dictionary) -> int:
	var remaining: int = xp_to_next(int(unit_state.get("level", 1))) - int(unit_state.get("exp", 0))
	return int(ceil(max(remaining, 1) * float(Database.progression.get("train_gold_per_xp", 1.5))))


# ------------------------------------------------------------------ enemies
## Enemy stats for a species at a level, with optional per-stage multipliers.
static func enemy_stats(enemy_def: Dictionary, level: int, hp_scale: float = 1.0) -> Dictionary:
	var base: Dictionary = enemy_def.get("base_stats", {})
	var sc: Dictionary = Database.progression.get("enemy_scaling", {})
	var l := float(max(level, 1) - 1)
	return {
		"hp": int(round(float(base.get("hp", 100)) * (1.0 + float(sc.get("hp", 0.22)) * l) * hp_scale)),
		"atk": int(round(float(base.get("atk", 30)) * (1.0 + float(sc.get("atk", 0.14)) * l))),
		"def": int(round(float(base.get("def", 20)) * (1.0 + float(sc.get("def", 0.1)) * l))),
		"rec": 0,
		"spd": int(round(float(base.get("spd", 40)) * (1.0 + float(sc.get("spd", 0.03)) * l))),
	}


static func enemy_xp(enemy_def: Dictionary, level: int) -> int:
	var sc: Dictionary = Database.progression.get("enemy_scaling", {})
	var base := float(enemy_def.get("rewards", {}).get("xp", 10))
	return int(round(base * (1.0 + float(sc.get("xp", 1.0)) * (max(level, 1) - 1))))


## Rolls gold + item drops for a defeated enemy. `drop_table` may be a table id
## (data/drop_tables.json), an inline table {guaranteed, rolls} or a legacy list.
static func roll_enemy_loot(enemy_def: Dictionary, level: int, rng: RandomNumberGenerator) -> Dictionary:
	var sc: Dictionary = Database.progression.get("enemy_scaling", {})
	var gold_range: Array = enemy_def.get("rewards", {}).get("gold", [5, 10])
	var gold := rng.randi_range(int(gold_range[0]), int(gold_range[1]))
	gold = int(round(gold * (1.0 + float(sc.get("gold", 0.35)) * (max(level, 1) - 1))))
	return {"gold": gold, "items": roll_table(enemy_def.get("drop_table", []), rng)}


## Resolves a drop table reference into {guaranteed: [...], rolls: [...]}.
static func resolve_table(table: Variant) -> Dictionary:
	if table is String:
		return Database.drop_tables.get(table, {})
	if table is Array:
		return {"rolls": table}
	if table is Dictionary:
		return table
	return {}


## Rolls a drop table. Guaranteed entries always drop; roll entries use their chance.
static func roll_table(table: Variant, rng: RandomNumberGenerator) -> Dictionary:
	var t := resolve_table(table)
	var drops := {}
	for entry in t.get("guaranteed", []):
		var q := rng.randi_range(int(entry.get("min", 1)), int(entry.get("max", 1)))
		drops[entry["item"]] = int(drops.get(entry["item"], 0)) + q
	for entry in t.get("rolls", []):
		if rng.randf() < float(entry.get("chance", 0.0)):
			var qty := rng.randi_range(int(entry.get("min", 1)), int(entry.get("max", 1)))
			drops[entry["item"]] = int(drops.get(entry["item"], 0)) + qty
	return drops


## Every item a table can drop (for "Obtained From" and "Possible drops").
static func table_items(table: Variant) -> Array:
	var t := resolve_table(table)
	var out: Array = []
	for key in ["guaranteed", "rolls"]:
		for entry in t.get(key, []):
			if not out.has(entry["item"]):
				out.append(entry["item"])
	return out


# ------------------------------------------------------------------ training
## EXP a training item grants to a hero (matching element gives a bonus).
static func item_xp(item_id: String, char_def: Dictionary) -> int:
	var it := Database.get_item(item_id)
	var xp := int(it.get("xp", 0))
	if xp > 0 and it.get("element", "") != "" and it.get("element", "") == char_def.get("element", ""):
		xp = int(round(xp * (1.0 + float(Database.balance("training", "element_bonus", 0.5)))))
	return xp


static func training_gold(xp: int) -> int:
	return int(ceil(xp * float(Database.balance("training", "gold_per_xp", 0.5))))


## Total EXP needed to reach the level cap from the unit's current state.
static func xp_to_cap(unit_state: Dictionary) -> int:
	var def := Database.get_character(unit_state.get("char_id", ""))
	var lvl := int(unit_state.get("level", 1))
	var total := -int(unit_state.get("exp", 0))
	for l in range(lvl, int(def.get("max_level", 20))):
		total += xp_to_next(l)
	return max(total, 0)


# ------------------------------------------------------------------ burst levels
static func burst_level_for_xp(xp: int) -> int:
	var steps: Array = Database.balance("burst_levels", "xp", [0, 4, 10, 18, 30])
	var lvl := 1
	for i in steps.size():
		if xp >= int(steps[i]):
			lvl = i + 1
	return clampi(lvl, 1, int(Database.balance("burst_levels", "max", 5)))


static func burst_xp_for_level(level: int) -> int:
	var steps: Array = Database.balance("burst_levels", "xp", [0, 4, 10, 18, 30])
	return int(steps[clampi(level - 1, 0, steps.size() - 1)])


## Returns a copy of a Burst skill with its per-level bonuses applied.
## level_bonus keys: power (+x per level), heal (+x to heal percent), value (+x to status values),
## shield (+x to shield percent), chance (+x to status chance), gauge (-x Burst cost per level),
## burst (+x to burst gain), duration_at ([levels] that add +1 turn).
static func scaled_burst(skill: Dictionary, level: int) -> Dictionary:
	var s := skill.duplicate(true)
	var n := maxi(level - 1, 0)
	if n == 0:
		return s
	var b: Dictionary = skill.get("level_bonus", {})
	if b.has("power") and float(s.get("power", 0.0)) > 0.0:
		s["power"] = float(s["power"]) * (1.0 + float(b["power"]) * n)
	var extra_turns := 0
	for at in b.get("duration_at", []):
		if level >= int(at):
			extra_turns += 1
	for e in s.get("effects", []):
		match e.get("type", ""):
			"heal":
				e["percent_max_hp"] = float(e.get("percent_max_hp", 0.0)) + float(b.get("heal", 0.0)) * n
			"shield":
				e["percent_caster_hp"] = float(e.get("percent_caster_hp", 0.0)) + float(b.get("shield", 0.0)) * n
			"burst":
				e["value"] = float(e.get("value", 0.0)) + float(b.get("burst", 0.0)) * n
			"status":
				if e.has("value") and float(e.get("value", 0.0)) > 0.0 and e.get("status", "") != "taunt":
					e["value"] = float(e["value"]) + float(b.get("value", 0.0)) * n
				e["chance"] = minf(1.0, float(e.get("chance", 1.0)) + float(b.get("chance", 0.0)) * n)
				e["duration"] = int(e.get("duration", 1)) + extra_turns
	return s


## Burst gauge needed at a Burst level (some Bursts get cheaper as they level).
static func burst_cost(skill: Dictionary, level: int) -> float:
	var base := float(Database.balance("burst", "max", 100))
	var g := float(skill.get("level_bonus", {}).get("gauge", 0.0))
	return maxf(60.0, base - g * max(level - 1, 0))


## Short human description of what the next Burst level improves.
static func burst_level_text(skill: Dictionary) -> String:
	var b: Dictionary = skill.get("level_bonus", {})
	var parts: Array = []
	if b.has("power"):
		parts.append("+%d%% damage" % int(round(float(b["power"]) * 100)))
	if b.has("heal"):
		parts.append("+%d%% healing" % int(round(float(b["heal"]) * 100)))
	if b.has("shield"):
		parts.append("+%d%% shield" % int(round(float(b["shield"]) * 100)))
	if b.has("value"):
		parts.append("stronger effects")
	if b.has("chance"):
		parts.append("+%d%% effect chance" % int(round(float(b["chance"]) * 100)))
	if b.has("burst"):
		parts.append("+%d Burst for allies" % int(b["burst"]))
	if b.has("gauge"):
		parts.append("-%d gauge cost" % int(b["gauge"]))
	if b.has("duration_at"):
		parts.append("+1 turn at Lv.%s" % "/".join(b["duration_at"].map(func(x): return str(int(x)))))
	return "Per level: " + ", ".join(parts) if not parts.is_empty() else ""


# ------------------------------------------------------------------ power
## Rough combat strength of a hero (informational only).
static func unit_power(unit_state: Dictionary) -> int:
	var def := Database.get_character(unit_state.get("char_id", ""))
	var st := unit_stats(def, int(unit_state.get("level", 1)))
	var w: Dictionary = Database.progression.get("power", {})
	var p := float(st["hp"]) * float(w.get("hp", 0.1)) + float(st["atk"]) * float(w.get("atk", 1.0)) \
			+ float(st["def"]) * float(w.get("def", 0.8)) + float(st["rec"]) * float(w.get("rec", 0.5))
	p *= 1.0 + float(w.get("burst_level", 0.03)) * (int(unit_state.get("burst_level", 1)) - 1)
	return int(round(p))
