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
    check(DB.tower_order.size() == 3, "three towers");
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

static void test_battle_every_starter()
{
    for (auto& sid : DB.starter_ids())
    {
        int wins = 0;
        for (int seed = 0; seed < 20; ++seed)
        {
            BattleModel m;
            m.setup("ashroot_01", Json::array({{{"uid", "u1"}, {"char_id", sid}, {"level", 1}}}), seed);
            for (int guard = 0; guard < 200 && !m.all_players_dead(); ++guard)
            {
                if (m.all_enemies_dead())
                {
                    if (!m.has_next_wave()) break;
                    m.advance_wave();
                    continue;
                }
                while (auto p = m.first_ready_player())
                {
                    Plan plan = p->burst_ready() ? m.plan_action(p, p->burst_skill, nullptr, true) : m.plan_action(p, p->normal_skill, nullptr);
                    m.resolve_instant(plan);
                    if (m.all_enemies_dead()) break;
                }
                for (auto& e : m.enemy_turn_order())
                {
                    if (!e->is_alive() || m.all_players_dead()) continue;
                    EnemyDecision d = m.decide(e);
                    if (d.type == "charge") m.begin_charge(*e, d.skill_id);
                    else if (d.type == "summon") m.summon_minions(*e);
                    else { Plan pl = m.plan_action(e, d.skill_id, d.target); m.resolve_instant(pl); }
                }
                for (auto& ev : m.end_round())
                    ev.type == "dot" ? (void)m.apply_dot(ev.unit, ev.amount) : (void)m.apply_hot(ev.unit, ev.amount);
                m.start_player_phase();
            }
            wins += m.all_enemies_dead() && !m.has_next_wave() ? 1 : 0;
        }
        check(wins >= 18, sid + " clears stage 1 (" + std::to_string(wins) + "/20)");
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

int main()
{
    DB.reload();
    GM.init();
    test_data();
    test_damage();
    test_burst_and_statuses();
    test_battle_every_starter();
    test_profile_flow();
    test_helpers();
    SaveManager::get().delete_profile();
    std::cout << passed << " checks passed, " << failed.size() << " failed\n";
    for (auto& f : failed) std::cout << "  - " << f << "\n";
    return failed.empty() ? 0 : 1;
}
