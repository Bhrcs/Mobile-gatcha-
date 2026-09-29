#include "GameManager.h"
#include "Platform.h"
#include <cmath>
#include <ctime>
#include <regex>

GameManager& GameManager::get()
{
    static GameManager g;
    return g;
}

void GameManager::init()
{
    rng.randomize();
    settings = SaveManager::get().load_settings();
}

double GameManager::now() const { return clock_override >= 0 ? clock_override : Platform::now(); }

void GameManager::tick(double dt)
{
    if (!has_profile()) return;
    _play_accum += dt;
    if (_play_accum >= 1.0)
    {
        int whole = (int)_play_accum;
        _play_accum -= whole;
        profile["player"]["play_seconds"] = I(profile["player"], "play_seconds", 0) + whole;
    }
    _energy_tick += dt;
    if (_energy_tick >= 1.0)
    {
        _energy_tick = 0;
        int before = I(profile["player"], "energy", 0);
        int cur = energy();
        if (cur != before) energy_changed.emit(cur, max_energy());
    }
}

// ------------------------------------------------------------------ profile lifecycle
bool GameManager::has_profile() const { return !profile.empty() && !S(profile, "starter_id").empty(); }

bool GameManager::can_continue()
{
    if (has_profile()) return true;
    Json p = SaveManager::get().load_profile();
    return !S(p, "starter_id").empty();
}

void GameManager::new_game(const std::string& starter_id)
{
    auto& sm = SaveManager::get();
    sm.delete_profile();
    profile = sm.default_profile();
    profile["starter_id"] = starter_id;
    profile["player"]["created"] = (int64_t)now();
    profile["player"]["energy"] = max_energy();
    profile["player"]["energy_ts"] = (int64_t)now();
    std::string uid = add_unit(starter_id, false);
    profile["party"] = Json::array({uid});
    profile["stages"]["unlocked"] = DB.stage_order.empty() ? Json::array() : Json::array({DB.stage_order[0]});
    for (auto& [id, q] : O(DB.progression, "starting_items").items()) add_item(id, I(q), false);
    save();
    profile_changed.emit();
}

bool GameManager::continue_game()
{
    Json p = SaveManager::get().load_profile();
    if (S(p, "starter_id").empty()) return false;
    profile = p;
    pending_migration_notes = SaveManager::get().migration_notes;
    if (I(profile["player"], "energy_ts", 0) <= 0) profile["player"]["energy_ts"] = (int64_t)now();
    grant_retroactive_unlocks();
    energy();
    profile_changed.emit();
    gold_changed.emit(gold());
    gems_changed.emit(gems());
    return true;
}

void GameManager::save()
{
    if (!profile.empty()) SaveManager::get().save_profile(profile);
}

// ------------------------------------------------------------------ units
std::string GameManager::add_unit(const std::string& char_id, bool mark_new)
{
    int n = I(profile, "next_uid", 1);
    std::string uid = "u" + std::to_string(n);
    profile["next_uid"] = n + 1;
    const Json& def = DB.character(char_id);
    profile["units"].push_back({{"uid", uid}, {"char_id", char_id}, {"level", I(def, "level", 1)},
                                {"exp", I(def, "experience", 0)}, {"burst_level", 1}, {"burst_xp", 0},
                                {"locked", false}, {"favorite", false}, {"new", mark_new}, {"obtained", (int64_t)now()}});
    std::string fam = S(def, "family", char_id);
    if (!contains(profile["codex"], fam)) profile["codex"].push_back(fam);
    return uid;
}

Json& GameManager::units()
{
    if (!profile["units"].is_array()) profile["units"] = Json::array();
    return profile["units"];
}

Json& GameManager::unit(const std::string& uid)
{
    static Json null;
    null = Json();
    for (auto& u : units())
        if (S(u, "uid") == uid) return u;
    return null;
}

bool GameManager::owns_family(const std::string& family)
{
    for (auto& u : units())
        if (S(DB.character(S(u, "char_id")), "family") == family) return true;
    return false;
}

void GameManager::mark_unit_seen(const std::string& uid)
{
    Json& u = unit(uid);
    if (!u.is_null() && B(u, "new", false))
    {
        u["new"] = false;
        save();
    }
}

void GameManager::set_unit_flag(const std::string& uid, const std::string& flag, bool on)
{
    Json& u = unit(uid);
    if (u.is_null() || (flag != "locked" && flag != "favorite")) return;
    u[flag] = on;
    save();
    profile_changed.emit();
}

Json GameManager::unit_stats(const Json& u) const
{
    return Progression::unit_stats(DB.character(S(u, "char_id")), I(u, "level", 1));
}

int GameManager::squad_power()
{
    int t = 0;
    for (auto& u : party_units()) t += unit_power(u);
    return t;
}

// ------------------------------------------------------------------ squad
Json GameManager::party_uids() const { return A(profile, "party"); }

Json GameManager::party_units()
{
    Json out = Json::array();
    for (auto& uid : party_uids())
    {
        Json& u = unit(S(uid));
        if (!u.is_null()) out.push_back(u);
    }
    return out;
}

int GameManager::max_party_size() const { return I(DB.progression, "party_size", 5); }
bool GameManager::is_in_party(const std::string& uid) const { return contains(A(profile, "party"), uid); }

