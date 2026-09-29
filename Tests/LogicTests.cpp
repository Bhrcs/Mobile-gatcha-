// Engine-free rule tests for the C++ logic layer (ported from the Godot logic tests).
// Build + run: Tests/run_logic_tests.sh
#include "logic/Battle.h"
#include "logic/GameManager.h"
#include "logic/Platform.h"
#include <cmath>
#include <iostream>

static int passed = 0;
static std::vector<std::string> failed;
static void check(bool ok, const std::string& what) { ok ? (void)++passed : failed.push_back(what); }
static CombatantPtr player(const std::string& id = "kael_emberclaw", int lvl = 1)
{
    return Combatant::from_player_unit({{"uid", "t"}, {"char_id", id}, {"level", lvl}, {"exp", 0}}, 0);
}
struct CombatOverride   // temporarily changes a combat knob
{
    std::string k; Json old;
    CombatOverride(std::string key, Json v) : k(std::move(key)) { old = DB.progression["combat"][k]; DB.progression["combat"][k] = v; }
    ~CombatOverride() { DB.progression["combat"][k] = old; }
};

static void test_data()
{
    check(DB.load_errors.empty(), "no data load errors");
    check(DB.starter_ids() == std::vector<std::string>{"kael_emberclaw", "mira_tidesong", "thorne_mossguard"}, "three starters");
    check(DB.stage_order.size() == 20, "two worlds of ten stages");
    check(DB.tower_order.size() == 4 && DB.tower_order.back() == "the_fracture", "three towers + the Fracture (last)");
    check(DB.family_ids().size() == 12, "twelve hero families");
    check(DB.element_multiplier("fire", "nature") == 1.25 && DB.element_multiplier("fire", "water") == 0.75 &&
              DB.element_multiplier("fire", "fire") == 1.0, "element chart");
}

static void test_damage()
{
    auto kael = player();
    auto pup = Combatant::from_enemy("bramble_pup", 1, 0), tide = Combatant::from_enemy("tidefin", 1, 0);
    Rng rng;
    rng.seed(5);
    CombatOverride c("crit_chance", 0.0);
    const Json& skill = DB.skill("ember_slash");
    check(DamageCalculator::calculate(*kael, *pup, skill, rng).tag == "WEAK", "WEAK vs nature");
    check(DamageCalculator::calculate(*kael, *tide, skill, rng).tag == "RESIST", "RESIST vs water");
    double expected = (145.0 * 1.1 - 35 * 0.3) * 1.25;
    for (int i = 0; i < 50; ++i)
    {
        int t = DamageCalculator::calculate(*kael, *pup, skill, rng).total;
        check(t >= std::floor(expected * 0.95) - 1 && t <= std::ceil(expected * 1.05) + 1, "variance within 5%");
    }
    for (int total : {1, 7, 100, 999})
        for (int hits : {1, 2, 3, 6})
        {
            auto parts = DamageCalculator::split_hits(total, hits, {1, 1, 1, 1.5, 1.5, 2});
            int s = 0;
            for (int p : parts) { s += p; check(p >= 1, "each hit >= 1"); }
            check((int)parts.size() == hits && (total < hits || s == total), "hits sum to total");
        }
    auto slime = Combatant::from_enemy("cinder_slime", 5, 0);
    auto thorne = player("thorne_mossguard");
    CombatOverride v1("variance_min", 1.0), v2("variance_max", 1.0);
    int normal = DamageCalculator::calculate(*slime, *thorne, DB.skill("slime_tackle"), rng).total;
    thorne->guarding = true;
    int guarded = DamageCalculator::calculate(*slime, *thorne, DB.skill("slime_tackle"), rng).total;
    check(std::abs(guarded - normal * 0.35) <= 1, "guard + Thorne passive");
}

