extends Node
## SaveManager (autoload)
## Local, offline JSON saves with:
##  - atomic writes (write .tmp, then rename) so a crash mid-save cannot corrupt the file
##  - a rolling .bak copy used automatically if the main file is unreadable
##  - field-by-field validation that repairs missing / wrong-typed data instead of crashing
## Settings live in their own file so they work before any profile exists.

signal save_completed
signal save_failed(reason: String)

const SAVE_VERSION := 2
var save_path := "user://cinderbound_save.json"
var settings_path := "user://cinderbound_settings.json"

## Result of the most recent load attempt: "ok", "missing", "recovered_backup", "corrupted"
var last_load_status := "missing"
## Human-readable notes about what a migration changed (shown once after loading an old save).
var migration_notes: PackedStringArray = []


# ------------------------------------------------------------------ defaults
func default_profile() -> Dictionary:
	return {
		"version": SAVE_VERSION,
		"starter_id": "",
		"player": {"name": "Wayfarer", "rank": 1, "rank_xp": 0, "gold": 0, "gems": 0, "soul_shards": 0,
				   "energy": 20, "energy_ts": 0, "play_seconds": 0, "created": 0},
		"units": [],          # [{uid, char_id, level, exp, burst_level, burst_xp, locked, favorite, new, obtained}]
		"next_uid": 1,
		"party": [],          # [uid, ...] leader first, up to 5
		"inventory": {},      # item_id -> qty (stacked)
		"stages": {"cleared": [], "unlocked": [], "stars": {}, "clears": {}},
		"unlocks": {"granted": [], "announced": []},
		"codex": [],          # hero families ever owned
		"tutorial": {"intro_seen": false, "hints_seen": [], "coach_done": []},
		"stats": {"battles_won": 0, "battles_lost": 0, "bosses_defeated": 0, "enemies_defeated": 0, "summons": 0},
		"missions": {"daily_key": "", "daily": {}, "daily_claimed": [], "chest_claimed": false,
					 "weekly_key": "", "weekly": {}, "weekly_claimed": []},
		"login": {"last_date": "", "day_index": 0, "total": 0},
		"summon": {"history": [], "total": 0, "seen": false},
	}


func default_settings() -> Dictionary:
	return {"master_volume": 0.8, "music_volume": 0.6, "sfx_volume": 0.8,
			"screen_shake": true, "fullscreen": false, "battle_speed": 1.0,
			"battle_effects": true, "damage_numbers": true, "auto_battle": false,
			"reduce_motion": false, "haptics": true, "safe_area": 0,
			"unit_sort": "recent", "unit_sort_desc": true, "unit_filter": ""}


# ------------------------------------------------------------------ profile
func has_save() -> bool:
	return FileAccess.file_exists(save_path) or FileAccess.file_exists(save_path + ".bak")


## Loads and repairs the profile. Returns {} when no usable save exists.
func load_profile() -> Dictionary:
	var data := _read_dict(save_path)
	if not data.is_empty():
		last_load_status = "ok"
		return sanitize_profile(data)
	var backup := _read_dict(save_path + ".bak")
	if not backup.is_empty():
		last_load_status = "recovered_backup"
		push_warning("Save file unreadable, recovered from backup.")
		return sanitize_profile(backup)
	last_load_status = "corrupted" if FileAccess.file_exists(save_path) else "missing"
	return {}


func save_profile(profile: Dictionary) -> bool:
	var clean := sanitize_profile(profile.duplicate(true), false)
	var ok := _write_atomic(save_path, JSON.stringify(clean, "\t"))
	if ok:
		save_completed.emit()
	else:
		save_failed.emit("Could not write save file")
	return ok


func delete_profile() -> void:
	for p in [save_path, save_path + ".bak", save_path + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))


# ------------------------------------------------------------------ settings
func load_settings() -> Dictionary:
	var s := default_settings()
	var data := _read_dict(settings_path)
	for key in s.keys():
		if data.has(key) and typeof(data[key]) in [TYPE_FLOAT, TYPE_INT, TYPE_BOOL]:
			s[key] = data[key]
		elif data.has(key) and typeof(data[key]) == TYPE_STRING and typeof(s[key]) == TYPE_STRING:
			s[key] = data[key]
	for key in ["master_volume", "music_volume", "sfx_volume"]:
		s[key] = clampf(float(s[key]), 0.0, 1.0)
	s["battle_speed"] = 2.0 if float(s["battle_speed"]) >= 1.5 else 1.0
	s["safe_area"] = clampi(int(s["safe_area"]), 0, 3)
	for key in ["screen_shake", "battle_effects", "damage_numbers", "auto_battle", "reduce_motion", "haptics", "unit_sort_desc"]:
		s[key] = bool(s[key])
	s["fullscreen"] = bool(s["fullscreen"])
	return s