bool GameManager::toggle_party(const std::string& uid)
{
    Json& party = profile["party"];
    if (contains(party, uid))
    {
        if (party.size() <= 1) return false;
        erase_value(party, uid);
    }
    else
    {
        if ((int)party.size() >= max_party_size() || unit(uid).is_null()) return false;
        party.push_back(uid);
    }
    save();
    profile_changed.emit();
    return true;
}

bool GameManager::set_leader(const std::string& uid)
{
    Json& party = profile["party"];
    auto it = std::find(party.begin(), party.end(), Json(uid));
    if (it == party.end()) return false;
    if (it != party.begin())
    {
        party.erase(it);
        party.insert(party.begin(), uid);
        save();
        profile_changed.emit();
    }
    return true;
}

bool GameManager::swap_party_slots(int a, int b)
{
    Json& party = profile["party"];
    if (a < 0 || b < 0 || a >= (int)party.size() || b >= (int)party.size() || a == b) return false;
    std::swap(party[a], party[b]);
    save();
    profile_changed.emit();
    return true;
}

std::string GameManager::leader_uid() const
{
    const Json& p = A(profile, "party");
    return p.empty() ? "" : S(p[0]);
}

Json GameManager::leader_skill()
{
    Json& u = unit(leader_uid());
    return u.is_null() ? Json::object() : O(DB.character(S(u, "char_id")), "leader_skill");
}

// ------------------------------------------------------------------ training
Json GameManager::preview_training(const std::string& uid, const Json& items)
{
    Json u = unit(uid);
    if (u.is_null()) return Json::object();
    const Json& def = DB.character(S(u, "char_id"));
    int xp = 0;
    for (auto& [id, q] : items.items()) xp += Progression::item_xp(id, def) * I(q);
    int cap = Progression::xp_to_cap(u);
    int used = std::min(xp, cap);
    Json sim = u;
    Json ups = Progression::add_unit_xp(sim, used);
    Json before = unit_stats(u), after = unit_stats(sim), gains = Json::object();
    for (auto k : {"hp", "atk", "def", "rec"}) gains[k] = I(after[k]) - I(before[k]);
    return {{"xp", xp},       {"used_xp", used},       {"wasted_xp", xp - used},        {"gold", Progression::training_gold(used)},
            {"level_before", I(u, "level", 1)}, {"level_after", I(sim, "level", 1)}, {"exp_after", I(sim, "exp", 0)},
            {"gains", gains}, {"level_ups", ups.size()}, {"at_cap", cap <= 0}};
}

Json GameManager::train_unit_with(const std::string& uid, const Json& items)
{
    Json pv = preview_training(uid, items);
    if (pv.empty() || B(pv, "at_cap", false) || I(pv, "xp", 0) <= 0)
        return {{"ok", false},
                {"reason", !pv.empty() && B(pv, "at_cap", false) ? "This hero is at max level." : "Choose training items."}};
    for (auto& [id, q] : items.items())
        if (item_count(id) < I(q)) return {{"ok", false}, {"reason", "Not enough " + DB.item_name(id) + "."}};
    if (gold() < I(pv, "gold", 0)) return {{"ok", false}, {"reason", "Not enough Gold."}};
    spend_gold(I(pv, "gold", 0), false);
    for (auto& [id, q] : items.items()) remove_item(id, I(q), false);
    pv["level_ups_detail"] = Progression::add_unit_xp(unit(uid), I(pv, "used_xp", 0));
    track("train", 1, false);
    save();
    profile_changed.emit();
    pv["ok"] = true;
    return pv;
}

Json GameManager::add_burst_xp(const std::string& uid, int amount, bool persist)
{
    Json& u = unit(uid);
    if (u.is_null() || amount <= 0) return Json::object();
    int before = I(u, "burst_level", 1);
    int cap_xp = Progression::burst_xp_for_level(I(DB.balance("burst_levels", "max"), 5));
    u["burst_xp"] = std::min(I(u, "burst_xp", 0) + amount, cap_xp);
    u["burst_level"] = Progression::burst_level_for_xp(I(u, "burst_xp", 0));
    int after = I(u, "burst_level", 1);
    if (persist)
    {
        save();
        profile_changed.emit();
    }
    return {{"before", before}, {"after", after}};
}

Json GameManager::train_burst(const std::string& uid, const std::string& method)
{
    Json& u = unit(uid);
    if (u.is_null()) return {{"ok", false}, {"reason", "Unknown hero."}};
    if (I(u, "burst_level", 1) >= I(DB.balance("burst_levels", "max"), 5))
        return {{"ok", false}, {"reason", "Burst is already at max level."}};
    int xp;
    if (method == "sigil")
    {
        if (!remove_item("spark_sigil", 1, false)) return {{"ok", false}, {"reason", "No Spark Sigils."}};
        xp = I(DB.item("spark_sigil"), "burst_xp", 3);
    }
    else
    {
        int cost = I(DB.balance("burst_levels", "shards_per_step"), 20);
        if (soul_shards() < cost) return {{"ok", false}, {"reason", "Need " + std::to_string(cost) + " Soul Shards."}};
        profile["player"]["soul_shards"] = soul_shards() - cost;
        xp = I(DB.balance("burst_levels", "shard_step_xp"), 3);
    }
    Json r = add_burst_xp(uid, xp);
    r["ok"] = true;
    r["xp"] = xp;
    return r;
}

