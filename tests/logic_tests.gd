extends Node
## Headless rules tests. Run:  godot --headless res://tests/logic_tests.tscn
## Exit code 0 = all passed.

var passed := 0
var failed: PackedStringArray = []


func _ready() -> void:
	SaveManager.save_path = "user://logic_test_save.json"
	SaveManager.settings_path = "user://logic_test_settings.json"
	for m in get_method_list():
		var n: String = m["name"]
		if n.begins_with("test_"):
			var before := failed.size()
			await call(n)
			print(("PASS  " if failed.size() == before else "FAIL  ") + n)
	SaveManager.delete_profile()
	print("\n%d checks passed, %d failed" % [passed, failed.size()])
	for f in failed:
		print("  - ", f)
	GameManager.quit_game(0 if failed.is_empty() else 1)


func check(cond: bool, what: String) -> void:
	if cond:
		passed += 1
	else:
		failed.append(what)


func _player(char_id := "kael_emberclaw", level := 1) -> Combatant:
	return Combatant.from_player_unit({"uid": "t", "char_id": char_id, "level": level, "exp": 0}, 0)


func _with_combat(key: String, value: Variant, fn: Callable) -> void:
	var cfg: Dictionary = Database.progression["combat"]
	var old = cfg[key]
	cfg[key] = value
	await fn.call()
	cfg[key] = old


# ------------------------------------------------------------------ data
func test_data_loaded() -> void:
	check(Database.load_errors.is_empty(), "no data load errors: %s" % [Database.load_errors])
	check(Database.starter_ids() == ["kael_emberclaw", "mira_tidesong", "thorne_mossguard"], "three starters in order")
	check(Database.enemies.size() >= 16, "12-18+ enemy variants (%d)" % Database.enemies.size())
	check(Database.stage_order.size() == 20, "two worlds of ten stages")
	check(Database.tower_order.size() == 3, "three elemental towers")
	check(Database.family_ids().size() == 12, "twelve hero families")
	for el in ["fire", "water", "nature"]:
		var n := 0
		for fam in Database.family_ids():
			if Database.get_character(Database.family_forms(fam)[0]).get("element", "") == el:
				n += 1
		check(n == 4, "four %s heroes" % el)
	for sid in Database.stage_order:
		for wave in Database.get_stage(sid)["waves"]:
			for spawn in wave:
				var ids: Array = spawn.get("enemy_by_leader_element", {}).values() if spawn.has("enemy_by_leader_element") else [spawn["enemy"]]
				for eid in ids:
					check(not Database.get_enemy(eid).is_empty(), "%s enemy %s exists" % [sid, eid])
	for cid in Database.characters:
		var c: Dictionary = Database.characters[cid]
		check(not Database.get_skill(c["normal_attack"]).is_empty() and not Database.get_skill(c["burst"]).is_empty(), cid + " skills exist")
		var frames := SpriteFactory.unit_frames(c["sprite"])
		for anim in ["idle", "attack", "hit", "victory", "ko", "burst"]:
			check(frames.has_animation(anim), "%s has %s animation" % [cid, anim])
		check(frames.get_frame_count("idle") == 4, cid + " idle is 4 frames")
		check(frames.get_frame_count("attack") >= 5 and frames.get_frame_count("attack") <= 8, cid + " attack 5-8 frames")
		check(frames.get_frame_count("burst") >= 8 and frames.get_frame_count("burst") <= 12, cid + " burst 8-12 frames")
	for eid in Database.enemies:
		var frames := SpriteFactory.unit_frames(Database.enemies[eid]["sprite"])
		for anim in ["idle", "attack", "hit", "death"]:
			check(frames.has_animation(anim), "%s has %s animation" % [eid, anim])


# ------------------------------------------------------------------ elements & damage
func test_element_chart() -> void:
	check(Database.element_multiplier("fire", "nature") == 1.25, "fire > nature")
	check(Database.element_multiplier("nature", "water") == 1.25, "nature > water")
	check(Database.element_multiplier("water", "fire") == 1.25, "water > fire")
	check(Database.element_multiplier("fire", "water") == 0.75, "fire resisted by water")
	check(Database.element_multiplier("fire", "fire") == 1.0, "same element neutral")


func test_damage_tags_and_variance() -> void:
	var kael := _player()
	var pup := Combatant.from_enemy("bramble_pup", 1, 0)
	var tide := Combatant.from_enemy("tidefin", 1, 0)
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	await _with_combat("crit_chance", 0.0, func():
		var skill := Database.get_skill("ember_slash")
		var weak := DamageCalculator.calculate(kael, pup, skill, rng)
		var resist := DamageCalculator.calculate(kael, tide, skill, rng)
		check(weak["tag"] == "WEAK", "WEAK tag vs nature")
		check(resist["tag"] == "RESIST", "RESIST tag vs water")
		# variance stays within 95%..105% of the expected value
		var expected := (145.0 * 1.1 - 35 * 0.3) * 1.25     # Kael's passive: ATK +10% above 70% HP
		for i in 50:
			var d := DamageCalculator.calculate(kael, pup, skill, rng)
			check(d["total"] >= floor(expected * 0.95) - 1 and d["total"] <= ceil(expected * 1.05) + 1, "variance within 5%")
		check(weak["hits"].size() == 2, "ember slash splits into 2 hits"))


func test_crit_and_min_damage() -> void:
	var kael := _player()
	var slime := Combatant.from_enemy("cinder_slime", 1, 0)
	var rng := RandomNumberGenerator.new()
	await _with_combat("crit_chance", 1.0, func():
		var d := DamageCalculator.calculate(kael, slime, Database.get_skill("ember_slash"), rng)
		check(d["crit"], "forced crit")
		var base := 145.0 * 1.1 - 20 * 0.3
		check(d["total"] >= floor(base * 1.5 * 0.95), "crit deals 150%"))
	# huge defence still takes minimum damage
	var wall := Combatant.from_enemy("cinder_slime", 1, 0)
	wall.base_stats["def"] = 99999
	var d2 := DamageCalculator.calculate(kael, wall, Database.get_skill("ember_slash"), rng)
	check(d2["total"] >= 2, "minimum damage enforced (%d)" % d2["total"])


func test_split_hits() -> void:
	for total in [1, 7, 100, 999]:
		for hits in [1, 2, 3, 6]:
			var parts := DamageCalculator.split_hits(total, hits, [1, 1, 1, 1.5, 1.5, 2])
			var s := 0
			for p in parts:
				s += p
				check(p >= 1, "each hit at least 1")
			check(parts.size() == hits, "hit count")
			if total >= hits:
				check(s == total, "hits sum to total (%d/%d)" % [total, hits])


