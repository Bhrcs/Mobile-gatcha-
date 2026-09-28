extends Node
## Database (autoload)
## Loads every data-driven definition (characters, enemies, skills, stages,
## items, elements, statuses, balance) from res://data at startup.
## Nothing here is hard-coded: drop a new JSON file into data/characters and
## the unit becomes available without touching combat code.

const DATA_ROOT := "res://data"

var characters: Dictionary = {}   # id -> Dictionary
var enemies: Dictionary = {}
var skills: Dictionary = {}
var items: Dictionary = {}
var statuses: Dictionary = {}
var worlds: Dictionary = {}       # story world id -> Dictionary
var world_order: Array[String] = []
var towers: Dictionary = {}       # tower id -> Dictionary (floors are stages too)
var tower_order: Array[String] = []
var stages: Dictionary = {}       # stage id -> Dictionary (with "world_id"), story stages AND tower floors
var stage_order: Array[String] = []   # story stages only, in play order
var drop_tables: Dictionary = {}
var summon: Dictionary = {}
var missions: Dictionary = {}
var login_rewards: Dictionary = {}
var elements: Dictionary = {}
var element_config: Dictionary = {}
var progression: Dictionary = {}
var hints: Dictionary = {}
var sprite_meta_cache: Dictionary = {}
var load_errors: PackedStringArray = []


func _ready() -> void:
	reload()


## Re-reads all data files. Safe to call more than once (used by tests).
func reload() -> void:
	load_errors.clear()
	characters = _load_folder(DATA_ROOT + "/characters")
	enemies = _load_folder(DATA_ROOT + "/enemies")
	skills = _merge_files(DATA_ROOT + "/skills")
	items = _read_json(DATA_ROOT + "/items/items.json")
	statuses = _read_json(DATA_ROOT + "/statuses.json")
	element_config = _read_json(DATA_ROOT + "/elements.json")
	elements = element_config.get("elements", {})
	progression = _read_json(DATA_ROOT + "/progression.json")
	hints = _read_json(DATA_ROOT + "/tutorial_hints.json")
	drop_tables = _read_json(DATA_ROOT + "/drop_tables.json")
	summon = _read_json(DATA_ROOT + "/summon.json")
	missions = _read_json(DATA_ROOT + "/missions.json")
	login_rewards = _read_json(DATA_ROOT + "/login_rewards.json")
	_load_worlds()
	_validate()
	for msg in load_errors:
		push_error(msg)


# ------------------------------------------------------------------ lookups
func get_character(id: String) -> Dictionary:
	return characters.get(id, {})


func get_enemy(id: String) -> Dictionary:
	return enemies.get(id, {})


func get_skill(id: String) -> Dictionary:
	return skills.get(id, {})


func get_item(id: String) -> Dictionary:
	return items.get(id, {})


func get_stage(id: String) -> Dictionary:
	return stages.get(id, {})


func get_status(id: String) -> Dictionary:
	return statuses.get(id, {})


func has_character(id: String) -> bool:
	return characters.has(id)


## Forms of a hero family in evolution order (e.g. kael: emberclaw -> blazeheart -> cinderlord).
## Accepts a family name ("kael") or any form id ("kael_emberclaw").
func family_forms(family: String) -> Array:
	if characters.has(family):
		family = characters[family].get("family", family)
	for c in characters.values():
		if c.get("family", "") == family:
			return c.get("forms", [c["id"]])
	return []


## One entry per hero family (its first form), in codex order.
func family_ids() -> Array[String]:
	var out: Array[String] = []
	var seen := {}
	var order := ["kael", "rhea", "voss", "seraphine", "mira", "corin", "nerys", "aldric", "thorne", "wren", "faye",
			"gorran"]
	for c in characters.values():
		var fam: String = c.get("family", c["id"])
		if not seen.has(fam) and int(c.get("form_index", 0)) == 0:
			seen[fam] = true
			out.append(c["id"])
	out.sort_custom(func(a, b):
		var fa: String = characters[a].get("family", "")
		var fb: String = characters[b].get("family", "")
		var ia := order.find(fa)
		var ib := order.find(fb)
		if ia < 0:
			ia = 999
		if ib < 0:
			ib = 999
		return ia < ib if ia != ib else a < b)
	return out


func item_name(id: String) -> String:
	return get_item(id).get("name", id.capitalize())


## True when a stage fields at least one elite enemy (shown as an elite node).
func stage_has_elite(id: String) -> bool:
	for wave in get_stage(id).get("waves", []):
		for e in wave:
			if get_enemy(String(e.get("enemy", ""))).get("elite", false):
				return true
	return false


## Elements of every enemy in a stage (for the squad element check).
func stage_enemy_elements(id: String) -> Array:
	var out: Array = []
	for wave in get_stage(id).get("waves", []):
		for e in wave:
			var el: String = get_enemy(String(e.get("enemy", ""))).get("element", "")
			if not el.is_empty() and not out.has(el):
				out.append(el)
	return out


func is_tower_stage(id: String) -> bool:
	return towers.has(get_stage(id).get("world_id", ""))


func starter_ids() -> Array[String]:
	var out: Array[String] = []
	for id in characters.keys():
		if characters[id].get("starter", false):
			out.append(id)
	# Fixed presentation order for the three prototype starters
	var order := ["kael_emberclaw", "mira_tidesong", "thorne_mossguard"]
	out.sort_custom(func(a, b): return order.find(a) < order.find(b))
	return out