// ------------------------------------------------------------------ evolution
Json GameManager::evolution_status(const std::string& uid)
{
    Json u = unit(uid);
    if (u.is_null()) return {{"ok", false}, {"reasons", {"Unknown hero."}}};
    const Json& def = DB.character(S(u, "char_id"));
    const Json& evo = at(def, "evolution");
    if (!evo.is_object()) return {{"ok", false}, {"final", true}, {"reasons", {"This is the hero's final form."}}};
    Json reasons = Json::array(), missing = Json::object();
    if (!feature_unlocked("evolution"))
        reasons.push_back("Evolution unlocks after clearing " + feature_unlock_label("evolution") + ".");
    if (I(u, "level", 1) < I(def, "max_level", 20)) reasons.push_back("Reach Lv." + std::to_string(I(def, "max_level", 20)) + " first.");
    for (auto& [m, q] : O(evo, "materials").items())
        if (item_count(m) < I(q)) missing[m] = I(q) - item_count(m);
    if (!missing.empty()) reasons.push_back("Missing materials.");
    if (gold() < I(evo, "gold", 0)) reasons.push_back("Need " + fmt_number(I(evo, "gold", 0)) + " Gold.");
    return {{"ok", reasons.empty()}, {"into", S(evo, "into")}, {"gold", I(evo, "gold", 0)},
            {"materials", O(evo, "materials")}, {"missing", missing}, {"reasons", reasons}};
}

bool GameManager::can_evolve(const std::string& uid) { return B(evolution_status(uid), "ok", false); }

Json GameManager::evolve(const std::string& uid)
{
    Json st = evolution_status(uid);
    if (!B(st, "ok", false)) return {{"ok", false}, {"reasons", st["reasons"]}};
    Json& u = unit(uid);
    std::string from = S(u, "char_id");
    spend_gold(I(st, "gold", 0), false);
    for (auto& [m, q] : st["materials"].items()) remove_item(m, I(q), false);
    u["char_id"] = st["into"];
    u["level"] = 1;
    u["exp"] = 0;
    save();
    profile_changed.emit();
    return {{"ok", true}, {"from", from}, {"into", st["into"]}};
}

Json GameManager::item_sources(const std::string& item_id)
{
    std::vector<Json> out;
    for (auto& [sid, st] : DB.stages.items())
    {
        bool found = false;
        for (auto& d : A(st, "drops")) found = found || S(d, "item") == item_id;
        if (!found && !is_stage_cleared(sid) && O(O(st, "first_clear"), "items").contains(item_id)) found = true;
        for (auto& wave : A(st, "waves"))
            for (auto& sp : wave)
            {
                auto ti = Progression::table_items(at(DB.enemy(S(sp, "enemy")), "drop_table"));
                found = found || std::find(ti.begin(), ti.end(), item_id) != ti.end();
            }
        if (found)
            out.push_back({{"id", sid}, {"kind", DB.is_tower_stage(sid) ? "tower" : "stage"}, {"label", stage_label(sid)},
                           {"unlocked", is_stage_unlocked(sid)}, {"order", stage_sort_key(sid)}});
    }
    std::stable_sort(out.begin(), out.end(), [](const Json& a, const Json& b) {
        bool ua = B(a, "unlocked", false), ub = B(b, "unlocked", false);
        return ua != ub ? ua : I(a, "order", 0) < I(b, "order", 0);
    });
    Json res = Json(out);
    if (res.is_null()) res = Json::array();
    for (auto kind : {"daily", "weekly"})
        for (auto& m : A(DB.missions, kind))
            if (O(O(m, "reward"), "items").contains(item_id))
                res.push_back({{"id", "missions"}, {"kind", "missions"},
                               {"label", capitalize(kind) + " Mission: " + S(m, "text")},
                               {"unlocked", feature_unlocked("missions")}, {"order", 5000}});
    if (O(O(O(DB.missions, "daily_chest"), "reward"), "items").contains(item_id))
        res.push_back({{"id", "missions"}, {"kind", "missions"}, {"label", "Daily Mission Chest"},
                       {"unlocked", feature_unlocked("missions")}, {"order", 5001}});
    for (auto& d : A(DB.login_rewards, "cycle"))
        if (O(O(d, "reward"), "items").contains(item_id))
            res.push_back({{"id", "login"}, {"kind", "login"}, {"label", "Login Reward - Day " + std::to_string(I(d, "day", 0))},
                           {"unlocked", true}, {"order", 6000}});
    return res;
}

int GameManager::stage_sort_key(const std::string& sid) const
{
    const Json& st = DB.stage(sid);
    std::string w = S(st, "world_id");
    auto idx = [](const std::vector<std::string>& v, const std::string& x) {
        return int(std::find(v.begin(), v.end(), x) - v.begin());
    };
    if (DB.towers.contains(w)) return 1000 + idx(DB.tower_order, w) * 100 + I(st, "number", 0);
    return idx(DB.world_order, w) * 100 + I(st, "number", 0);
}

std::string GameManager::stage_label(const std::string& sid) const
{
    const Json& st = DB.stage(sid);
    std::string w = S(st, "world_id");
    if (DB.towers.contains(w)) return S(DB.towers[w], "name") + " Floor " + std::to_string(I(st, "number", 0));
    const Json& world = O(DB.worlds, w);
    return S(world, "name") + " " + std::to_string(I(world, "number", 1)) + "-" + std::to_string(I(st, "number", 0));
}