func test_guard_and_reduction() -> void:
	var slime := Combatant.from_enemy("cinder_slime", 5, 0)
	var thorne := _player("thorne_mossguard")
	var rng := RandomNumberGenerator.new()
	await _with_combat("crit_chance", 0.0, func():
		await _with_combat("variance_min", 1.0, func():
			await _with_combat("variance_max", 1.0, func():
				var skill := Database.get_skill("slime_tackle")
				var normal: int = DamageCalculator.calculate(slime, thorne, skill, rng)["total"]
				thorne.guarding = true
				var guarded: int = DamageCalculator.calculate(slime, thorne, skill, rng)["total"]
				check(abs(guarded - normal * 0.35) <= 1, "guard halves damage, Thorne's passive adds 15%% (%d vs %d)" % [guarded, normal])
				thorne.guarding = false
				thorne.add_status("damage_reduction", 0.4, 2)
				var reduced: int = DamageCalculator.calculate(slime, thorne, skill, rng)["total"]
				check(abs(reduced - normal * 0.6) <= 1, "bastion reduces 40%"))))


# ------------------------------------------------------------------ burst
func test_burst_exactly_100() -> void:
	var kael := _player()
	check(not kael.burst_ready(), "starts empty")
	kael.add_burst(99)
	check(not kael.burst_ready(), "99 is not ready")
	kael.add_burst(1)
	check(kael.burst == 100.0 and kael.burst_ready(), "exactly 100 is ready")
	kael.add_burst(50)
	check(kael.burst == 100.0, "clamped at 100")
	var m := BattleModel.new()
	m.setup("ashroot_01", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 1, "exp": 0}], 1)
	var p: Combatant = m.players[0]
	p.add_burst(100)
	var plan := m.plan_action(p, p.burst_skill, m.enemies[0], true)
	check(p.burst == 0.0, "burst resets when used")
	m.resolve_instant(plan)
	check(p.burst == 0.0, "burst does not gain from its own use")
	check(plan["targets"][0]["hits"].size() == 6, "inferno break has 6 hits")


func test_burst_gain_sources() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_01", [{"uid": "u1", "char_id": "mira_tidesong", "level": 1, "exp": 0}], 3)
	var p: Combatant = m.players[0]
	m.resolve_instant(m.plan_action(p, p.normal_skill, m.enemies[0]))
	check(p.burst == 34.0, "normal attack gives 34 (%s)" % p.burst)
	var e: Combatant = m.enemies[0]
	m.resolve_instant(m.plan_action(e, e.normal_skill, p))
	check(p.burst == 40.0, "taking damage gives 6 once per attack (%s)" % p.burst)
	m.start_player_phase()
	m.guard(p)
	check(p.burst == 55.0, "guard gives 15")


# ------------------------------------------------------------------ multi-hit / death edge cases
func test_enemy_dies_mid_combo() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_02", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 10, "exp": 0}], 9)
	var p: Combatant = m.players[0]
	var e: Combatant = m.enemies[0]
	e.hp = 5
	var xp_before := m.xp_earned
	var plan := m.plan_action(p, p.burst_skill, e, true)
	var results: Array = []
	for hi in plan["targets"][0]["hits"].size():
		results.append(m.apply_hit(plan, 0, hi))
	check(results[0]["killed"], "first hit kills")
	for i in range(1, results.size()):
		check(results[i]["skipped"], "later hits skipped")
	check(e.hp == 0, "hp not negative")
	check(m.enemies_defeated == 1 and m.xp_earned > xp_before, "kill rewarded exactly once")
	m.finish_action(plan)
	check(not e.has_status("burn"), "dead enemies cannot be burned")


func test_player_dies_during_enemy_attack() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_10", [{"uid": "u1", "char_id": "mira_tidesong", "level": 1, "exp": 0}], 4)
	m.advance_wave()
	var p: Combatant = m.players[0]
	var boss: Combatant = m.enemies[0]
	p.hp = 3
	var plan := m.plan_action(boss, "verdant_rampage", p)
	m.resolve_instant(plan)
	check(not p.is_alive() and p.hp == 0, "player KO'd")
	check(m.all_players_dead(), "defeat detected")
	check(p.burst == 0.0, "KO clears burst")
	check(not m.players_can_act(), "KO'd unit cannot act")


func test_retarget_dead_target() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_02", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 1, "exp": 0}], 2)
	var dead: Combatant = m.enemies[0]
	dead.take_damage(99999)
	var plan := m.plan_action(m.players[0], "ember_slash", dead)
	check(plan["targets"].size() == 1 and plan["targets"][0]["unit"] == m.enemies[1], "retargets to living enemy")


# ------------------------------------------------------------------ statuses
func test_burn_and_buffs() -> void:
	var e := Combatant.from_enemy("bramble_pup", 1, 0)
	e.add_status("burn", 0.0, 3)
	var total := 0
	for i in 4:
		for ev in e.tick_statuses():
			total += 1
			check(ev["amount"] == int(round(e.max_hp * 0.05)), "burn is 5% max hp")
	check(total == 3, "burn ticks 3 times")
	check(not e.has_status("burn"), "burn expires")
	var t := _player("thorne_mossguard")
	var base_def := t.get_stat("def")
	t.add_status("def_up", 0.3, 3)
	check(is_equal_approx(t.get_stat("def"), base_def * 1.3), "def up +30%")
	t.add_status("burn", 0.0, 3)
	t.cleanse(1)
	check(not t.has_status("burn") and t.has_status("def_up"), "cleanse removes only negatives")


func test_support_bursts() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_01", [{"uid": "u1", "char_id": "mira_tidesong", "level": 1, "exp": 0}], 6)
	var mira: Combatant = m.players[0]
	mira.hp = 100
	mira.add_status("burn", 0.0, 3)
	mira.add_burst(100)
	m.resolve_instant(m.plan_action(mira, mira.burst_skill, null, true))
	# 25% max HP + REC (leader skill REC +8%), boosted 10% by Mira's own "healing received" passive
	check(mira.hp == 100 + int(round((650 * 0.25 + 150 * 1.08) * 1.1)), "heal = 25%% max HP + REC (%d)" % mira.hp)
	check(not mira.has_status("burn"), "restoring current cleanses")
	check(mira.has_status("def_up"), "restoring current grants DEF up")
	var m2 := BattleModel.new()
	m2.setup("ashroot_01", [{"uid": "u1", "char_id": "thorne_mossguard", "level": 1, "exp": 0}], 6)
	var th: Combatant = m2.players[0]
	th.add_burst(100)
	m2.resolve_instant(m2.plan_action(th, th.burst_skill, null, true))
	check(th.has_status("def_up") and th.has_status("damage_reduction") and th.has_status("taunt"), "bastion statuses")
	check(th.taunt_weight() > 1.0, "taunt raises target weight")


func test_taunt_targeting() -> void:
	var a := _player("kael_emberclaw")
	var b := _player("thorne_mossguard")
	b.add_status("taunt", 1.0, 2)
	var slime := Combatant.from_enemy("cinder_slime", 1, 0)
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	var hits_b := 0
	for i in 1000:
		if EnemyAI.choose_target(slime, [a, b], rng) == b:
			hits_b += 1
	check(hits_b > 700, "taunted unit targeted far more often (%d/1000)" % hits_b)


