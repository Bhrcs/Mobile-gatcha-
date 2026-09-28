class_name UnitFilter
extends RefCounted
## Filter & sort overlay for the Units grid. The choice is remembered between
## sessions (settings: unit_filter, unit_sort, unit_sort_desc).

const SORTS := [["RECENT", "recent"], ["LEVEL", "level"], ["RARITY", "rarity"], ["POWER", "power"], ["HP", "hp"],
		["ATK", "atk"], ["DEF", "def"], ["REC", "rec"], ["NAME", "name"], ["ELEMENT", "element"]]
const ROLES := ["attacker", "defender", "healer", "support", "breaker"]
const DEFAULT := {"el": "all", "rarity": 0, "role": "", "evolve": false, "fav": false}


static func load_state() -> Dictionary:
	var st := DEFAULT.duplicate()
	var raw := String(GameManager.settings.get("unit_filter", ""))
	if not raw.is_empty():
		var parsed = JSON.parse_string(raw)
		if parsed is Dictionary:
			for k in DEFAULT:
				if parsed.has(k):
					st[k] = parsed[k]
	st["el"] = String(st["el"])
	st["role"] = String(st["role"])
	st["rarity"] = int(st["rarity"])
	st["evolve"] = bool(st["evolve"])
	st["fav"] = bool(st["fav"])
	st["sort"] = String(GameManager.settings.get("unit_sort", "recent"))
	st["desc"] = bool(GameManager.settings.get("unit_sort_desc", true))
	return st


static func save_state(st: Dictionary) -> void:
	var f := {}
	for k in DEFAULT:
		f[k] = st.get(k, DEFAULT[k])
	GameManager.set_setting("unit_filter", JSON.stringify(f))
	GameManager.set_setting("unit_sort", st.get("sort", "recent"))
	GameManager.set_setting("unit_sort_desc", st.get("desc", true))


## Number of active filters (for the FILTER button badge).
static func active_count(st: Dictionary) -> int:
	var n := 0
	for k in DEFAULT:
		if st.get(k) != DEFAULT[k]:
			n += 1
	return n


static func sort_label(st: Dictionary) -> String:
	for s in SORTS:
		if s[1] == st.get("sort", "recent"):
			return "%s %s" % [s[0], "v" if st.get("desc", true) else "^"]
	return "SORT"


static func matches(st: Dictionary, u: Dictionary, def: Dictionary) -> bool:
	if st["el"] != "all" and def.get("element", "") != st["el"]:
		return false
	if int(st["rarity"]) > 0 and int(def.get("rarity", 3)) != int(st["rarity"]):
		return false
	if not String(st["role"]).is_empty() and String(def.get("role", "")).to_lower() != st["role"]:
		return false
	if st["fav"] and not bool(u.get("favorite", false)):
		return false
	if st["evolve"] and not GameManager.can_evolve(u.get("uid", "")):
		return false
	return true


## Comparison for sort_custom on entries {unit, def, idx, stats}.
static func compare(st: Dictionary, a: Dictionary, b: Dictionary) -> bool:
	var ka: Variant = _key(st["sort"], a)
	var kb: Variant = _key(st["sort"], b)
	if ka == kb:
		return int(a["idx"]) > int(b["idx"])
	var less: bool = ka < kb
	# names read A-Z by default; everything else biggest first by default
	if st["sort"] == "name":
		return less if st["desc"] else not less
	return not less if st["desc"] else less


static func _key(sort: String, e: Dictionary) -> Variant:
	match sort:
		"level":
			return int(e["unit"].get("level", 1))
		"rarity":
			return int(e["def"].get("rarity", 3)) * 1000 + int(e["unit"].get("level", 1))
		"power":
			return GameManager.unit_power(e["unit"])
		"hp", "atk", "def", "rec":
			return int(e["stats"].get(sort, 0))
		"name":
			return String(e["def"].get("name", ""))
		"element":
			return ["nature", "water", "fire"].find(e["def"].get("element", ""))
	return int(e["idx"])


