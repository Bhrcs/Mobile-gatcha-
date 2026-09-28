extends Node
## GameManager (autoload)
## Owns the live player profile and every progression rule that changes it:
## gold/gems/soul shards, energy (with offline regeneration), rank, heroes,
## squad + leader, training, Burst levels, evolution, summoning, stage/tower
## progress, stars, feature unlocks, missions and login rewards.
## Every change that should persist calls save().

signal profile_changed
signal gold_changed(new_amount: int)
signal gems_changed(new_amount: int)
signal energy_changed(current: int, maximum: int)
signal settings_changed

var profile: Dictionary = {}
var settings: Dictionary = {}
var current_stage_id := ""          # stage the next battle scene should load
var last_unlocked_stage := ""       # used by stage select to highlight new stages
var rng := RandomNumberGenerator.new()
## Test hook: when >= 0 this replaces the system clock (unix seconds).
var clock_override := -1.0
## Notes from a save migration, shown once on the home screen.
var pending_migration_notes: Array = []

var _play_accum := 0.0
var _energy_tick := 0.0


func _ready() -> void:
	get_tree().auto_accept_quit = false     # close requests go through quit_game() for a clean shutdown
	rng.randomize()
	settings = SaveManager.load_settings()
	get_tree().root.theme = UIKit.build_theme()
	apply_settings()
	if OS.get_cmdline_user_args().has("--selftest"):
		_selftest.call_deferred()


func _process(delta: float) -> void:
	if not has_profile():
		return
	_play_accum += delta
	if _play_accum >= 1.0:
		var whole := int(_play_accum)
		_play_accum -= whole
		profile["player"]["play_seconds"] = int(profile["player"].get("play_seconds", 0)) + whole
	_energy_tick += delta
	if _energy_tick >= 1.0:
		_energy_tick = 0.0
		var before := int(profile["player"].get("energy", 0))
		var cur := energy()
		if cur != before:
			energy_changed.emit(cur, max_energy())


func _exit_tree() -> void:
	# release static caches so the engine shuts down cleanly
	UIKit._theme = null
	UIKit._font = null
	SpriteFactory._frames_cache.clear()
	SpriteFactory._effect_cache.clear()
	BattleUnitView.clear_cache()
	get_tree().root.theme = null


## `Cinderbound.exe -- --selftest` prints a data/asset check and exits (useful for builds).
func _selftest() -> void:
	var ok := Database.load_errors.is_empty() and Database.starter_ids().size() == 3 \
			and Database.stage_order.size() == 20 and Database.towers.size() == 3 and UIKit.font() != null
	for c in Database.characters.values():
		ok = ok and Database.load_texture(c["sprite"]["sheet"]) != null and Database.load_texture(c["portrait"]) != null
	for e in Database.enemies.values():
		ok = ok and Database.load_texture(e["sprite"]["sheet"]) != null
	print("SELFTEST %s characters=%d enemies=%d skills=%d stages=%d towers=%d items=%d errors=%s" % [
		"OK" if ok else "FAILED", Database.characters.size(), Database.enemies.size(), Database.skills.size(),
		Database.stage_order.size(), Database.towers.size(), Database.items.size(), Database.load_errors])
	quit_game(0 if ok else 1)


## Clean shutdown: stop audio and let the audio thread release its streams
## before the engine exits (avoids leaked-playback warnings in the log).
var _quitting := false


func quit_game(code := 0) -> void:
	if _quitting:
		return
	_quitting = true
	if has_profile():
		save()
	# callers may still be inside a scene's _ready (the tree is busy adding it)
	await get_tree().process_frame
	# freeze gameplay (battles keep firing sounds and timers otherwise), drop the
	# current scene, then silence audio and give the audio thread time to let go
	# let a running battle action finish so no coroutine is left waiting on a
	# tween or timer of a freed node (those would leak at exit)
	var cs := get_tree().current_scene
	if cs is BattleController:
		cs.prepare_quit()
		var waited := 0.0
		while is_instance_valid(cs) and not cs.is_idle() and waited < 8.0:
			await get_tree().process_frame
			waited += get_process_delta_time()
	AudioManager.shutdown()
	if get_tree().current_scene:
		get_tree().unload_current_scene()
	Engine.time_scale = 1.0
	for i in 6:
		await get_tree().process_frame
	await get_tree().create_timer(0.5, true, false, true).timeout
	AudioManager.shutdown()
	await get_tree().create_timer(0.1, true, false, true).timeout
	get_tree().quit(code)


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		quit_game(0)


func now() -> float:
	return clock_override if clock_override >= 0.0 else Time.get_unix_time_from_system()


# ------------------------------------------------------------------ profile lifecycle
func has_profile() -> bool:
	return not profile.is_empty() and not profile.get("starter_id", "").is_empty()


func can_continue() -> bool:
	if has_profile():
		return true
	var p := SaveManager.load_profile()
	return not p.is_empty() and not p.get("starter_id", "").is_empty()


## Starts a fresh profile owning only the chosen starter, and saves it.
func new_game(starter_id: String) -> void:
	assert(Database.has_character(starter_id), "Unknown starter " + starter_id)
	SaveManager.delete_profile()
	profile = SaveManager.default_profile()
	profile["starter_id"] = starter_id
	profile["player"]["created"] = int(now())
	profile["player"]["energy"] = max_energy()
	profile["player"]["energy_ts"] = int(now())
	var uid := _add_unit(starter_id, false)
	profile["party"] = [uid]
	profile["stages"]["unlocked"] = [Database.stage_order[0]] if not Database.stage_order.is_empty() else []
	for item_id in Database.progression.get("starting_items", {}).keys():
		add_item(item_id, int(Database.progression["starting_items"][item_id]), false)
	save()
	profile_changed.emit()