func save_settings(settings: Dictionary) -> void:
	_write_atomic(settings_path, JSON.stringify(settings, "\t"))


# ------------------------------------------------------------------ validation / migration
## Repairs a profile dictionary so every field exists with a sane type/value, and
## migrates older save versions (v1: no gems, energy, burst levels, stars...).
## Unknown units/items/stages (e.g. from removed content) are dropped.
func sanitize_profile(data: Dictionary, record_notes := true) -> Dictionary:
	var version := _int(data.get("version"), 1)
	if record_notes:
		migration_notes.clear()
	var p := default_profile()
	p["starter_id"] = _str(data.get("starter_id"), "")
	if not Database.has_character(p["starter_id"]):
		p["starter_id"] = ""

	var player: Dictionary = data.get("player") if data.get("player") is Dictionary else {}
	var pl: Dictionary = p["player"]
	pl["name"] = _str(player.get("name"), "Wayfarer").strip_edges().substr(0, 16)
	if pl["name"].is_empty():
		pl["name"] = "Wayfarer"
	pl["rank"] = clampi(_int(player.get("rank"), 1), 1, int(Database.progression.get("rank_max", 99)))
	pl["rank_xp"] = max(_int(player.get("rank_xp"), 0), 0)
	pl["gold"] = clampi(_int(player.get("gold"), 0), 0, 999_999_999)
	pl["gems"] = clampi(_int(player.get("gems"), 0), 0, 9_999_999)
	pl["soul_shards"] = clampi(_int(player.get("soul_shards"), 0), 0, 9_999_999)
	var emax := max_energy_for_rank(pl["rank"])
	pl["energy"] = clampi(_int(player.get("energy"), emax), 0, 999) if player.has("energy") else emax
	pl["energy_ts"] = max(_int(player.get("energy_ts"), 0), 0)
	pl["play_seconds"] = max(_int(player.get("play_seconds"), 0), 0)
	pl["created"] = max(_int(player.get("created"), 0), 0)

	var legacy: Dictionary = Database.progression.get("legacy_items", {})
	var seen_uids := {}
	var max_uid := 0
	var clamped := 0
	for u in (data.get("units") if data.get("units") is Array else []):
		if not (u is Dictionary):
			continue
		var char_id := _str(u.get("char_id"), "")
		var uid := _str(u.get("uid"), "")
		if not Database.has_character(char_id) or uid.is_empty() or seen_uids.has(uid):
			continue
		var max_level := int(Database.get_character(char_id).get("max_level", 20))
		var lvl := _int(u.get("level"), 1)
		if lvl > max_level:
			clamped += 1
		var bmax := int(Database.balance("burst_levels", "max", 5))
		var unit := {"uid": uid, "char_id": char_id,
					 "level": clampi(lvl, 1, max_level),
					 "exp": max(_int(u.get("exp"), 0), 0) if lvl < max_level else 0,
					 "burst_level": clampi(_int(u.get("burst_level"), 1), 1, bmax),
					 "burst_xp": max(_int(u.get("burst_xp"), 0), 0),
					 "locked": bool(u.get("locked", false)), "favorite": bool(u.get("favorite", false)),
					 "new": bool(u.get("new", false)), "obtained": max(_int(u.get("obtained"), 0), 0)}
		p["units"].append(unit)
		seen_uids[uid] = true
		var fam: String = Database.get_character(char_id).get("family", char_id)
		if not p["codex"].has(fam):
			p["codex"].append(fam)
		if uid.begins_with("u") and uid.substr(1).is_valid_int():
			max_uid = max(max_uid, int(uid.substr(1)))
	if clamped > 0 and record_notes:
		migration_notes.append("%d hero(es) were above the new level cap and are now at max level, ready to evolve." % clamped)
	p["next_uid"] = max(_int(data.get("next_uid"), 1), max_uid + 1)

	# A save with a starter but no units (e.g. truncated) regains the starter unit.
	if p["units"].is_empty() and not p["starter_id"].is_empty():
		p["units"].append({"uid": "u%d" % p["next_uid"], "char_id": p["starter_id"], "level": 1, "exp": 0,
						   "burst_level": 1, "burst_xp": 0, "locked": false, "favorite": false, "new": false,
						   "obtained": 0})
		p["next_uid"] += 1
	for c in (data.get("codex") if data.get("codex") is Array else []):
		if c is String and not p["codex"].has(c) and not Database.family_forms(c).is_empty():
			p["codex"].append(c)

	var max_party := int(Database.progression.get("party_size", 5))
	for uid in (data.get("party") if data.get("party") is Array else []):
		if typeof(uid) == TYPE_STRING and seen_uids.has(uid) and not p["party"].has(uid) and p["party"].size() < max_party:
			p["party"].append(uid)
	if p["party"].is_empty() and not p["units"].is_empty():
		p["party"].append(p["units"][0]["uid"])

	var inv: Dictionary = data.get("inventory") if data.get("inventory") is Dictionary else {}
	var stack := int(Database.progression.get("inventory_stack_limit", 9999))
	var converted := 0
	for item_id in inv.keys():
		var target: String = legacy.get(item_id, item_id)
		if target != item_id and Database.items.has(target):
			converted += 1
		if Database.items.has(target):
			var q := clampi(_int(inv[item_id], 0), 0, stack)
			if q > 0:
				p["inventory"][target] = clampi(int(p["inventory"].get(target, 0)) + q, 0, stack)
	if converted > 0 and record_notes:
		migration_notes.append("Old elemental shards were converted into the new Fragments.")
	if version < 2:
		if record_notes and not p["starter_id"].is_empty():
			migration_notes.append("Your save was updated for the new update: Energy, Gems, Burst levels and stage stars were added. You also received a set of training wisps.")
		for item_id in Database.progression.get("starting_items", {}).keys():
			p["inventory"][item_id] = int(p["inventory"].get(item_id, 0)) + int(Database.progression["starting_items"][item_id])

	var st: Dictionary = data.get("stages") if data.get("stages") is Dictionary else {}
	for key in ["cleared", "unlocked"]:
		for sid in (st.get(key) if st.get(key) is Array else []):
			if typeof(sid) == TYPE_STRING and Database.stages.has(sid) and not p["stages"][key].has(sid):
				p["stages"][key].append(sid)
	var stars: Dictionary = st.get("stars") if st.get("stars") is Dictionary else {}
	for sid in stars.keys():
		if Database.stages.has(sid) and stars[sid] is Array:
			var arr: Array = []
			for b in stars[sid].slice(0, 3):
				arr.append(bool(b))
			while arr.size() < 3:
				arr.append(false)
			p["stages"]["stars"][sid] = arr
	var clears: Dictionary = st.get("clears") if st.get("clears") is Dictionary else {}
	for sid in clears.keys():
		if Database.stages.has(sid):
			p["stages"]["clears"][sid] = max(_int(clears[sid], 0), 0)
	# old saves: every cleared stage earned at least its first star
	for sid in p["stages"]["cleared"]:
		if not p["stages"]["stars"].has(sid):
			p["stages"]["stars"][sid] = [true, false, false]
		if int(p["stages"]["clears"].get(sid, 0)) < 1:
			p["stages"]["clears"][sid] = 1
	# first stage is always available; cleared stages always unlock their successors
	if not Database.stage_order.is_empty() and not p["stages"]["unlocked"].has(Database.stage_order[0]):
		p["stages"]["unlocked"].append(Database.stage_order[0])
	for sid in p["stages"]["cleared"]:
		if not p["stages"]["unlocked"].has(sid):
			p["stages"]["unlocked"].append(sid)
		for next_id in Database.get_stage(sid).get("unlocks", []):
			if not p["stages"]["unlocked"].has(next_id):
				p["stages"]["unlocked"].append(next_id)

	var ul: Dictionary = data.get("unlocks") if data.get("unlocks") is Dictionary else {}
	for key in ["granted", "announced"]:
		for v in (ul.get(key) if ul.get(key) is Array else []):
			if v is String and not p["unlocks"][key].has(v):
				p["unlocks"][key].append(v)

	var tut: Dictionary = data.get("tutorial") if data.get("tutorial") is Dictionary else {}
	p["tutorial"]["intro_seen"] = bool(tut.get("intro_seen", false))
	for c in (tut.get("coach_done") if tut.get("coach_done") is Array else []):
		if c is String and not p["tutorial"]["coach_done"].has(c):
			p["tutorial"]["coach_done"].append(c)
	for h in (tut.get("hints_seen") if tut.get("hints_seen") is Array else []):
		if typeof(h) == TYPE_STRING and not p["tutorial"]["hints_seen"].has(h):
			p["tutorial"]["hints_seen"].append(h)

	var stats: Dictionary = data.get("stats") if data.get("stats") is Dictionary else {}
	for key in p["stats"].keys():
		p["stats"][key] = max(_int(stats.get(key), 0), 0)

	var ms: Dictionary = data.get("missions") if data.get("missions") is Dictionary else {}
	var pm: Dictionary = p["missions"]
	pm["daily_key"] = _str(ms.get("daily_key"), "")
	pm["weekly_key"] = _str(ms.get("weekly_key"), "")
	pm["chest_claimed"] = bool(ms.get("chest_claimed", false))
	for key in ["daily", "weekly"]:
		var d: Dictionary = ms.get(key) if ms.get(key) is Dictionary else {}
		for k in d.keys():
			pm[key][k] = max(_int(d[k], 0), 0)
	for key in ["daily_claimed", "weekly_claimed"]:
		for v in (ms.get(key) if ms.get(key) is Array else []):
			if v is String and not pm[key].has(v):
				pm[key].append(v)

	var lg: Dictionary = data.get("login") if data.get("login") is Dictionary else {}
	p["login"]["last_date"] = _str(lg.get("last_date"), "")
	p["login"]["day_index"] = max(_int(lg.get("day_index"), 0), 0)
	p["login"]["total"] = max(_int(lg.get("total"), 0), 0)

	var sm: Dictionary = data.get("summon") if data.get("summon") is Dictionary else {}
	p["summon"]["total"] = max(_int(sm.get("total"), 0), 0)
	p["summon"]["seen"] = bool(sm.get("seen", false))
	for h in (sm.get("history") if sm.get("history") is Array else []):
		if h is Dictionary and Database.has_character(_str(h.get("id"), "")):
			p["summon"]["history"].append({"id": h["id"], "r": _int(h.get("r"), 3), "new": bool(h.get("new", false)),
										  "shards": _int(h.get("shards"), 0), "t": _int(h.get("t"), 0)})
	if p["summon"]["history"].size() > 100:
		p["summon"]["history"] = p["summon"]["history"].slice(p["summon"]["history"].size() - 100)
	return p