// ------------------------------------------------------------------ currencies & items
int GameManager::gold() const { return I(O(profile, "player"), "gold", 0); }
int GameManager::gems() const { return I(O(profile, "player"), "gems", 0); }
int GameManager::soul_shards() const { return I(O(profile, "player"), "soul_shards", 0); }

void GameManager::add_gold(int n, bool persist)
{
    profile["player"]["gold"] = std::clamp((long long)gold() + n, 0LL, 999999999LL);
    gold_changed.emit(gold());
    if (persist) save();
}

bool GameManager::spend_gold(int n, bool persist)
{
    if (n < 0 || gold() < n) return false;
    profile["player"]["gold"] = gold() - n;
    gold_changed.emit(gold());
    if (persist) save();
    return true;
}

void GameManager::add_gems(int n, bool persist)
{
    profile["player"]["gems"] = std::clamp((long long)gems() + n, 0LL, 9999999LL);
    gems_changed.emit(gems());
    if (persist) save();
}

bool GameManager::spend_gems(int n, bool persist)
{
    if (n < 0 || gems() < n) return false;
    profile["player"]["gems"] = gems() - n;
    gems_changed.emit(gems());
    if (persist) save();
    return true;
}

void GameManager::add_item(const std::string& id, int qty, bool persist)
{
    if (qty <= 0 || !DB.items.contains(id)) return;
    Json& inv = profile["inventory"];
    inv[id] = std::min(I(inv, id, 0) + qty, I(DB.progression, "inventory_stack_limit", 9999));
    if (persist) save();
}

bool GameManager::remove_item(const std::string& id, int qty, bool persist)
{
    if (item_count(id) < qty) return false;
    Json& inv = profile["inventory"];
    inv[id] = I(inv, id, 0) - qty;
    if (I(inv, id, 0) <= 0) inv.erase(id);
    if (persist) save();
    return true;
}

int GameManager::item_count(const std::string& id) const { return I(O(profile, "inventory"), id, 0); }

Json GameManager::grant(const Json& reward, bool persist)
{
    Json out = {{"gold", I(reward, "gold", 0)}, {"gems", I(reward, "gems", 0)}, {"soul_shards", I(reward, "soul_shards", 0)},
                {"items", O(reward, "items")}};
    if (I(out["gold"]) > 0) add_gold(I(out["gold"]), false);
    if (I(out["gems"]) > 0) add_gems(I(out["gems"]), false);
    if (I(out["soul_shards"]) > 0) profile["player"]["soul_shards"] = soul_shards() + I(out["soul_shards"]);
    for (auto& [id, q] : out["items"].items()) add_item(id, I(q), false);
    if (persist)
    {
        save();
        profile_changed.emit();
    }
    return out;
}

// ------------------------------------------------------------------ energy
int GameManager::max_energy() const { return SaveManager::get().max_energy_for_rank(rank()); }

// Current energy after (offline) regeneration. Clock going backwards re-anchors.
int GameManager::energy()
{
    if (profile.empty()) return 0;
    Json& pl = profile["player"];
    int cur = I(pl, "energy", 0), mx = max_energy();
    long long t = (long long)now();
    long long ts = pl.contains("energy_ts") ? (long long)F(pl["energy_ts"], (double)t) : t;
    int regen = I(DB.balance("energy", "regen_seconds"), 180);
    if (cur >= mx || ts > t || ts <= 0)
    {
        pl["energy_ts"] = t;
        pl["energy"] = std::max(cur, 0);
        return I(pl["energy"]);
    }
    int gained = int((t - ts) / regen);
    if (gained > 0)
    {
        cur = std::min(cur + gained, mx);
        pl["energy"] = cur;
        pl["energy_ts"] = cur >= mx ? t : ts + (long long)gained * regen;
    }
    return cur;
}

int GameManager::energy_seconds_to_next()
{
    int cur = energy();
    if (cur >= max_energy()) return 0;
    int regen = I(DB.balance("energy", "regen_seconds"), 180);
    return std::max(regen - int((long long)now() - (long long)F(profile["player"]["energy_ts"], now())), 0);
}

bool GameManager::spend_energy(int n)
{
    int cur = energy();
    if (cur < n) return false;
    if (cur >= max_energy()) profile["player"]["energy_ts"] = (long long)now();
    profile["player"]["energy"] = cur - n;
    save();
    energy_changed.emit(energy(), max_energy());
    return true;
}

// ------------------------------------------------------------------ progress
int GameManager::rank() const { return I(O(profile, "player"), "rank", 1); }
bool GameManager::is_stage_unlocked(const std::string& sid) const { return contains(A(O(profile, "stages"), "unlocked"), sid); }
bool GameManager::is_stage_cleared(const std::string& sid) const { return contains(A(O(profile, "stages"), "cleared"), sid); }

Json GameManager::stage_stars(const std::string& sid) const
{
    const Json& s = at(O(O(profile, "stages"), "stars"), sid);
    return s.is_array() ? s : Json::array({false, false, false});
}

int GameManager::star_count(const std::string& sid) const
{
    int n = 0;
    for (auto& b : stage_stars(sid)) n += B(b) ? 1 : 0;
    return n;
}

std::string GameManager::player_name() const { return S(O(profile, "player"), "name", "Wayfarer"); }