# ------------------------------------------------------------------ progression
func test_leveling() -> void:
	var unit := {"uid": "u1", "char_id": "kael_emberclaw", "level": 1, "exp": 0}
	var ups := Progression.add_unit_xp(unit, 49)
	check(ups.is_empty() and unit["level"] == 1, "49 xp is not enough")
	ups = Progression.add_unit_xp(unit, 1)
	check(ups.size() == 1 and unit["level"] == 2 and unit["exp"] == 0, "level 2 at 50 xp")
	check(ups[0]["gains"] == {"hp": 28, "atk": 5, "def": 3, "rec": 2}, "gains match growth")
	check(Progression.xp_to_next(2) > Progression.xp_to_next(1), "xp curve increases")
	Progression.add_unit_xp(unit, 10_000_000)
	check(unit["level"] == 15 and unit["exp"] == 0, "3-star caps at level 15 (%d)" % unit["level"])
	var five := {"uid": "u5", "char_id": "seraphine_pyrelance", "level": 1, "exp": 0}
	Progression.add_unit_xp(five, 10_000_000)
	check(five["level"] == 35, "5-star caps at level 35 (%d)" % five["level"])


func test_enemy_scaling_and_loot() -> void:
	var def := Database.get_enemy("cinder_slime")
	var l1 := Progression.enemy_stats(def, 1)
	var l7 := Progression.enemy_stats(def, 7)
	check(l1["hp"] == 180 and l1["atk"] == 40, "level 1 uses base stats")
	check(l7["hp"] > l1["hp"] and l7["atk"] > l1["atk"], "higher level is stronger")
	var rng := RandomNumberGenerator.new()
	rng.seed = 1
	var shards := 0
	for i in 400:
		var loot := Progression.roll_enemy_loot(def, 1, rng)
		check(loot["gold"] >= 6, "gold drop")
		shards += int(loot["items"].get("ember_fragment", 0))
	check(shards > 40 and shards < 140, "ember fragment drop rate ~22%% (%d/400)" % shards)
	# boss tables always give their guaranteed drops
	for i in 20:
		var b := Progression.roll_table("fire_boss", rng)
		check(b.get("flame_core", 0) >= 1 and b.get("ember_wisp", 0) >= 1, "boss guaranteed drops")


# ------------------------------------------------------------------ saves
func test_save_roundtrip_and_unlocks() -> void:
	GameManager.new_game("mira_tidesong")
	check(GameManager.party_units().size() == 1, "starter in party")
	check(GameManager.is_stage_unlocked("ashroot_01") and not GameManager.is_stage_unlocked("ashroot_02"), "only stage 1 unlocked")
	var summary := GameManager.apply_victory("ashroot_01", 20, 30, {"tide_fragment": 2})
	check(GameManager.is_stage_unlocked("ashroot_02"), "stage 2 unlocked after clear")
	check(summary["first_clear"], "first clear flagged")
	check(GameManager.item_count("tide_fragment") == 2, "items added to inventory")
	var gold := GameManager.gold()
	GameManager.profile = {}
	check(GameManager.continue_game(), "continue works")
	check(GameManager.gold() == gold and GameManager.item_count("tide_fragment") == 2, "gold + items persisted")
	check(GameManager.is_stage_cleared("ashroot_01"), "clear persisted")
	var again := GameManager.apply_victory("ashroot_01", 0, 0, {})
	check(not again["first_clear"], "second clear is not first clear")


func test_train_unit() -> void:
	GameManager.new_game("kael_emberclaw")
	var uid: String = GameManager.party_uids()[0]
	check(GameManager.train_unit(uid).is_empty(), "cannot train without gold")
	GameManager.add_gold(10000)
	var cost := Progression.train_cost(GameManager.get_unit(uid))
	var up := GameManager.train_unit(uid)
	check(not up.is_empty() and GameManager.get_unit(uid)["level"] == 2, "training levels up")
	check(GameManager.gold() == 10000 - cost, "training costs gold")
	check(not GameManager.toggle_party(uid), "cannot remove the last party member")


func test_save_corruption_handling() -> void:
	GameManager.new_game("thorne_mossguard")
	GameManager.add_gold(123)
	GameManager.save()
	GameManager.save()       # second save creates a backup of the first
	# 1) garbage main file -> recovers from backup
	var f := FileAccess.open(SaveManager.save_path, FileAccess.WRITE)
	f.store_string("{this is not json")
	f.close()
	var p := SaveManager.load_profile()
	check(SaveManager.last_load_status == "recovered_backup" and p["starter_id"] == "thorne_mossguard", "backup recovery")
	# 2) both corrupted -> empty profile, no crash
	for path in [SaveManager.save_path, SaveManager.save_path + ".bak"]:
		var g := FileAccess.open(path, FileAccess.WRITE)
		g.store_string("\u0001\u0002garbage")
		g.close()
	p = SaveManager.load_profile()
	check(p.is_empty() and SaveManager.last_load_status == "corrupted", "corruption detected safely")
	check(not GameManager.continue_game(), "continue refuses corrupted save")
	# 3) missing fields / wrong types are repaired
	var clean := SaveManager.sanitize_profile({"starter_id": "kael_emberclaw", "player": {"gold": "lots"}, "units": "nope",
			"party": [42], "inventory": {"fire_shard": -5, "unknown_item": 3}, "stages": {"cleared": ["ashroot_01", "bogus"]}})
	check(clean["units"].size() == 1 and clean["units"][0]["char_id"] == "kael_emberclaw", "starter unit restored")
	check(clean["party"].size() == 1, "party repaired")
	check(clean["player"]["gold"] == 0, "bad gold -> 0")
	check(not clean["inventory"].has("unknown_item") and not clean["inventory"].has("fire_shard")
			and int(clean["inventory"].get("ember_fragment", 0)) == 0, "invalid items dropped")
	check(clean["stages"]["unlocked"].has("ashroot_02") and not clean["stages"]["cleared"].has("bogus"), "stages repaired")
	var empty := SaveManager.sanitize_profile({})
	check(empty.has("tutorial") and empty.has("stats") and empty["stages"]["unlocked"] == ["ashroot_01"], "empty dict repaired")
	# 4) settings file garbage
	var s := FileAccess.open(SaveManager.settings_path, FileAccess.WRITE)
	s.store_string("[1,2,3]")
	s.close()
	check(SaveManager.load_settings()["master_volume"] == 0.8, "settings fall back to defaults")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SaveManager.settings_path))