func continue_game() -> bool:
	var p := SaveManager.load_profile()
	if p.is_empty() or p.get("starter_id", "").is_empty():
		return false
	profile = p
	pending_migration_notes = Array(SaveManager.migration_notes)
	if int(profile["player"].get("energy_ts", 0)) <= 0:
		profile["player"]["energy_ts"] = int(now())
	_grant_retroactive_unlocks()
	energy()
	profile_changed.emit()
	gold_changed.emit(gold())
	gems_changed.emit(gems())
	return true


func save() -> void:
	if not profile.is_empty():
		SaveManager.save_profile(profile)


# ------------------------------------------------------------------ units
func _add_unit(char_id: String, mark_new := true) -> String:
	var uid := "u%d" % int(profile.get("next_uid", 1))
	profile["next_uid"] = int(profile.get("next_uid", 1)) + 1
	var def := Database.get_character(char_id)
	profile["units"].append({"uid": uid, "char_id": char_id, "level": int(def.get("level", 1)),
							 "exp": int(def.get("experience", 0)), "burst_level": 1, "burst_xp": 0,
							 "locked": false, "favorite": false, "new": mark_new, "obtained": int(now())})
	var fam: String = def.get("family", char_id)
	if not profile.has("codex"):
		profile["codex"] = []
	if not profile["codex"].has(fam):
		profile["codex"].append(fam)
	return uid


func owned_units() -> Array:
	return profile.get("units", [])


func get_unit(uid: String) -> Dictionary:
	for u in owned_units():
		if u["uid"] == uid:
			return u
	return {}


func owns_family(family: String) -> bool:
	for u in owned_units():
		if Database.get_character(u["char_id"]).get("family", "") == family:
			return true
	return false


func unit_of_family(family: String) -> Dictionary:
	for u in owned_units():
		if Database.get_character(u["char_id"]).get("family", "") == family:
			return u
	return {}


func mark_unit_seen(uid: String) -> void:
	var u := get_unit(uid)
	if not u.is_empty() and bool(u.get("new", false)):
		u["new"] = false
		save()


func set_unit_flag(uid: String, flag: String, on: bool) -> void:
	var u := get_unit(uid)
	if u.is_empty() or not flag in ["locked", "favorite"]:
		return
	u[flag] = on
	save()
	profile_changed.emit()


func unit_stats(unit: Dictionary) -> Dictionary:
	return Progression.unit_stats(Database.get_character(unit.get("char_id", "")), int(unit.get("level", 1)))


func unit_power(unit: Dictionary) -> int:
	return Progression.unit_power(unit)


func squad_power() -> int:
	var total := 0
	for u in party_units():
		total += unit_power(u)
	return total


# ------------------------------------------------------------------ squad
func party_uids() -> Array:
	return profile.get("party", [])


func party_units() -> Array:
	var out: Array = []
	for uid in party_uids():
		var u := get_unit(uid)
		if not u.is_empty():
			out.append(u)
	return out


func max_party_size() -> int:
	return int(Database.progression.get("party_size", 5))


func is_in_party(uid: String) -> bool:
	return party_uids().has(uid)


## Adds/removes a unit from the party. The party can never become empty and a
## hero instance can only appear once.
func toggle_party(uid: String) -> bool:
	var party: Array = profile["party"]
	if party.has(uid):
		if party.size() <= 1:
			return false
		party.erase(uid)
	else:
		if party.size() >= max_party_size() or get_unit(uid).is_empty():
			return false
		party.append(uid)
	save()
	profile_changed.emit()
	return true


## Makes a party member the leader (slot 0). Returns false if the unit is not in the party.
func set_leader(uid: String) -> bool:
	var party: Array = profile.get("party", [])
	var i := party.find(uid)
	if i < 0:
		return false
	if i > 0:
		party.remove_at(i)
		party.insert(0, uid)
		save()
		profile_changed.emit()
	return true


## Swaps two party slots (used by the squad editor).
func swap_party_slots(a: int, b: int) -> bool:
	var party: Array = profile.get("party", [])
	if a < 0 or b < 0 or a >= party.size() or b >= party.size() or a == b:
		return false
	var t = party[a]
	party[a] = party[b]
	party[b] = t
	save()
	profile_changed.emit()
	return true


func leader_uid() -> String:
	var party := party_uids()
	return str(party[0]) if not party.is_empty() else ""


func leader_skill() -> Dictionary:
	var u := get_unit(leader_uid())
	return Database.get_character(u.get("char_id", "")).get("leader_skill", {}) if not u.is_empty() else {}


# ------------------------------------------------------------------ training
## Previews feeding training items to a hero. items: {item_id: qty}
func preview_training(uid: String, items: Dictionary) -> Dictionary:
	var unit := get_unit(uid)
	if unit.is_empty():
		return {}
	var def := Database.get_character(unit["char_id"])
	var xp := 0
	for item_id in items.keys():
		xp += Progression.item_xp(item_id, def) * int(items[item_id])
	var cap := Progression.xp_to_cap(unit)
	var used := mini(xp, cap)
	var sim := unit.duplicate()
	var ups := Progression.add_unit_xp(sim, used)
	var before := unit_stats(unit)
	var after := unit_stats(sim)
	var gains := {}
	for key in ["hp", "atk", "def", "rec"]:
		gains[key] = int(after[key]) - int(before[key])
	return {"xp": xp, "used_xp": used, "wasted_xp": xp - used, "gold": Progression.training_gold(used),
			"level_before": int(unit["level"]), "level_after": int(sim["level"]), "exp_after": int(sim["exp"]),
			"gains": gains, "level_ups": ups.size(), "at_cap": cap <= 0}


## Feeds training items (XP material + Gold). Returns the preview dict with "ok".
func train_unit_with(uid: String, items: Dictionary) -> Dictionary:
	var pv := preview_training(uid, items)
	if pv.is_empty() or pv["at_cap"] or int(pv["xp"]) <= 0:
		return {"ok": false, "reason": "This hero is at max level." if not pv.is_empty() and pv["at_cap"] else "Choose training items."}
	for item_id in items.keys():
		if item_count(item_id) < int(items[item_id]):
			return {"ok": false, "reason": "Not enough %s." % Database.item_name(item_id)}
	if gold() < int(pv["gold"]):
		return {"ok": false, "reason": "Not enough Gold."}
	spend_gold(int(pv["gold"]), false)
	for item_id in items.keys():
		remove_item(item_id, int(items[item_id]), false)
	var unit := get_unit(uid)
	var ups := Progression.add_unit_xp(unit, int(pv["used_xp"]))
	track("train", 1, false)
	save()
	profile_changed.emit()
	pv["ok"] = true
	pv["level_ups_detail"] = ups
	return pv