static void test_burst_and_statuses()
{
    auto kael = player();
    kael->add_burst(99);
    check(!kael->burst_ready(), "99 is not ready");
    kael->add_burst(1);
    check(kael->burst_ready(), "100 is ready");
    kael->add_status("burn", 0, 2);
    auto ev = kael->tick_statuses();
    check(ev.size() == 1 && S(ev[0], "type") == "dot", "burn ticks");
    kael->tick_statuses();
    check(!kael->has_status("burn"), "burn expires");
    kael->add_shield(50, 2);
    int hp = kael->hp;
    kael->take_damage(30);
    check(kael->hp == hp && kael->shield_amount() == 20, "shield absorbs first");
}

struct SimResult { bool win = false; int rounds = 0, ko = 0; };
// Plays a whole stage with a simple policy (Burst when ready, Guard a charge when low). Used by tests + `audit`.
static SimResult simulate(const std::string& stage, const Json& party, int seed)
{
    BattleModel m;
    m.setup(stage, party, seed);
    for (int guard = 0; guard < 200 && !m.all_players_dead(); ++guard)
    {
        if (m.all_enemies_dead())
        {
            if (!m.has_next_wave()) break;
            m.advance_wave();
            continue;
        }
        bool charging = false;
        for (auto& e : m.alive(m.enemies)) charging = charging || !e->charging_skill.empty();
        while (auto p = m.first_ready_player())
        {
            if (charging && !p->burst_ready() && p->hp_ratio() < 0.5) { m.guard(*p); continue; }
            CombatantPtr focus;   // focus fire the weakest foe, like a player would
            for (auto& e : m.alive(m.enemies))
                if (!focus || e->hp < focus->hp) focus = e;
            Plan plan = p->burst_ready() ? m.plan_action(p, p->burst_skill, focus, true) : m.plan_action(p, p->normal_skill, focus);
            m.resolve_instant(plan);
            if (m.all_enemies_dead()) break;
        }
        for (auto& e : m.enemy_turn_order())
        {
            if (!e->is_alive() || m.all_players_dead()) continue;
            Json ph = m.check_phase(*e);
            if (ph.contains("summon")) m.summon_minions(*e, ph["summon"]);
            EnemyDecision d = m.decide(e);
            if (d.type == "charge") m.begin_charge(*e, d.skill_id);
            else if (d.type == "summon") m.summon_minions(*e);
            else if (d.type == "skill") { Plan pl = m.plan_action(e, d.skill_id, d.target); m.resolve_instant(pl); }
        }
        for (auto& ev : m.end_round())
            if (ev.type == "dot") m.apply_dot(ev.unit, ev.amount);
            else if (ev.type == "hot") m.apply_hot(ev.unit, ev.amount);
        m.start_player_phase();
    }
    return {m.all_enemies_dead() && !m.has_next_wave(), m.total_rounds, m.players_ko};
}

static Json party_of(const std::vector<std::string>& ids, int level)
{
    Json p = Json::array();
    for (auto id : ids)
    {
        while (level > I(DB.character(id), "max_level", 99) && !S(O(DB.character(id), "evolution"), "into").empty())
            id = S(DB.character(id)["evolution"], "into");   // the form a player would have at this level
        p.push_back({{"uid", id}, {"char_id", id}, {"level", level}});
    }
    return p;
}

static void test_battle_every_starter()
{
    for (auto& sid : DB.starter_ids())
    {
        int wins = 0;
        for (int seed = 0; seed < 20; ++seed) wins += simulate("ashroot_01", party_of({sid}, 1), seed).win ? 1 : 0;
        check(wins >= 18, sid + " clears stage 1 (" + std::to_string(wins) + "/20)");
    }
}