# ------------------------------------------------------------------ Phase 4: roster data
func test_roster_and_evolution_data() -> void:
	for fam in Database.family_ids():
		var forms := Database.family_forms(fam)
		check(forms.size() >= 1 and forms.size() <= 3, fam + " has 1-3 forms")
		var prev_sheet := ""
		var prev_r := 0
		for i in forms.size():
			var c := Database.get_character(forms[i])
			var r := int(c.get("rarity", 0))
			check(r >= 3 and r <= 5, forms[i] + " rarity 3-5")
			check(r > prev_r, forms[i] + " rarity increases along the path")
			check(c["sprite"]["sheet"] != prev_sheet, forms[i] + " evolution changes the sprite")
			prev_sheet = c["sprite"]["sheet"]
			prev_r = r
			for key in ["role", "passive", "leader_skill", "lore", "normal_attack", "burst"]:
				check(c.has(key) and not str(c[key]).is_empty(), "%s has %s" % [forms[i], key])
			check(int(c.get("max_level", 0)) == int(Database.progression["max_level_by_rarity"][str(r)]), forms[i] + " max level by rarity")
			var evo = c.get("evolution")
			if i < forms.size() - 1:
				check(evo is Dictionary and evo.get("into", "") == forms[i + 1], forms[i] + " evolves into next form")
				for m in evo.get("materials", {}).keys():
					check(Database.items.has(m), "%s material %s exists" % [forms[i], m])
					check(not GameManager.item_sources(m).is_empty() or m == "prism_shard", "%s has an Obtained From source" % m)
			else:
				check(evo == null or (evo is Dictionary and evo.is_empty()), forms[i] + " is a final form")
			check(Database.load_texture(c["portrait"]) != null, forms[i] + " portrait loads")
	var banner := GameManager.summon_banner("standard")
	var hr := SummonSystem.hero_rates(banner)
	var sum := 0.0
	for k in hr:
		sum += hr[k]
	check(absf(sum - 1.0) < 0.0001, "per-hero summon rates sum to 100%")
	check(hr.size() == 12, "every family is summonable")


func test_stage_and_tower_data() -> void:
	for sid in Database.stages.keys():
		var st := Database.get_stage(sid)
		check(int(st.get("energy", 0)) > 0, sid + " costs energy")
		check(int(st.get("recommended_power", 0)) > 0, sid + " has recommended power")
		check(st.get("stars", []).size() == 3, sid + " has 3 star objectives")
		if not Database.is_tower_stage(sid):
			var gems := int(st.get("first_clear", {}).get("gems", 0))
			check(gems == (25 if st.get("boss", false) else 5), "%s first-clear gems (%d)" % [sid, gems])
	for tid in Database.tower_order:
		var floors: Array = Database.towers[tid]["stages"]
		check(floors.size() == 10, tid + " has 10 floors")
		for i in range(1, floors.size()):
			check(int(floors[i]["energy"]) >= int(floors[i - 1]["energy"]), tid + " energy escalates")
			check(int(floors[i]["recommended_power"]) >= int(floors[i - 1]["recommended_power"]), tid + " difficulty escalates")
		check(floors[4].get("boss", false) and floors[9].get("boss", false), tid + " floors 5 and 10 are bosses")
	var w2: Dictionary = Database.worlds.get("saltglass_reach", {})
	check(w2.get("stages", []).size() == 10, "world 2 has 10 stages")
	check(w2.get("stages", [])[9].get("boss", false), "world 2 ends in a boss")


# ------------------------------------------------------------------ Phase 4: energy & rank
func test_energy_regen_and_clamp() -> void:
	GameManager.clock_override = 1_600_000_000.0
	GameManager.new_game("kael_emberclaw")
	var mx := GameManager.max_energy()
	check(mx == 20 and GameManager.energy() == mx, "new game starts with full energy")
	check(GameManager.spend_energy(10) and GameManager.energy() == 10, "spend energy")
	GameManager.clock_override += 180 * 3 + 5
	check(GameManager.energy() == 13, "regenerates 1 per 3 minutes (%d)" % GameManager.energy())
	check(GameManager.energy_seconds_to_next() > 0 and GameManager.energy_seconds_to_next() <= 180, "timer to next point")
	# offline: quit and come back 20 minutes later
	GameManager.save()
	GameManager.profile = {}
	GameManager.clock_override += 180 * 4
	check(GameManager.continue_game() and GameManager.energy() == 17, "offline regeneration (%d)" % GameManager.energy())
	GameManager.clock_override += 86400 * 30
	check(GameManager.energy() == mx, "clamped at max after a long absence")
	GameManager.clock_override -= 86400 * 400      # system clock moved backwards
	check(GameManager.energy() == mx, "clock going backwards is safe")
	check(GameManager.spend_energy(mx) and GameManager.energy() == 0, "spend to zero")
	GameManager.clock_override -= 5000
	check(GameManager.energy() == 0, "never negative")
	check(not GameManager.begin_stage("ashroot_01") and GameManager.energy() == 0, "cannot start a stage without energy")
	GameManager.clock_override += 180 * 3
	check(GameManager.begin_stage("ashroot_01"), "can start once energy returns (%d, %s)" % [GameManager.energy(), GameManager.is_stage_unlocked("ashroot_01")])
	GameManager.clock_override = -1.0


func test_rank_up_rewards() -> void:
	GameManager.new_game("mira_tidesong")
	GameManager.spend_energy(15)
	var gems_before := GameManager.gems()
	var xp := 0
	for r in range(1, 5):
		xp += Progression.rank_xp_to_next(r)
	var res := GameManager._add_rank_xp(xp)
	check(GameManager.rank() == 5 and res["ups"].size() == 4, "rank 1 -> 5")
	check(GameManager.energy() == GameManager.max_energy(), "rank up restores energy")
	check(GameManager.max_energy() == 22, "max energy grows with rank (%d)" % GameManager.max_energy())
	check(GameManager.gems() == gems_before + 50, "rank 5 milestone gives gems")


# ------------------------------------------------------------------ Phase 4: training, burst, evolution
func test_training_with_wisps() -> void:
	GameManager.new_game("kael_emberclaw")
	var uid: String = GameManager.party_uids()[0]
	var pv := GameManager.preview_training(uid, {"ember_wisp": 1})
	check(pv["xp"] == 900, "same-element wisp gives +50%% (%d)" % pv["xp"])
	check(pv["level_after"] > pv["level_before"], "preview shows the new level")
	check(pv["gains"]["atk"] > 0, "preview shows stat gains")
	check(not GameManager.train_unit_with(uid, {"ember_wisp": 1})["ok"], "needs gold")
	GameManager.add_gold(100000)
	var gold := GameManager.gold()
	var r := GameManager.train_unit_with(uid, {"ember_wisp": 1})
	check(r["ok"] and GameManager.get_unit(uid)["level"] == pv["level_after"], "training applies the preview")
	check(GameManager.gold() == gold - int(pv["gold"]) and GameManager.item_count("ember_wisp") == 0, "costs gold + wisp")
	check(not GameManager.train_unit_with(uid, {"ember_wisp": 1})["ok"], "cannot use wisps you don't own")
	GameManager.add_item("radiant_wisp", 50)
	GameManager.train_unit_with(uid, {"radiant_wisp": 20})
	check(GameManager.get_unit(uid)["level"] == 15, "trains up to the level cap")
	var capped := GameManager.preview_training(uid, {"radiant_wisp": 1})
	check(capped["at_cap"] and not GameManager.train_unit_with(uid, {"radiant_wisp": 1})["ok"], "no training past the cap")
	# overflow is not charged
	GameManager.new_game("kael_emberclaw")
	uid = GameManager.party_uids()[0]
	GameManager.add_item("radiant_wisp", 50)
	var big := GameManager.preview_training(uid, {"radiant_wisp": 50})
	check(big["wasted_xp"] > 0 and big["used_xp"] == Progression.xp_to_cap(GameManager.get_unit(uid)), "overflow XP reported")