## Legacy helper kept for tests/tools: trains one level using radiant wisps if owned, else fails.
func train_unit(uid: String) -> Dictionary:
	var unit := get_unit(uid)
	if unit.is_empty():
		return {}
	var def := Database.get_character(unit["char_id"])
	if int(unit["level"]) >= int(def.get("max_level", 20)):
		return {}
	var cost := Progression.train_cost(unit)
	if not spend_gold(cost):
		return {}
	var needed := Progression.xp_to_next(int(unit["level"])) - int(unit["exp"])
	var ups := Progression.add_unit_xp(unit, needed)
	save()
	profile_changed.emit()
	return ups[0] if not ups.is_empty() else {}


# ------------------------------------------------------------------ burst levels
func add_burst_xp(uid: String, amount: int, persist := true) -> Dictionary:
	var u := get_unit(uid)
	if u.is_empty() or amount <= 0:
		return {}
	var before := int(u.get("burst_level", 1))
	var cap_xp := Progression.burst_xp_for_level(int(Database.balance("burst_levels", "max", 5)))
	u["burst_xp"] = mini(int(u.get("burst_xp", 0)) + amount, cap_xp)
	u["burst_level"] = Progression.burst_level_for_xp(int(u["burst_xp"]))
	if persist:
		save()
		profile_changed.emit()
	return {"before": before, "after": int(u["burst_level"])}


## Burst training: "sigil" uses a Spark Sigil, "shards" spends Soul Shards.
func train_burst(uid: String, method: String) -> Dictionary:
	var u := get_unit(uid)
	if u.is_empty():
		return {"ok": false, "reason": "Unknown hero."}
	if int(u.get("burst_level", 1)) >= int(Database.balance("burst_levels", "max", 5)):
		return {"ok": false, "reason": "Burst is already at max level."}
	var xp := 0
	if method == "sigil":
		if not remove_item("spark_sigil", 1, false):
			return {"ok": false, "reason": "No Spark Sigils."}
		xp = int(Database.get_item("spark_sigil").get("burst_xp", 3))
	else:
		var cost := int(Database.balance("burst_levels", "shards_per_step", 20))
		if soul_shards() < cost:
			return {"ok": false, "reason": "Need %d Soul Shards." % cost}
		profile["player"]["soul_shards"] = soul_shards() - cost
		xp = int(Database.balance("burst_levels", "shard_step_xp", 3))
	var r := add_burst_xp(uid, xp)
	r["ok"] = true
	r["xp"] = xp
	return r


# ------------------------------------------------------------------ evolution
## Checks an evolution. Returns {ok, into, gold, materials, missing, reasons}.
func evolution_status(uid: String) -> Dictionary:
	var u := get_unit(uid)
	if u.is_empty():
		return {"ok": false, "reasons": ["Unknown hero."]}
	var def := Database.get_character(u["char_id"])
	var evo = def.get("evolution")
	if not (evo is Dictionary):
		return {"ok": false, "final": true, "reasons": ["This is the hero's final form."]}
	var reasons: Array = []
	var missing := {}
	if not feature_unlocked("evolution"):
		reasons.append("Evolution unlocks after clearing %s." % feature_unlock_label("evolution"))
	if int(u["level"]) < int(def.get("max_level", 20)):
		reasons.append("Reach Lv.%d first." % int(def.get("max_level", 20)))
	for m in evo.get("materials", {}).keys():
		var need := int(evo["materials"][m])
		if item_count(m) < need:
			missing[m] = need - item_count(m)
	if not missing.is_empty():
		reasons.append("Missing materials.")
	if gold() < int(evo.get("gold", 0)):
		reasons.append("Need %s Gold." % UIKit.format_number(int(evo.get("gold", 0))))
	return {"ok": reasons.is_empty(), "into": evo.get("into", ""), "gold": int(evo.get("gold", 0)),
			"materials": evo.get("materials", {}), "missing": missing, "reasons": reasons}


func can_evolve(uid: String) -> bool:
	return bool(evolution_status(uid).get("ok", false))


## Evolves a hero into its next form (Lv.1, Burst level kept). Returns {ok, from, into}.
func evolve(uid: String) -> Dictionary:
	var st := evolution_status(uid)
	if not st.get("ok", false):
		return {"ok": false, "reasons": st.get("reasons", [])}
	var u := get_unit(uid)
	var from: String = u["char_id"]
	spend_gold(int(st["gold"]), false)
	for m in st["materials"].keys():
		remove_item(m, int(st["materials"][m]), false)
	u["char_id"] = st["into"]
	u["level"] = 1
	u["exp"] = 0
	save()
	profile_changed.emit()
	return {"ok": true, "from": from, "into": st["into"]}