int GameManager::all_stars() const
{
    int n = 0;
    for (auto& w : DB.world_order) n += total_stars(w);
    return n;
}

int GameManager::total_stars(const std::string& wid) const
{
    const Json& w = DB.worlds.contains(wid) ? DB.worlds[wid] : O(DB.towers, wid);
    int n = 0;
    for (auto& st : A(w, "stages")) n += star_count(S(st, "id"));
    return n;
}

std::string GameManager::next_stage_id(const std::string& sid) const { return S(at(A(DB.stage(sid), "unlocks"), 0)); }

bool GameManager::tower_open(const std::string& tid) const
{
    std::string req = S(O(DB.towers, tid), "requires");
    return feature_unlocked("tower") && (req.empty() || is_stage_cleared(req));
}

bool GameManager::world_unlocked(const std::string& wid) const
{
    std::string req = S(O(DB.worlds, wid), "requires");
    return req.empty() || is_stage_cleared(req);
}

int GameManager::tower_highest_floor(const std::string& tid) const
{
    int best = 0;
    for (auto& fl : A(O(DB.towers, tid), "stages"))
        if (is_stage_cleared(S(fl, "id"))) best = std::max(best, I(fl, "number", 0));
    return best;
}

int GameManager::stages_cleared_count() const
{
    int n = 0;
    for (auto& s : A(O(profile, "stages"), "cleared")) n += DB.is_tower_stage(S(s)) ? 0 : 1;
    return n;
}

bool GameManager::feature_unlocked(const std::string& f) const
{
    std::string req = S(O(DB.progression, "unlocks"), f);
    return req.empty() || is_stage_cleared(req);
}

std::string GameManager::feature_unlock_label(const std::string& f) const
{
    std::string req = S(O(DB.progression, "unlocks"), f);
    if (req.empty()) return "";
    std::string l = stage_label(req);
    return "Stage " + l.substr(l.rfind(' ') + 1);
}

Json GameManager::features_unlocked_by(const std::string& sid) const
{
    Json out = Json::array();
    for (auto& [f, s] : O(DB.progression, "unlocks").items())
        if (S(s) == sid) out.push_back(f);
    return out;
}

Json GameManager::grant_unlock_gift(const std::string& sid)
{
    const Json& gifts = O(DB.progression, "unlock_gifts");
    if (!gifts.contains(sid) || contains(profile["unlocks"]["granted"], sid)) return Json::object();
    const Json& g = gifts[sid];
    Json out = grant({{"gems", I(g, "gems", 0)}, {"items", O(g, "items")}}, false);
    if (g.contains("hero_by_starter"))
    {
        std::string hero = S(O(g, "hero_by_starter"), S(profile, "starter_id"));
        if (!hero.empty() && DB.has_character(hero))
        {
            if (!owns_family(S(DB.character(hero), "family")))
            {
                out["hero_uid"] = add_unit(hero);
                out["hero"] = hero;
                if ((int)profile["party"].size() < max_party_size()) profile["party"].push_back(out["hero_uid"]);
            }
            else
            {
                out["soul_shards"] = I(O(DB.summon, "duplicate_shards"), "3", 10);
                profile["player"]["soul_shards"] = soul_shards() + I(out["soul_shards"]);
            }
        }
    }
    profile["unlocks"]["granted"].push_back(sid);
    return out;
}

void GameManager::grant_retroactive_unlocks()
{
    bool any = false;
    for (auto& [sid, g] : O(DB.progression, "unlock_gifts").items())
        if (is_stage_cleared(sid) && !contains(profile["unlocks"]["granted"], sid))
        {
            grant_unlock_gift(sid);
            any = true;
        }
    for (auto& tid : DB.tower_order)
    {
        std::string first = S(DB.towers[tid]["stages"][0], "id");
        if (tower_open(tid) && !is_stage_unlocked(first))
        {
            profile["stages"]["unlocked"].push_back(first);
            any = true;
        }
    }
    if (any) save();
}

// ------------------------------------------------------------------ battles
Json GameManager::try_start_stage(const std::string& sid)
{
    if (!is_stage_unlocked(sid)) return {{"ok", false}, {"reason", "locked"}};
    if (party_units().empty()) return {{"ok", false}, {"reason", "no_squad"}};
    if (!spend_energy(stage_energy(sid))) return {{"ok", false}, {"reason", "energy"}};
    current_stage_id = sid;
    return {{"ok", true}};
}