// Phase 7: resistances, Dispel, mitigation cap, Break Gauge, boss phases, totem auras, interrupts.
static void test_phase7_combat()
{
    Rng rng;
    rng.seed(3);
    // status resistance + diminishing returns on bosses
    auto warden = Combatant::from_enemy("ashen_warden", 26, 0);
    check(warden->has_status("flame_armor") && warden->break_max > 0, "Warden starts armoured with a Break Gauge");
    check(std::abs(warden->status_resist("burn") - 0.8) < 1e-9, "data resist (burn 80%)");
    check(std::abs(warden->status_resist("def_down") - 0.3) < 1e-9, "bosses default to 30% resist");
    warden->status_hits["def_down"] = 2;
    check(warden->status_resist("def_down") > 0.59, "repeated statuses land less often on bosses");
    // Dispel removes buffs but not protected boss mechanics
    warden->add_status("atk_up", 0.2, 2);
    auto gone = warden->dispel(5);
    check(gone.size() == 1 && gone[0] == "atk_up" && warden->has_status("flame_armor"), "Dispel skips undispellable Flame Armor");
    // mitigation cap
    {
        auto kael = player("kael_emberclaw", 20);
        auto pup = Combatant::from_enemy("bramble_pup", 20, 0);
        CombatOverride c("crit_chance", 0.0), v1("variance_min", 1.0), v2("variance_max", 1.0);
        int open = DamageCalculator::calculate(*pup, *kael, DB.skill("bramble_bite"), rng).total;
        kael->add_status("damage_reduction", 0.9, 3);
        kael->guarding = true;
        int walled = DamageCalculator::calculate(*pup, *kael, DB.skill("bramble_bite"), rng).total;
        check(walled >= (int)std::floor(open * 0.25) - 1, "stacked mitigation is capped at 75%");
    }
    // Break: a Breaker drains the gauge; Broken strips armour, cancels the charge and skips the turn
    BattleModel m;
    m.setup("fracture_01_normal", party_of({"voss_ashmantle", "mira_tidesong"}, 26), 1);
    auto w = m.enemies[0];
    auto voss = m.players[0], mira = m.players[1];
    m.begin_charge(*w, "furnace_collapse");
    Plan pv = m.plan_action(voss, voss->normal_skill, w), pm = m.plan_action(mira, mira->normal_skill, w);
    check(pv.targets[0].break_per_hit * pv.targets[0].hits.size() > pm.targets[0].break_per_hit * pm.targets[0].hits.size() * 0.9,
          "Breakers deal more Break than a Water healer's hit");
    bool broke = false;
    for (int i = 0; i < 40 && !broke; ++i)
    {
        Plan p = m.plan_action(voss, voss->normal_skill, w);
        for (size_t h = 0; h < p.targets[0].hits.size(); ++h) broke = broke || m.apply_hit(p, 0, (int)h).broke;
        w->hp = w->max_hp;   // keep it alive (and above the phase thresholds)
    }
    check(broke && w->is_broken() && !w->has_status("flame_armor") && w->charging_skill.empty(), "Break: armour off, charge cancelled");
    check(m.decide(w).type == "skip", "Broken foes lose their turn");
    for (int i = 0; i < 3; ++i) m.end_round();
    check(!w->is_broken() && w->break_value == w->break_max, "gauge refills after Broken ends");
    // phases: totems at 70% feed ATK; killing them removes it
    w->hp = (int)(w->max_hp * 0.65);
    Json ph = m.check_phase(*w);
    check(I(ph, "index", 0) == 1 && ph.contains("summon"), "phase 1 at 70%: summon");
    Units totems = m.summon_minions(*w, ph["summon"]);
    double atk2 = w->get_stat("atk");
    check(totems.size() == 2 && std::abs(F(w->statuses.back(), "value", 0) - 0.4) < 1e-9, "two totems: +40% ATK");
    totems[0]->take_damage(99999);
    Plan dummy = m.plan_action(voss, voss->normal_skill, totems[1]);
    m.resolve_instant(dummy);   // may or may not kill; force the first death through the model
    totems[1]->take_damage(99999);
    m.apply_dot(totems[0], 1);
    m.apply_dot(totems[1], 1);
    check(!w->has_status("ember_fervor") && w->get_stat("atk") < atk2, "destroying the totems removes the buff");
    // phase 2 at 40%: telegraphed Furnace Collapse, interruptible by damage
    w->hp = (int)(w->max_hp * 0.35);
    Json ph2 = m.check_phase(*w);
    EnemyDecision d = m.decide(w);
    check(I(ph2, "index", 0) == 2 && d.type == "charge" && d.skill_id == "furnace_collapse", "phase 2 starts charging at once");
    m.begin_charge(*w, d.skill_id);
    Plan big = m.plan_action(voss, voss->normal_skill, w);
    big.targets[0].hits = {(int)(w->max_hp * 0.16)};
    big.targets[0].break_per_hit = 0;
    check(m.apply_hit(big, 0, 0).interrupted && w->charging_skill.empty(), "15% HP while charging interrupts");
}