## Where an item can be obtained: [{label, kind: stage|tower, id}] (story stages, tower floors, first clears).
func item_sources(item_id: String) -> Array:
	var out: Array = []
	for sid in Database.stages.keys():
		var st := Database.get_stage(sid)
		var found := false
		for d in st.get("drops", []):
			if d.get("item", "") == item_id:
				found = true
		if not found and not is_stage_cleared(sid) and st.get("first_clear", {}).get("items", {}).has(item_id):
			found = true
		if not found:
			for wave in st.get("waves", []):
				for sp in wave:
					var e := Database.get_enemy(sp.get("enemy", ""))
					if Progression.table_items(e.get("drop_table", [])).has(item_id):
						found = true
		if found:
			out.append({"id": sid, "kind": "tower" if Database.is_tower_stage(sid) else "stage",
						"label": stage_label(sid), "unlocked": is_stage_unlocked(sid),
						"order": _stage_sort_key(sid)})
	out.sort_custom(func(a, b): return (1 if a["unlocked"] else 0) > (1 if b["unlocked"] else 0) or \
		((a["unlocked"] == b["unlocked"]) and a["order"] < b["order"]))
	# rewards outside battle
	for kind in ["daily", "weekly"]:
		for m in Database.missions.get(kind, []):
			if m.get("reward", {}).get("items", {}).has(item_id):
				out.append({"id": "missions", "kind": "missions", "label": "%s Mission: %s" % [kind.capitalize(), m.get("text", "")],
							"unlocked": feature_unlocked("missions"), "order": 5000})
	if Database.missions.get("daily_chest", {}).get("reward", {}).get("items", {}).has(item_id):
		out.append({"id": "missions", "kind": "missions", "label": "Daily Mission Chest", "unlocked": feature_unlocked("missions"),
					"order": 5001})
	for d in Database.login_rewards.get("cycle", []):
		if d.get("reward", {}).get("items", {}).has(item_id):
			out.append({"id": "login", "kind": "login", "label": "Login Reward - Day %d" % int(d.get("day", 0)), "unlocked": true,
						"order": 6000})
	return out


func _stage_sort_key(sid: String) -> int:
	var st := Database.get_stage(sid)
	var w: String = st.get("world_id", "")
	if Database.towers.has(w):
		return 1000 + Database.tower_order.find(w) * 100 + int(st.get("number", 0))
	return Database.world_order.find(w) * 100 + int(st.get("number", 0))


## "Ashroot Wilds 1-6" / "Verdant Tower Floor 2"
func stage_label(sid: String) -> String:
	var st := Database.get_stage(sid)
	var w: String = st.get("world_id", "")
	if Database.towers.has(w):
		return "%s Floor %d" % [Database.towers[w].get("name", ""), int(st.get("number", 0))]
	var world: Dictionary = Database.worlds.get(w, {})
	return "%s %d-%d" % [world.get("name", ""), int(world.get("number", 1)), int(st.get("number", 0))]


# ------------------------------------------------------------------ currencies & items
func gold() -> int:
	return int(profile.get("player", {}).get("gold", 0))


func gems() -> int:
	return int(profile.get("player", {}).get("gems", 0))


func soul_shards() -> int:
	return int(profile.get("player", {}).get("soul_shards", 0))


func add_gold(amount: int, persist := true) -> void:
	profile["player"]["gold"] = clampi(gold() + amount, 0, 999_999_999)
	gold_changed.emit(gold())
	if persist:
		save()


func spend_gold(amount: int, persist := true) -> bool:
	if amount < 0 or gold() < amount:
		return false
	profile["player"]["gold"] = gold() - amount
	gold_changed.emit(gold())
	if persist:
		save()
	return true


func add_gems(amount: int, persist := true) -> void:
	profile["player"]["gems"] = clampi(gems() + amount, 0, 9_999_999)
	gems_changed.emit(gems())
	if persist:
		save()


func spend_gems(amount: int, persist := true) -> bool:
	if amount < 0 or gems() < amount:
		return false
	profile["player"]["gems"] = gems() - amount
	gems_changed.emit(gems())
	if persist:
		save()
	return true


func add_item(item_id: String, qty: int, persist := true) -> void:
	if qty <= 0 or not Database.items.has(item_id):
		return
	var inv: Dictionary = profile["inventory"]
	inv[item_id] = mini(int(inv.get(item_id, 0)) + qty, int(Database.progression.get("inventory_stack_limit", 9999)))
	if persist:
		save()


func remove_item(item_id: String, qty: int, persist := true) -> bool:
	if item_count(item_id) < qty:
		return false
	var inv: Dictionary = profile["inventory"]
	inv[item_id] = int(inv.get(item_id, 0)) - qty
	if int(inv[item_id]) <= 0:
		inv.erase(item_id)
	if persist:
		save()
	return true


func item_count(item_id: String) -> int:
	return int(profile.get("inventory", {}).get(item_id, 0))


## Grants a reward bundle {gold, gems, soul_shards, items:{}}; returns it normalised.
func grant(reward: Dictionary, persist := true) -> Dictionary:
	var out := {"gold": int(reward.get("gold", 0)), "gems": int(reward.get("gems", 0)),
				"soul_shards": int(reward.get("soul_shards", 0)), "items": reward.get("items", {}).duplicate()}
	if out["gold"] > 0:
		add_gold(out["gold"], false)
	if out["gems"] > 0:
		add_gems(out["gems"], false)
	if out["soul_shards"] > 0:
		profile["player"]["soul_shards"] = soul_shards() + out["soul_shards"]
	for item_id in out["items"].keys():
		add_item(item_id, int(out["items"][item_id]), false)
	if persist:
		save()
		profile_changed.emit()
	return out


# ------------------------------------------------------------------ energy
func max_energy() -> int:
	return SaveManager.max_energy_for_rank(rank())


## Current energy after applying (offline) regeneration. Clock errors never
## create negative or runaway energy: time going backwards just re-anchors.
func energy() -> int:
	if profile.is_empty():
		return 0
	var pl: Dictionary = profile["player"]
	var cur := int(pl.get("energy", 0))
	var mx := max_energy()
	var t := int(now())
	var ts := int(pl.get("energy_ts", t))
	var regen := int(Database.balance("energy", "regen_seconds", 180))
	if cur >= mx or ts > t or ts <= 0:
		pl["energy_ts"] = t
		pl["energy"] = maxi(cur, 0)
		return int(pl["energy"])
	var gained := int((t - ts) / regen)
	if gained > 0:
		cur = mini(cur + gained, mx)
		pl["energy"] = cur
		pl["energy_ts"] = t if cur >= mx else ts + gained * regen
	return cur