// Applies a won battle: hero XP, rank XP (+rewards), gold, drops, stars, first-clear
// rewards, unlocks and gifts, Burst EXP and mission progress.
Json GameManager::apply_battle_result(const std::string& sid, const Json& data)
{
    const Json& stage = DB.stage(sid);
    bool is_tower = DB.is_tower_stage(sid), first_clear = !is_stage_cleared(sid);
    const Json& rewards = O(stage, "rewards");
    int xp = I(data, "xp", 0) + I(rewards, "xp", 0);
    int gold_total = I(data, "gold", 0) + I(rewards, "gold", 0);
    Json items = O(data, "items"), first_reward = Json::object();
    if (first_clear)
    {
        gold_total += I(rewards, "first_clear_gold", 0);
        first_reward = grant(O(stage, "first_clear"), false);
    }
    Json unit_results = Json::array();
    const Json& bursts = O(data, "bursts");
    for (auto& uid : party_uids())
    {
        Json& u = unit(S(uid));
        if (u.is_null()) continue;
        Json before = {{"level", I(u, "level", 1)}, {"exp", I(u, "exp", 0)}, {"burst_level", I(u, "burst_level", 1)}};
        Json ups = Progression::add_unit_xp(u, xp);
        int bx = I(bursts, S(uid), 0) * I(DB.balance("burst_levels", "per_use"), 1);
        Json b = bx > 0 ? add_burst_xp(S(uid), bx, false) : Json::object();
        Json& u2 = unit(S(uid));
        unit_results.push_back({{"uid", uid}, {"char_id", u2["char_id"]}, {"before", before},
                                {"after", {{"level", I(u2, "level", 1)}, {"exp", I(u2, "exp", 0)}, {"burst_level", I(u2, "burst_level", 1)}}},
                                {"level_ups", ups}, {"burst_up", !b.empty() && I(b, "after", 0) > I(b, "before", 0)}});
    }
    Json rank_ups = add_rank_xp(xp);
    add_gold(gold_total, false);
    for (auto& [id, q] : items.items()) add_item(id, I(q), false);

    Json& st = profile["stages"];
    Json earned = data.contains("stars") ? data["stars"] : Json::array({true, false, false});
    Json old = stage_stars(sid);
    int new_stars = 0;
    for (int i = 0; i < 3; ++i)
    {
        bool got = B(at(earned, i));
        if (got && !B(old[i])) ++new_stars;
        old[i] = B(old[i]) || got;
    }
    st["stars"][sid] = old;
    st["clears"][sid] = I(st["clears"], sid, 0) + 1;

    Json newly = Json::array(), features = Json::array(), gift = Json::object();
    if (first_clear)
    {
        st["cleared"].push_back(sid);
        features = features_unlocked_by(sid);
        gift = grant_unlock_gift(sid);
        for (auto& tid : DB.tower_order)   // towers open with the feature; the Fracture after its "requires" stage
        {
            std::string f0 = S(DB.towers[tid]["stages"][0], "id");
            if (tower_open(tid) && !contains(st["unlocked"], f0)) st["unlocked"].push_back(f0);
        }
        if (contains(features, "world2"))
            for (auto& w : DB.world_order)
                if (S(DB.worlds[w], "requires") == sid)
                {
                    std::string s0 = S(DB.worlds[w]["stages"][0], "id");
                    if (!contains(st["unlocked"], s0))
                    {
                        st["unlocked"].push_back(s0);
                        newly.push_back(s0);
                    }
                }
    }
    for (auto& nx : A(stage, "unlocks"))
        if (!contains(st["unlocked"], nx))
        {
            st["unlocked"].push_back(nx);
            newly.push_back(nx);
        }
    if (!newly.empty()) last_unlocked_stage = S(newly[0]);

    Json& stats = profile["stats"];
    stats["battles_won"] = I(stats, "battles_won", 0) + 1;
    stats["enemies_defeated"] = I(stats, "enemies_defeated", 0) + I(data, "enemies_defeated", 0);
    stats["bosses_defeated"] = I(stats, "bosses_defeated", 0) + I(data, "bosses_defeated", 0);
    track("stage_clear", 1, false);
    if (is_tower) track("tower_clear", 1, false);
    track("enemy_kill", I(data, "enemies_defeated", 0), false);
    track("boss_kill", I(data, "bosses_defeated", 0), false);
    int total_bursts = 0;
    for (auto& [k, v] : bursts.items()) total_bursts += I(v);
    track("burst_use", total_bursts, false);
    save();
    profile_changed.emit();
    return {{"xp", xp},
            {"gold", gold_total},
            {"items", items},
            {"units", unit_results},
            {"first_clear", first_clear},
            {"first_clear_gold", first_clear ? I(rewards, "first_clear_gold", 0) : 0},
            {"first_clear_reward", first_reward},
            {"unlocked", newly},
            {"rank_before", rank_ups["before"]},
            {"rank_after", rank()},
            {"rank_ups", rank_ups["ups"]},
            {"stars", old},
            {"stars_this_run", earned},
            {"new_stars", new_stars},
            {"features", features},
            {"gift", gift},
            {"tower", is_tower}};
}

Json GameManager::add_rank_xp(int xp)
{
    Json& pl = profile["player"];
    int before = I(pl, "rank", 1);
    Json ups = Json::array();
    pl["rank_xp"] = I(pl, "rank_xp", 0) + xp;
    while (I(pl, "rank", 1) < I(DB.progression, "rank_max", 99) && I(pl, "rank_xp", 0) >= Progression::rank_xp_to_next(I(pl, "rank", 1)))
    {
        pl["rank_xp"] = I(pl, "rank_xp", 0) - Progression::rank_xp_to_next(I(pl, "rank", 1));
        int old_max = max_energy();
        pl["rank"] = I(pl, "rank", 1) + 1;
        int new_max = max_energy();
        energy();
        pl["energy"] = std::max(I(pl, "energy", 0), new_max);
        pl["energy_ts"] = (long long)now();
        int gems_gain = 0;
        const Json& rr = O(DB.progression, "rank_rewards");
        if (I(pl, "rank", 1) % std::max(I(rr, "gems_every", 5), 1) == 0)
        {
            gems_gain = I(rr, "gems", 50);
            add_gems(gems_gain, false);
        }
        ups.push_back({{"rank", I(pl, "rank", 1)}, {"energy_max_up", new_max - old_max}, {"gems", gems_gain}});
    }
    return {{"before", before}, {"ups", ups}};
}