// `logic_tests audit`: win rate / rounds / KOs for every story stage at its recommended level.
static void audit()
{
    std::vector<std::pair<std::string, std::vector<std::string>>> squads = {
        {"starters", {"kael_emberclaw", "mira_tidesong", "thorne_mossguard"}},
        {"fire-only", {"kael_emberclaw", "rhea_flintwhistle"}},
        {"no-healer", {"kael_emberclaw", "thorne_mossguard", "wren_briarshot"}}};
    for (auto& [name, ids] : squads)
    {
        std::cout << "== " << name << "\n";
        for (auto& st : DB.stage_order)
        {
            int lvl = I(DB.stage(st), "recommended_level", 1), wins = 0, rounds = 0, ko = 0;
            for (int seed = 0; seed < 30; ++seed)
            {
                auto r = simulate(st, party_of(ids, lvl), seed);
                wins += r.win; rounds += r.rounds; ko += r.ko;
            }
            std::printf("%-14s lv%-3d win %3d%%  rounds %4.1f  ko %3.1f\n", st.c_str(), lvl, wins * 100 / 30, rounds / 30.0, ko / 30.0);
        }
    }
    std::vector<std::pair<std::string, std::vector<std::string>>> late = {
        {"starters", {"kael_emberclaw", "mira_tidesong", "thorne_mossguard"}},
        {"starters+breaker+water", {"kael_emberclaw", "mira_tidesong", "thorne_mossguard", "voss_ashmantle", "corin_saltmarsh"}},
        {"fire x3", {"kael_emberclaw", "rhea_flintwhistle", "voss_ashmantle"}},
        {"5 no healer", {"kael_emberclaw", "thorne_mossguard", "voss_ashmantle", "corin_saltmarsh", "wren_briarshot"}}};
    for (auto& [name, ids] : late)
    {
        std::cout << "== Fracture I, " << name << "\n";
        for (auto& fl : A(DB.towers["the_fracture"], "stages"))
        {
            std::string st = S(fl, "id");
            int lvl = I(fl, "recommended_level", 1), wins = 0, rounds = 0, ko = 0;
            for (int seed = 0; seed < 30; ++seed)
            {
                auto r = simulate(st, party_of(ids, lvl), seed);
                wins += r.win; rounds += r.rounds; ko += r.ko;
            }
            std::printf("%-22s lv%-3d win %3d%%  rounds %4.1f  ko %3.1f\n", st.c_str(), lvl, wins * 100 / 30, rounds / 30.0, ko / 30.0);
        }
    }
}

