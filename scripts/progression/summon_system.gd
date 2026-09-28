class_name SummonSystem
extends RefCounted
## Embergate summon rolls. Pure functions over banner data (data/summon.json) so the
## rates shown on the DETAILS screen are exactly the rates used by the roll.


## Rarity -> probability, normalised so the values always sum to 1.
static func rates(banner: Dictionary) -> Dictionary:
	var raw: Dictionary = banner.get("rates", {})
	var total := 0.0
	for k in raw:
		total += maxf(0.0, float(raw[k]))
	var out := {}
	if total <= 0.0:
		return {"3": 1.0}
	for k in raw:
		out[str(k)] = maxf(0.0, float(raw[k])) / total
	return out


## Pool members grouped by rarity: {"3": [ids], ...}. Unknown ids are skipped.
static func pool_by_rarity(banner: Dictionary) -> Dictionary:
	var out := {}
	for cid in banner.get("pool", []):
		var def := Database.get_character(str(cid))
		if def.is_empty():
			continue
		var r := str(int(def.get("rarity", 3)))
		if not out.has(r):
			out[r] = []
		out[r].append(str(cid))
	return out


## Per-hero chance (0..1) of each pool member on a single summon.
static func hero_rates(banner: Dictionary) -> Dictionary:
	var rr := rates(banner)
	var pool := pool_by_rarity(banner)
	var out := {}
	var norm := _available_weight(rr, pool)
	for r in pool:
		var ids: Array = pool[r]
		for cid in ids:
			out[cid] = float(rr.get(r, 0.0)) / norm / float(ids.size())
	return out


static func _available_weight(rr: Dictionary, pool: Dictionary) -> float:
	var s := 0.0
	for r in rr:
		if pool.has(r) and not pool[r].is_empty():
			s += float(rr[r])
	return s if s > 0.0 else 1.0


## Picks a rarity by banner rate (only rarities that have pool members), then a
## uniform pool member of that rarity. Returns "" only for an empty pool.
static func roll(banner: Dictionary, rng: RandomNumberGenerator) -> String:
	var rr := rates(banner)
	var pool := pool_by_rarity(banner)
	if pool.is_empty():
		return ""
	var keys: Array = rr.keys()
	keys.sort()
	var pick := rng.randf() * _available_weight(rr, pool)
	var chosen := ""
	for r in keys:
		if not pool.has(r) or pool[r].is_empty():
			continue
		chosen = r
		pick -= float(rr[r])
		if pick < 0.0:
			break
	if chosen == "":
		chosen = pool.keys()[0]
	var ids: Array = pool[chosen]
	return ids[rng.randi_range(0, ids.size() - 1)]