func test_burst_levels() -> void:
	GameManager.new_game("kael_emberclaw")
	var uid: String = GameManager.party_uids()[0]
	check(GameManager.get_unit(uid)["burst_level"] == 1, "burst starts at Lv.1")
	GameManager.add_burst_xp(uid, 4)
	check(GameManager.get_unit(uid)["burst_level"] == 2, "4 burst uses -> Lv.2")
	GameManager.add_burst_xp(uid, 999)
	check(GameManager.get_unit(uid)["burst_level"] == 5, "capped at Lv.5")
	check(not GameManager.train_burst(uid, "sigil")["ok"], "no training past Lv.5")
	var skill := Database.get_skill(Database.get_character("kael_emberclaw")["burst"])
	var s5 := Progression.scaled_burst(skill, 5)
	check(float(s5["power"]) > float(skill["power"]), "Burst Lv.5 hits harder")
	var seen := {}
	for cid in Database.characters:
		var b := Database.get_skill(Database.characters[cid]["burst"])
		seen[JSON.stringify(b.get("level_bonus", {}))] = true
		check(not b.get("level_bonus", {}).is_empty(), cid + " burst has level bonuses")
	check(seen.size() >= 6, "burst upgrades are not all identical (%d kinds)" % seen.size())
	GameManager.new_game("mira_tidesong")
	uid = GameManager.party_uids()[0]
	GameManager.add_item("spark_sigil", 1)
	check(GameManager.train_burst(uid, "sigil")["ok"] and GameManager.item_count("spark_sigil") == 0, "spark sigil trains burst")
	check(not GameManager.train_burst(uid, "shards")["ok"], "shards needed")


func test_evolution() -> void:
	GameManager.new_game("kael_emberclaw")
	var uid: String = GameManager.party_uids()[0]
	var st := GameManager.evolution_status(uid)
	check(not st["ok"] and st["into"] == "kael_blazeheart", "evolution preview known but locked")
	GameManager.profile["stages"]["cleared"].append("ashroot_08")
	GameManager.get_unit(uid)["level"] = 15
	GameManager.get_unit(uid)["burst_level"] = 3
	st = GameManager.evolution_status(uid)
	check(not st["ok"] and not st["missing"].is_empty(), "missing materials reported")
	for m in st["materials"].keys():
		GameManager.add_item(m, int(st["materials"][m]), false)
	GameManager.add_gold(st["gold"])
	check(GameManager.can_evolve(uid), "can evolve with materials, gold and max level")
	var r := GameManager.evolve(uid)
	var u := GameManager.get_unit(uid)
	check(r["ok"] and u["char_id"] == "kael_blazeheart" and u["level"] == 1, "evolved to the next form at Lv.1")
	check(u["burst_level"] == 3, "burst level kept")
	check(GameManager.gold() == 0 and GameManager.item_count("ember_fragment") == 0, "materials and gold consumed")
	check(GameManager.party_uids().has(uid), "evolved hero stays in the squad")
	u["level"] = 25
	check(GameManager.evolution_status(uid)["into"] == "kael_cinderlord", "second evolution to 5-star")
	GameManager.get_unit(uid)["char_id"] = "kael_cinderlord"
	check(GameManager.evolution_status(uid).get("final", false), "final form cannot evolve")


# ------------------------------------------------------------------ Phase 4: squad & summon
func test_squad_rules() -> void:
	GameManager.new_game("thorne_mossguard")
	var uids: Array = [GameManager.party_uids()[0]]
	for cid in ["kael_emberclaw", "mira_tidesong", "wren_briarshot", "corin_saltmarsh", "rhea_flintwhistle"]:
		uids.append(GameManager._add_unit(cid))
	for i in range(1, 6):
		GameManager.toggle_party(uids[i])
	check(GameManager.party_uids().size() == 5, "squad holds 5")
	check(not GameManager.party_uids().has(uids[5]), "sixth hero rejected")
	check(GameManager.toggle_party(uids[1]) and not GameManager.is_in_party(uids[1]), "remove from squad")
	check(GameManager.toggle_party(uids[5]), "add after freeing a slot")
	var seen := {}
	for uid in GameManager.party_uids():
		check(not seen.has(uid), "no duplicate instance in the squad")
		seen[uid] = true
	check(GameManager.set_leader(uids[5]) and GameManager.leader_uid() == uids[5], "set leader")
	check(not GameManager.leader_skill().is_empty(), "leader skill comes from the leader")
	check(GameManager.swap_party_slots(0, 1) and GameManager.leader_uid() != uids[5], "swap slots")
	check(GameManager.squad_power() > 0, "squad power computed")


func test_summon_and_duplicates() -> void:
	GameManager.new_game("kael_emberclaw")
	check(not GameManager.summon("standard", 1)["ok"], "summon locked before 1-9")
	GameManager.profile["stages"]["cleared"].append("ashroot_09")
	check(not GameManager.summon("standard", 1)["ok"] and GameManager.gems() == 0, "not enough gems: nothing spent")
	GameManager.add_gems(1100)
	var r := GameManager.summon("standard", 10)
	check(r["ok"] and r["results"].size() == 10 and GameManager.gems() == 100, "10x summon costs 1000")
	var fams := {}
	for u in GameManager.owned_units():
		var f: String = Database.get_character(u["char_id"])["family"]
		check(not fams.has(f), "no duplicate family owned")
		fams[f] = true
	var shards := 0
	for e in r["results"]:
		shards += int(e["shards"])
		if e["char_id"] == "kael_emberclaw":
			check(not e["is_new"] and e["shards"] == 10, "owned starter converts to shards")
	check(GameManager.soul_shards() == shards, "duplicate shards credited")
	check(GameManager.profile["codex"].size() == fams.size(), "codex tracks owned families")
	# saved before any animation
	var saved := SaveManager.load_profile()
	check(saved["units"].size() == GameManager.owned_units().size() and int(saved["player"]["gems"]) == 100, "summon results saved immediately")
	# rate check
	var rng := RandomNumberGenerator.new()
	rng.seed = 42
	var counts := {3: 0, 4: 0, 5: 0}
	var banner := GameManager.summon_banner()
	for i in 20000:
		counts[int(Database.get_character(SummonSystem.roll(banner, rng))["rarity"])] += 1
	check(absf(counts[3] / 20000.0 - 0.75) < 0.02, "3-star rate ~75%% (%d)" % counts[3])
	check(absf(counts[4] / 20000.0 - 0.22) < 0.02, "4-star rate ~22%% (%d)" % counts[4])
	check(absf(counts[5] / 20000.0 - 0.03) < 0.008, "5-star rate ~3%% (%d)" % counts[5])