## Seconds until the next Energy point (0 when full).
func energy_seconds_to_next() -> int:
	var cur := energy()
	if cur >= max_energy():
		return 0
	var regen := int(Database.balance("energy", "regen_seconds", 180))
	return maxi(regen - (int(now()) - int(profile["player"].get("energy_ts", now()))), 0)


func spend_energy(amount: int) -> bool:
	var cur := energy()
	if cur < amount:
		return false
	if cur >= max_energy():
		profile["player"]["energy_ts"] = int(now())
	profile["player"]["energy"] = cur - amount
	save()
	energy_changed.emit(energy(), max_energy())
	return true


func add_energy(amount: int) -> void:
	profile["player"]["energy"] = energy() + amount
	save()
	energy_changed.emit(energy(), max_energy())


func stage_energy(stage_id: String) -> int:
	return int(Database.get_stage(stage_id).get("energy", 0))


# ------------------------------------------------------------------ progress
func rank() -> int:
	return int(profile.get("player", {}).get("rank", 1))


func is_stage_unlocked(stage_id: String) -> bool:
	return profile.get("stages", {}).get("unlocked", []).has(stage_id)


func is_stage_cleared(stage_id: String) -> bool:
	return profile.get("stages", {}).get("cleared", []).has(stage_id)


func stage_stars(stage_id: String) -> Array:
	return profile.get("stages", {}).get("stars", {}).get(stage_id, [false, false, false])


func star_count(stage_id: String) -> int:
	return stage_stars(stage_id).filter(func(b): return b).size()


func player_name() -> String:
	return String(profile.get("player", {}).get("name", "Wayfarer"))


## Stars earned across every story world.
func all_stars() -> int:
	var n := 0
	for w in Database.world_order:
		n += total_stars(w)
	return n


func total_stars(world_id: String) -> int:
	var n := 0
	for st in Database.worlds.get(world_id, Database.towers.get(world_id, {})).get("stages", []):
		n += star_count(st["id"])
	return n


func next_stage_id(stage_id: String) -> String:
	var unlocks: Array = Database.get_stage(stage_id).get("unlocks", [])
	return unlocks[0] if not unlocks.is_empty() else ""


func world_unlocked(world_id: String) -> bool:
	var w: Dictionary = Database.worlds.get(world_id, {})
	var req: String = w.get("requires", "")
	return req.is_empty() or is_stage_cleared(req)


func tower_highest_floor(tower_id: String) -> int:
	var best := 0
	for fl in Database.towers.get(tower_id, {}).get("stages", []):
		if is_stage_cleared(fl["id"]):
			best = max(best, int(fl["number"]))
	return best


func stages_cleared_count() -> int:
	return profile.get("stages", {}).get("cleared", []).filter(func(s): return not Database.is_tower_stage(s)).size()


# ------------------------------------------------------------------ feature unlocks
func feature_unlocked(feature: String) -> bool:
	var req: String = Database.progression.get("unlocks", {}).get(feature, "")
	return req.is_empty() or is_stage_cleared(req)


func feature_unlock_label(feature: String) -> String:
	var req: String = Database.progression.get("unlocks", {}).get(feature, "")
	return "Stage " + stage_label(req).get_slice(" ", stage_label(req).count(" ")) if not req.is_empty() else ""


## Features that became available by clearing `stage_id` (for the victory screen).
func features_unlocked_by(stage_id: String) -> Array:
	var out: Array = []
	var ul: Dictionary = Database.progression.get("unlocks", {})
	for f in ul.keys():
		if ul[f] == stage_id:
			out.append(f)
	return out


## Grants the one-time gifts attached to a stage (hero, gems, items). Idempotent.
func _grant_unlock_gift(stage_id: String) -> Dictionary:
	var gifts: Dictionary = Database.progression.get("unlock_gifts", {})
	if not gifts.has(stage_id) or profile["unlocks"]["granted"].has(stage_id):
		return {}
	var g: Dictionary = gifts[stage_id]
	var out := grant({"gems": int(g.get("gems", 0)), "items": g.get("items", {})}, false)
	if g.has("hero_by_starter"):
		var hero: String = g["hero_by_starter"].get(profile.get("starter_id", ""), "")
		if not hero.is_empty() and Database.has_character(hero):
			var fam: String = Database.get_character(hero).get("family", "")
			if not owns_family(fam):
				out["hero_uid"] = _add_unit(hero)
				out["hero"] = hero
				if profile["party"].size() < max_party_size():
					profile["party"].append(out["hero_uid"])
			else:
				out["soul_shards"] = int(Database.summon.get("duplicate_shards", {}).get("3", 10))
				profile["player"]["soul_shards"] = soul_shards() + out["soul_shards"]
	profile["unlocks"]["granted"].append(stage_id)
	return out


## Old saves: grant gifts for milestones already cleared before Phase 4.
func _grant_retroactive_unlocks() -> void:
	var any := false
	for sid in Database.progression.get("unlock_gifts", {}).keys():
		if is_stage_cleared(sid) and not profile["unlocks"]["granted"].has(sid):
			_grant_unlock_gift(sid)
			any = true
	for tower_id in Database.tower_order:
		var first: String = Database.towers[tower_id]["stages"][0]["id"]
		if feature_unlocked("tower") and not is_stage_unlocked(first):
			profile["stages"]["unlocked"].append(first)
			any = true
	if any:
		save()


# ------------------------------------------------------------------ battle results
## Spends the stage's energy. Returns false (and spends nothing) if there is not enough.
func begin_stage(stage_id: String) -> bool:
	if not is_stage_unlocked(stage_id):
		return false
	return spend_energy(stage_energy(stage_id))


## Spends a stage's Energy and remembers it as the battle to load.
## Squad Power never blocks entry; only locks and Energy do.
func try_start_stage(stage_id: String) -> Dictionary:
	if not is_stage_unlocked(stage_id):
		return {"ok": false, "reason": "locked"}
	if party_units().is_empty():
		return {"ok": false, "reason": "no_squad"}
	if not begin_stage(stage_id):
		return {"ok": false, "reason": "energy"}
	current_stage_id = stage_id
	return {"ok": true}