static void test_profile_flow()
{
    auto& gm = GM;
    gm.new_game("kael_emberclaw");
    check(gm.has_profile() && gm.party_uids().size() == 1, "new game with starter");
    int e0 = gm.energy();
    Json r = gm.try_start_stage("ashroot_01");
    check(B(r, "ok", false) && gm.energy() == e0 - gm.stage_energy("ashroot_01"), "starting a stage spends energy");
    Json res = gm.apply_battle_result("ashroot_01", {{"xp", 100}, {"gold", 50}, {"items", Json::object()}, {"stars", {true, true, false}}});
    check(gm.is_stage_cleared("ashroot_01") && gm.is_stage_unlocked("ashroot_02") && B(res, "first_clear", false), "clear unlocks next");
    check(gm.star_count("ashroot_01") == 2, "stars kept");
    // energy regen from the clock
    gm.clock_override = gm.now();
    gm.profile["player"]["energy"] = 0;
    gm.profile["player"]["energy_ts"] = (long long)gm.clock_override;
    gm.clock_override += 3 * I(DB.balance("energy", "regen_seconds"), 180) + 5;
    check(gm.energy() == 3, "offline energy regen");
    gm.clock_override = -1;
    // training
    gm.add_item("radiant_wisp", 3);
    gm.add_gold(100000);
    std::string uid = gm.leader_uid();
    int lvl = I(gm.unit(uid), "level", 1);
    Json t = gm.train_unit_with(uid, {{"radiant_wisp", 1}});
    check(B(t, "ok", false) && I(gm.unit(uid), "level", 1) > lvl, "training levels up");
    // evolution
    Json& u = gm.unit(uid);
    u["level"] = I(DB.character(S(u, "char_id")), "max_level", 15);
    for (int i = 1; i <= 8; ++i) gm.apply_battle_result("ashroot_0" + std::to_string(i), {{"xp", 10}});
    Json st = gm.evolution_status(uid);
    for (auto& [m, q] : st["materials"].items()) gm.add_item(m, I(q));
    std::string from = S(gm.unit(uid), "char_id");
    check(B(gm.evolve(uid), "ok", false) && S(gm.unit(uid), "char_id") != from && I(gm.unit(uid), "level", 0) == 1, "evolution");
    // summon + duplicates
    gm.apply_battle_result("ashroot_09", {{"xp", 10}});
    gm.add_gems(5000);
    Json s = gm.summon("standard", 10);
    int dup = 0;
    for (auto& e : s["results"]) dup += B(e, "is_new", false) ? 0 : 1;
    check(B(s, "ok", false) && s["results"].size() == 10, "10x summon");
    check(dup == 0 || gm.soul_shards() > 0, "duplicates become shards");
    // missions + login
    gm.apply_battle_result("ashroot_10", {{"xp", 10}});
    gm.track("stage_clear", 5);
    Json all = gm.claim_all_missions();
    check(I(all, "count", 0) >= 1 && gm.missions_claimable() == 0, "claim all");
    gm.profile["login"]["last_date"] = "";
    check(gm.login_available() && !gm.claim_login().empty() && !gm.login_available(), "login claim once a day");
    // save round trip + corruption recovery
    gm.save();
    Json saved = gm.profile;
    check(gm.continue_game() && gm.profile["units"] == saved["units"], "save round trip");
    Platform::writeText(SaveManager::get().save_path, "{ broken");
    check(gm.continue_game() && SaveManager::get().last_load_status == "recovered_backup", "backup recovers a corrupted save");
    Json bad = SaveManager::get().sanitize_profile({{"player", "nope"}, {"units", {1, 2}}, {"starter_id", "kael_emberclaw"}});
    check(bad["units"].size() == 1 && I(bad["player"], "gold", -1) == 0, "sanitize repairs wrong types");
}

static void test_helpers()
{
    check(fmt_number(1234567) == "1,234,567" && fmt_number(999) == "999", "fmt_number");
    check(GameManager::validate_player_name("Kael").empty(), "valid name");
    for (auto bad : {"", "a", "12345678901234567", "<script>", "two  spaces"})
        check(!GameManager::validate_player_name(bad).empty(), std::string("bad name rejected: ") + bad);
}

int main(int argc, char** argv)
{
    DB.reload();
    GM.init();
    if (argc > 1 && std::string(argv[1]) == "audit") { audit(); return 0; }
    test_data();
    test_damage();
    test_burst_and_statuses();
    test_battle_every_starter();
    test_phase7_combat();
    test_profile_flow();
    test_helpers();
    SaveManager::get().delete_profile();
    std::cout << passed << " checks passed, " << failed.size() << " failed\n";
    for (auto& f : failed) std::cout << "  - " << f << "\n";
    return failed.empty() ? 0 : 1;
}