void GameManager::record_defeat()
{
    profile["stats"]["battles_lost"] = I(profile["stats"], "battles_lost", 0) + 1;
    save();
}

// ------------------------------------------------------------------ summoning
Json GameManager::summon_banner(const std::string& id) const { return O(O(DB.summon, "banners"), id); }

// Results are committed and saved BEFORE any animation plays.
Json GameManager::summon(const std::string& banner_id, int count)
{
    Json b = summon_banner(banner_id);
    if (b.empty()) return {{"ok", false}, {"reason", "Unknown banner."}};
    if (!feature_unlocked("summon"))
        return {{"ok", false}, {"reason", "Summoning unlocks after clearing " + feature_unlock_label("summon") + "."}};
    int cost = count == 1 ? I(b, "single_cost", 100) : I(b, "multi_cost", 1000);
    if (!spend_gems(cost, false)) return {{"ok", false}, {"reason", "Not enough Gems."}};
    Json results = Json::array();
    for (int i = 0; i < count; ++i)
    {
        std::string cid = SummonSystem::roll(b, rng);
        const Json& def = DB.character(cid);
        Json e = {{"char_id", cid}, {"rarity", I(def, "rarity", 3)}, {"is_new", false}, {"uid", ""}, {"shards", 0}};
        if (owns_family(S(def, "family", cid)))
        {
            e["shards"] = I(O(DB.summon, "duplicate_shards"), std::to_string(I(e["rarity"])), 10);
            profile["player"]["soul_shards"] = soul_shards() + I(e["shards"]);
        }
        else
        {
            e["is_new"] = true;
            e["uid"] = add_unit(cid);
        }
        results.push_back(e);
        profile["summon"]["history"].push_back({{"id", cid}, {"r", e["rarity"]}, {"new", e["is_new"]}, {"shards", e["shards"]},
                                                {"t", (long long)now()}});
    }
    Json& hist = profile["summon"]["history"];
    if (hist.size() > 100) hist.erase(hist.begin(), hist.begin() + (hist.size() - 100));
    profile["summon"]["total"] = I(profile["summon"], "total", 0) + count;
    profile["stats"]["summons"] = I(profile["stats"], "summons", 0) + count;
    track("summon", count, false);
    save();
    profile_changed.emit();
    return {{"ok", true}, {"results", results}, {"cost", cost}};
}

// ------------------------------------------------------------------ missions
std::string GameManager::date_key() const
{
    time_t t = (time_t)now() + Platform::tzBiasMinutes() * 60;
    std::tm tm = *std::gmtime(&t);
    char buf[32];
    std::snprintf(buf, sizeof buf, "%04d-%02d-%02d", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday);
    return buf;
}

std::string GameManager::week_key() const
{
    long long days = ((long long)now() + Platform::tzBiasMinutes() * 60) / 86400;
    return "w" + std::to_string((days + 3) / 7);   // weeks start on Monday
}

void GameManager::refresh_missions()
{
    if (profile.empty()) return;
    Json& m = profile["missions"];
    if (S(m, "daily_key") != date_key())
    {
        m["daily_key"] = date_key();
        m["daily"] = Json::object();
        m["daily_claimed"] = Json::array();
        m["chest_claimed"] = false;
    }
    if (S(m, "weekly_key") != week_key())
    {
        m["weekly_key"] = week_key();
        m["weekly"] = Json::object();
        m["weekly_claimed"] = Json::array();
    }
}

void GameManager::track(const std::string& event, int amount, bool persist)
{
    if (profile.empty() || amount <= 0) return;
    refresh_missions();
    Json& m = profile["missions"];
    for (auto kind : {"daily", "weekly"})
        for (auto& mi : A(DB.missions, kind))
            if (S(mi, "event") == event)
                m[kind][S(mi, "id")] = std::min(I(m[kind], S(mi, "id"), 0) + amount, I(mi, "target", 1));
    if (persist) save();
}

int GameManager::mission_progress(const std::string& kind, const Json& mission)
{
    refresh_missions();
    return I(profile["missions"][kind], S(mission, "id"), 0);
}

bool GameManager::mission_claimed(const std::string& kind, const std::string& id) const
{
    return contains(A(O(profile, "missions"), kind + "_claimed"), id);
}

Json GameManager::claim_mission(const std::string& kind, const std::string& id)
{
    refresh_missions();
    for (auto& m : A(DB.missions, kind))
        if (S(m, "id") == id)
        {
            if (mission_claimed(kind, id) || mission_progress(kind, m) < I(m, "target", 1)) return Json::object();
            profile["missions"][kind + "_claimed"].push_back(id);
            Json r = grant(O(m, "reward"), false);
            save();
            profile_changed.emit();
            return r;
        }
    return Json::object();
}

void GameManager::merge_reward(Json& total, const Json& r)
{
    if (r.empty()) return;
    total["count"] = I(total, "count", 0) + 1;
    for (auto k : {"gold", "gems", "soul_shards"}) total[k] = I(total, k, 0) + I(r, k, 0);
    for (auto& [id, q] : O(r, "items").items()) total["items"][id] = I(total["items"], id, 0) + I(q);
}