func max_energy_for_rank(rank: int) -> int:
	var e: Dictionary = Database.progression.get("energy", {})
	return mini(int(e.get("base_max", 20)) + int(floor((rank - 1) * float(e.get("per_rank", 0.5)))), int(e.get("cap", 60)))


# ------------------------------------------------------------------ file helpers
func _read_dict(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var text := f.get_as_text()
	f.close()
	if text.strip_edges().is_empty():
		return {}
	var json := JSON.new()
	if json.parse(text) != OK or typeof(json.data) != TYPE_DICTIONARY:
		return {}
	return json.data


func _write_atomic(path: String, text: String) -> bool:
	var tmp := path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_error("Cannot open %s for writing (%s)" % [tmp, FileAccess.get_open_error()])
		return false
	f.store_string(text)
	f.close()
	var abs_path := ProjectSettings.globalize_path(path)
	if FileAccess.file_exists(path):
		# keep the last good save as a backup
		var bak := ProjectSettings.globalize_path(path + ".bak")
		if FileAccess.file_exists(path + ".bak"):
			DirAccess.remove_absolute(bak)
		DirAccess.rename_absolute(abs_path, bak)
	return DirAccess.rename_absolute(ProjectSettings.globalize_path(tmp), abs_path) == OK


static func _int(v: Variant, fallback: int) -> int:
	if typeof(v) == TYPE_INT:
		return v
	if typeof(v) == TYPE_FLOAT and is_finite(v):
		return int(v)
	return fallback


static func _str(v: Variant, fallback: String) -> String:
	return v if typeof(v) == TYPE_STRING else fallback