## Legacy signature kept for tests: xp/gold/items from the battle model.
func apply_victory(stage_id: String, battle_xp: int, battle_gold: int, items: Dictionary, extra: Dictionary = {}) -> Dictionary:
	var data := extra.duplicate()
	data["xp"] = battle_xp
	data["gold"] = battle_gold
	data["items"] = items
	return apply_battle_result(stage_id, data)


## Applies a won battle: hero XP, rank XP (+rank rewards), gold, drops, stars,
## first-clear rewards, unlocks and gifts, Burst EXP and mission progress.
## data: {xp, gold, items, stars:[bool x3], bursts:{uid: n}, enemies_defeated, bosses_defeated}
func apply_battle_result(stage_id: String, data: Dictionary) -> Dictionary:
	var stage := Database.get_stage(stage_id)
	var is_tower := Database.is_tower_stage(stage_id)
	var first_clear := not is_stage_cleared(stage_id)
	var rewards: Dictionary = stage.get("rewards", {})
	var xp := int(data.get("xp", 0)) + int(rewards.get("xp", 0))
	var gold_total := int(data.get("gold", 0)) + int(rewards.get("gold", 0))
	var items: Dictionary = data.get("items", {}).duplicate()
	var first_reward := {}
	if first_clear:
		gold_total += int(rewards.get("first_clear_gold", 0))
		first_reward = grant(stage.get("first_clear", {}), false)

	var unit_results: Array = []
	var bursts: Dictionary = data.get("bursts", {})
	for unit in party_units():
		var before := {"level": int(unit["level"]), "exp": int(unit["exp"]), "burst_level": int(unit.get("burst_level", 1))}
		var ups := Progression.add_unit_xp(unit, xp)
		var bx := int(bursts.get(unit["uid"], 0)) * int(Database.balance("burst_levels", "per_use", 1))
		var b := add_burst_xp(unit["uid"], bx, false) if bx > 0 else {}
		unit_results.append({"uid": unit["uid"], "char_id": unit["char_id"], "before": before,
							 "after": {"level": int(unit["level"]), "exp": int(unit["exp"]),
									   "burst_level": int(unit.get("burst_level", 1))},
							 "level_ups": ups, "burst_up": not b.is_empty() and int(b["after"]) > int(b["before"])})

	var rank_ups := _add_rank_xp(xp)
	add_gold(gold_total, false)
	for item_id in items.keys():
		add_item(item_id, int(items[item_id]), false)

	# stars (keep the best result per objective)
	var st: Dictionary = profile["stages"]
	var earned: Array = data.get("stars", [true, false, false])
	var old: Array = stage_stars(stage_id).duplicate()
	var new_stars := 0
	for i in 3:
		var got := i < earned.size() and bool(earned[i])
		if got and not old[i]:
			new_stars += 1
		old[i] = old[i] or got
	st["stars"][stage_id] = old
	st["clears"][stage_id] = int(st["clears"].get(stage_id, 0)) + 1

	var newly_unlocked: Array = []
	var features: Array = []
	var gift := {}
	if first_clear:
		st["cleared"].append(stage_id)
		features = features_unlocked_by(stage_id)
		gift = _grant_unlock_gift(stage_id)
		if features.has("tower"):
			for tower_id in Database.tower_order:
				var f0: String = Database.towers[tower_id]["stages"][0]["id"]
				if not st["unlocked"].has(f0):
					st["unlocked"].append(f0)
		if features.has("world2"):
			for w in Database.world_order:
				if Database.worlds[w].get("requires", "") == stage_id:
					var s0: String = Database.worlds[w]["stages"][0]["id"]
					if not st["unlocked"].has(s0):
						st["unlocked"].append(s0)
						newly_unlocked.append(s0)
	for next_id in stage.get("unlocks", []):
		if not st["unlocked"].has(next_id):
			st["unlocked"].append(next_id)
			newly_unlocked.append(next_id)
	if not newly_unlocked.is_empty():
		last_unlocked_stage = newly_unlocked[0]

	var stats: Dictionary = profile["stats"]
	stats["battles_won"] = int(stats.get("battles_won", 0)) + 1
	stats["enemies_defeated"] = int(stats.get("enemies_defeated", 0)) + int(data.get("enemies_defeated", 0))
	stats["bosses_defeated"] = int(stats.get("bosses_defeated", 0)) + int(data.get("bosses_defeated", 0))
	track("stage_clear", 1, false)
	if is_tower:
		track("tower_clear", 1, false)
	track("enemy_kill", int(data.get("enemies_defeated", 0)), false)
	track("boss_kill", int(data.get("bosses_defeated", 0)), false)
	var total_bursts := 0
	for k in bursts.keys():
		total_bursts += int(bursts[k])
	track("burst_use", total_bursts, false)
	save()
	profile_changed.emit()
	return {"xp": xp, "gold": gold_total, "items": items, "units": unit_results, "first_clear": first_clear,
			"first_clear_gold": int(rewards.get("first_clear_gold", 0)) if first_clear else 0,
			"first_clear_reward": first_reward, "unlocked": newly_unlocked,
			"rank_before": int(rank_ups["before"]), "rank_after": rank(), "rank_ups": rank_ups["ups"],
			"stars": old, "stars_this_run": earned, "new_stars": new_stars, "features": features, "gift": gift,
			"tower": is_tower}