## Opens the overlay. on_apply(state) is called whenever something changes.
static func open(parent: Control, st: Dictionary, on_apply: Callable) -> FantasyPopup:
	var p := FantasyPopup.open(parent, "FILTER & SORT", 980)
	p.name = "FilterPopup"
	p.tap_outside_closes = true
	var body := UIKit.vbox(UIKit.SP_M)
	p.content.add_child(body)
	# ctx is shared by reference, so every button can rebuild the overlay
	var ctx := {"st": st, "body": body, "on_apply": on_apply}
	_fill(ctx)
	var row := UIKit.hbox(UIKit.SP_XL)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var reset := UIKit.btn("RESET", "quiet", Vector2(300, 110))
	reset.name = "FilterReset"
	reset.pressed.connect(func():
		for k in DEFAULT:
			st[k] = DEFAULT[k]
		st["sort"] = "recent"
		st["desc"] = true
		save_state(st)
		on_apply.call(st)
		_fill(ctx))
	var done := UIKit.btn("DONE", "primary", Vector2(300, 110))
	done.name = "FilterDone"
	done.pressed.connect(p.close)
	row.add_child(reset)
	row.add_child(done)
	p.content.add_child(row)
	p.default_action = p.close
	return p


static func _fill(ctx: Dictionary) -> void:
	var st: Dictionary = ctx["st"]
	var body: VBoxContainer = ctx["body"]
	for c in body.get_children():
		body.remove_child(c)
		c.queue_free()
	body.add_child(_section("ELEMENT"))
	body.add_child(_choices(ctx, "el", ["all", "fire", "water", "nature"], "Filter_el_"))
	body.add_child(_section("RARITY"))
	body.add_child(_choices(ctx, "rarity", [0, 3, 4, 5], "Filter_rarity_"))
	body.add_child(_section("ROLE"))
	body.add_child(_choices(ctx, "role", [""] + ROLES, "Filter_role_", 3))
	var toggles := UIKit.hbox(UIKit.SP_L)
	for t in [["CAN EVOLVE", "evolve"], ["FAVORITES", "fav"]]:
		var key: String = t[1]
		var b := UIKit.btn(t[0], "reward" if st[key] else "quiet", Vector2(0, 92))
		b.name = "Filter_" + key
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.pressed.connect(_pick.bind(ctx, key, not st[key]))
		toggles.add_child(b)
	body.add_child(toggles)
	body.add_child(UIKit.separator())
	var sh := UIKit.hbox(UIKit.SP_M)
	var sl := _section("SORT BY")
	sl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sh.add_child(sl)
	var dir_text := ("HIGH FIRST" if st["desc"] else "LOW FIRST") if st["sort"] != "name" else ("A - Z" if st["desc"] else "Z - A")
	var dir := UIKit.btn(dir_text, "secondary", Vector2(300, 88))
	dir.name = "SortDirection"
	dir.pressed.connect(_pick.bind(ctx, "desc", not st["desc"]))
	sh.add_child(dir)
	body.add_child(sh)
	var keys: Array = []
	for s2 in SORTS:
		keys.append(s2[1])
	body.add_child(_choices(ctx, "sort", keys, "Sort_", 5))


static func _pick(ctx: Dictionary, key: String, value: Variant) -> void:
	ctx["st"][key] = value
	save_state(ctx["st"])
	ctx["on_apply"].call(ctx["st"])
	_fill.call_deferred(ctx)


static func _label_of(key: String, v: Variant) -> String:
	match key:
		"el":
			return "ALL" if v == "all" else Database.element_name(v).to_upper()
		"rarity":
			return "ALL" if int(v) == 0 else "%d STAR" % int(v)
		"role":
			return "ALL" if String(v).is_empty() else String(v).to_upper()
		"sort":
			for s3 in SORTS:
				if s3[1] == v:
					return s3[0]
	return str(v)


static func _section(text: String) -> Label:
	return UIKit.label(text, UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5)


static func _choices(ctx: Dictionary, key: String, values: Array, prefix: String, cols := 4) -> GridContainer:
	var g := GridContainer.new()
	g.columns = cols if values.size() > cols else values.size()
	g.add_theme_constant_override("h_separation", UIKit.SP_S)
	g.add_theme_constant_override("v_separation", UIKit.SP_S)
	for v in values:
		var on: bool = v == ctx["st"][key]
		var text := _label_of(key, v)
		var b := UIKit.btn(text, "reward" if on else "quiet", Vector2(900.0 / g.columns - UIKit.SP_S, 84))
		b.name = prefix + str(v)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", UIKit.T_BODY if text.length() < 9 else UIKit.T_SMALL)
		b.pressed.connect(_pick.bind(ctx, key, v))
		g.add_child(b)
	return g