# ------------------------------------------------------------------ Phase 4: results, unlocks, missions, login
func test_battle_results_and_unlocks() -> void:
	GameManager.new_game("mira_tidesong")
	var r := GameManager.apply_battle_result("ashroot_01", {"xp": 10, "gold": 5, "items": {}, "stars": [true, true, false]})
	check(r["first_clear"] and int(r["first_clear_reward"].get("gems", 0)) == 5 and GameManager.gems() == 5, "first clear gives 5 gems")
	check(GameManager.star_count("ashroot_01") == 2 and r["new_stars"] == 2, "stars recorded")
	r = GameManager.apply_battle_result("ashroot_01", {"xp": 10, "gold": 5, "items": {}, "stars": [true, false, true]})
	check(not r["first_clear"] and GameManager.gems() == 5, "replays give no first-clear gems")
	check(GameManager.star_count("ashroot_01") == 3 and r["new_stars"] == 1, "best stars kept per objective")
	check(not GameManager.feature_unlocked("units"), "units locked early")
	for i in range(2, 6):
		r = GameManager.apply_victory("ashroot_%02d" % i, 10, 5, {})
	check(GameManager.feature_unlocked("units") and r["features"].has("units"), "units + squad unlock at 1-5")
	check(r["gift"].get("hero", "") == "wren_briarshot" and GameManager.owned_units().size() == 2, "1-5 gifts a second hero")
	for i in range(6, 11):
		r = GameManager.apply_victory("ashroot_%02d" % i, 10, 5, {})
	check(GameManager.feature_unlocked("summon") and GameManager.gems() >= 150, "summon unlock gift")
	check(GameManager.is_stage_unlocked("ember_tower_01") and GameManager.is_stage_unlocked("saltglass_01"), "towers and world 2 unlocked")
	check(GameManager.world_unlocked("saltglass_reach"), "world 2 accessible")
	check(r["units"].size() == GameManager.party_units().size(), "results per squad member")


func test_missions_and_login() -> void:
	GameManager.clock_override = 1_700_000_000.0
	GameManager.new_game("kael_emberclaw")
	var daily: Array = Database.missions["daily"]
	check(daily.size() >= 3 and daily.size() <= 5, "3-5 daily missions")
	GameManager.track("stage_clear", 2)
	var m0: Dictionary = daily[0]
	check(GameManager.mission_progress("daily", m0) == 2 and GameManager.claim_mission("daily", m0["id"]).is_empty(), "incomplete mission cannot be claimed")
	GameManager.track("stage_clear", 5)
	check(GameManager.mission_progress("daily", m0) == int(m0["target"]), "progress clamps at target")
	var gold := GameManager.gold()
	check(not GameManager.claim_mission("daily", m0["id"]).is_empty() and GameManager.gold() > gold, "claim reward")
	check(GameManager.claim_mission("daily", m0["id"]).is_empty(), "cannot claim twice")
	check(not GameManager.can_claim_chest(), "chest needs more missions")
	GameManager.clock_override += 86400
	check(GameManager.mission_progress("daily", m0) == 0 and not GameManager.mission_claimed("daily", m0["id"]), "daily reset next day")
	# login rewards: missed days continue the cycle
	GameManager.clock_override = 1_700_000_000.0
	check(GameManager.login_available(), "login reward available")
	var l1 := GameManager.claim_login()
	check(l1["day"] == 1 and not GameManager.login_available(), "day 1 claimed once")
	GameManager.clock_override += 86400 * 4
	var l2 := GameManager.claim_login()
	check(l2["day"] == 2, "after missing days the cycle continues at day 2")
	GameManager.clock_override = -1.0


func test_migration_from_v1() -> void:
	var v1 := {"version": 1, "starter_id": "thorne_mossguard",
		"player": {"name": "Old", "rank": 6, "rank_xp": 12, "gold": 4321},
		"units": [{"uid": "u1", "char_id": "thorne_mossguard", "level": 19, "exp": 40}],
		"next_uid": 2, "party": ["u1"], "inventory": {"nature_shard": 3, "fire_shard": 1},
		"stages": {"cleared": ["ashroot_01", "ashroot_02", "ashroot_03", "ashroot_04", "ashroot_05", "ashroot_06", "ashroot_07"],
				   "unlocked": ["ashroot_01", "ashroot_08"]},
		"tutorial": {"intro_seen": true, "hints_seen": ["guard"]}}
	var p := SaveManager.sanitize_profile(v1)
	check(p["version"] == 2 and p["player"]["gold"] == 4321 and p["player"]["rank"] == 6, "progress kept")
	check(p["units"][0]["level"] == 15 and p["units"][0]["burst_level"] == 1, "level clamped to new cap, burst level added")
	check(p["inventory"].get("sprout_fragment", 0) == 3 and p["inventory"].get("ember_fragment", 0) == 1, "shards converted to fragments")
	check(p["player"]["energy"] == SaveManager.max_energy_for_rank(6), "energy starts full")
	check(GameManager.stage_stars("ashroot_01") != null and p["stages"]["stars"]["ashroot_01"][0], "cleared stages get their first star")
	check(SaveManager.migration_notes.size() >= 2, "migration explained to the player")
	check(p["tutorial"]["intro_seen"] and p["tutorial"]["hints_seen"].has("guard"), "tutorial progress kept")
	# retroactive gifts on continue
	var f := FileAccess.open(SaveManager.save_path, FileAccess.WRITE)
	f.store_string(JSON.stringify(v1))
	f.close()
	FileAccess.open(SaveManager.save_path + ".bak", FileAccess.WRITE).close()
	check(GameManager.continue_game(), "v1 save continues")
	check(GameManager.owned_units().size() == 2, "milestone hero gift granted retroactively")
	check(GameManager.is_stage_unlocked("ember_tower_01"), "towers unlocked for saves past 1-7")
	check(GameManager.is_stage_unlocked("ashroot_08") and not GameManager.is_stage_cleared("ashroot_08"), "story position kept")