## Adds player EXP. Each rank-up restores Energy (max may grow) and milestone ranks give Gems.
func _add_rank_xp(xp: int) -> Dictionary:
	var player: Dictionary = profile["player"]
	var before := int(player["rank"])
	var ups: Array = []
	player["rank_xp"] = int(player["rank_xp"]) + xp
	while int(player["rank"]) < int(Database.progression.get("rank_max", 99)) \
			and int(player["rank_xp"]) >= Progression.rank_xp_to_next(int(player["rank"])):
		player["rank_xp"] = int(player["rank_xp"]) - Progression.rank_xp_to_next(int(player["rank"]))
		var old_max := max_energy()
		player["rank"] = int(player["rank"]) + 1
		var new_max := max_energy()
		energy()
		player["energy"] = maxi(int(player["energy"]), new_max)
		player["energy_ts"] = int(now())
		var gems_gain := 0
		var rr: Dictionary = Database.progression.get("rank_rewards", {})
		if int(player["rank"]) % int(rr.get("gems_every", 5)) == 0:
			gems_gain = int(rr.get("gems", 50))
			add_gems(gems_gain, false)
		ups.append({"rank": int(player["rank"]), "energy_max_up": new_max - old_max, "gems": gems_gain})
	return {"before": before, "ups": ups}


func record_defeat(_stage_id := "") -> void:
	profile["stats"]["battles_lost"] = int(profile["stats"].get("battles_lost", 0)) + 1
	save()


# ------------------------------------------------------------------ summoning
func summon_banner(banner_id := "standard") -> Dictionary:
	return Database.summon.get("banners", {}).get(banner_id, {})


## Performs `count` summons. Results are committed and saved BEFORE any animation
## plays, so closing the game mid-animation never loses (or duplicates) a hero.
## Returns {ok, results: [{char_id, rarity, is_new, uid, shards}], reason}
func summon(banner_id := "standard", count := 1) -> Dictionary:
	var b := summon_banner(banner_id)
	if b.is_empty():
		return {"ok": false, "reason": "Unknown banner."}
	if not feature_unlocked("summon"):
		return {"ok": false, "reason": "Summoning unlocks after clearing %s." % feature_unlock_label("summon")}
	var cost := int(b.get("single_cost", 100)) if count == 1 else int(b.get("multi_cost", 1000))
	if not spend_gems(cost, false):
		return {"ok": false, "reason": "Not enough Gems."}
	var results: Array = []
	for i in count:
		var cid := SummonSystem.roll(b, rng)
		var def := Database.get_character(cid)
		var fam: String = def.get("family", cid)
		var entry := {"char_id": cid, "rarity": int(def.get("rarity", 3)), "is_new": false, "uid": "", "shards": 0}
		if owns_family(fam):
			entry["shards"] = int(Database.summon.get("duplicate_shards", {}).get(str(entry["rarity"]), 10))
			profile["player"]["soul_shards"] = soul_shards() + entry["shards"]
		else:
			entry["is_new"] = true
			entry["uid"] = _add_unit(cid)
		results.append(entry)
		profile["summon"]["history"].append({"id": cid, "r": entry["rarity"], "new": entry["is_new"],
											"shards": entry["shards"], "t": int(now())})
	if profile["summon"]["history"].size() > 100:
		profile["summon"]["history"] = profile["summon"]["history"].slice(profile["summon"]["history"].size() - 100)
	profile["summon"]["total"] = int(profile["summon"].get("total", 0)) + count
	profile["stats"]["summons"] = int(profile["stats"].get("summons", 0)) + count
	track("summon", count, false)
	save()
	profile_changed.emit()
	return {"ok": true, "results": results, "cost": cost}


# ------------------------------------------------------------------ missions
func _date_key() -> String:
	var d := Time.get_datetime_dict_from_unix_time(int(now()) + int(Time.get_time_zone_from_system().get("bias", 0)) * 60)
	return "%04d-%02d-%02d" % [d["year"], d["month"], d["day"]]


func _week_key() -> String:
	var days := int((int(now()) + int(Time.get_time_zone_from_system().get("bias", 0)) * 60) / 86400)
	return "w%d" % int((days + 3) / 7)     # weeks start on Monday


## Resets daily/weekly progress when the day/week changed.
func refresh_missions() -> void:
	if profile.is_empty():
		return
	var m: Dictionary = profile["missions"]
	var dk := _date_key()
	if m.get("daily_key", "") != dk:
		m["daily_key"] = dk
		m["daily"] = {}
		m["daily_claimed"] = []
		m["chest_claimed"] = false
	var wk := _week_key()
	if m.get("weekly_key", "") != wk:
		m["weekly_key"] = wk
		m["weekly"] = {}
		m["weekly_claimed"] = []


## Progress event for missions: stage_clear, tower_clear, enemy_kill, boss_kill, burst_use, train, summon.
func track(event: String, amount := 1, persist := true) -> void:
	if profile.is_empty() or amount <= 0:
		return
	refresh_missions()
	var m: Dictionary = profile["missions"]
	for kind in ["daily", "weekly"]:
		for mission in Database.missions.get(kind, []):
			if mission.get("event", "") == event:
				m[kind][mission["id"]] = mini(int(m[kind].get(mission["id"], 0)) + amount, int(mission.get("target", 1)))
	if persist:
		save()


func mission_progress(kind: String, mission: Dictionary) -> int:
	refresh_missions()
	return int(profile["missions"][kind].get(mission["id"], 0))


func mission_claimed(kind: String, mission_id: String) -> bool:
	return profile["missions"][kind + "_claimed"].has(mission_id)


func claim_mission(kind: String, mission_id: String) -> Dictionary:
	refresh_missions()
	for mission in Database.missions.get(kind, []):
		if mission["id"] == mission_id:
			if mission_claimed(kind, mission_id) or mission_progress(kind, mission) < int(mission.get("target", 1)):
				return {}
			profile["missions"][kind + "_claimed"].append(mission_id)
			var r := grant(mission.get("reward", {}), false)
			save()
			profile_changed.emit()
			return r
	return {}


## CLAIM ALL: every finished mission (daily + weekly) and the daily chest.
## Returns the combined reward plus "count" (0 when nothing was claimable).
func claim_all_missions() -> Dictionary:
	var total := {"gold": 0, "gems": 0, "soul_shards": 0, "items": {}, "count": 0}
	for kind in ["daily", "weekly"]:
		for m in Database.missions.get(kind, []):
			if not mission_claimed(kind, m["id"]) and mission_progress(kind, m) >= int(m.get("target", 1)):
				_merge_reward(total, claim_mission(kind, m["id"]))
	if can_claim_chest():
		_merge_reward(total, claim_chest())
	return total