func balance(section: String, key: String, fallback: Variant) -> Variant:
	return progression.get(section, {}).get(key, fallback)


# ------------------------------------------------------------------ elements
func element_name(element: String) -> String:
	return elements.get(element, {}).get("name", element.capitalize())


func element_color(element: String) -> Color:
	return Color(elements.get(element, {}).get("color", "#cccccc"))


func element_icon(element: String) -> Texture2D:
	return load_texture(elements.get(element, {}).get("icon", ""))


## Returns the damage multiplier when `attacker` element hits `defender` element.
func element_multiplier(attacker: String, defender: String) -> float:
	var att: Dictionary = elements.get(attacker, {})
	var def: Dictionary = elements.get(defender, {})
	if att.get("strong_against", []).has(defender):
		return float(element_config.get("strong_multiplier", 1.25))
	if def.get("strong_against", []).has(attacker):
		return float(element_config.get("weak_multiplier", 0.75))
	return 1.0


# ------------------------------------------------------------------ assets
func load_texture(path: String) -> Texture2D:
	if path.is_empty() or not ResourceLoader.exists(path):
		return null
	return load(path) as Texture2D


## Reads (and caches) the animation metadata JSON produced by tools/make_assets.py
func get_sprite_meta(path: String) -> Dictionary:
	if sprite_meta_cache.has(path):
		return sprite_meta_cache[path]
	var meta := _read_json(path)
	sprite_meta_cache[path] = meta
	return meta


# ------------------------------------------------------------------ loading helpers
func _load_worlds() -> void:
	worlds.clear()
	world_order.clear()
	towers.clear()
	tower_order.clear()
	stages.clear()
	stage_order.clear()
	var story := _load_folder(DATA_ROOT + "/stages").values()
	story.sort_custom(func(a, b): return int(a.get("order", 0)) < int(b.get("order", 0)))
	for world in story:
		worlds[world["id"]] = world
		world_order.append(world["id"])
		for stage in world.get("stages", []):
			stage["world_id"] = world["id"]
			stages[stage["id"]] = stage
			stage_order.append(stage["id"])
	for tower in _load_folder(DATA_ROOT + "/towers").values():
		towers[tower["id"]] = tower
		tower_order.append(tower["id"])
		for floor in tower.get("stages", []):
			floor["world_id"] = tower["id"]
			stages[floor["id"]] = floor
	tower_order.sort()


## Reports broken references between data files (unknown enemies, skills, items...).
func _validate() -> void:
	for c in characters.values():
		for key in ["normal_attack", "burst"]:
			if not skills.has(c.get(key, "")):
				load_errors.append("%s: unknown skill %s" % [c["id"], c.get(key, "")])
		var evo = c.get("evolution")
		if evo is Dictionary:
			if not characters.has(evo.get("into", "")):
				load_errors.append("%s: unknown evolution %s" % [c["id"], evo.get("into", "")])
			for m in evo.get("materials", {}).keys():
				if not items.has(m):
					load_errors.append("%s: unknown material %s" % [c["id"], m])
	for e in enemies.values():
		for key in e.get("skills", {}).keys():
			if not skills.has(e["skills"][key]):
				load_errors.append("%s: unknown skill %s" % [e["id"], e["skills"][key]])
		var dt = e.get("drop_table")
		if dt is String and not drop_tables.has(dt):
			load_errors.append("%s: unknown drop table %s" % [e["id"], dt])
	for st in stages.values():
		for wave in st.get("waves", []):
			for sp in wave:
				var ids: Array = [sp.get("enemy", "")]
				if sp.has("enemy_by_leader_element"):
					ids = sp["enemy_by_leader_element"].values()
				for eid in ids:
					if not enemies.has(eid):
						load_errors.append("%s: unknown enemy %s" % [st["id"], eid])
		for d in st.get("drops", []):
			if not items.has(d.get("item", "")):
				load_errors.append("%s: unknown drop %s" % [st["id"], d.get("item", "")])
	for fid in summon.get("banners", {}).get("standard", {}).get("pool", []):
		if not characters.has(fid):
			load_errors.append("summon pool: unknown hero " + fid)


func _load_folder(path: String) -> Dictionary:
	var out := {}
	for file in _list_json(path):
		var data := _read_json(path + "/" + file)
		if data.has("id"):
			out[data["id"]] = data
		else:
			load_errors.append("Data file without id: %s/%s" % [path, file])
	return out


## Skills live in several files that are merged into one id -> definition map.
func _merge_files(path: String) -> Dictionary:
	var out := {}
	for file in _list_json(path):
		var data := _read_json(path + "/" + file)
		for key in data.keys():
			if not String(key).begins_with("_"):
				out[key] = data[key]
	return out


func _list_json(path: String) -> PackedStringArray:
	var files := PackedStringArray()
	var dir := DirAccess.open(path)
	if dir == null:
		load_errors.append("Missing data folder: " + path)
		return files
	for f in dir.get_files():
		# exported builds may list remapped names; only accept raw json
		if f.ends_with(".json"):
			files.append(f)
	files.sort()
	return files


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		load_errors.append("Missing data file: " + path)
		return {}
	var text := FileAccess.get_file_as_string(path)
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		load_errors.append("Invalid JSON in " + path)
		return {}
	return parsed