# ------------------------------------------------------------------ Phase 4: combat mechanics
func test_shields_debuffs_regen() -> void:
	var t := _player("thorne_mossguard")
	t.add_shield(100, 2)
	var hp0 := t.hp
	check(t.take_damage(60) == 0 and t.last_absorbed == 60 and t.hp == hp0, "shield absorbs damage")
	check(t.take_damage(70) == 30 and t.last_absorbed == 40 and not t.has_status("shield"), "shield breaks, rest goes through")
	var atk := t.get_stat("atk")
	t.add_status("atk_down", 0.2, 2)
	check(is_equal_approx(t.get_stat("atk"), atk * 0.8), "ATK Down lowers ATK")
	t.hp = 100
	t.add_status("regen", 0.05, 2)
	var ev := t.tick_statuses()
	check(ev.size() == 1 and ev[0]["type"] == "hot" and ev[0]["amount"] == int(round(t.max_hp * 0.05)), "regen heals 5%")
	var e := Combatant.from_enemy("tide_slime", 3, 0)
	e.add_status("def_down", 0.3, 2)
	check(e.has_negative_status(), "debuff detected")


func test_leader_skill_and_team_passives() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_01", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 1, "exp": 0},
			{"uid": "u2", "char_id": "rhea_flintwhistle", "level": 1, "exp": 0},
			{"uid": "u3", "char_id": "mira_tidesong", "level": 1, "exp": 0}], 1)
	var kael: Combatant = m.players[0]
	var rhea: Combatant = m.players[1]
	var mira: Combatant = m.players[2]
	var base_k := float(Progression.unit_stats(kael.def, 1)["atk"])
	check(is_equal_approx(kael.base_stats["atk"], base_k * 1.08), "leader: fire allies +8% ATK")
	check(is_equal_approx(mira.base_stats["atk"], float(Progression.unit_stats(mira.def, 1)["atk"])), "leader skill skips other elements")
	check(is_equal_approx(kael.burst_gain_mult, 1.1) and is_equal_approx(mira.burst_gain_mult, 1.1), "Rhea's passive: +10% Burst gain for all")
	check(is_equal_approx(kael.heal_received_up, 0.1), "Mira's passive: +10% healing received for all")
	m.resolve_instant(m.plan_action(rhea, rhea.normal_skill, m.enemies[0]))
	check(is_equal_approx(rhea.burst, 34.0 * 1.1), "burst gain multiplied (%s)" % rhea.burst)


func test_burst_level_in_battle() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_01", [{"uid": "u1", "char_id": "seraphine_pyrelance", "level": 1, "exp": 0, "burst_level": 5}], 1)
	var s: Combatant = m.players[0]
	check(s.burst_max == 84.0, "phoenix lance gauge cost drops with level (%s)" % s.burst_max)
	check(float(s.skill_data(s.burst_skill)["power"]) > float(Database.get_skill(s.burst_skill)["power"]), "burst scaled by level")
	s.add_burst(84)
	check(s.burst_ready(), "ready at the reduced cost")
	var plan := m.plan_action(s, s.burst_skill, m.enemies[0], true)
	check(m.bursts_used.get("u1", 0) == 1, "burst use counted for stars / burst EXP")
	m.resolve_instant(plan)


func test_enemy_ai_profiles() -> void:
	var m := BattleModel.new()
	m.setup("ashroot_01", [{"uid": "u1", "char_id": "thorne_mossguard", "level": 10, "exp": 0}], 3)
	# charger: charges on its 3rd turn, releases next turn
	var beetle := Combatant.from_enemy("scorch_beetle", 5, 0)
	m.enemies = [beetle]
	var types: Array = []
	for i in 4:
		var a := EnemyAI.decide(beetle, m)
		types.append(a["type"] + ":" + a.get("skill_id", ""))
		if a["type"] == "charge":
			m.begin_charge(beetle, a["skill_id"])
			check(beetle.has_status("charging"), "charging status shown")
			beetle.tick_statuses()
			check(beetle.has_status("charging"), "charging survives the end of round")
	check(types[2] == "charge:scorch_charge" and types[3] == "skill:scorch_charge", "charge telegraphed then released (%s)" % [types])
	check(not beetle.has_status("charging"), "charge cleared on release")
	# healer heals an injured ally
	var cap := Combatant.from_enemy("glowcap", 5, 0)
	var hurt := Combatant.from_enemy("moss_slime", 5, 1)
	hurt.hp = 10
	m.enemies = [cap, hurt]
	var h := EnemyAI.decide(cap, m)
	check(h["skill_id"] == "glow_mend", "healer heals when an ally is low")
	var plan := m.plan_action(cap, h["skill_id"], h["target"])
	m.resolve_instant(plan)
	check(hurt.hp > 10, "heal lands on the most injured ally")
	# debuffer targets the highest-ATK hero
	m.setup("ashroot_01", [{"uid": "u1", "char_id": "thorne_mossguard", "level": 1, "exp": 0},
			{"uid": "u2", "char_id": "kael_emberclaw", "level": 10, "exp": 0}], 3)
	var moth := Combatant.from_enemy("hexmoth", 5, 0)
	check(EnemyAI.choose_target(moth, m.players, m.rng, "hex_powder") == m.players[1], "debuffer picks the strongest hero")
	# elite extra skill every 3rd turn
	var elite := Combatant.from_enemy("elite_tidefin", 5, 0)
	m.enemies = [elite]
	var ex := ""
	for i in 3:
		ex = EnemyAI.decide(elite, m)["skill_id"]
	check(ex == "tidal_mend" and elite.is_elite, "elite uses its extra skill")


func test_boss_mechanics() -> void:
	var m := BattleModel.new()
	m.setup("saltglass_10", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 15, "exp": 0}], 5)
	while m.has_next_wave():
		m.advance_wave()
	var boss: Combatant = null
	for e in m.enemies:
		if e.is_boss:
			boss = e
	check(boss != null and boss.id == "saltglass_colossus", "world 2 ends with the Saltglass Colossus")
	var atk := boss.get_stat("atk")
	boss.hp = int(boss.max_hp * 0.4)
	var p2 := m.check_phase2(boss)
	check(not p2.is_empty() and boss.phase2 and boss.get_stat("atk") > atk, "phase 2 below 50% HP enrages")
	check(m.check_phase2(boss).is_empty(), "phase 2 triggers once")
	check(EnemyAI.decide(boss, m)["skill_id"] == "glass_carapace", "phase 2 skill used next")
	# summoning boss
	var m2 := BattleModel.new()
	m2.setup("ashroot_10", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 12, "exp": 0}], 5)
	m2.advance_wave()
	var pup: Combatant = m2.enemies[0]
	check(pup.is_boss, "1-10 boss")
	var saw_summon := false
	for i in 8:
		var a := EnemyAI.decide(pup, m2)
		if a["type"] == "summon":
			var n := m2.summon_minions(pup)
			saw_summon = saw_summon or not n.is_empty()
		elif a["type"] == "charge":
			m2.begin_charge(pup, a["skill_id"])
	var minions := m2.alive(m2.enemies).filter(func(e): return e.summoned).size()
	check(saw_summon and minions <= 2, "boss summons, capped at 2 minions (%d)" % minions)
	var slots := {}
	for e in m2.enemies:
		check(not slots.has(e.slot), "summons use free slots")
		slots[e.slot] = true
	var hp_event_fired := false
	pup.hp = int(pup.max_hp * 0.5)
	pup.charging_skill = ""
	pup.remove_status("charging")
	var a2 := EnemyAI.decide(pup, m2)
	check(a2["skill_id"] == "bark_armor", "HP threshold reaction")