static func _merge_reward(total: Dictionary, r: Dictionary) -> void:
	if r.is_empty():
		return
	total["count"] = int(total["count"]) + 1
	for k in ["gold", "gems", "soul_shards"]:
		total[k] = int(total[k]) + int(r.get(k, 0))
	for item_id in r.get("items", {}).keys():
		total["items"][item_id] = int(total["items"].get(item_id, 0)) + int(r["items"][item_id])


func daily_completed() -> int:
	return profile["missions"]["daily_claimed"].size()


func can_claim_chest() -> bool:
	refresh_missions()
	return not profile["missions"]["chest_claimed"] \
			and daily_completed() >= int(Database.missions.get("daily_chest", {}).get("needed", 4))


func claim_chest() -> Dictionary:
	if not can_claim_chest():
		return {}
	profile["missions"]["chest_claimed"] = true
	var r := grant(Database.missions.get("daily_chest", {}).get("reward", {}), false)
	save()
	profile_changed.emit()
	return r


func missions_claimable() -> int:
	if not feature_unlocked("missions"):
		return 0
	refresh_missions()
	var n := 0
	for kind in ["daily", "weekly"]:
		for mission in Database.missions.get(kind, []):
			if not mission_claimed(kind, mission["id"]) and mission_progress(kind, mission) >= int(mission.get("target", 1)):
				n += 1
	if can_claim_chest():
		n += 1
	return n


# ------------------------------------------------------------------ login rewards
func login_available() -> bool:
	return has_profile() and profile["login"].get("last_date", "") != _date_key()


func login_day_index() -> int:
	return int(profile["login"].get("day_index", 0)) % max(Database.login_rewards.get("cycle", []).size(), 1)


## Claims today's login reward. Missed days simply continue the cycle.
func claim_login() -> Dictionary:
	if not login_available():
		return {}
	var cycle: Array = Database.login_rewards.get("cycle", [])
	if cycle.is_empty():
		return {}
	var idx := login_day_index()
	var r := grant(cycle[idx].get("reward", {}), false)
	profile["login"]["last_date"] = _date_key()
	profile["login"]["day_index"] = int(profile["login"].get("day_index", 0)) + 1
	profile["login"]["total"] = int(profile["login"].get("total", 0)) + 1
	save()
	profile_changed.emit()
	r["day"] = idx + 1
	return r


# ------------------------------------------------------------------ notifications
func units_badge() -> bool:
	for u in owned_units():
		if bool(u.get("new", false)):
			return true
	if feature_unlocked("evolution"):
		for u in party_units():
			if can_evolve(u["uid"]):
				return true
	return false


func summon_badge() -> bool:
	return feature_unlocked("summon") and not bool(profile.get("summon", {}).get("seen", false))


func mark_summon_seen() -> void:
	if not bool(profile["summon"].get("seen", false)):
		profile["summon"]["seen"] = true
		save()


# ------------------------------------------------------------------ tutorial
func hint_seen(hint_id: String) -> bool:
	return profile.get("tutorial", {}).get("hints_seen", []).has(hint_id)


func mark_hint_seen(hint_id: String) -> void:
	if hint_id.is_empty() or hint_seen(hint_id):
		return
	profile["tutorial"]["hints_seen"].append(hint_id)
	save()


## Coach marks (visual step-by-step tutorial) are permanent once completed.
func coach_done(step_id: String) -> bool:
	return profile.get("tutorial", {}).get("coach_done", []).has(step_id)


func mark_coach_done(step_id: String) -> void:
	if step_id.is_empty() or coach_done(step_id) or not profile.has("tutorial"):
		return
	if not profile["tutorial"].has("coach_done"):
		profile["tutorial"]["coach_done"] = []
	profile["tutorial"]["coach_done"].append(step_id)
	save()


## Settings > Reset Tutorial: shows hints and coach marks again.
func reset_tutorial() -> void:
	if not profile.has("tutorial"):
		return
	profile["tutorial"]["hints_seen"] = []
	profile["tutorial"]["coach_done"] = []
	save()


func mark_intro_seen() -> void:
	profile["tutorial"]["intro_seen"] = true
	save()


func feature_announced(feature: String) -> bool:
	return profile.get("unlocks", {}).get("announced", []).has(feature)


func mark_feature_announced(feature: String) -> void:
	if not feature_announced(feature):
		profile["unlocks"]["announced"].append(feature)
		save()


## Returns "" when the name is fine, otherwise a short reason to show the player.
static func validate_player_name(n: String) -> String:
	n = n.strip_edges()
	if n.length() < 2:
		return "Use at least 2 characters."
	if n.length() > 16:
		return "Use at most 16 characters."
	var re := RegEx.create_from_string("^[A-Za-z0-9 _'\\-]+$")
	if re.search(n) == null:
		return "Letters, numbers, spaces, - ' and _ only."
	if "  " in n:
		return "Avoid double spaces."
	return ""


func set_player_name(n: String) -> void:
	n = n.strip_edges().substr(0, 16)
	if not validate_player_name(n).is_empty():
		return
	profile["player"]["name"] = n
	save()
	profile_changed.emit()


# ------------------------------------------------------------------ settings
func set_setting(key: String, value: Variant) -> void:
	settings[key] = value
	SaveManager.save_settings(settings)
	apply_settings()
	settings_changed.emit()


func apply_settings() -> void:
	SceneRouter.reduce_motion = bool(settings.get("reduce_motion", false))
	AudioManager.set_volumes(float(settings.get("master_volume", 0.8)), float(settings.get("music_volume", 0.6)),
							 float(settings.get("sfx_volume", 0.8)))
	if DisplayServer.get_name() != "headless":
		var want_fs := bool(settings.get("fullscreen", false))
		var mode := DisplayServer.window_get_mode()
		var is_fs := mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN
		if want_fs != is_fs:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if want_fs else DisplayServer.WINDOW_MODE_WINDOWED)