Json GameManager::claim_all_missions()
{
    Json total = {{"gold", 0}, {"gems", 0}, {"soul_shards", 0}, {"items", Json::object()}, {"count", 0}};
    for (auto kind : {"daily", "weekly"})
        for (auto& m : A(DB.missions, kind))
            if (!mission_claimed(kind, S(m, "id")) && mission_progress(kind, m) >= I(m, "target", 1))
                merge_reward(total, claim_mission(kind, S(m, "id")));
    if (can_claim_chest()) merge_reward(total, claim_chest());
    return total;
}

int GameManager::daily_completed() const { return (int)A(O(profile, "missions"), "daily_claimed").size(); }

bool GameManager::can_claim_chest()
{
    refresh_missions();
    return !B(profile["missions"], "chest_claimed", false) && daily_completed() >= I(O(DB.missions, "daily_chest"), "needed", 4);
}

Json GameManager::claim_chest()
{
    if (!can_claim_chest()) return Json::object();
    profile["missions"]["chest_claimed"] = true;
    Json r = grant(O(O(DB.missions, "daily_chest"), "reward"), false);
    save();
    profile_changed.emit();
    return r;
}

int GameManager::missions_claimable()
{
    if (!feature_unlocked("missions")) return 0;
    refresh_missions();
    int n = 0;
    for (auto kind : {"daily", "weekly"})
        for (auto& m : A(DB.missions, kind))
            if (!mission_claimed(kind, S(m, "id")) && mission_progress(kind, m) >= I(m, "target", 1)) ++n;
    return n + (can_claim_chest() ? 1 : 0);
}

bool GameManager::login_available() const { return has_profile() && S(O(profile, "login"), "last_date") != date_key(); }

int GameManager::login_day_index() const
{
    return I(O(profile, "login"), "day_index", 0) % std::max((int)A(DB.login_rewards, "cycle").size(), 1);
}

Json GameManager::claim_login()
{
    if (!login_available()) return Json::object();
    const Json& cycle = A(DB.login_rewards, "cycle");
    if (cycle.empty()) return Json::object();
    int idx = login_day_index();
    Json r = grant(O(cycle[idx], "reward"), false);
    Json& lg = profile["login"];
    lg["last_date"] = date_key();
    lg["day_index"] = I(lg, "day_index", 0) + 1;
    lg["total"] = I(lg, "total", 0) + 1;
    save();
    profile_changed.emit();
    r["day"] = idx + 1;
    return r;
}

// ------------------------------------------------------------------ notifications & tutorial
bool GameManager::units_badge()
{
    for (auto& u : units())
        if (B(u, "new", false)) return true;
    if (feature_unlocked("evolution"))
        for (auto& uid : party_uids())
            if (can_evolve(S(uid))) return true;
    return false;
}

bool GameManager::summon_badge() const { return feature_unlocked("summon") && !B(O(profile, "summon"), "seen", false); }

void GameManager::mark_summon_seen()
{
    if (!B(profile["summon"], "seen", false))
    {
        profile["summon"]["seen"] = true;
        save();
    }
}

bool GameManager::hint_seen(const std::string& id) const { return contains(A(O(profile, "tutorial"), "hints_seen"), id); }

void GameManager::mark_hint_seen(const std::string& id)
{
    if (id.empty() || hint_seen(id)) return;
    profile["tutorial"]["hints_seen"].push_back(id);
    save();
}

bool GameManager::coach_done(const std::string& id) const { return contains(A(O(profile, "tutorial"), "coach_done"), id); }

void GameManager::mark_coach_done(const std::string& id)
{
    if (id.empty() || coach_done(id) || !profile.contains("tutorial")) return;
    profile["tutorial"]["coach_done"].push_back(id);
    save();
}

void GameManager::reset_tutorial()
{
    if (!profile.contains("tutorial")) return;
    profile["tutorial"]["hints_seen"] = Json::array();
    profile["tutorial"]["coach_done"] = Json::array();
    save();
}

void GameManager::mark_intro_seen()
{
    profile["tutorial"]["intro_seen"] = true;
    save();
}

bool GameManager::feature_announced(const std::string& f) const { return contains(A(O(profile, "unlocks"), "announced"), f); }

void GameManager::mark_feature_announced(const std::string& f)
{
    if (feature_announced(f)) return;
    profile["unlocks"]["announced"].push_back(f);
    save();
}

static std::string trim(std::string s)
{
    s.erase(0, s.find_first_not_of(" \t\r\n"));
    s.erase(s.find_last_not_of(" \t\r\n") + 1);
    return s;
}

std::string GameManager::validate_player_name(std::string n)
{
    n = trim(n);
    if (n.size() < 2) return "Use at least 2 characters.";
    if (n.size() > 16) return "Use at most 16 characters.";
    if (!std::regex_match(n, std::regex("^[A-Za-z0-9 _'\\-]+$"))) return "Letters, numbers, spaces, - ' and _ only.";
    if (n.find("  ") != std::string::npos) return "Avoid double spaces.";
    return "";
}

void GameManager::set_player_name(std::string n)
{
    n = trim(n).substr(0, 16);
    if (!validate_player_name(n).empty()) return;
    profile["player"]["name"] = n;
    save();
    profile_changed.emit();
}

void GameManager::set_setting(const std::string& key, const Json& value)
{
    settings[key] = value;
    SaveManager::get().save_settings(settings);
    settings_changed.emit();
}