func test_stars_and_victory_data() -> void:
	var sim = load("res://tests/balance_sim.gd").new()
	var r: Dictionary = sim.simulate("ashroot_01", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 8, "exp": 0}], 3)
	check(r["win"] and r["stars"][0], "clear star")
	check(r["stars"].size() == 3 and r.has("bursts") and r.has("enemies_defeated"), "victory data complete")
	var m := BattleModel.new()
	m.setup("ashroot_10", [{"uid": "u1", "char_id": "kael_emberclaw", "level": 1, "exp": 0}], 1)
	m.players_ko = 1
	m.total_rounds = 99
	check(m.evaluate_stars() == [true, false, false], "failed objectives give no stars")
	sim.free()


# ------------------------------------------------------------------ anti-softlock
func _reachable(item_id: String) -> bool:
	for src in GameManager.item_sources(item_id):
		if src["unlocked"]:
			return true
	return false



func test_anti_softlock() -> void:
	GameManager.clock_override = 1_650_000_000.0
	GameManager.new_game("thorne_mossguard")
	# Energy: every stage and floor fits in the smallest energy pool, and energy always comes back
	for sid in Database.stages.keys():
		check(GameManager.stage_energy(sid) <= SaveManager.max_energy_for_rank(1), sid + " affordable at rank 1")
	GameManager.spend_energy(GameManager.energy())
	GameManager.profile["player"]["gold"] = 0
	GameManager.clock_override += 180 * 5
	check(GameManager.try_start_stage("ashroot_01")["ok"], "broke player with no energy recovers and can play")
	# defeat keeps everything
	GameManager.add_gold(500)
	GameManager.add_item("ember_wisp", 2)
	GameManager.record_defeat("ashroot_01")
	check(GameManager.gold() == 500 and GameManager.item_count("ember_wisp") == 3, "defeat loses nothing")
	# the squad can never be emptied
	check(not GameManager.toggle_party(GameManager.party_uids()[0]), "last hero cannot leave the squad")
	# evolution materials are reachable once evolution unlocks (towers open one stage earlier)
	for i in range(1, 9):
		GameManager.apply_victory("ashroot_%02d" % i, 10, 5, {})
	check(GameManager.feature_unlocked("evolution") and GameManager.feature_unlocked("tower"), "evolution + towers open")
	# 3* -> 4* materials: reachable as soon as evolution opens
	for fam in Database.family_ids():
		var evo = Database.get_character(fam).get("evolution")
		if not evo is Dictionary or int(Database.get_character(fam)["rarity"]) != 3:
			continue
		for m in evo.get("materials", {}).keys():
			check(_reachable(m), "%s material %s has an unlocked source at 1-8" % [fam, m])
	var prism := false
	for src in GameManager.item_sources("prism_shard"):
		prism = prism or src["unlocked"]
	check(prism, "prism shard always obtainable (login rewards)")
	# cleared stages stay replayable; the next region opens after the boss
	for i in range(9, 11):
		GameManager.apply_victory("ashroot_%02d" % i, 10, 5, {})
	for sid in Database.worlds["ashroot_wilds"]["stages"].map(func(x): return x["id"]):
		check(GameManager.is_stage_unlocked(sid), sid + " replayable")
	check(GameManager.is_stage_unlocked("saltglass_01"), "world 2 reachable")
	# 4* -> 5* materials: reachable after World 1 and the first five floors of every tower
	for tid in Database.tower_order:
		for fl in Database.towers[tid]["stages"].slice(0, 5):
			GameManager.apply_victory(fl["id"], 10, 5, {})
	for cid in Database.characters.keys():
		var evo2 = Database.get_character(cid).get("evolution")
		if evo2 is Dictionary:
			for m in evo2.get("materials", {}).keys():
				check(_reachable(m), "%s material %s reachable mid-game" % [cid, m])
	# summoning with too few gems never takes anything
	var g := GameManager.gems()
	GameManager.profile["player"]["gems"] = 50
	check(not GameManager.summon("standard", 1)["ok"] and GameManager.gems() == 50, "failed summon costs nothing")
	GameManager.profile["player"]["gems"] = g
	# power never blocks entry
	GameManager.profile["player"]["energy"] = 60
	check(GameManager.try_start_stage("saltglass_01")["ok"], "low squad power can still depart")
	GameManager.clock_override = -1.0


# ------------------------------------------------------------------ whole-battle simulation
func test_every_starter_can_clear_stage_1() -> void:
	var sim = load("res://tests/balance_sim.gd").new()
	for starter in Database.starter_ids():
		var wins := 0
		for s in 30:
			if sim.simulate("ashroot_01", [{"uid": "u1", "char_id": starter, "level": 1, "exp": 0}], s)["win"]:
				wins += 1
		check(wins == 30, "%s wins stage 1 every time (%d/30)" % [starter, wins])
	sim.free()


# ------------------------------------------------------------------ phase 5 UI helpers
func test_ui_helpers() -> void:
	for pair in [[999, "999"], [9999, "9,999"], [12400, "12.4K"], [1_300_000, "1.3M"], [2_100_000_000, "2.1B"], [-12400, "-12.4K"]]:
		check(UIKit.format_compact(pair[0]) == pair[1], "format_compact(%d) = %s (got %s)" % [pair[0], pair[1], UIKit.format_compact(pair[0])])
	check(GameManager.validate_player_name("Kael").is_empty(), "valid name accepted")
	for bad in ["", "a", "12345678901234567", "<script>", "two  spaces"]:
		check(not GameManager.validate_player_name(bad).is_empty(), "bad name rejected: '%s'" % bad)
	# element advice: all-fire squad vs water foes warns, fire vs nature is good
	check(StageInfo.matchup_advice(["fire"], ["water"])[1], "matchup warns when nothing beats the foes")
	check(not StageInfo.matchup_advice(["fire"], ["nature"])[1], "matchup approves an advantage")
	# unit filter state survives a save / load of settings
	var st := UnitFilter.load_state()
	st["el"] = "water"
	st["sort"] = "atk"
	UnitFilter.save_state(st)
	var back := UnitFilter.load_state()
	check(back["el"] == "water" and back["sort"] == "atk", "unit filter + sort remembered")
	UnitFilter.save_state(UnitFilter.DEFAULT.merged({"sort": "recent", "desc": true}))
